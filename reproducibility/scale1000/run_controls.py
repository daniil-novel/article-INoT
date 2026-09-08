"""Run both full-allocation native controls, retaining exclusive attempt folders."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from .. import codex_subscription as c

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--inputs',type=Path,default=Path('reproducibility/scale1000/inputs-v1'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--image',default='bcb-segregation80:v3')
    p.add_argument('--requirements',type=Path,default=Path('reproducibility/segregation80/environment/requirements.txt'))
    p.add_argument('--dockerfile',type=Path,default=Path('reproducibility/segregation80/environment/Dockerfile'))
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inputs=a.inputs.resolve()
    for kind in ('gold','incorrect'):
        argv=[sys.executable,'-X','utf8','-m','reproducibility.heldout200.run_observed_native',
              '--dataset',str(inputs/'evaluator/evaluator_dataset.jsonl'),'--prepared',str(inputs/'input/prepared.jsonl'),
              '--samples',str(inputs/'evaluator'/f'{kind}.jsonl'),'--output',str(out/kind),
              '--selection',str(inputs/'selection.json'),'--image',a.image,
              '--requirements',str(a.requirements),'--dockerfile',str(a.dockerfile),'--deadline-seconds','14400']
        c.save(out/f'{kind}.argv.json',argv)
        with (out/f'{kind}.launcher.stdout.log').open('wb') as stdout,(out/f'{kind}.launcher.stderr.log').open('wb') as stderr:
            result=subprocess.run(argv,stdout=stdout,stderr=stderr)
        c.save(out/f'{kind}.exit.json',{'returncode':result.returncode,'finished_unix':time.time()})
        print(c.canonical({'control':kind,'returncode':result.returncode}).decode(),flush=True)
        if result.returncode:raise RuntimeError(f'{kind} failed; all evidence retained')
    from .controls import build_gate
    gate=build_gate(out,inputs,inputs/'selection.json')
    print(c.canonical({'assigned':len(gate['assigned_task_ids']),'eligible':len(gate['evaluable_task_ids'])}).decode(),flush=True)

if __name__=='__main__':main()
