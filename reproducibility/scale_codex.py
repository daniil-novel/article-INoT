"""Run predeclared disjoint shards with the unchanged, audited subscription runner."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import codex_subscription as c
from .audit_codex_pilot import audit, inventory_attempt
from .record_codex_runtime import capture


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def plan(tasks, gate, gate_sha):
    ids = [t['task_id'] for t in tasks]
    if len(ids) != 40 or len(set(ids)) != 40:
        raise ValueError('The development scale stage requires all 40 distinct assigned tasks')
    if gate.get('assigned_task_ids') != ids or gate.get('controls_complete') is not True:
        raise ValueError('Complete gold/negative controls for the exact ordered assignment are required')
    eligible = gate.get('evaluable_task_ids')
    if not isinstance(eligible, list) or not eligible or not set(eligible).issubset(ids):
        raise ValueError('Control-derived eligibility must be explicit and nonempty')
    # Index-based partitions retain every task, including unavailable controls.
    shards = []
    for replicate in (2, 3):
        for partition in range(4):
            selected = tasks[partition::4]
            m = c.make_manifest(selected, [replicate], list(c.ARMS))
            shards.append({'name': f'r{replicate}-s{partition}', 'replicate': replicate,
                           'task_ids': [t['task_id'] for t in selected], 'manifest': m})
    p = {'schema': 'codex-development-scale-v1', 'source_sha256_lf': source_hash(),
         'runner_source_sha256_lf': c.source_hash(), 'tasks_sha256': c.digest(tasks),
         'control_gate_sha256': gate_sha, 'assigned_task_ids': ids,
         'evaluable_task_ids': eligible, 'replicate_ids': [2, 3],
         'shards_per_wave': 4, 'workers_per_shard': 2, 'max_cli_processes': 8,
         'planned_generations': 400, 'planned_cli_turns': 720, 'shards': shards,
         'stop_rule': 'No retry; finish the current wave on a shard failure and do not start the next wave',
         'cost_semantics': 'API-equivalent valuation, not subscription charges',
         'inference': 'Development; task is the independent cluster; provider seeds are not controlled'}
    return {**p, 'manifest_sha256': c.digest(p)}


def run(tasks_path, gate_path, manifest_path, archive, npm_root):
    tasks = c.tasks_from(tasks_path)
    gate = c.read(gate_path)
    p = c.read(manifest_path)
    if p != plan(tasks, gate, sha(gate_path)):
        raise ValueError('Frozen plan, controls, tasks or implementation changed')
    archive = archive.resolve()
    archive.mkdir(parents=True, exist_ok=False)
    c.save(archive / 'manifest.json', p)
    c.save(archive / 'tasks.json', tasks)
    (archive / 'control-gate.json').write_bytes(gate_path.read_bytes())
    (archive / 'orchestrator_source.py').write_bytes(Path(__file__).read_bytes().replace(b'\r\n', b'\n'))
    c.save(archive / 'status.json', {'state': 'started', 'started_unix': time.time()})
    taskmap = {t['task_id']: t for t in tasks}
    env = os.environ.copy()
    env['CODEX_STUDY_CLI_JS'] = str(npm_root.resolve() / 'node_modules/@openai/codex/bin/codex.js')
    reports = []

    def shard_run(shard):
        name = shard['name']
        inputs = archive / 'inputs' / name
        inputs.mkdir(parents=True)
        inputs.joinpath('tasks.jsonl').write_bytes(b''.join(c.canonical(taskmap[k]) + b'\n' for k in shard['task_ids']))
        c.save(inputs / 'manifest.json', shard['manifest'])
        out = archive / 'shards' / name
        command = [sys.executable, '-m', 'reproducibility.codex_subscription', 'run',
                   '--tasks', str(inputs / 'tasks.jsonl'), '--manifest', str(inputs / 'manifest.json'),
                   '--archive', str(out), '--workers', '2', '--timeout', '180']
        c.save(inputs / 'command.json', command)
        with (inputs / 'stdout.log').open('wb') as stdout, (inputs / 'stderr.log').open('wb') as stderr:
            result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr, check=False)
        report = {'shard': name, 'returncode': result.returncode, 'state': 'blocked'}
        if (out / 'runtime.json').exists():
            # Capture metadata even for a failed matrix; do not hide its submitted turns.
            capture(out, npm_root, Path(c.__file__))
        if (out / 'status.json').exists() and (out / 'turns').exists():
            report['attempt_inventory'] = inventory_attempt(out)
        if result.returncode == 0:
            checked = audit(out)
            # The v2 audit's legacy prose describes a single replicate ID per shard.
            checked['replicate_ids'] = [shard['replicate']]
            checked['replicate_semantics'] = 'one labelled repeat per shard; no controlled model seed'
            c.save(out / 'audit.json', checked)
            report.update({'state': 'completed', 'audit': checked})
        c.save(inputs / 'completion.json', report)
        return report

    for replicate in p['replicate_ids']:
        wave = [s for s in p['shards'] if s['replicate'] == replicate]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(shard_run, s): s['name'] for s in wave}
            for future in as_completed(futures):
                try:
                    report = future.result()
                except Exception as exc:
                    report = {'shard': futures[future], 'state': 'blocked', 'reason': str(exc)}
                reports.append(report)
                c.save(archive / 'progress.json', {'reports': reports})
                print(json.dumps({'shard': report['shard'], 'state': report['state']}), flush=True)
        if any(r['state'] != 'completed' for r in reports):
            break
    complete = len(reports) == len(p['shards']) and all(r['state'] == 'completed' for r in reports)
    status = {'state': 'completed' if complete else 'blocked', 'completed_unix': time.time(),
              'planned_shards': len(p['shards']), 'finished_shards': len(reports),
              'completed_shards': sum(r['state'] == 'completed' for r in reports)}
    c.save(archive / 'status.json', status)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'run'))
    parser.add_argument('--tasks', required=True, type=Path)
    parser.add_argument('--gate', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--npm-root', type=Path, default=Path('tmp/codex-runtime'))
    a = parser.parse_args()
    if a.command == 'plan':
        if a.manifest.exists():
            raise ValueError('Refuse to overwrite a frozen plan')
        c.save(a.manifest, plan(c.tasks_from(a.tasks), c.read(a.gate), sha(a.gate)))
    else:
        if a.archive is None:
            parser.error('--archive is required to run')
        status = run(a.tasks, a.gate, a.manifest, a.archive, a.npm_root)
        print(json.dumps(status))
        if status['state'] != 'completed':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
