"""Join disjoint INoT first attempts and evaluate only actual observed programs."""
import argparse
import json
from pathlib import Path
from .. import codex_subscription as c
from ..benchmark_bridge import _extract_fenced_block
from ..scale_env.validate_native import validate_native
from . import inot_audit
from .inot_continue import tree,sha
from .evidence import environment_from_gate


def load(original,continuation,tasks,selection,gate,protocol):
    m=c.read(continuation/'continuation_manifest.json')
    if c.digest({k:v for k,v in m.items() if k!='manifest_sha256'})!=m['manifest_sha256']:
        raise ValueError('Continuation manifest changed')
    before=tree(original)
    if before!=m['original_archive_tree']:raise ValueError('Original archive changed since continuation freeze')
    for name,digest in m['dependency_sha256'].items():
        if sha(continuation/'continuation_sources'/name.replace('/','__'))!=digest:
            raise ValueError('Archived executed continuation source changed')
    if sha(continuation/'continuation_protocol.md')!=m['input_hashes']['amendment']:
        raise ValueError('Execution amendment changed')
    original_audit=inot_audit.audit(original,tasks,selection,gate,protocol)
    continuation_audit=inot_audit.audit(continuation,tasks,selection,gate,protocol)
    if tree(original)!=before:raise ValueError('Original audit changed frozen archive bytes')
    original_manifest=c.read(original/'manifest.json')
    if c.read(continuation/'manifest.json')!=original_manifest or m['original_manifest']!=original_manifest:
        raise ValueError('Different INoT allocations')
    started={p.name for p in (original/'turns').iterdir()}
    pending=[cell for cell in original_manifest['cells'] if cell['id'] not in started]
    if pending!=m['pending_cells']:raise ValueError('Continuation changed pending order or included started cell')
    new_started={p.name for p in (continuation/'turns').iterdir()}
    if started & new_started or not new_started.issubset({cell['id'] for cell in pending}):
        raise ValueError('A model attempt was repeated or an unauthorized cell submitted')
    rows=[]
    for archive in (original,continuation):
        rows.extend(json.loads(line) for line in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate INoT result')
    order=original_manifest['task_ids'];rows.sort(key=lambda r:order.index(r['task_id']))
    return {'assigned_task_ids':order,'rows':rows,'source_archive_hashes':{'original':c.digest(tree(original)),'continuation':c.digest(tree(continuation))},
            'audits':{'original':original_audit,'continuation':continuation_audit},'control_gate_sha256':sha(gate),
            'missing_generation_task_ids':[t for t in order if t not in {r['task_id'] for r in rows}]}


def samples(joined):
    out=[]
    for row in joined['rows']:
        solution,ok=_extract_fenced_block(row['final_text'],'bigcodebench')
        out.append({'task_id':row['task_id'],'solution':solution,'format_extracted':ok})
    return out


def export(joined,out):
    out.mkdir(parents=True,exist_ok=False)
    path=out/'samples.jsonl';path.write_bytes(b''.join(c.canonical(s)+b'\n' for s in samples(joined)))
    c.save(out/'export_manifest.json',{'assigned_task_ids':joined['assigned_task_ids'],'missing_generation_task_ids':joined['missing_generation_task_ids'],
                                     'source_archive_hashes':joined['source_archive_hashes'],'samples_sha256':sha(path)})
    c.save(out/'generation_audit.json',joined['audits'])
    return {'assigned':len(joined['assigned_task_ids']),'observed':len(joined['rows'])}


def collect(joined,predictions,native,controls,out):
    meta=c.read(predictions/'export_manifest.json');expected_samples=samples(joined)
    path=predictions/'samples.jsonl'
    if meta['source_archive_hashes']!=joined['source_archive_hashes'] or meta['samples_sha256']!=sha(path) or path.read_bytes()!=b''.join(c.canonical(s)+b'\n' for s in expected_samples):
        raise ValueError('Predictions do not match exact INoT outputs')
    gate=c.read(controls/'heldout200_control_gate.json')
    if sha(controls/'heldout200_control_gate.json')!=joined['control_gate_sha256']:raise ValueError('Control gate changed')
    environment=environment_from_gate(controls);run=c.read(native/'run-metadata.json')
    if run.get('status')!='completed' or run.get('exit_code')!=0:raise ValueError('Native evaluator did not complete')
    checked=validate_native(native,{s['task_id']:s['solution'] for s in expected_samples},environment)
    if not checked['ok']:raise ValueError('Native integrity failed: '+repr(checked['errors']))
    byid={r['task_id']:r for r in joined['rows']};records=[]
    for sample in expected_samples:
        task=sample['task_id'];status=checked['statuses'][task]
        records.append({**byid[task],'raw_test_status':status,'analysis_status':status if task in gate['evaluable_task_ids'] else None,
                        'format_extracted':sample['format_extracted'],'native_report_sha256':checked['report_sha256']})
    observed=[r for r in records if r['analysis_status'] is not None];passes=sum(r['analysis_status']=='pass' for r in observed)
    summary={'treatment':'inot_algorithm_replication','assigned':len(joined['assigned_task_ids']),'generated':len(records),'evaluable':len(observed),'passes':passes,
             'evaluable_only_rate':passes/len(observed) if observed else None,
             'missingness_bounds':[passes/len(joined['assigned_task_ids']),(passes+len(joined['assigned_task_ids'])-len(observed))/len(joined['assigned_task_ids'])],
             'missing_generation_task_ids':joined['missing_generation_task_ids'],'format_failures':sum(not r['format_extracted'] for r in records),
             'completed_candidate_totals':{k:sum(r[k] for r in records) for k in ('total_tokens','api_equivalent_usd','uncached_sensitivity_usd')},
             'submitted_turn_usage':{name:{k:report['inventory'][k] for k in ('known_total_tokens','known_api_equivalent_usd','submitted_turns','turns_with_unavailable_usage','turns_without_supported_valuation')} for name,report in joined['audits'].items()},
             'scope':'exploratory independently worded algorithm replication; amended execution; not native author code'}
    from .resource_ledger import summarize_turns
    summary['submitted_token_components']={name:summarize_turns(report['inventory']['turns']) for name,report in joined['audits'].items()}
    out.mkdir(parents=True,exist_ok=False)
    (out/'candidate_records.jsonl').write_bytes(b''.join(c.canonical(r)+b'\n' for r in records))
    c.save(out/'summary.json',summary);c.save(out/'native_audit.json',checked);c.save(out/'generation_audit.json',joined['audits'])
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('export','collect'))
    for name in ('original','continuation','tasks','selection','gate','protocol','predictions'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('native','controls','output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();joined=load(a.original,a.continuation,a.tasks,a.selection,a.gate,a.protocol)
    if a.command=='export':print(json.dumps(export(joined,a.predictions)))
    else:
        if any(x is None for x in (a.native,a.controls,a.output)):p.error('collect requires --native --controls --output')
        print(json.dumps(collect(joined,a.predictions,a.native,a.controls,a.output)))
