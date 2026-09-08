"""Reconcile native upstream CLI evaluation with original samples and pilot controls."""
import argparse
import hashlib
import json
from pathlib import Path
try:
    from .bcb_pilot_evaluator import control_code
    from .factorial_runner import save
except ImportError:
    from bcb_pilot_evaluator import control_code
    from factorial_runner import save


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def jsonl(path):return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def check_run(folder, expected, dataset_sha):
    meta=read(folder/'run-metadata.json');supp=read(folder/'provenance-supplement.json')
    source=folder/'input/samples.jsonl';results=read(folder/'input/samples_eval_results.json')['eval']
    samples=jsonl(source)
    if len(samples)!=len(expected) or {r['task_id']:r['solution'] for r in samples}!=expected:raise ValueError('Native CLI samples differ from frozen solutions')
    if sha(source)!=meta['samples_sha256'] or sha(source)!=supp['post_evaluator_staged_samples_sha256']:raise ValueError('Native CLI input was changed')
    if set(results)!=set(expected):raise ValueError('Native CLI result denominator differs')
    if meta['official_dataset_sha256']!=dataset_sha:raise ValueError('Dataset changed')
    argv=meta['arguments']
    pos=argv.index('bigcodebench.evaluate')
    if argv[pos+1:pos+3]!=['instruct','full']:raise ValueError('Wrong benchmark mode')
    for key,value in {'--execution':'local','--calibrated':'False','--no_gt':'True','--parallel':'1','--network':'none','--cap-drop':'ALL'}.items():
        if argv[argv.index(key)+1]!=value:raise ValueError('Native evaluator settings differ')
    if '--read-only' not in argv or meta['calibrated'] is not False:raise ValueError('Native evaluation isolation/calibration differs')
    if not any('target=/run/input/samples.jsonl,readonly' in v for v in argv):raise ValueError('Samples are not mounted read-only')
    if meta['upstream_commit_verified']!='09dd993f46c3fbf3a799465bb96d524edcb0b199':raise ValueError('Upstream version changed')
    if sha(folder/'pip-freeze.txt')!=supp['package_freeze_sha256']:raise ValueError('Package record changed')
    statuses={}
    for task_id,entries in results.items():
        if len(entries)!=1 or entries[0]['solution']!=expected[task_id]:raise ValueError('Native report solved different code')
        statuses[task_id]=entries[0]['status']
    return {'raw_status_by_task':statuses,'image_id':meta['image_id_invoked'],
            'sample_sha256':sha(source),'report_sha256':sha(folder/'input/samples_eval_results.json'),
            'packages_sha256':supp['package_freeze_sha256']}


def crosscheck(predictions, native, controls, core, dataset):
    problems={r['task_id']:r for r in jsonl(dataset)}
    manifest=read(predictions/'export_manifest.json');reports={};common=None
    for group in manifest['groups']:
        # Paths in the source export manifest remain original; use their retained basename.
        samples=jsonl(predictions/Path(group['path'].replace('\\','/')).name)
        expected={r['task_id']:r['solution'] for r in samples}
        report=check_run(native/group['arm'],expected,sha(dataset))
        original=read(core/group['arm']/'pilot-predictions.json')
        raw={r['task_id']:r['status'] for r in original['records'] if r['control']=='prediction'}
        if report['raw_status_by_task']!=raw:raise ValueError('Official CLI and upstream-core statuses disagree')
        fingerprint=(report['image_id'],report['packages_sha256'])
        if common and common!=fingerprint:raise ValueError('Native environments differ across groups')
        common=fingerprint;reports[group['arm']]=report
    ids=list(next(iter(reports.values()))['raw_status_by_task']);control_reports={}
    for kind in ['gold','incorrect']:
        expected={task_id:control_code(problems[task_id],kind) for task_id in ids}
        result=check_run(controls/(kind+'-run'),expected,sha(dataset))
        if (result['image_id'],result['packages_sha256'])!=common:raise ValueError('Control environment differs')
        control_reports[kind]=result
    eligible=[task_id for task_id in ids if control_reports['gold']['raw_status_by_task'][task_id]=='pass' and control_reports['incorrect']['raw_status_by_task'][task_id] in {'fail','timeout'}]
    return {'audit':'passed','raw_status_matches':sum(len(r['raw_status_by_task']) for r in reports.values()),
            'assigned_tasks':len(ids),'evaluable_task_ids':eligible,'unavailable_task_ids':sorted(set(ids)-set(eligible)),
            'reports':reports,'controls':control_reports,
            'scope':'Native pinned BigCodeBench CLI, selective eight-task instruct run in a custom restricted environment; not a full benchmark score',
            'groundtruth_handling':'no_gt=True disables internal reference caching; separate native gold and incorrect runs determine eligibility'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['predictions','native','controls','core','dataset','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=crosscheck(a.predictions,a.native,a.controls,a.core,a.dataset);save(a.output,r)
    print(json.dumps({k:r[k] for k in ['audit','raw_status_matches','assigned_tasks','evaluable_task_ids','unavailable_task_ids']},indent=2))
