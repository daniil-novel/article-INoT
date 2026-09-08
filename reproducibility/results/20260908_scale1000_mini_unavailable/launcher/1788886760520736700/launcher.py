"""One local execution: dispatch, then evaluate only a finished allocation."""
import json
import ctypes
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
study = root / 'reproducibility/runs/scale1000-v1'
session = study / 'launcher' / str(time.time_ns())
session.mkdir(parents=True)
commands = {
    'generate': [sys.executable, '-X', 'utf8', '-m', 'reproducibility.scale1000.dispatch', 'run',
        '--inputs', 'reproducibility/scale1000/inputs-v1',
        '--gate-dir', 'reproducibility/runs/scale1000-v1/controls-v3',
        '--manifest', 'reproducibility/scale1000/generation_manifest.json',
        '--out', 'reproducibility/runs/scale1000-v1/generation', '--npm-root', 'tmp/codex-runtime'],
    'finish': [sys.executable, '-X', 'utf8', '-m', 'reproducibility.scale1000.finish',
        '--gate-dir', 'reproducibility/runs/scale1000-v1/controls-v3',
        '--image', 'bcb-scale1000:v2',
        '--requirements', 'reproducibility/scale1000/environment-v2/requirements.txt',
        '--dockerfile', 'reproducibility/scale1000/environment-v2/Dockerfile'],
}
(session / 'commands.json').write_text(json.dumps(commands, indent=2), encoding='utf-8')
(session / 'launcher.py').write_bytes(Path(__file__).read_bytes())
if sys.platform == 'win32':
    # Thread-scoped request expires when this launcher exits; display may sleep.
    awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    (session / 'sleep_request.json').write_text(json.dumps({'automatic_system_sleep_inhibited': awake}), encoding='utf-8')
for name, argv in commands.items():
    if name == 'finish':
        status = json.loads((study / 'generation/status.json').read_text(encoding='utf-8'))
        if status['state'] != 'generation_finished':
            print(json.dumps({'state': 'paused', 'generation_status': status}), flush=True)
            break
    result = subprocess.run(argv, cwd=root)
    info = {'stage': name, 'returncode': result.returncode, 'finished_unix': time.time()}
    (session / f'{name}.exit.json').write_text(json.dumps(info), encoding='utf-8')
    print(json.dumps(info), flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
if sys.platform == 'win32':
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
