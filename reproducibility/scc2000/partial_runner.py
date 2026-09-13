"""Run prepared groups through the unchanged official observed-native evaluator."""
from __future__ import annotations
import argparse, json, subprocess, sys, hashlib
from pathlib import Path
from reproducibility.heldout200.evidence import environment_from_gate
from reproducibility.heldout200.run_observed_native import validate_observed_ids
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def validate_setup(s):
    for key, field in (('dataset','dataset_sha256'),('prepared','prepared_sha256'),('selection','selection_sha256'),('control_gate','control_gate_sha256')):
        p=Path(s[key]);
        if not p.is_file() or digest(p) != s[field]: raise ValueError(f'frozen {key} changed')
    gate=json.loads(Path(s['control_gate']).read_text(encoding='utf-8'))
    if not gate.get('controls_complete') or gate.get('image_id') != s.get('frozen_image_id'): raise ValueError('control gate identity changed')
    if environment_from_gate(Path(s['control_gate']).parent) != s.get('control_environment'):
        raise ValueError('raw control evidence differs from diagnostic environment')
    selection = json.loads(Path(s['selection']).read_text(encoding='utf-8'))
    groups=s.get('groups',[]); ids=[]; identities=[]
    for g in groups:
        if g.get('native_outcome') != 'unassigned' or not Path(g['samples']).is_file(): raise ValueError('group is not a prepared sample set')
        rows=[json.loads(x) for x in Path(g['samples']).read_text(encoding='utf-8').splitlines() if x.strip()]
        if len(rows) != g['count'] or len({r.get('task_id') for r in rows}) != len(rows): raise ValueError('group identity/count mismatch')
        validate_observed_ids([r['task_id'] for r in rows], selection['assigned_task_ids'])
        ids.extend(r.get('task_id') for r in rows)
        identities.extend((g['replicate_id'], r.get('task_id')) for r in rows)
    if sum(g['count'] for g in groups) != 396: raise ValueError('diagnostic must contain exactly 396 candidates')
    if len(set(identities)) != 396: raise ValueError('diagnostic identities must be unique by replicate and task')
    expected = s.get('candidate_source_hashes', {})
    if len(expected) != 396: raise ValueError('candidate source hash inventory is incomplete')
    for g in groups:
        for row in [json.loads(x) for x in Path(g['samples']).read_text(encoding='utf-8').splitlines() if x.strip()]:
            matches=[k for k in expected if k.startswith(f"{g['replicate_id']}:{row.get('task_id')}:")]
            if len(matches) != 1 or hashlib.sha256(str(row.get('solution','')).encode('utf-8')).hexdigest() != expected[matches[0]]: raise ValueError('sample solution differs from retained developer program')
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--setup',type=Path,required=True); p.add_argument('--image',required=True); p.add_argument('--requirements',type=Path,required=True); p.add_argument('--dockerfile',type=Path,required=True); p.add_argument('--deadline-seconds',type=int,default=7200); p.add_argument('--run',action='store_true'); a=p.parse_args()
    if not a.run: raise SystemExit('preparation only: pass --run after the native queue is released')
    s=json.loads(a.setup.read_text(encoding='utf-8')); validate_setup(s); root=a.setup.parent
    for path, key in ((a.requirements, 'requirements_sha256'), (a.dockerfile, 'dockerfile_sha256')):
        if not path.is_file() or digest(path) != s['control_environment'][key]:
            raise ValueError('diagnostic runtime source differs from frozen controls: ' + key)
    if a.run:
        actual = subprocess.run(['docker','--context','default','image','inspect',a.image,'--format','{{.Id}}'],check=True,capture_output=True,text=True).stdout.strip()
        if actual != s['frozen_image_id']: raise ValueError('image does not match frozen control gate')
    for g in s['groups']:
        out=root/'native'/f"replicate-{g['replicate_id']}"; out.mkdir(parents=True,exist_ok=True)
        argv=[sys.executable,'-m','reproducibility.heldout200.run_observed_native','--dataset',s['dataset'],'--prepared',s['prepared'],'--samples',g['samples'],'--output',str(out),'--selection',s['selection'],'--image',a.image,'--requirements',str(a.requirements),'--dockerfile',str(a.dockerfile),'--deadline-seconds',str(a.deadline_seconds)]
        subprocess.run(argv,check=True)
    return 0
if __name__=='__main__': raise SystemExit(main())
