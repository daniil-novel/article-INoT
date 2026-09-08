"""Frozen single-call dispatch with complete, separately retained failure traces."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path
import random
import subprocess
import time

from .. import codex_subscription as c
from .prepare import ARM_NAMES

ROOT = Path(__file__).resolve().parents[2]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def full_prompt(row):
    text = 'TASK\n' + row['prompt'] + '\nFULL SUPPLIED CONTEXT\n' + row['context']
    if len(text.encode('utf-8')) > 65536:
        raise ValueError('Full input exceeds 65536-byte guard; no compression')
    return text


def plan(inputs, gate):
    selection = c.read(inputs / 'selection.json')
    g = c.read(gate)
    ids = selection['assigned_task_ids']
    if len(ids) != 80 or g['assigned_task_ids'] != ids or g['controls_complete'] is not True:
        raise ValueError('All 80 control attempts must precede generation')
    rows = {arm: c.tasks_from(inputs / 'input' / (arm + '.jsonl')) for arm in ARM_NAMES}
    by_arm = {arm: {t['task_id']: t for t in ts} for arm, ts in rows.items()}
    if any(set(v) != set(ids) for v in by_arm.values()):
        raise ValueError('Arm assignment mismatch')
    rng = random.Random(20260908)
    order = ids.copy()
    rng.shuffle(order)
    cells = []
    for tid in order:
        arms = list(ARM_NAMES)
        rng.shuffle(arms)
        for arm in arms:
            cell = {'task_id': tid, 'arm': arm, 'replicate_id': 1, 'cli_turns': 1}
            cells.append({**cell, 'id': c.digest(cell)[:24], 'prompt_sha256': hashlib.sha256(full_prompt(by_arm[arm][tid]).encode()).hexdigest()})
    sources = [Path(__file__), Path(c.__file__), ROOT/'reproducibility/segregation80/prepare.py',
               ROOT/'reproducibility/segregation80/analyze.py', ROOT/'reproducibility/benchmark_bridge.py']
    p = {'schema': 'segregation80-generation-v1', 'cells': cells, 'assigned_task_ids': ids,
         'planned_candidates': 320, 'model_requested': c.MODEL, 'reasoning_effort': 'medium', 'cli_version': c.CLI_VERSION,
         'inputs_sha256': {str(f.relative_to(inputs).as_posix()): sha(f) for f in sorted(inputs.rglob('*')) if f.is_file()},
         'control_gate_sha256': sha(gate), 'controls': g,
         'source_sha256_lf': {str(f.relative_to(ROOT).as_posix()): hashlib.sha256(f.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for f in sources},
         'protocol_sha256_lf': hashlib.sha256((Path(__file__).parent/'PROTOCOL.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
         'workers': 4, 'timeout_seconds': 600, 'order_seed': 20260908,
         'provider_seed_controlled': False, 'known_usage_planning_stop_usd': 25,
         'price_per_million': c.PRICES, 'pricing_source': c.PRICING_URL,
         'retry_policy': 'none; failed cell retained; unrelated assignments continue except authentication/quota failure'}
    return {**p, 'manifest_sha256': c.digest(p)}


def run(inputs, gate, manifest, out):
    p = c.read(manifest)
    if p != plan(inputs, gate):
        raise ValueError('Frozen sources, inputs or gate changed')
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    c.save(out/'manifest.json',p)
    prefix = c.resolved_prefix()
    version = subprocess.check_output(prefix+['--version'], text=True).strip()
    if version != c.CLI_VERSION:
        raise ValueError('Frozen CLI version mismatch')
    auth = subprocess.run(prefix+['login','status'],capture_output=True,text=True)
    if auth.returncode or 'ChatGPT' not in auth.stdout+auth.stderr:
        raise ValueError('Subscription login required')
    cwd = out/'empty'
    cwd.mkdir()
    instructions = out/'instructions.txt'
    instructions.write_bytes(c.BASE.encode())
    command = c.cli_command(prefix,cwd,instructions)
    c.save(out/'runtime.json', {'version':version,'prefix':prefix,'authentication':'chatgpt','workers':4,'timeout_seconds':600,'started_unix':time.time()})
    for rel in p['source_sha256_lf']:
        target=out/'sources'/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/rel).read_bytes().replace(b'\r\n',b'\n'))
    by_arm={arm:{r['task_id']:r for r in c.tasks_from(inputs/'input'/(arm+'.jsonl'))} for arm in ARM_NAMES}
    c.save(out/'status.json',{'state':'started','started_unix':time.time()})

    def one(cell):
        prompt=full_prompt(by_arm[cell['arm']][cell['task_id']])
        record={**cell,'generation_complete':False}
        try:
            result=c.archive_turn(out/'turns'/cell['id'],command,prompt,600)
            record.update(result)
            record['generation_complete']=True
            record['total_tokens']=result['usage']['input_tokens']+result['usage']['output_tokens']
        except Exception as exc:
            record['failure_reason']=str(exc)
            eventfile=out/'turns'/cell['id']/'events.jsonl'
            if eventfile.exists():
                # Late usage is still charged to the ledger, never an on-time candidate.
                import json
                for line in eventfile.read_text(encoding='utf-8',errors='replace').splitlines():
                    try:
                        event=json.loads(line)
                        if event.get('type')=='turn.completed':
                            record['interrupted_usage']=event['usage']
                    except (ValueError,KeyError):
                        pass
        c.save(out/'cells'/(cell['id']+'.json'),record)
        return record

    records=[]
    stop=None
    for start in range(0,len(p['cells']),4):
        if sum(c.value_usage(r.get('usage',r.get('interrupted_usage',{'input_tokens':0,'cached_input_tokens':0,'output_tokens':0}))) for r in records)>=25:
            stop='known usage planning limit';break
        with ThreadPoolExecutor(max_workers=4) as pool:
            for future in as_completed([pool.submit(one,cell) for cell in p['cells'][start:start+4]]):
                record=future.result();records.append(record)
                print(c.canonical({'completed':len(records),'arm':record['arm'],'task':record['task_id'],'ok':record['generation_complete']}).decode(),flush=True)
                c.save(out/'progress.json',{'attempted':len(records),'complete':sum(r['generation_complete'] for r in records)})
                if not record['generation_complete']:
                    turn=out/'turns'/record['id']
                    raw='\n'.join(f.read_text(encoding='utf-8',errors='replace') for f in (turn/'stderr.txt',turn/'events.jsonl') if f.exists()).lower()
                    if any(s in raw for s in ('usage_limit_reached','usage limit','rate_limit_exceeded','unauthorized','authentication failed')):
                        stop='subscription access failure'
        if stop:break
    (out/'results.jsonl').write_bytes(b''.join(c.canonical(r)+b'\n' for r in sorted(records,key=lambda r:r['id'])))
    c.save(out/'status.json',{'state':'completed' if len(records)==320 and all(r['generation_complete'] for r in records) else 'incomplete',
                            'attempted':len(records),'complete':sum(r['generation_complete'] for r in records),'stop_reason':stop,'finished_unix':time.time()})


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['freeze','run'])
    for name in ('inputs','gate','manifest'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.command=='freeze':
        if a.manifest.exists():raise ValueError('Frozen manifest exists')
        c.save(a.manifest,plan(a.inputs,a.gate))
    else:run(a.inputs,a.gate,a.manifest,a.out)


if __name__=='__main__':main()
