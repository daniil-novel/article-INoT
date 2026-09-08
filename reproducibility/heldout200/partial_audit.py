"""Strict provenance reconciliation for terminal original and continuation archives."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from .. import codex_subscription as c


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observed_usage(raw):
    """Cost accounting is independent of treatment validity; truncated usage is unknown."""
    events=[]
    for line in raw.splitlines():
        try:
            value=json.loads(line)
            if isinstance(value,dict):events.append(value)
        except (ValueError,UnicodeDecodeError):
            continue
    completed=[e for e in events if e.get('type')=='turn.completed']
    if len(completed)!=1:return None
    usage=completed[0].get('usage')
    if not isinstance(usage,dict):return None
    if any(type(usage.get(k)) is not int or usage[k]<0 for k in ('input_tokens','cached_input_tokens','output_tokens')):
        raise ValueError('Malformed usage counter')
    if usage['cached_input_tokens']>usage['input_tokens']:raise ValueError('Invalid cached input subset')
    return usage


def audit_shard(shard, expected_manifest, tasks, allowed_cells=None):
    manifest=c.read(shard/'manifest.json')
    if manifest!=expected_manifest:raise ValueError('Shard manifest changed')
    saved_tasks=c.read(shard/'tasks.json')
    if manifest!=c.make_manifest(saved_tasks,manifest['replicate_ids'],manifest['arms']):
        raise ValueError('Frozen source or shard task manifest changed')
    taskmap={t['task_id']:t for t in tasks}
    if saved_tasks!=sorted([taskmap[t['task_id']] for t in saved_tasks],key=lambda t:t['task_id']):
        raise ValueError('Shard tasks differ from root inputs')
    state=c.read(shard/'status.json')
    if state.get('state') not in ('completed','blocked'):raise ValueError('Wait for terminal shard')
    runtime=c.read(shard/'runtime.json');provenance=c.read(shard/'runtime_provenance.json')
    if runtime.get('version')!=c.CLI_VERSION or runtime.get('authentication')!='chatgpt' or runtime.get('workers')!=2 or runtime.get('timeout_seconds')!=180:
        raise ValueError('Runtime settings differ')
    if provenance.get('cli_version')!=runtime['version'] or provenance.get('prefix')!=runtime['prefix'] or provenance.get('package_version')!='0.153.4' or not provenance.get('native_executable_sha256'):
        raise ValueError('Runtime identity differs')
    if (shard/'instructions.txt').read_bytes()!=c.BASE.encode() or provenance.get('instructions_sha256')!=sha256(shard/'instructions.txt'):
        raise ValueError('Loaded instructions changed')
    if sha256(shard/'npm-package-lock.json')!=provenance.get('npm_lock_sha256') or sha256(shard/'runner_source.py')!=manifest['source_sha256_lf']:
        raise ValueError('Archived runtime source changed')
    argv=c.cli_command(runtime['prefix'],provenance['empty_working_directory'],provenance['instructions_path'])
    cells={x['id']:x for x in manifest['cells']}
    allowed=set(cells) if allowed_cells is None else set(allowed_cells)
    if not allowed.issubset(cells):raise ValueError('Dispatch outside frozen assignment')
    rows=[json.loads(line) for line in (shard/'results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    rowmap={r['id']:r for r in rows}
    files={f.stem:c.read(f) for f in (shard/'cells').glob('*.json')}
    if len(rowmap)!=len(rows) or files!=rowmap or not set(rowmap).issubset(allowed):
        raise ValueError('Duplicate, unauthorized or inconsistent result cell files')
    actual={p.name for p in (shard/'turns').iterdir()}
    permitted={f"{cid}-{stage}" for cid in allowed for stage in range(cells[cid]['cli_turns'])}
    if not actual.issubset(permitted):raise ValueError('Unexpected or orphan turn artifact')
    valid=[];inventory=[];availability={cid:'never_started' for cid in cells}
    for cid,cell in cells.items():
        stages=[s for s in range(cell['cli_turns']) if f'{cid}-{s}' in actual]
        if not stages:
            if cid in rowmap:raise ValueError('Cell result without submitted turns')
            continue
        if stages!=list(range(len(stages))):raise ValueError('Submitted stage after missing predecessor')
        availability[cid]='submitted_incomplete';parts=[];history=[];failed=False
        for stage in stages:
            folder=shard/'turns'/f'{cid}-{stage}'
            if failed:raise ValueError('Submitted a new stage after an invalid predecessor')
            if (folder/'prompt.txt').read_bytes()!=c.prompt_for(taskmap[cell['task_id']],cell,stage,history).encode():
                raise ValueError('Prompt bytes or complete history changed')
            if c.read(folder/'argv.json')!=argv:raise ValueError('Exact CLI argv changed')
            raw=(folder/'events.jsonl').read_bytes();usage=observed_usage(raw)
            valued=usage is not None and usage.get('cache_write_input_tokens',0)==0
            item={'cell':cid,'stage':stage,'status':c.read(folder/'status.json'),
                  'files_sha256':{n:sha256(folder/n) for n in ('prompt.txt','argv.json','events.jsonl','stderr.txt')},
                  'observed_usage':usage,'api_equivalent_usd':c.value_usage(usage) if valued else None}
            inventory.append(item)
            try:parsed=c.parse_events(raw)
            except (ValueError,KeyError,UnicodeDecodeError):
                if (folder/'result.json').exists():raise ValueError('Invalid raw stream has a saved completed result')
                failed=True;item['text_only_valid']=False
                if cid in rowmap:raise ValueError('Complete row includes invalid CLI turn')
                continue
            item['text_only_valid']=True
            if item['status'].get('state')!='completed' or not (folder/'result.json').is_file():
                failed=True
                if cid in rowmap:raise ValueError('Complete row contains unfinished turn')
                continue
            result=c.read(folder/'result.json')
            if result.get('files_sha256')!=item['files_sha256'] or any(result.get(k)!=v for k,v in parsed.items()):
                raise ValueError('Saved turn data differ from original event stream')
            history.append(parsed['final_text']);parts.append(parsed)
        if cid not in rowmap:
            if not failed and len(parts)==cell['cli_turns']:raise ValueError('Completed stages missing final cell artifact')
            continue
        if failed or len(parts)!=cell['cli_turns']:raise ValueError('Incomplete stages have final result row')
        row=rowmap[cid]
        if any(row.get(k)!=v for k,v in cell.items()) or row.get('model')!=c.MODEL or row.get('seed')!=cell['replicate_id']:
            raise ValueError('Result treatment label changed')
        usage={k:sum(p['usage'][k] for p in parts) for k in ('input_tokens','cached_input_tokens','output_tokens')}
        reasoning=[p['usage'].get('reasoning_output_tokens') for p in parts]
        usage['reasoning_output_tokens']=sum(reasoning) if all(x is not None for x in reasoning) else None
        if row.get('usage')!=usage or row.get('total_tokens')!=usage['input_tokens']+usage['output_tokens'] or row.get('final_text')!=history[-1]:
            raise ValueError('Final row text or token totals changed')
        for metric in ('api_equivalent_usd','uncached_sensitivity_usd'):
            if row.get(metric)!=sum(p[metric] for p in parts):raise ValueError('Final row valuation changed')
        valid.append(row);availability[cid]='completed'
    if state['state']=='completed' and (set(rowmap)!=allowed or state.get('failures')):
        raise ValueError('Archive claims completion despite missing/failed cells')
    known=[i for i in inventory if i['observed_usage'] is not None]
    return {'shard':shard.name,'archive_state':state['state'],'rows':valid,'cells':availability,
            'assigned_cells':len(cells),'submitted_cells':sum(v!='never_started' for v in availability.values()),
            'completed_cells':len(valid),'turn_inventory':inventory,'submitted_turns':len(inventory),
            'turns_without_supported_valuation':sum(i['api_equivalent_usd'] is None for i in inventory),
            'known_total_tokens':sum(i['observed_usage']['input_tokens']+i['observed_usage']['output_tokens'] for i in known),
            'known_api_equivalent_usd':sum(i['api_equivalent_usd'] for i in inventory if i['api_equivalent_usd'] is not None),
            'unknown_usage_turns':len(inventory)-len(known)}


def audit_archive(archive):
    archive=Path(archive)
    root=c.read(archive/'manifest.json');tasks=c.read(archive/'tasks.json')
    if c.read(archive/'status.json').get('state') not in ('completed','blocked'):
        raise ValueError('Wait for terminal archive before audit')
    continuation=root.get('schema')=='codex-heldout200-continuation-v1'
    original=root['original_parent_plan'] if continuation else root
    gate_path=archive/('original-control-gate.json' if continuation else 'control-gate.json')
    from .generate import plan
    if original!=plan(tasks,c.read(gate_path),sha256(gate_path)):
        raise ValueError('Original root plan or task/control/source identity changed')
    pending={x['id']:x for x in root.get('pending_cells',[])}
    if continuation:
        if len(pending)!=root['pending_count'] or c.digest({k:v for k,v in root.items() if k!='manifest_sha256'})!=root['manifest_sha256']:
            raise ValueError('Continuation manifest integrity failed')
        if sha256(archive/'protocol.md')!=root['protocol_sha256']:raise ValueError('Continuation protocol changed')
        for name,digest in root['dependency_sha256'].items():
            b=(archive/'sources'/name.replace('/','__')).read_bytes().replace(b'\r\n',b'\n')
            if hashlib.sha256(b).hexdigest()!=digest:raise ValueError('Continuation archived source changed')
    frozen={s['name']:s for s in original['shards']}
    actual={p.name for p in (archive/'shards').iterdir() if p.is_dir()}
    expected_names={v['shard'] for v in pending.values()} if continuation else set(frozen)
    if not actual.issubset(expected_names) or (not continuation and actual!=expected_names):
        raise ValueError('Missing or unexpected shard directory')
    reports=[];availability={x['id']:'never_started' for s in frozen.values() for x in s['manifest']['cells']}
    for name in sorted(actual):
        allowed=[x['id'] for x in pending.values() if x['shard']==name] if continuation else None
        if continuation:
            expected=[{k:v for k,v in x.items() if k!='shard'} for x in pending.values() if x['shard']==name]
            if c.read(archive/'shards'/name/'continuation_cells.json')!=expected:raise ValueError('Continuation dispatch subset changed')
        report=audit_shard(archive/'shards'/name,frozen[name]['manifest'],tasks,allowed)
        reports.append(report);availability.update(report['cells'])
    return {'archive':archive.name,'schema':root['schema'],'assigned_cells':len(availability),
            'all_assignment_availability':availability,'rows':[r for s in reports for r in s['rows']],
            'shards':reports,'submitted_cells':sum(s['submitted_cells'] for s in reports),
            'completed_cells':sum(s['completed_cells'] for s in reports),
            'submitted_turns':sum(s['submitted_turns'] for s in reports),
            'turns_without_supported_valuation':sum(s['turns_without_supported_valuation'] for s in reports),
            'known_total_tokens':sum(s['known_total_tokens'] for s in reports),
            'known_api_equivalent_usd':sum(s['known_api_equivalent_usd'] for s in reports),
            'unknown_usage_turns':sum(s['unknown_usage_turns'] for s in reports)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();c.save(a.out,audit_archive(a.archive))
