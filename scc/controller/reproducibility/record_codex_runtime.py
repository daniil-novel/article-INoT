"""Capture installed official CLI provenance without archiving login material."""
from pathlib import Path
import argparse
import hashlib
import os
import subprocess
import time
try:
    from .factorial_runner import read, save
except ImportError:
    from factorial_runner import read, save


def capture(archive, npm_root, runner):
    archive=archive.resolve();npm_root=npm_root.resolve()
    if (archive/'runtime_provenance.json').exists():raise ValueError('Refuse to replace original runtime evidence')
    runtime=read(archive/'runtime.json');package=npm_root/'node_modules/@openai/codex'
    if len(runtime['prefix'])!=2 or Path(runtime['prefix'][1]).resolve()!=package/'bin/codex.js':
        raise ValueError('Runtime prefix does not match selected official package')
    natives=[p for p in package.parent.rglob('*') if p.is_file() and p.name in {'codex.exe','codex'}]
    if len(natives)!=1:raise ValueError('Expected exactly one installed native Codex executable')
    native=natives[0];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    version=subprocess.check_output(runtime['prefix']+['--version'],text=True).strip()
    if version!=runtime['version']:raise ValueError('Installed runtime changed')
    names=['CODEX_HOME','OPENAI_BASE_URL','OPENAI_API_KEY','OPENAI_ORG_ID','OPENAI_ORGANIZATION','OPENAI_PROJECT','CODEX_API_KEY','OPENROUTER_API_KEY']
    save(archive/'runtime_provenance.json',{'recorded_unix':time.time(),
         'recording_phase':'explicit provenance capture; timestamp is not the generation start',
         'cli_version':version,'prefix':runtime['prefix'],'package_version':read(package/'package.json')['version'],
         'package_json_sha256':sha(package/'package.json'),'node_entry_sha256':sha(package/'bin/codex.js'),
         'native_executable_sha256':sha(native),'native_executable_path':str(native),
         'npm_lock_sha256':sha(npm_root/'package-lock.json'),
         'empty_working_directory':str(archive/'empty'),'instructions_path':str(archive/'instructions.txt'),
         'instructions_sha256':sha(archive/'instructions.txt'),
         'ambient_sensitive_setting_presence':{n:n in os.environ for n in names},
         'auth_material_archived':False,
         'note':'Parent setting presence at capture time; no secret values copied. The CLI uses the shared default login home.'})
    for name in ['package.json','package-lock.json']:
        (archive/('npm-'+name)).write_bytes((npm_root/name).read_bytes())
    (archive/'cli-package.json').write_bytes((package/'package.json').read_bytes())
    (archive/'runner_source.py').write_bytes(runner.read_bytes().replace(b'\r\n',b'\n'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--npm-root',type=Path,required=True)
    p.add_argument('--runner',type=Path,default=Path(__file__).with_name('codex_subscription.py'))
    a=p.parse_args();capture(a.archive,a.npm_root,a.runner)
