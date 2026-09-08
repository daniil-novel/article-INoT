"""Inventory exact evidence bytes and optionally verify staged Git blob identity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

NAME='EVIDENCE_MANIFEST.json'


def entries(root):
    return [{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob('*')) if p.is_file() and p!=root/NAME]


def write(root):
    files=entries(root)
    (root/NAME).write_text(json.dumps({'algorithm':'SHA-256 of exact retained file bytes; no line-ending conversion','files':files},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return {'files':len(files),'bytes':sum(r['bytes'] for r in files)}


def verify(root):
    m=json.loads((root/NAME).read_text(encoding='utf-8'))
    files=m['files']
    if len({r['path'] for r in files})!=len(files):raise ValueError('Duplicate manifest path')
    expected={r['path']:(r['bytes'],r['sha256']) for r in files}
    actual={r['path']:(r['bytes'],r['sha256']) for r in entries(root)}
    if actual!=expected:raise ValueError('Missing, unexpected or changed evidence bytes')
    return {'files':len(files),'bytes':sum(r['bytes'] for r in files)}


def verify_git_index(root):
    repository=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
    prefix=root.resolve().relative_to(repository.resolve()).as_posix()
    raw=subprocess.check_output(['git','ls-files','--stage','-z','--',prefix],cwd=repository)
    staged={}
    for item in raw.split(b'\0'):
        if not item:continue
        meta,path=item.split(b'\t',1);mode,digest,stage=meta.split()
        if stage!=b'0' or mode!=b'100644':raise ValueError('Unexpected Git index mode/stage')
        staged[path.decode('utf-8')]=digest.decode()
    actual={p.relative_to(repository).as_posix():p for p in root.resolve().rglob('*') if p.is_file()}
    if set(staged)!=set(actual):raise ValueError('Staged evidence file set differs from retained archive')
    for name,p in actual.items():
        content=p.read_bytes();digest=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if staged[name]!=digest:raise ValueError('Git normalized or changed original evidence bytes: '+name)
    return {'staged_exact_blob_matches':len(actual)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('write','verify','verify-git-index'));p.add_argument('root',type=Path)
    a=p.parse_args();print(json.dumps({'write':write,'verify':verify,'verify-git-index':verify_git_index}[a.command](a.root.resolve())))
