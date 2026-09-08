"""Reconstruct all repeated assignments from raw CLI streams and native reports."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .. import codex_luna_subscription as c
from .. import benchmark_bridge as bridge
from ..heldout200.evidence import environment_from_gate
from ..scale_env.validate_native import validate_native
from . import dispatch as d

def event_parse_errors(folder):
    errors=[]
    path=folder/'events.jsonl'
    if not path.exists():return ['event_stream_absent']
    for number,line in enumerate(path.read_bytes().splitlines(),1):
        if not line.strip():continue
        try:json.loads(line.decode('utf-8'))
        except (json.JSONDecodeError,UnicodeDecodeError):errors.append(f'invalid_event_line_{number}')
    return errors

def raw_usage(folder):
    found=[]
    if not (folder/'events.jsonl').exists():return None
    for line in (folder/'events.jsonl').read_text(encoding='utf-8',errors='replace').splitlines():
        try:event=json.loads(line)
        except json.JSONDecodeError:continue
        if event.get('type')=='turn.completed' and isinstance(event.get('usage'),dict):found.append(event['usage'])
    if len(found)>1:raise ValueError('Multiple usage completions in one fresh turn')
    if not found:return None
    u=found[0]
    if u.get('cache_write_input_tokens',0)!=0:raise ValueError('Nonzero cache-write counters require a separate accounting amendment')
    if any(type(u.get(k)) is not int or u[k]<0 for k in ('input_tokens','cached_input_tokens','output_tokens')) or u['cached_input_tokens']>u['input_tokens']:raise ValueError('Invalid usage counters')
    c.value_usage(u)
    return found[0]

def reconstruct(archive,inputs,gate_dir,manifest):
    frozen=c.read(manifest)
    if frozen!=d.plan(inputs,gate_dir) or c.read(archive/'manifest.json')!=frozen:raise ValueError('Frozen archive plan mismatch')
    if c.read(archive/'status.json')['state']=='running':raise ValueError('Do not snapshot an active generation writer')
    if (archive/'instructions.txt').read_bytes()!=c.BASE.encode():raise ValueError('Model policy bytes changed')
    tasks=c.tasks_from(inputs/'input/prepared.jsonl');by_task={t['task_id']:t for t in tasks}
    if c.read(archive/'tasks.json')!=tasks:raise ValueError('Saved tasks changed')
    submitted=d.validate_turn_inventory(archive,frozen['inner_manifest']['cells'])
    records=[];ledger=[]
    for cell in frozen['inner_manifest']['cells']:
        saved_path=archive/'cells'/f"{cell['id']}.json"
        saved=c.read(saved_path) if saved_path.exists() else None
        history=[];turns=[]
        for stage in range(cell['cli_turns']):
            folder=archive/'turns'/f"{cell['id']}-{stage}"
            if not folder.exists():break
            if len(history)!=stage:raise ValueError('A later turn follows an unverified stage')
            if (folder/'prompt.txt').read_bytes()!=c.prompt_for(by_task[cell['task_id']],cell,stage,history).encode():raise ValueError('Prompt or forwarded response differs')
            argv=c.read(folder/'argv.json');runtime=c.read(archive/'runtime.json')
            cwd=Path(argv[argv.index('--cd')+1]);instructions=Path(next(json.loads(x.split('=',1)[1]) for x in argv if x.startswith('model_instructions_file=')))
            if argv!=c.cli_command(runtime['prefix'],cwd,instructions) or runtime['version']!=c.CLI_VERSION:raise ValueError('CLI configuration differs')
            usage=raw_usage(folder)
            ledger.append({'cell_id':cell['id'],'task_id':cell['task_id'],'arm':cell['arm'],'replicate_id':cell['replicate_id'],
                           'stage':stage,'usage':usage,'usage_known':usage is not None,
                           'event_parse_errors':event_parse_errors(folder),
                           'api_equivalent_usd':c.value_usage(usage) if usage is not None else None,
                           'uncached_sensitivity_usd':(usage['input_tokens']*c.PRICES['input']+usage['output_tokens']*c.PRICES['output'])/1e6 if usage is not None else None})
            status=c.read(folder/'status.json')
            if (folder/'result.json').exists():
                parsed=c.parse_events((folder/'events.jsonl').read_bytes());record=c.read(folder/'result.json')
                if status.get('state')!='completed':raise ValueError('Completed result lacks terminal acceptance')
            elif (folder/'empty_response_classification.json').exists():
                parsed=d.completed_empty(folder);record=c.read(folder/'empty_response_classification.json')
            else:
                if saved:raise ValueError('Candidate is marked complete with unaccepted turn')
                break
            for key in ('final_text','usage','api_equivalent_usd','uncached_sensitivity_usd'):
                if parsed[key]!=record[key]:raise ValueError('Saved response/usage differs from events')
            for name in ('prompt.txt','argv.json','events.jsonl','stderr.txt'):
                if record['files_sha256'][name]!=d.sha(folder/name):raise ValueError('Raw turn hash changed')
            history.append(parsed['final_text']);turns.append(parsed)
        row={**cell,'generation_complete':saved is not None,'quality':None,'outcome_type':'generation_unavailable','native_status':None}
        if saved:
            if len(turns)!=cell['cli_turns'] or saved['final_text']!=history[-1] or any(saved[k]!=v for k,v in cell.items()):raise ValueError('Candidate identity/response changed')
            usage={k:sum(t['usage'][k] for t in turns) for k in ('input_tokens','cached_input_tokens','output_tokens')}
            metrics={'total_tokens':usage['input_tokens']+usage['output_tokens'],
                     'api_equivalent_usd':sum(t['api_equivalent_usd'] for t in turns),
                     'uncached_sensitivity_usd':sum(t['uncached_sensitivity_usd'] for t in turns)}
            if any(saved[k]!=v for k,v in metrics.items()) or any(saved['usage'][k]!=v for k,v in usage.items()):raise ValueError('Candidate usage changed')
            solution,ok=bridge._extract_fenced_block(history[-1],'bigcodebench')
            row.update(metrics);row.update({'final_text':history[-1],'solution':solution,'format_extracted':ok})
        records.append(row)
    if {f"{row['cell_id']}-{row['stage']}" for row in ledger}!=submitted:raise ValueError('Submitted turn omitted from resource ledger')
    return records,ledger

def export(archive,inputs,gate_dir,manifest,out):
    records,ledger=reconstruct(archive,inputs,gate_dir,manifest);out.mkdir(parents=True,exist_ok=False)
    ids=c.read(inputs/'selection.json')['assigned_task_ids'];hashes={}
    for rep in d.REPEATS:
        for arm in c.ARMS:
            key=f'{arm}-r{rep}';mapping={r['task_id']:r for r in records if r['replicate_id']==rep and r['arm']==arm and r['generation_complete']}
            samples=[{'task_id':t,'solution':mapping[t]['solution']} for t in ids if t in mapping]
            path=out/f'{key}.jsonl';path.write_bytes(b''.join(c.canonical(r)+b'\n' for r in samples));hashes[key]=d.sha(path)
    c.save(out/'export_manifest.json',{'sample_hashes':hashes,'generation_manifest_sha256':d.sha(manifest)})
    c.save(out/'turn_usage.json',ledger)

def collect(archive,inputs,gate_dir,manifest,predictions,native,out):
    records,ledger=reconstruct(archive,inputs,gate_dir,manifest);ids=c.read(inputs/'selection.json')['assigned_task_ids']
    gate=c.read(gate_dir/'heldout200_control_gate.json');eligible=set(gate['evaluable_task_ids']);env=environment_from_gate(gate_dir)
    export_meta=c.read(predictions/'export_manifest.json');audits={};statuses={}
    if export_meta['generation_manifest_sha256']!=d.sha(manifest):raise ValueError('Export plan differs')
    for rep in d.REPEATS:
        for arm in c.ARMS:
            key=f'{arm}-r{rep}';mapping={r['task_id']:r for r in records if r['replicate_id']==rep and r['arm']==arm and r['generation_complete']}
            expected=[{'task_id':t,'solution':mapping[t]['solution']} for t in ids if t in mapping]
            path=predictions/f'{key}.jsonl'
            if path.read_bytes()!=b''.join(c.canonical(r)+b'\n' for r in expected) or export_meta['sample_hashes'][key]!=d.sha(path):raise ValueError('Export differs from original response')
            audit=validate_native(native/key,{r['task_id']:r['solution'] for r in expected},env) if expected else {'ok':True,'statuses':{}}
            if not audit['ok']:raise ValueError(f'Native evidence invalid: {key}: {audit.get("errors")}')
            audits[key]=audit;statuses[key]=audit['statuses']
    for r in records:
        if r['generation_complete']:
            status=statuses[f"{r['arm']}-r{r['replicate_id']}"][r['task_id']]
            r['native_status']=status
            if r['task_id'] in eligible and status in ('pass','fail','timeout'):
                r['quality']=status=='pass' and r['format_extracted']
                r['outcome_type']='native_outcome' if r['format_extracted'] else 'model_format_failure'
            else:r['outcome_type']='control_unavailable'
        r.pop('final_text',None);r.pop('solution',None)
    out.mkdir(parents=True,exist_ok=False)
    (out/'candidate_records.jsonl').write_bytes(b''.join(c.canonical(r)+b'\n' for r in records))
    c.save(out/'turn_usage.json',ledger);c.save(out/'native_audit.json',audits)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['export','collect'])
    for n in ('archive','inputs','gate-dir','manifest','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('predictions','native'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.command=='export':export(a.archive,a.inputs,a.gate_dir,a.manifest,a.out)
    else:collect(a.archive,a.inputs,a.gate_dir,a.manifest,a.predictions,a.native,a.out)
