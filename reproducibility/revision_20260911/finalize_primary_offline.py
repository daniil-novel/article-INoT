"""Wait for the existing primary finisher, then verify and package its evidence.

This operational wrapper never submits model requests, executes generated code,
repeats native evaluation, edits frozen sources, or publishes to GitHub. It uses
the previously reviewed analysis/publication entry points without changing them.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'reproducibility/runs/scale1000-luna-v1'
SENSITIVITY = STUDY / 'source-family-sensitivity'
ARMS = ('single_neutral', 'single_roles', 'multi_neutral', 'multi_roles', 'direct')
STAGES = ('export', *(f'native-{arm}-r{rep}' for rep in (101, 102, 103) for arm in ARMS), 'collect', 'analyze')


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def complete_stage_gate(study):
    """Cheap completion prerequisite; does not inspect candidate quality."""
    status = json.loads((study / 'generation/status.json').read_bytes())
    if status.get('state') != 'generation_finished' or (study / 'generation/DISPATCH.lock').exists():
        raise ValueError('Primary generation is not terminal')
    exits = {}
    for stage in STAGES:
        path = study / 'pipeline' / (stage + '.exit.json')
        if not path.is_file():
            raise ValueError('Missing completed stage: ' + stage)
        record = json.loads(path.read_bytes())
        if type(record.get('returncode')) is not int or record['returncode'] != 0:
            raise ValueError('Unsuccessful completed stage: ' + stage)
        exits[stage] = record
    return exits


def source_inventory():
    """Bind tracked processing code without reacting to later prose-only edits."""
    result = subprocess.run(['git', 'ls-files', '-z', '--', 'reproducibility/*.py'],
                            cwd=ROOT, check=True, capture_output=True)
    paths = [p for p in result.stdout.decode('utf-8').split('\0') if p
             and not p.startswith(('reproducibility/results/', 'reproducibility/runs/'))]
    if not paths:
        raise ValueError('No tracked processing source was found')
    paths.extend(['reproducibility/task_dependence/PROTOCOL.md',
                  'reproducibility/scale1000_luna/PROTOCOL.md',
                  'reproducibility/scale1000_luna/generation_manifest.json'])
    return {p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in sorted(paths)}


def confirm_finisher(pid):
    process = psutil.Process(pid)
    command = process.cmdline()
    if '-m' not in command or command[command.index('-m') + 1] != 'reproducibility.scale1000_luna.finish':
        raise ValueError('The supplied PID is not the existing primary finisher')
    if Path(process.cwd()).resolve() != ROOT:
        raise ValueError('The finisher belongs to another checkout')
    return process


def destination_gate(job, archive, tables):
    targets = [p.resolve() for p in (job, archive, tables, SENSITIVITY)]
    protected = (STUDY / 'generation', STUDY / 'native', STUDY / 'analysis',
                 ROOT / 'reproducibility/scale1000/inputs-v1',
                 ROOT / 'reproducibility/runs/scale1000-v1/controls-v3')
    for target in targets:
        if target == ROOT or not target.is_relative_to(ROOT):
            raise ValueError('Outputs must be new directories within this checkout')
        if target.exists():
            raise FileExistsError('Refusing to overwrite an existing output')
        for source in protected:
            if target == source or target.is_relative_to(source) or source.is_relative_to(target):
                raise ValueError('Output overlaps retained study evidence')
    for index, target in enumerate(targets):
        for other in targets[index + 1:]:
            if target == other or target.is_relative_to(other) or other.is_relative_to(target):
                raise ValueError('Output directories overlap')


def run(pid, job, archive, tables, *, check_only=False):
    job, archive, tables = (p.resolve() for p in (job, archive, tables))
    destination_gate(job, archive, tables)
    finisher = confirm_finisher(pid)
    identity = {'pid': pid, 'created_unix': finisher.create_time(),
                'module': 'reproducibility.scale1000_luna.finish'}
    commands = [
        ('source-family', ['reproducibility.task_dependence.sensitivity', '--study', 'factorial',
         '--run-root', str(STUDY), '--audit', str(ROOT / 'reproducibility/task_dependence/source-audit-v2'),
         '--output', str(SENSITIVITY)]),
        ('archive-and-full-replay', ['reproducibility.revision_20260911.publish_scale',
         '--root', str(STUDY), '--output', str(archive)]),
        ('assignment-tables', ['reproducibility.revision_20260911.render_assignment_tables',
         '--archive', str(archive), '--output', str(tables)]),
    ]
    sources = source_inventory()
    if check_only:
        return {'preflight': 'passed', 'finisher': identity, 'stages': [name for name, _ in commands],
                'tracked_source_files': len(sources), 'model_calls': False, 'outputs_created': False}
    lock = STUDY / 'OFFLINE_FINALIZATION.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    awake = False
    try:
        job.mkdir(parents=True)
        save(job / 'plan.json', {'finisher': identity, 'commands': commands,
             'source_sha256_lf': sources, 'model_calls': False,
             'native_or_generated_code_execution': False, 'github_publication': False,
             'scope': 'One completed primary study; main-paper integration remains after both studies and final reviews.'})
        (job / 'executed_wrapper.py').write_bytes(Path(__file__).read_bytes())
        if sys.platform == 'win32':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
            if not awake:
                raise RuntimeError('The offline continuation could not retain its sleep request')
        save(job / 'status.json', {'state': 'waiting_for_finisher', 'finisher': identity,
                                 'system_sleep_inhibited': awake, 'started_unix': time.time()})
        exit_code = None
        while finisher.is_running():
            try:
                exit_code = finisher.wait(timeout=55)
                break
            except psutil.TimeoutExpired:
                # Expiry is not completion. is_running also detects PID reuse;
                # after the original exits, the full stage gate remains required.
                continue
        save(job / 'finisher_exit.json', {'exit_code': exit_code, 'observed_unix': time.time()})
        if exit_code not in (0, None):
            raise RuntimeError('The original finisher exited unsuccessfully')
        save(job / 'completed_stage_gate.json', complete_stage_gate(STUDY))
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        for name, arguments in commands:
            if source_inventory() != sources:
                raise RuntimeError('Processing source changed after the continuation was scheduled')
            save(job / 'status.json', {'state': 'running_offline_stage', 'stage': name,
                                     'started_unix': time.time(), 'model_calls': False})
            with (job / (name + '.stdout.log')).open('x', encoding='utf-8') as stdout, \
                 (job / (name + '.stderr.log')).open('x', encoding='utf-8') as stderr:
                result = subprocess.run([sys.executable, '-X', 'utf8', '-m', *arguments],
                                        cwd=ROOT, env=environment, stdout=stdout, stderr=stderr)
            save(job / (name + '.exit.json'), {'returncode': result.returncode, 'finished_unix': time.time()})
            if result.returncode:
                raise RuntimeError('Offline stage failed; retained output requires review: ' + name)
        status = {'state': 'completed', 'finished_unix': time.time(), 'model_calls': False,
                  'archive': str(archive.relative_to(ROOT)), 'tables': str(tables.relative_to(ROOT)),
                  'paper_integrated': False, 'github_published': False, 'visual_review_completed': False}
        save(job / 'status.json', status)
        return status
    except BaseException as error:
        if job.exists():
            save(job / 'status.json', {'state': 'stopped_without_retry', 'error': str(error),
                                     'observed_unix': time.time(), 'model_calls': False})
        raise
    finally:
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        if lock.exists() and lock.read_text(encoding='utf-8') == str(os.getpid()):
            lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-pid', type=int, required=True)
    for name in ('job', 'archive', 'tables'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.wait_pid, args.job, args.archive, args.tables, check_only=args.check_only)))
