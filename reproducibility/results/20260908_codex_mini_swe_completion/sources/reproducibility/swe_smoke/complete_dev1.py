"""Prospective completion/recovery of the eight unavailable SWE development cells.

The original generation archive is read-only. A previously started cell is
explicitly a fresh recovery attempt, never a repaired first attempt.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

from .. import codex_subscription as c
from ..benchmark_bridge import _extract_fenced_block
from ..record_codex_runtime import capture

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'reproducibility/runs/swe-smoke-dev1/generation'
TASKS = ROOT / 'reproducibility/runs/swe-smoke-dev1/retrieval/runner-v2/tasks.jsonl'
PROTOCOL = ROOT / 'reproducibility/revision/SWE_COMPLETION_PROTOCOL.md'
DEPENDENCIES = [Path(__file__), Path(c.__file__), ROOT / 'reproducibility/factorial_runner.py',
                ROOT / 'reproducibility/benchmark_bridge.py',
                ROOT / 'reproducibility/record_codex_runtime.py',
                ROOT / 'reproducibility/swe_smoke/evaluate_predictions.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(original):
    m = c.read(original / 'manifest.json')
    if c.read(original / 'status.json')['state'] not in ('completed', 'blocked'):
        raise ValueError('Original run must be terminal')
    result = []
    for cell in m['cells']:
        turns = sorted((original / 'turns').glob(cell['id'] + '-*'))
        complete = (original / 'cells' / (cell['id'] + '.json')).is_file()
        result.append({**cell, 'original_status': 'completed' if complete else 'started_incomplete' if turns else 'never_submitted',
                       'original_turns': [t.name for t in turns]})
    return result


def plan():
    inv = inventory(ORIGINAL)
    if len(inv) != 10 or sum(x['original_status'] == 'completed' for x in inv) != 2:
        raise ValueError('Expected the original two-complete ten-cell allocation')
    selected = [x for x in inv if x['original_status'] != 'completed']
    p = {'schema': 'swe-dev1-completion-v1', 'original_inventory': inv, 'cells': selected,
         'original_tree': {str(x.relative_to(ORIGINAL).as_posix()): sha(x) for x in sorted(ORIGINAL.rglob('*')) if x.is_file()},
         'tasks_sha256': sha(TASKS), 'protocol_sha256_lf': hashlib.sha256(PROTOCOL.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
         'source_sha256_lf': {str(x.relative_to(ROOT).as_posix()): hashlib.sha256(x.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for x in DEPENDENCIES},
         'timeout_seconds': 600, 'workers': 2, 'planned_candidates': 8,
         'planned_turns': sum(x['cli_turns'] for x in selected),
         'retry_policy': 'One new full attempt per unavailable assignment; prior started attempt retained separately; no outcome-based repair',
         'budget_stop_known_api_equivalent_usd': 10.0,
         'model_requested': c.MODEL, 'reasoning_effort': 'medium', 'cli_version': c.CLI_VERSION}
    return {**p, 'manifest_sha256': c.digest(p)}


def run(manifest, out, npm_root):
    p = c.read(manifest)
    if p != plan():
        raise ValueError('Frozen completion plan or original evidence changed')
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    c.save(out / 'manifest.json', p)
    (out / 'tasks.jsonl').write_bytes(TASKS.read_bytes())
    (out / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    for src in DEPENDENCIES:
        dst = out / 'sources' / src.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes().replace(b'\r\n', b'\n'))
    tasks = c.tasks_from(TASKS)
    env = os.environ.copy()
    env['CODEX_STUDY_CLI_JS'] = str(npm_root.resolve() / 'node_modules/@openai/codex/bin/codex.js')
    c.save(out / 'status.json', {'state': 'started', 'started_unix': time.time()})

    def one(cell):
        cid = cell['id']
        inp = out / 'inputs' / cid
        inp.mkdir(parents=True)
        single = c.make_manifest(tasks, [cell['replicate_id']], [cell['arm']])
        c.save(inp / 'manifest.json', single)
        archive = out / 'generation' / cid
        argv = [sys.executable, '-m', 'reproducibility.codex_subscription', 'run', '--tasks', str(out / 'tasks.jsonl'),
                '--manifest', str(inp / 'manifest.json'), '--archive', str(archive), '--workers', '1', '--timeout', '600']
        c.save(inp / 'argv.json', argv)
        with (inp / 'stdout.log').open('wb') as stdout, (inp / 'stderr.log').open('wb') as stderr:
            proc = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr)
        if (archive / 'runtime.json').exists():
            capture(archive, npm_root, Path(c.__file__))
        record = {'cell': cell, 'returncode': proc.returncode, 'attempt_type': 'recovery_after_started_failure' if cell['original_status'] == 'started_incomplete' else 'first_submission_after_stop'}
        result = archive / 'cells' / (cid + '.json')
        if result.exists():
            row = c.read(result)
            patch, valid = _extract_fenced_block(row['final_text'], 'swebench')
            label = f"completion-{cell['arm']}--r{cell['replicate_id']}"
            pred = out / 'predictions' / (cid + '.jsonl')
            pred.parent.mkdir(parents=True, exist_ok=True)
            pred.write_bytes(c.canonical({'instance_id': cell['task_id'], 'model_name_or_path': label, 'model_patch': patch}) + b'\n')
            record.update({'generation_complete': True, 'format_valid': valid, 'generation_source_sha256': sha(result),
                           'prediction_sha256': sha(pred), 'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
                           'api_equivalent_usd': row['api_equivalent_usd']})
        else:
            record['generation_complete'] = False
        c.save(inp / 'completion.json', record)
        print(c.canonical({'cell': cid, 'generation_complete': record['generation_complete']}).decode(), flush=True)
        return record

    records = []
    # Small fixed waves ensure each cell is attempted despite another cell failure.
    for start in range(0, len(p['cells']), 2):
        if sum(r.get('api_equivalent_usd', 0) for r in records) >= 10:
            break
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(one, cell) for cell in p['cells'][start:start+2]]
            for f in as_completed(futures):
                records.append(f.result())
                c.save(out / 'progress.json', records)
    c.save(out / 'status.json', {'state': 'completed' if len(records) == 8 and all(x['generation_complete'] for x in records) else 'incomplete',
                               'completed_unix': time.time(), 'records': records})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze', 'run'])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--npm-root', type=Path, default=ROOT / 'tmp/codex-runtime')
    a = parser.parse_args()
    if a.command == 'freeze':
        if a.manifest.exists():
            raise ValueError('Refusing to overwrite frozen plan')
        c.save(a.manifest, plan())
    else:
        run(a.manifest, a.out, a.npm_root)


if __name__ == '__main__':
    main()
