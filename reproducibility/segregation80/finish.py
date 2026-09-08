"""Finish the already-dispatched study: strict export, all native evaluations, analysis."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time

from .. import codex_subscription as c
from .prepare import ARM_NAMES


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('reproducibility/runs/segregation80-v1'))
    p.add_argument('--inputs',type=Path,default=Path('reproducibility/segregation80/inputs-v2'))
    p.add_argument('--manifest',type=Path,default=Path('reproducibility/segregation80/generation_manifest.json'))
    a=p.parse_args()
    root=a.root.resolve();inputs=a.inputs.resolve();manifest=a.manifest.resolve()
    gen=root/'generation';gate=root/'controls-v4/heldout200_control_gate.json'
    while c.read(gen/'status.json')['state']=='started':time.sleep(5)
    stage=root/'pipeline'
    stage.mkdir(exist_ok=False)

    def execute(name, args):
        argv=[sys.executable,'-X','utf8','-m',*map(str,args)]
        c.save(stage/(name+'.argv.json'),argv)
        with (stage/(name+'.stdout.log')).open('wb') as stdout,(stage/(name+'.stderr.log')).open('wb') as stderr:
            result=subprocess.run(argv,stdout=stdout,stderr=stderr)
        c.save(stage/(name+'.exit.json'),{'returncode':result.returncode,'finished_unix':time.time()})
        print(c.canonical({'stage':name,'returncode':result.returncode}).decode(),flush=True)
        if result.returncode:raise RuntimeError(f'{name} failed; complete logs retained')

    execute('export',['reproducibility.segregation80.collect','export','--archive',gen,'--inputs',inputs,'--gate',gate,'--manifest',manifest,'--out',root/'predictions'])
    for arm in ARM_NAMES:
        execute('native-'+arm,['reproducibility.heldout200.run_observed_native',
                '--dataset',inputs/'evaluator/evaluator_dataset.jsonl','--prepared',inputs/'input/prepared.jsonl',
                '--samples',root/'predictions'/(arm+'.jsonl'),'--output',root/'native'/arm,
                '--selection',inputs/'selection.json','--image','bcb-segregation80:v3',
                '--requirements','reproducibility/segregation80/environment/requirements.txt',
                '--dockerfile','reproducibility/segregation80/environment/Dockerfile'])
    execute('collect',['reproducibility.segregation80.collect','collect','--archive',gen,'--inputs',inputs,
                      '--export-dir',root/'predictions','--native-dir',root/'native','--gate-dir',gate.parent,
                      '--manifest',manifest,'--out',root/'analysis'])
    execute('analyze',['reproducibility.segregation80.analyze','--records',root/'analysis/candidate_records.jsonl',
                      '--selection',inputs/'selection.json','--out',root/'analysis/summary.json'])


if __name__=='__main__':main()
