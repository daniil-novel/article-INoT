"""Wait for the selected SCC evaluation, then audit retained partial programs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import psutil

ROOT = Path(__file__).resolve().parents[2]


def save(path: Path, value: dict) -> None:
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--created', type=float, required=True)
    parser.add_argument('--job', type=Path, required=True)
    args = parser.parse_args()
    process = psutil.Process(args.pid)
    if abs(process.create_time()-args.created) > .01 or Path(process.cwd()).resolve() != ROOT:
        raise ValueError('native queue identity changed')
    if 'reproducibility.scc2000.queue_finish_parallel' not in process.cmdline():
        raise ValueError('PID is not the authorized native queue')
    job = args.job.resolve(); job.mkdir(parents=True, exist_ok=False)
    files = [ROOT / 'reproducibility/scc2000' / (name+'.py')
             for name in ('partial_candidate_audit', 'partial_setup', 'partial_runner', 'partial_report', 'queue_partial')]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    setup = ROOT / 'reproducibility/runs/scc-partial-programs-20260913/setup.json'
    setup_hash = hashlib.sha256(setup.read_bytes()).hexdigest()
    argv = [str(ROOT / 'tmp/revision/replay-venv/Scripts/python.exe'), '-X', 'utf8', '-m',
        'reproducibility.scc2000.partial_runner', '--setup', str(setup), '--image', 'bcb-scale1000:v2',
        '--requirements', 'reproducibility/scale1000/environment-v2/requirements.txt',
        '--dockerfile', 'reproducibility/scale1000/environment-v2/Dockerfile', '--run']
    save(job/'provenance.json', {'queue_pid': args.pid, 'queue_created': args.created,
         'source_hashes': hashes, 'argv': argv, 'setup_sha256': setup_hash})
    save(job/'status.json', {'state': 'waiting_for_main_native_queue', 'started_unix': time.time()})
    try:
        while process.is_running():
            try:
                process.wait(timeout=30)
            except psutil.TimeoutExpired:
                continue
        previous = ROOT / 'reproducibility/runs/scc1000-luna-v1/finish-queue-parallel-20260913/status.json'
        if json.loads(previous.read_bytes()).get('state') != 'completed':
            raise ValueError('main native queue did not finish successfully')
        for name, expected in hashes.items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
                raise ValueError('queued diagnostic source changed: '+name)
        if hashlib.sha256(setup.read_bytes()).hexdigest() != setup_hash:
            raise ValueError('queued diagnostic setup changed')
        save(job/'status.json', {'state': 'native_diagnostic', 'started_unix': time.time()})
        with (job/'native.stdout.log').open('xb') as stdout, (job/'native.stderr.log').open('xb') as stderr:
            result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
        save(job/'native.exit.json', {'returncode': result.returncode, 'finished_unix': time.time()})
        if result.returncode:
            raise ValueError('diagnostic native runner failed; evidence retained')
        report_argv = [argv[0], '-X', 'utf8', '-m', 'reproducibility.scc2000.partial_report',
            '--setup', str(setup), '--output', str(setup.parent/'diagnostic-report.json')]
        with (job/'report.stdout.log').open('xb') as stdout, (job/'report.stderr.log').open('xb') as stderr:
            subprocess.run(report_argv, cwd=ROOT, stdout=stdout, stderr=stderr, check=True)
        report = json.loads((setup.parent/'diagnostic-report.json').read_bytes())
        if not all(g['validation_ok'] for g in report['groups']):
            raise ValueError('diagnostic contains invalid or missing native evidence')
        save(job/'status.json', {'state': 'completed', 'programs': len(report['records']),
            'primary_imputation': None, 'finished_unix': time.time()})
    except BaseException as exc:
        save(job/'status.json', {'state': 'stopped', 'reason': str(exc), 'finished_unix': time.time()})
        raise


if __name__ == '__main__':
    main()
