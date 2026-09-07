"""Independently reconcile complete Codex CLI archives before reporting pilot costs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
try:
    from . import codex_subscription as c
except ImportError:
    import codex_subscription as c


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_attempt(archive):
    """Account for every submitted turn, including rejected treatment traces."""
    turns=[]
    for folder in sorted((archive/'turns').iterdir()):
        raw=(folder/'events.jsonl').read_bytes()
        events=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
        completed=[e for e in events if e.get('type')=='turn.completed']
        usage=completed[0].get('usage') if len(completed)==1 else None
        if usage is not None:
            if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('input_tokens','cached_input_tokens','output_tokens')) or usage['cached_input_tokens']>usage['input_tokens']:
                raise ValueError('Malformed usage cannot be valued')
        try:
            c.parse_events(raw); text_only=True
        except (ValueError,KeyError): text_only=False
        tariff_supported = usage is not None and usage.get('cache_write_input_tokens',0)==0
        turns.append({'turn':folder.name,'status':c.read(folder/'status.json'),
                      'events_sha256':sha(folder/'events.jsonl'),'text_only_trace':text_only,
                      'observed_usage':usage,
                      'observed_api_equivalent_usd':c.value_usage(usage) if tariff_supported else None})
    known=[t for t in turns if t['observed_usage'] is not None]
    return {'archive':archive.name,'status':c.read(archive/'status.json'),
            'submitted_turns':len(turns),'turns_with_complete_usage':len(known),
            'turns_with_unavailable_usage':len(turns)-len(known),
            'known_total_tokens':sum(t['observed_usage']['input_tokens']+t['observed_usage']['output_tokens'] for t in known),
            'turns_without_supported_valuation':sum(t['observed_api_equivalent_usd'] is None for t in turns),
            'known_api_equivalent_usd':sum(t['observed_api_equivalent_usd'] for t in known if t['observed_api_equivalent_usd'] is not None),
            'interpretation':'includes invalid/incomplete generations; unobserved usage is unknown, not zero',
            'turns':turns}


def audit(archive):
    m=c.read(archive/'manifest.json');tasks=c.read(archive/'tasks.json')
    if m != c.make_manifest(tasks,m['replicate_ids'],m['arms']):raise ValueError('Frozen manifest/source mismatch')
    if (archive/'instructions.txt').read_text(encoding='utf-8')!=c.BASE:raise ValueError('Instructions differ')
    if c.read(archive/'status.json')['state']!='completed':raise ValueError('Generation matrix is incomplete')
    runtime=c.read(archive/'runtime.json')
    if runtime['version']!=c.CLI_VERSION or runtime['authentication']!='chatgpt':raise ValueError('Runtime version/authentication differs')
    if runtime['workers'] not in (1,2) or runtime['timeout_seconds']!=180:raise ValueError('Runtime execution limits differ from pilot')
    provenance=c.read(archive/'runtime_provenance.json')
    if provenance['cli_version']!=runtime['version'] or provenance['prefix']!=runtime['prefix']:raise ValueError('Runtime provenance differs')
    if provenance['package_version']!='0.153.4' or not provenance['native_executable_sha256']:raise ValueError('Missing pinned package/binary provenance')
    if sha(archive/'runner_source.py')!=m['source_sha256_lf']:raise ValueError('Archived frozen runner differs')
    if sha(archive/'npm-package-lock.json')!=provenance['npm_lock_sha256']:raise ValueError('Runtime package lock changed')
    saved=[json.loads(line) for line in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    rows={r['id']:r for r in saved}
    if len(rows)!=len(saved) or set(rows)!={x['id'] for x in m['cells']}:raise ValueError('Missing or duplicate result cells')
    taskmap={t['task_id']:t for t in tasks};expected_turns=set();checked=[];canonical_argv=None
    for cell in m['cells']:
        history=[];parts=[]
        row=rows[cell['id']]
        if any(row.get(k)!=v for k,v in cell.items()):raise ValueError('Result treatment label changed')
        for stage in range(cell['cli_turns']):
            name=f"{cell['id']}-{stage}";expected_turns.add(name);folder=archive/'turns'/name
            if c.read(folder/'status.json')['state']!='completed':raise ValueError('Unfinished turn')
            result=c.read(folder/'result.json')
            if set(result['files_sha256'])!={'prompt.txt','argv.json','events.jsonl','stderr.txt'}:raise ValueError('Missing artifact hashes')
            for file,digest in result['files_sha256'].items():
                if sha(folder/file)!=digest:raise ValueError('CLI artifact hash mismatch: '+name+'/'+file)
            expected=c.prompt_for(taskmap[cell['task_id']],cell,stage,history)
            if (folder/'prompt.txt').read_bytes()!=expected.encode('utf-8'):raise ValueError('Task, treatment, or full history changed')
            parsed=c.parse_events((folder/'events.jsonl').read_bytes())
            if any(result[k]!=value for k,value in parsed.items()):raise ValueError('Derived turn data differ from CLI event stream')
            argv=c.read(folder/'argv.json')
            # Original absolute paths are recorded in provenance before publication moves the archive.
            required=c.cli_command(runtime['prefix'],provenance['empty_working_directory'],provenance['instructions_path'])
            if argv!=required:raise ValueError('Exact CLI arguments or instruction path differ')
            if provenance['instructions_sha256']!=sha(archive/'instructions.txt'):raise ValueError('Loaded instruction artifact differs')
            if canonical_argv is not None and argv!=canonical_argv:raise ValueError('CLI settings changed between turns')
            canonical_argv=argv
            history.append(parsed['final_text']);parts.append(parsed)
        usage={k:sum(p['usage'][k] for p in parts) for k in ('input_tokens','cached_input_tokens','output_tokens')}
        reasoning=[p['usage'].get('reasoning_output_tokens') for p in parts]
        usage['reasoning_output_tokens']=sum(reasoning) if all(v is not None for v in reasoning) else None
        if row['final_text']!=history[-1] or row['usage']!=usage:raise ValueError('Saved final answer or usage differ')
        if row['api_equivalent_usd']!=sum(p['api_equivalent_usd'] for p in parts):raise ValueError('Valuation differs')
        if row['uncached_sensitivity_usd']!=sum(p['uncached_sensitivity_usd'] for p in parts):raise ValueError('No-cache valuation differs')
        if row['total_tokens']!=usage['input_tokens']+usage['output_tokens']:raise ValueError('Total token count differs')
        checked.append(row)
    if {p.name for p in (archive/'turns').iterdir()}!=expected_turns:raise ValueError('Unexpected turn artifacts')
    byarm=[]
    for arm in m['arms']:
        group=[r for r in checked if r['arm']==arm];n=len(group)
        byarm.append({'arm':arm,'generations':n,'cli_turns':sum(r['cli_turns'] for r in group),
                      'mean_total_tokens':sum(r['total_tokens'] for r in group)/n,
                      'mean_input_tokens':sum(r['usage']['input_tokens'] for r in group)/n,
                      'mean_cached_input_tokens':sum(r['usage']['cached_input_tokens'] for r in group)/n,
                      'mean_output_tokens':sum(r['usage']['output_tokens'] for r in group)/n,
                      'mean_reasoning_output_tokens':sum(r['usage']['reasoning_output_tokens'] for r in group)/n if all(r['usage']['reasoning_output_tokens'] is not None for r in group) else None,
                      'mean_api_equivalent_usd':sum(r['api_equivalent_usd'] for r in group)/n,
                      'total_api_equivalent_usd':sum(r['api_equivalent_usd'] for r in group),
                      'mean_no_cache_usd':sum(r['uncached_sensitivity_usd'] for r in group)/n,
                      'mean_cli_wall_seconds':sum(r['wall_seconds'] for r in group)/n})
    return {'audit':'passed','manifest_sha256':m['manifest_sha256'],'model_requested':c.MODEL,
            'replicate_semantics':'one replicate ID, no controlled model seed',
            'task_count':len(tasks),'generations':len(checked),'cli_turns':len(expected_turns),
            'total_tokens':sum(r['total_tokens'] for r in checked),
            'total_api_equivalent_usd':sum(r['api_equivalent_usd'] for r in checked),
            'cost_semantics':'observed tokens valued at official standard API list prices; not subscription charges',
            'quality_status':'not evaluated by this audit','by_arm':byarm}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=audit(args.archive);c.save(args.output,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
