"""Wait for the authorized generator, then schedule native groups in parallel.

No model calls, retries, quota resets or publication occur in this wrapper.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import psutil

ROOT=Path(__file__).resolve().parents[2]


def check_process(process: psutil.Process, created: float, root: Path=ROOT) -> None:
    args=process.cmdline()
    if abs(process.create_time()-created)>.01 or Path(process.cwd()).resolve()!=root:
        raise ValueError('Generator process identity changed')
    index=args.index('-m') if '-m' in args else -1
    if index<0 or args[index+1:index+3]!=['reproducibility.scc2000.continuation','generate']:
        raise ValueError('PID is not the authorized SCC continuation')


def save(path: Path, value: dict) -> None:
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--created',type=float,required=True)
    parser.add_argument('--job',type=Path,required=True)
    a=parser.parse_args(); job=a.job.resolve()
    process=psutil.Process(a.pid);check_process(process,a.created)
    job.mkdir(parents=True,exist_ok=False)
    tracked=['reproducibility/scc2000/'+name for name in ('finish.py','analyze.py','queue_finish.py','AMENDMENT.md','parallel_finish.py','queue_finish_parallel.py')]
    subprocess.run(['git','ls-files','--error-unmatch',*tracked],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
    subprocess.run(['git','diff','--quiet','HEAD','--',*tracked],cwd=ROOT,check=True)
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in tracked}
    argv=[str(ROOT/'tmp/revision/replay-venv/Scripts/python.exe'),'-X','utf8','-m','reproducibility.scc2000.parallel_finish',
        '--root',str(ROOT/'reproducibility/runs/scc1000-luna-v1'),
        '--inputs',str(ROOT/'reproducibility/scale1000/inputs-v1'),
        '--gate-dir',str(ROOT/'reproducibility/runs/scale1000-v1/controls-v3'),
        '--manifest',str(ROOT/'reproducibility/revision_20260911/scc_manifest.json'),
        '--selection-manifest',str(ROOT/'reproducibility/scc2000/freeze-v3/selection_manifest.json')]
    save(job/'provenance.json',{'queue_pid':os.getpid(),'generator_pid':a.pid,'generator_created':a.created,'source_hashes':hashes,'argv':argv})
    if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        save(job/'status.json',{'state':'waiting_for_generation','started_unix':time.time()})
        while process.is_running():
            try: process.wait(timeout=30)
            except psutil.TimeoutExpired: continue
            break
        for name,sha in hashes.items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:raise ValueError('Queued source changed: '+name)
        status=ROOT/'reproducibility/runs/scc1000-luna-v1/generation/continuation_status.json'
        if not status.is_file() or json.loads(status.read_bytes()).get('state')!='completed':
            raise ValueError('Selected generation is incomplete; no automatic resume')
        save(job/'status.json',{'state':'native_and_analysis','started_unix':time.time()})
        with (job/'finish.stdout.log').open('xb') as out,(job/'finish.stderr.log').open('xb') as err:
            result=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
        save(job/'finish.exit.json',{'returncode':result.returncode,'finished_unix':time.time()})
        if result.returncode:raise RuntimeError('Native/analysis stage failed; inspect retained logs')
        save(job/'status.json',{'state':'completed','finished_unix':time.time(),'paper_integrated':False,'published':False})
    except BaseException as exc:
        save(job/'status.json',{'state':'stopped','reason':str(exc),'finished_unix':time.time()})
        raise
    finally:
        if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':main()
