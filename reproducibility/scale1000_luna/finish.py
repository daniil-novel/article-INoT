"""Evaluate every observed candidate after all assigned generation attempts end."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from .. import codex_luna_subscription as c
from .dispatch import REPEATS

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('reproducibility/runs/scale1000-luna-v1'))
    p.add_argument('--inputs',type=Path,default=Path('reproducibility/scale1000/inputs-v1'))
    p.add_argument('--gate-dir',type=Path,required=True)
    p.add_argument('--manifest',type=Path,default=Path('reproducibility/scale1000_luna/generation_manifest.json'))
    p.add_argument('--image',default='bcb-scale1000:v2')
    p.add_argument('--requirements',default='reproducibility/scale1000/environment-v2/requirements.txt')
    p.add_argument('--dockerfile',default='reproducibility/scale1000/environment-v2/Dockerfile')
    a=p.parse_args();root=a.root.resolve();gen=root/'generation';inputs=a.inputs.resolve()
    if c.read(gen/'status.json')['state']!='generation_finished':raise ValueError('All assignments must be attempted before final evaluation')
    stage=root/'pipeline';stage.mkdir(parents=True,exist_ok=True)
    def run(name,args):
        if (stage/f'{name}.exit.json').exists():
            if c.read(stage/f'{name}.exit.json')['returncode']==0:return
            raise ValueError('Previous stage failed; preserve and diagnose before continuing')
        argv=[sys.executable,'-X','utf8','-m',*map(str,args)]
        c.save(stage/f'{name}.argv.json',argv)
        with (stage/f'{name}.stdout.log').open('xb') as stdout,(stage/f'{name}.stderr.log').open('xb') as stderr:
            result=subprocess.run(argv,stdout=stdout,stderr=stderr)
        c.save(stage/f'{name}.exit.json',{'returncode':result.returncode,'finished_unix':time.time()})
        print(c.canonical({'stage':name,'returncode':result.returncode}).decode(),flush=True)
        if result.returncode:raise RuntimeError(f'{name} failed; raw evidence retained')
    common=['--archive',gen,'--inputs',inputs,'--gate-dir',a.gate_dir,'--manifest',a.manifest]
    run('export',['reproducibility.scale1000_luna.collect','export',*common,'--out',root/'predictions'])
    for rep in REPEATS:
        for arm in c.ARMS:
            key=f'{arm}-r{rep}'
            if not (root/'predictions'/f'{key}.jsonl').stat().st_size:continue
            run('native-'+key,['reproducibility.heldout200.run_observed_native','--dataset',inputs/'evaluator/evaluator_dataset.jsonl',
                '--prepared',inputs/'input/prepared.jsonl','--samples',root/'predictions'/f'{key}.jsonl',
                '--output',root/'native'/key,'--selection',inputs/'selection.json','--image',a.image,
                '--requirements',a.requirements,'--dockerfile',a.dockerfile,'--deadline-seconds','14400'])
    run('collect',['reproducibility.scale1000_luna.collect','collect',*common,'--predictions',root/'predictions','--native',root/'native','--out',root/'analysis'])
    run('analyze',['reproducibility.scale1000.analyze','--records',root/'analysis/candidate_records.jsonl','--selection',inputs/'selection.json','--out',root/'analysis/summary.json'])

if __name__=='__main__':main()
