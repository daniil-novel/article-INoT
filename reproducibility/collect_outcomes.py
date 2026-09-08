"""Join complete generation archives to official benchmark reports, preserving missingness."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
try:
    from .factorial_runner import audit, read, canonical
    from .benchmark_bridge import _extract_fenced_block
except ImportError:
    from factorial_runner import audit, read, canonical
    from benchmark_bridge import _extract_fenced_block


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _same_patch(left, right):
    return left.replace('\r\n', '\n').rstrip('\n') == right.replace('\r\n', '\n').rstrip('\n')


def collect(archive: Path, export_manifest: Path, reports: Path) -> list[dict]:
    check=audit(archive)
    if not check['ok']:raise ValueError(f"Generation archive failed audit: {check['errors']}")
    m=read(archive/'manifest.json');c=read(archive/'config.json');export=read(export_manifest)
    generations=[json.loads(line) for line in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    gen={(r['task_id'],r['arm'],r['seed']):r for r in generations}
    predictions={};prediction_paths={};report_sources={};run_roots={}
    for group in export['groups']:
        if group['model']!=c['model']:raise ValueError('Mixed model export')
        p=Path(group['path'])
        if not p.is_absolute():p=Path.cwd()/p
        if sha(p)!=group['sha256']:raise ValueError('Prediction file hash mismatch')
        for line in p.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            tid=row.get('task_id',row.get('instance_id'))
            key=(tid,group['arm'],group['seed'])
            if key in predictions:raise ValueError('Duplicate exported prediction')
            predictions[key]=row
            prediction_paths[key]=p
            if export['benchmark']=='bigcodebench':
                report_sources[key]=reports/(p.stem+'_eval_results.json')
            else:
                run_roots[key]=reports/group['run_id']
                report_sources[key]=run_roots[key]/c['model'].replace('/','__')/tid/'report.json'
    expected={(cell['task_id'],cell['arm'],cell['seed']) for cell in m['cells']}
    if set(gen)!=expected or set(predictions)!=expected:raise ValueError('Prediction/manifest matrix mismatch')
    # Confirm exports were made from this exact generation file.
    if sha(archive/'results.jsonl')!=export['source_sha256']:raise ValueError('Export belongs to another generation file')
    rows=[]
    cache={}
    for key in sorted(expected):
        g=gen[key];p=predictions[key];prediction_path=prediction_paths[key];report=report_sources[key]
        result={k:g[k] for k in ('task_id','arm','seed','model','cost_usd','total_tokens','truncated')}
        result.update(resolved=None,evaluator=export['benchmark'],report_path=str(report.resolve()),report_sha256=None,
                      prediction_path=str(prediction_path.resolve()),prediction_sha256=sha(prediction_path),
                      generation_path=str((archive/'results.jsonl').resolve()),generation_sha256=export['source_sha256'],
                      outcome_type='missing',missing_reason='official_report_missing')
        if export['benchmark']=='swebench':
            if not isinstance(g.get('final_text'),str):
                result['missing_reason']='generation_response_unavailable'
                result['outcome_type']='invalid_export_join'
                rows.append(result)
                continue
            expected_patch, extracted=_extract_fenced_block(g['final_text'],'swebench')
            result['generation_format_extracted']=extracted
            patch_value=p.get('model_patch')
            if not isinstance(patch_value,str) or patch_value != expected_patch or p.get('model_name_or_path')!=g['model']:
                result['missing_reason']='exported_patch_differs_from_generation'
                result['outcome_type']='invalid_export_join'
                rows.append(result)
                continue
            run_results=run_roots[key]/'results.json'
            summary=read(run_results) if run_results.exists() else {}
            if run_results.exists():
                result['run_results_path']=str(run_results.resolve());result['run_results_sha256']=sha(run_results)
            if key[0] in summary.get('infra_failure_ids',[]):
                result['missing_reason']='evaluator_infrastructure_failure';result['outcome_type']='infrastructure_unknown'
                rows.append(result)
                continue
            if key[0] in summary.get('empty_patch_ids',[]) and patch_value:
                result['missing_reason']='contradictory_empty_patch_summary';result['outcome_type']='invalid_export_join'
                rows.append(result)
                continue
        if report.exists():
            if report not in cache:cache[report]=read(report)
            data=cache[report]
            if export['benchmark']=='bigcodebench':
                evaluations=data['eval'].get(key[0],[])
                if len(evaluations)!=1:raise ValueError('Expected one official candidate evaluation per task/seed')
                case=evaluations[0]
                if case['solution']!=p['solution']:raise ValueError('Official evaluation used different code; disable calibration or document transformation')
                status=case['status']
                if status=='pass':result['resolved']=True;result['outcome_type']='official_report';result['missing_reason']=None
                elif status in ('fail','timeout'):result['resolved']=False;result['outcome_type']='official_report';result['missing_reason']=None
                else:result['missing_reason']='unclassified_official_status:'+str(status)
            else:
                case=data[key[0]]
                patch=report.parent/'patch.diff'
                patch_value=p.get('model_patch')
                if case.get('infra_failure'):
                    result['missing_reason']='evaluator_infrastructure_failure'
                    result['outcome_type']='infrastructure_unknown'
                elif patch_value=='':
                    result['resolved']=False
                    result['outcome_type']='candidate_invalid_patch'
                    result['candidate_failure_reason']='empty_or_invalid_final_patch_format'
                elif not patch.exists() or patch.read_text(encoding='utf-8').rstrip('\n')!=patch_value.rstrip('\n'):
                    raise ValueError('Evaluated patch does not match exported prediction')
                elif type(case['resolved']) is not bool:raise ValueError('Invalid official resolved flag')
                else:
                    result['resolved']=case['resolved'];result['outcome_type']='official_report';result['missing_reason']=None
            result['report_sha256']=sha(report)
        elif export['benchmark']=='swebench':
            # The upstream harness may stop after patch validation and leave no
            # instance report. Use the run summary only to distinguish known
            # infrastructure/evaluator failures from an explicit empty patch.
            infra_ids=set(summary.get('infra_failure_ids',[]))
            error_ids=set(summary.get('error_ids',[]))
            patch_value=p.get('model_patch')
            patch_file=report.parent/'patch.diff'
            log_file=report.parent/'run_instance.log'
            native_rejection=(
                key[0] in error_ids and patch_value not in (None,'')
                and patch_file.exists() and _same_patch(patch_value, patch_file.read_text(encoding='utf-8'))
                and log_file.exists() and '>>>>> Patch Apply Failed' in log_file.read_text(encoding='utf-8', errors='replace')
            )
            if key[0] in infra_ids:
                result['missing_reason']='evaluator_infrastructure_failure';result['outcome_type']='infrastructure_unknown'
            elif native_rejection:
                result['resolved']=False;result['missing_reason']=None;result['outcome_type']='native_application_rejection'
                result['application_log_path']=str(log_file.resolve());result['application_log_sha256']=sha(log_file)
                result['patch_path']=str(patch_file.resolve());result['patch_sha256']=sha(patch_file)
            elif key[0] in error_ids and patch_value not in (None,''):
                result['missing_reason']='evaluator_error';result['outcome_type']='evaluator_error'
            elif patch_value=='':
                result['resolved']=False
                result['outcome_type']='candidate_invalid_patch'
                result['candidate_failure_reason']='empty_or_invalid_final_patch_format'
        if result['resolved'] is not None:result['missing_reason']=None
        rows.append(result)
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','export-manifest','reports','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();rows=collect(a.archive,a.export_manifest,a.reports)
    a.output.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    print(json.dumps({'assigned':len(rows),'classified_outcomes':sum(r['resolved'] is not None for r in rows),
                      'native_report_outcomes':sum(r['resolved'] is not None and r['outcome_type']=='official_report' for r in rows),
                      'resolved':sum(r['resolved'] is True for r in rows)}))


if __name__=='__main__':main()
