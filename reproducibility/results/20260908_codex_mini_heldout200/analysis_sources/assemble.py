"""Reconcile first attempts, continuation, exact exports and native task outcomes."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from .. import codex_subscription as c
from ..benchmark_bridge import _extract_fenced_block
from ..scale_env.validate_native import validate_native
from .evidence import environment_from_gate
from .partial_audit import audit_archive, sha256
from .continue_unsubmitted import tree_snapshot
from .analyze import summarize

ARMS=c.ARMS


def merge_audits(parent_audit, assigned_manifest, continuation_audit=None):
    m=c.read(assigned_manifest)
    cells={x['id']:x for s in m['shards'] for x in s['manifest']['cells']}
    if len(cells)!=m['planned_generations']:raise ValueError('Original assignment count mismatch')
    available=dict(parent_audit['all_assignment_availability'])
    if set(available)!=set(cells):raise ValueError('Parent availability must cover full allocation')
    rows={}
    for report in [parent_audit]+([continuation_audit] if continuation_audit is not None else []):
        if set(report['all_assignment_availability'])!=set(cells):raise ValueError('Audit allocation differs')
        if report is not parent_audit:
            for cid,status in report['all_assignment_availability'].items():
                if status!='never_started':
                    if available[cid]!='never_started':raise ValueError('Continuation repeats an already started cell')
                    available[cid]=status
        for row in report['rows']:
            cid=row['id']
            if cid not in cells or cid in rows:raise ValueError('Unexpected or duplicate candidate')
            if any(row.get(k)!=v for k,v in cells[cid].items()):raise ValueError('Candidate labels changed')
            rows[cid]=row
    return {'assigned_task_ids':m['assigned_task_ids'],'assigned_cell_count':len(cells),
            'assignment_availability':available,'rows':list(rows.values()),
            'original_manifest_sha256':m['manifest_sha256']}


def load_archives(archive,continuation=None):
    parent=audit_archive(archive)
    reports={'original':parent}
    hashes={'original':c.digest(tree_snapshot(archive))}
    extra=None
    if continuation is not None:
        manifest=c.read(continuation/'manifest.json')
        if manifest['original_parent_archive_sha256']!=hashes['original']:
            raise ValueError('Continuation refers to changed original archive')
        extra=audit_archive(continuation);reports['continuation']=extra
        hashes['continuation']=c.digest(tree_snapshot(continuation))
    result=merge_audits(parent,archive/'manifest.json',extra)
    result['source_archive_hashes']=hashes
    result['generation_audits']=reports
    result['control_gate_sha256']=c.read(archive/'manifest.json')['control_gate_sha256']
    return result


def samples_for(assembled,arm):
    indexed={r['task_id']:r for r in assembled['rows'] if r['arm']==arm}
    if len(indexed)!=sum(r['arm']==arm for r in assembled['rows']):raise ValueError('Duplicate arm task')
    samples=[]
    for task in assembled['assigned_task_ids']:
        if task not in indexed:continue
        solution,ok=_extract_fenced_block(indexed[task]['final_text'],'bigcodebench')
        samples.append({'task_id':task,'solution':solution,'format_extracted':ok})
    return samples


def export_bigcodebench(assembled,out,source_archive_hashes=None):
    out.mkdir(parents=True,exist_ok=False)
    groups={}
    for arm in ARMS:
        samples=samples_for(assembled,arm);observed=[s['task_id'] for s in samples]
        filename=f'samples-{arm}.jsonl';path=out/filename
        path.write_bytes(b''.join(c.canonical(s)+b'\n' for s in samples))
        groups[arm]={'samples':filename,'sha256':sha256(path),'observed_task_ids':observed,
                     'missing_task_ids':[t for t in assembled['assigned_task_ids'] if t not in observed],
                     'analysis_status':'pending' if samples else 'no_eval'}
    manifest={'assigned_task_ids':assembled['assigned_task_ids'],'assigned_cell_count':assembled['assigned_cell_count'],
              'original_manifest_sha256':assembled.get('original_manifest_sha256'),
              'source_archive_hashes':source_archive_hashes or assembled.get('source_archive_hashes',{}),
              'arms':groups,'assignment_availability':assembled['assignment_availability']}
    c.save(out/'export-manifest.json',manifest)
    if 'generation_audits' in assembled:c.save(out/'generation_audit.json',assembled['generation_audits'])
    return manifest


def collect_native(assembled,predictions,native,gate_dir,out):
    if out.exists():raise ValueError('Refuse to overwrite analysis output')
    gate=c.read(gate_dir/'heldout200_control_gate.json')
    if sha256(gate_dir/'heldout200_control_gate.json')!=assembled['control_gate_sha256'] or gate['assigned_task_ids']!=assembled['assigned_task_ids']:
        raise ValueError('Controls differ from frozen assignment')
    environment=environment_from_gate(gate_dir)
    exported=c.read(predictions/'export-manifest.json')
    if exported['source_archive_hashes']!=assembled['source_archive_hashes'] or exported['original_manifest_sha256']!=assembled['original_manifest_sha256'] or set(exported['arms'])!=set(ARMS):
        raise ValueError('Export originates from different archive or allocation')
    bykey={(r['task_id'],r['arm']):r for r in assembled['rows']};records=[];audits={}
    for arm in ARMS:
        group=exported['arms'][arm];samples=samples_for(assembled,arm)
        path=predictions/group['samples'];expected_bytes=b''.join(c.canonical(s)+b'\n' for s in samples)
        if path.read_bytes()!=expected_bytes or sha256(path)!=group['sha256']:
            raise ValueError('Export bytes differ from exact archived responses')
        observed=[s['task_id'] for s in samples]
        if group['observed_task_ids']!=observed or group['missing_task_ids']!=[t for t in assembled['assigned_task_ids'] if t not in observed]:
            raise ValueError('Export availability metadata changed')
        if not samples:continue
        folder=native/arm;meta=c.read(folder/'run-metadata.json')
        if meta.get('status')!='completed' or meta.get('exit_code')!=0:
            raise ValueError('Evaluator process did not complete successfully')
        expected={s['task_id']:s['solution'] for s in samples}
        checked=validate_native(folder,expected,environment)
        if not checked['ok']:raise ValueError('Native integrity failed: '+repr(checked['errors']))
        audits[arm]=checked
        for sample in samples:
            task=sample['task_id'];status=checked['statuses'][task]
            records.append({**bykey[task,arm],'raw_test_status':status,
                            'analysis_status':status if task in gate['evaluable_task_ids'] else None,
                            'format_extracted':sample['format_extracted'],'native_report_sha256':checked['report_sha256']})
    if len(records)!=len(assembled['rows']):raise ValueError('Not every observed candidate was evaluated')
    summary=summarize(records,assembled['assigned_task_ids'])
    summary['generation_availability']={s:sum(v==s for v in assembled['assignment_availability'].values()) for s in ('completed','submitted_incomplete','never_started')}
    summary['submitted_turn_usage']={name:{k:report[k] for k in ('known_total_tokens','known_api_equivalent_usd','unknown_usage_turns','submitted_cells','completed_cells','submitted_turns','turns_without_supported_valuation')} for name,report in assembled['generation_audits'].items()}
    summary['execution_amended']=True
    from .resource_ledger import summarize_turns
    summary['submitted_token_components']={name:summarize_turns([turn for shard in report['shards'] for turn in shard['turn_inventory']]) for name,report in assembled['generation_audits'].items()}
    out.mkdir(parents=True)
    (out/'candidate_records.jsonl').write_bytes(b''.join(c.canonical(r)+b'\n' for r in records))
    c.save(out/'summary.json',summary);c.save(out/'native_audit.json',audits)
    c.save(out/'generation_audit.json',assembled['generation_audits'])
    c.save(out/'assignment_availability.json',assembled['assignment_availability'])
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('export','collect'))
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--continuation',type=Path)
    p.add_argument('--predictions',type=Path,required=True)
    for name in ('native','controls','output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();joined=load_archives(a.archive,a.continuation)
    if a.command=='export':
        result=export_bigcodebench(joined,a.predictions);print(json.dumps({'exported':{k:len(v['observed_task_ids']) for k,v in result['arms'].items()}}))
    else:
        if any(x is None for x in (a.native,a.controls,a.output)):p.error('collect requires --native --controls --output')
        result=collect_native(joined,a.predictions,a.native,a.controls,a.output)
        print(json.dumps({'recorded':result['recorded_attempts'],'by_arm':result['by_arm']}))


if __name__=='__main__':main()
