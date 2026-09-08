"""Resumable, subscription-only dispatch; submitted attempts are never replaced."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from .. import codex_subscription as c
from ..heldout200.evidence import environment_from_gate
from ..record_codex_runtime import capture

ROOT=Path(__file__).resolve().parents[2]
REPEATS=[101,102,103]
DEPENDENCIES=['codex_subscription.py','factorial_runner.py','benchmark_bridge.py','record_codex_runtime.py',
              'scale1000/dispatch.py','scale1000/prepare.py','scale1000/controls.py','scale1000/analyze.py',
              'scale1000/collect.py','heldout200/evidence.py','scale_env/validate_native.py']
DEPENDENCIES += ['scale1000/ENVIRONMENT_AMENDMENT.md','scale1000/environment/Dockerfile','scale1000/environment/requirements.txt']
DEPENDENCIES += ['scale1000/environment-v2/Dockerfile','scale1000/environment-v2/requirements.txt']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_turn_inventory(archive, cells):
    """Reject evidence outside the allocation or beyond an unaccepted stage."""
    root=archive/'turns'
    if not root.exists():return set()
    expected={f"{cell['id']}-{stage}":(cell,stage) for cell in cells for stage in range(cell['cli_turns'])}
    actual=set()
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name not in expected:raise ValueError('Unexpected turn evidence outside frozen allocation: '+folder.name)
        cell,stage=expected[folder.name]
        for previous in range(stage):
            prior=root/f"{cell['id']}-{previous}"
            if not (prior/'result.json').exists() and not (prior/'empty_response_classification.json').exists():raise ValueError('Later turn follows absent or unaccepted prior stage: '+folder.name)
        actual.add(folder.name)
    return actual

def plan(inputs:Path,gate_dir:Path):
    tasks=c.tasks_from(inputs/'input/prepared.jsonl');selection=c.read(inputs/'selection.json')
    gate=c.read(gate_dir/'heldout200_control_gate.json');environment_from_gate(gate_dir)
    if len(tasks)!=1000 or len(selection['assigned_task_ids'])!=1000 or len(set(selection['assigned_task_ids']))!=1000 or {t['task_id'] for t in tasks}!=set(selection['assigned_task_ids']):raise ValueError('All 1000 unique tasks required')
    if gate['assigned_task_ids']!=selection['assigned_task_ids'] or not gate['controls_complete']:raise ValueError('Full frozen control gate required')
    inner=c.make_manifest(tasks,REPEATS,list(c.ARMS))
    for t in tasks:
        for arm in c.ARMS:c.prompt_for(t,{'arm':arm,'cli_turns':3 if arm.startswith('multi') else 1},0,[])
    sources={n:hashlib.sha256((ROOT/'reproducibility'/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in DEPENDENCIES}
    p={'schema':'scale1000-generation-v1','inner_manifest':inner,'assigned_task_ids':selection['assigned_task_ids'],
       'selection_sha256':sha(inputs/'selection.json'),'prepared_sha256':sha(inputs/'input/prepared.jsonl'),
       'control_gate_sha256':sha(gate_dir/'heldout200_control_gate.json'),'source_sha256_lf':sources,
       'protocol_sha256_lf':hashlib.sha256((Path(__file__).parent/'PROTOCOL.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
       'workers':8,'timeout_seconds':600,'known_valuation_submission_guard_usd':285,
       'resume_policy':'untouched assignments only; original attempts remain immutable',
       'provider_seed_controlled':False,'planned_candidates':15000,'planned_cli_turns':27000}
    return {**p,'manifest_sha256':c.digest(p)}

def completed_empty(folder):
    """Classify a terminal empty model message without changing its raw trace."""
    status=c.read(folder/'status.json')
    if status.get('state')!='blocked' or status.get('reason')!='One completed turn and one complete answer required':raise ValueError('Only terminal empty-response parser rejection can be reclassified')
    raw=(folder/'events.jsonl').read_bytes()
    events=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    messages=[e for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
    if len(messages)>1 or (messages and (not isinstance(messages[0]['item'].get('text'),str) or messages[0]['item']['text'].strip())):raise ValueError('Not an empty completed response')
    original=messages[0]['item']['text'] if messages else ''
    if messages:messages[0]['item']['text']='EMPTY_RESPONSE_VALIDATION_SENTINEL'
    else:events.insert(0,{'type':'item.completed','item':{'type':'agent_message','text':'EMPTY_RESPONSE_VALIDATION_SENTINEL'}})
    normalized=c.parse_events(b'\n'.join(c.canonical(e) for e in events))
    normalized['final_text']=original;normalized['empty_model_response']=True
    normalized['original_terminal_status']=status
    normalized['wall_seconds']=None
    normalized['files_sha256']={n:sha(folder/n) for n in ('prompt.txt','argv.json','events.jsonl','stderr.txt')}
    return normalized

def run(inputs,gate_dir,manifest,out,npm_root):
    frozen=c.read(manifest)
    if frozen!=plan(inputs,gate_dir):raise ValueError('Frozen execution plan changed')
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    lock_path=out/'DISPATCH.lock'
    with lock_path.open('x') as f:f.write(str(os.getpid()))
    try:
        validate_turn_inventory(out,frozen['inner_manifest']['cells'])
        tasks=c.tasks_from(inputs/'input/prepared.jsonl');by_id={t['task_id']:t for t in tasks}
        os.environ['CODEX_STUDY_CLI_JS']=str(npm_root.resolve()/'node_modules/@openai/codex/bin/codex.js')
        prefix=c.resolved_prefix();version=subprocess.check_output(prefix+['--version'],text=True).strip()
        if version!=c.CLI_VERSION:raise ValueError('Frozen CLI version mismatch')
        auth=subprocess.run(prefix+['login','status'],text=True,capture_output=True)
        if auth.returncode or 'ChatGPT' not in auth.stdout+auth.stderr:raise ValueError('Subscription login required')
        if not (out/'manifest.json').exists():
            c.save(out/'manifest.json',frozen);c.save(out/'tasks.json',tasks)
            (out/'instructions.txt').write_bytes(c.BASE.encode());(out/'empty').mkdir()
            for name in DEPENDENCIES:
                p=out/'sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/'reproducibility'/name).read_bytes().replace(b'\r\n',b'\n'))
        elif c.read(out/'manifest.json')!=frozen or c.read(out/'tasks.json')!=tasks or (out/'instructions.txt').read_bytes()!=c.BASE.encode():raise ValueError('Existing archive identity mismatch')
        if any((out/'empty').iterdir()):raise ValueError('Task-free working directory changed')
        session=out/'sessions'/str(time.time_ns());session.mkdir(parents=True)
        runtime={'version':version,'prefix':prefix,'authentication':'chatgpt','workers':8,'timeout_seconds':600,'started_unix':time.time()}
        c.save(session/'runtime.json',runtime)
        if not (out/'runtime.json').exists():
            c.save(out/'runtime.json',runtime);capture(out,npm_root,Path(c.__file__))
        else:
            provenance=c.read(out/'runtime_provenance.json')
            if c.read(out/'runtime.json')['prefix']!=prefix:raise ValueError('Resume must use the original CLI runtime path')
            if sha(Path(provenance['native_executable_path']))!=provenance['native_executable_sha256'] or sha(Path(prefix[1]))!=provenance['node_entry_sha256']:raise ValueError('CLI binary changed since initial dispatch')
        command=c.cli_command(prefix,out/'empty',out/'instructions.txt');c.save(session/'command.json',command)
        inner=frozen['inner_manifest'];cells=inner['cells']
        def touched(cell):return (out/'cells'/f"{cell['id']}.json").exists() or any((out/'turns'/f"{cell['id']}-{stage}").exists() for stage in range(cell['cli_turns']))
        pending=[cell for cell in cells if not touched(cell)]
        c.save(session/'pending.json',{'ids':[x['id'] for x in pending],'started_unix':time.time()})
        from .collect import raw_usage
        known=0.0
        for p in (out/'turns').iterdir() if (out/'turns').exists() else []:
            usage=raw_usage(p)
            if usage is not None:known+=c.value_usage(usage)
        lock=threading.Lock();stop=threading.Event();failures=[];complete=[]
        c.save(out/'status.json',{'state':'running','session':session.name,'pending_at_start':len(pending)})
        def one(cell):
            nonlocal known
            with lock:
                if stop.is_set() or known>=285:stop.set();return
            history=[];turns=[]
            try:
                for stage in range(cell['cli_turns']):
                    with lock:
                        if stop.is_set() or known>=285:raise RuntimeError('Submission paused before untouched stage')
                    prompt=c.prompt_for(by_id[cell['task_id']],cell,stage,history)
                    folder=out/'turns'/f"{cell['id']}-{stage}"
                    try:result=c.archive_turn(folder,command,prompt,600)
                    except Exception as original:
                        try:result=completed_empty(folder)
                        except Exception:raise original
                        c.save(folder/'empty_response_classification.json',result)
                    history.append(result['final_text']);turns.append(result)
                    with lock:known+=result['api_equivalent_usd']
                usage={k:sum(r['usage'][k] for r in turns) for k in ('input_tokens','cached_input_tokens','output_tokens')}
                reasoning=[r['usage'].get('reasoning_output_tokens') for r in turns]
                usage['reasoning_output_tokens']=sum(reasoning) if all(x is not None for x in reasoning) else None
                row={**cell,'model':c.MODEL,'generation_complete':True,'final_text':history[-1],
                     'usage':usage,'total_tokens':usage['input_tokens']+usage['output_tokens'],
                     'api_equivalent_usd':sum(r['api_equivalent_usd'] for r in turns),
                     'uncached_sensitivity_usd':sum(r['uncached_sensitivity_usd'] for r in turns),
                     'session':session.name,'seed_field_semantics':'replicate label; provider seed not controlled'}
                c.save(out/'cells'/f"{cell['id']}.json",row)
                with lock:
                    complete.append(cell['id'])
                    if len(complete)%25==0:print(c.canonical({'completed_this_session':len(complete),'known_valuation':known}).decode(),flush=True)
            except Exception as exc:
                if 'folder' in locals() and folder.exists() and not (folder/'result.json').exists() and not (folder/'empty_response_classification.json').exists():
                    usage=raw_usage(folder)
                    if usage is not None:
                        with lock:known+=c.value_usage(usage)
                retained='\n'.join(p.read_text(encoding='utf-8',errors='replace')[-12000:] for stage in range(cell['cli_turns']) for p in (out/'turns'/f"{cell['id']}-{stage}"/'events.jsonl',out/'turns'/f"{cell['id']}-{stage}"/'stderr.txt') if p.exists())
                fatal=any(word in retained.lower() for word in ('usage limit','usage_limit','rate limit','rate_limit','quota','not logged in','unauthorized'))
                row={**cell,'generation_complete':False,'failure_reason':str(exc),'session':session.name,'quota_or_auth_stop':fatal}
                c.save(out/'failures'/f"{cell['id']}.json",row)
                with lock:
                    failures.append(cell['id'])
                    if fatal:stop.set()
        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in as_completed([pool.submit(one,cell) for cell in pending]):future.result()
        rows=[c.read(p) for p in sorted((out/'cells').glob('*.json'))] if (out/'cells').exists() else []
        (out/'results.jsonl').write_bytes(b''.join(c.canonical(r)+b'\n' for r in rows))
        remaining=[cell['id'] for cell in cells if not touched(cell)]
        status={'state':'paused' if remaining else 'generation_finished','completed_candidates':len(rows),
                'submitted_incomplete_candidates':sum(touched(x) for x in cells)-len(rows),
                'untouched_candidates':len(remaining),'session':session.name,'known_valuation':known,'finished_unix':time.time()}
        c.save(session/'completion.json',status);c.save(out/'status.json',status);print(c.canonical(status).decode(),flush=True)
    finally:lock_path.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run'])
    for n in ('inputs','gate-dir','manifest'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--out',type=Path);p.add_argument('--npm-root',type=Path,default=Path('tmp/codex-runtime'))
    a=p.parse_args()
    if a.command=='freeze':
        if a.manifest.exists():raise ValueError('Refusing to overwrite frozen plan')
        c.save(a.manifest,plan(a.inputs,a.gate_dir))
    else:run(a.inputs,a.gate_dir,a.manifest,a.out,a.npm_root)
