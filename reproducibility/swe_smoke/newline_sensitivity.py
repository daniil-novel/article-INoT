"""Evaluate one fixed export-boundary sensitivity for every observed SWE patch.

Append exactly one final LF where absent. No hunk repair, code change, model
call or outcome-dependent selection is allowed. Original outcomes stay intact.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

from .. import codex_subscription as c
from .completion_evidence import audit_native


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sources=list(Path('reproducibility/results/20260908_codex_mini_swe_completion/predictions').glob('*.jsonl'))+list(Path('reproducibility/results/20260908_codex_mini_swe_dev1/predictions').glob('*.jsonl'))
    if len(sources)!=10:raise ValueError('Exactly ten original predictions required')
    plan=[]
    for src in sorted(sources):
        row=c.read(src);before=row['model_patch']
        modified=before if before.endswith('\n') else before+'\n'
        name=row['model_name_or_path']+'-final-lf'
        pred=out/'predictions'/(name+'.jsonl')
        pred.parent.mkdir(parents=True,exist_ok=True)
        pred.write_bytes(c.canonical({**row,'model_name_or_path':name,'model_patch':modified})+b'\n')
        plan.append({'source':src.as_posix(),'source_sha256':sha(src),'label':name,
                     'prediction':pred.relative_to(out).as_posix(),'prediction_sha256':sha(pred),
                     'transformation':'append exactly one final LF if absent','changed':modified!=before})
    c.save(out/'plan.json',{'scope':'post-observation export-format sensitivity, all ten patches, no new inference','predictions':plan})
    results=[]
    for item in plan:
        pred=out/item['prediction'];folder=out/'evaluations'/item['label']
        command=[sys.executable,'-X','utf8','-m','reproducibility.swe_smoke.evaluate_predictions','--predictions',str(pred),'--out',str(folder)]
        c.save(out/'commands'/(item['label']+'.json'),command)
        run=subprocess.run(command,capture_output=True)
        (out/'commands'/(item['label']+'.stdout.log')).write_bytes(run.stdout)
        (out/'commands'/(item['label']+'.stderr.log')).write_bytes(run.stderr)
        source=c.read(Path(item['source']));prediction=c.read(pred)
        if sha(Path(item['source']))!=item['source_sha256'] or sha(pred)!=item['prediction_sha256']:
            raise ValueError('Changed source or prediction')
        expected=source['model_patch'] if source['model_patch'].endswith('\n') else source['model_patch']+'\n'
        if prediction['model_patch']!=expected:raise ValueError('Unexpected transformation')
        result={**item,'returncode':run.returncode,**audit_native(folder,{'prediction_path':str(pred)})}
        results.append(result);c.save(out/'summary.json',{'rows':results,'complete':len(results)==10 and all(x.get('native_status')=='complete' for x in results)})
        print(c.canonical({'evaluated':len(results),'label':item['label'],'classification':result.get('classification'),'resolved':result.get('resolved')}).decode(),flush=True)


if __name__=='__main__':main()
