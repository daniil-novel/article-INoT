"""Join complete generation archives to official benchmark reports, preserving missingness."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
try:
    from .factorial_runner import audit, read, canonical
except ImportError:
    from factorial_runner import audit, read, canonical


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(archive: Path, export_manifest: Path, reports: Path) -> list[dict]:
    check=audit(archive)
    if not check['ok']:raise ValueError(f"Generation archive failed audit: {check['errors']}")
    m=read(archive/'manifest.json');c=read(archive/'config.json');export=read(export_manifest)
    generations=[json.loads(line) for line in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    gen={(r['task_id'],r['arm'],r['seed']):r for r in generations}
    predictions={};report_sources={}
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
            if export['benchmark']=='bigcodebench':
                report_sources[key]=reports/(p.stem+'_eval_results.json')
            else:
                report_sources[key]=reports/group['run_id']/c['model'].replace('/','__')/tid/'report.json'
    expected={(cell['task_id'],cell['arm'],cell['seed']) for cell in m['cells']}
    if set(gen)!=expected or set(predictions)!=expected:raise ValueError('Prediction/manifest matrix mismatch')
    # Confirm exports were made from this exact generation file.
    if sha(archive/'results.jsonl')!=export['source_sha256']:raise ValueError('Export belongs to another generation file')
    rows=[]
    cache={}
    for key in sorted(expected):
        g=gen[key];p=predictions[key];report=report_sources[key]
        result={k:g[k] for k in ('task_id','arm','seed','model','cost_usd','total_tokens','truncated')}
        result.update(resolved=None,evaluator=export['benchmark'],report_path=str(report.resolve()),report_sha256=None,
                      missing_reason='official_report_missing')
        if report.exists():
            if report not in cache:cache[report]=read(report)
            data=cache[report]
            if export['benchmark']=='bigcodebench':
                evaluations=data['eval'].get(key[0],[])
                if len(evaluations)!=1:raise ValueError('Expected one official candidate evaluation per task/seed')
                case=evaluations[0]
                if case['solution']!=p['solution']:raise ValueError('Official evaluation used different code; disable calibration or document transformation')
                status=case['status']
                if status=='pass':result['resolved']=True
                elif status in ('fail','timeout'):result['resolved']=False
                else:result['missing_reason']='unclassified_official_status:'+str(status)
            else:
                case=data[key[0]]
                patch=report.parent/'patch.diff'
                if not patch.exists() or patch.read_text(encoding='utf-8').rstrip('\n')!=p['model_patch'].rstrip('\n'):
                    raise ValueError('Evaluated patch does not match exported prediction')
                if type(case['resolved']) is not bool:raise ValueError('Invalid official resolved flag')
                result['resolved']=case['resolved']
            result['report_sha256']=sha(report)
            if result['resolved'] is not None:result['missing_reason']=None
        rows.append(result)
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','export-manifest','reports','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();rows=collect(a.archive,a.export_manifest,a.reports)
    a.output.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    print(json.dumps({'assigned':len(rows),'officially_evaluated':sum(r['resolved'] is not None for r in rows),
                      'resolved':sum(r['resolved'] is True for r in rows)}))


if __name__=='__main__':main()
