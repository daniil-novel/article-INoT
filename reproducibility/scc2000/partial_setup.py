"""Prepare (without executing) the three native partial-candidate groups."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from .partial_candidate_audit import audit
from reproducibility.heldout200.evidence import environment_from_gate
from reproducibility.heldout200.run_observed_native import ids, sha256

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--selection-manifest', type=Path, required=True)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--control-gate', type=Path, required=True)
    a = p.parse_args(); out = a.output.resolve()
    for path in (a.dataset, a.prepared, a.selection, a.control_gate):
        if not path.is_file(): raise FileNotFoundError(path)
    gate = json.loads(a.control_gate.read_text(encoding='utf-8'))
    if not gate.get('controls_complete') or not gate.get('image_id'):
        raise ValueError('frozen control gate is incomplete')
    environment = environment_from_gate(a.control_gate.resolve().parent)
    selection = json.loads(a.selection.read_text(encoding='utf-8'))
    assigned = selection['assigned_task_ids']
    if gate['assigned_task_ids'] != assigned or ids(a.dataset) != assigned or ids(a.prepared) != assigned:
        raise ValueError('diagnostic source allocation differs from frozen controls')
    if sha256(a.dataset) != selection['evaluator_dataset_sha256'] or sha256(a.prepared) != selection['model_input_sha256']:
        raise ValueError('diagnostic data differ from frozen input hashes')
    summary = audit(a.source_root.resolve(), a.selection_manifest.resolve(), out / 'candidates', a.inventory.resolve())
    byrep = {}
    for row in summary['records']:
        byrep.setdefault(str(row['replicate_id']), []).append(row)
    groups = []
    for rep, rows in sorted(byrep.items()):
        group = out / f'replicate-{rep}'; group.mkdir(parents=True, exist_ok=True)
        samples = group / 'samples.jsonl'
        lines = []
        for row in sorted(rows, key=lambda x: assigned.index(x['task_id'])):
            code = (out / 'candidates' / row['assignment_id'] / 'developer_program.py').read_text(encoding='utf-8')
            lines.append(json.dumps({'task_id': row['task_id'], 'solution': code}, ensure_ascii=False))
        data = ('\n'.join(lines) + '\n').encode('utf-8')
        if samples.exists() and samples.read_bytes() != data: raise ValueError(f'group samples are immutable: {samples}')
        if not samples.exists(): samples.write_bytes(data)
        groups.append({'replicate_id': int(rep), 'samples': str(samples), 'count': len(rows), 'native_outcome': 'unassigned'})
    if len(summary['records']) != 396 or sum(g['count'] for g in groups) != 396:
        raise ValueError('diagnostic must contain exactly 396 candidates')
    identities = [(r['assignment_id'], r['task_id'], r['replicate_id']) for r in summary['records']]
    if len(set(identities)) != 396: raise ValueError('candidate identities are not unique')
    manifest = {'schema': 'scc-partial-programs-20260913-v2', 'native_executed': False,
                'quality_interpretation': 'diagnostic only; no SCC method score or imputation',
                'control_gate': str(a.control_gate.resolve()), 'dataset': str(a.dataset.resolve()),
                'prepared': str(a.prepared.resolve()), 'selection': str(a.selection.resolve()),
                'control_gate_sha256': digest(a.control_gate), 'dataset_sha256': digest(a.dataset),
                'prepared_sha256': digest(a.prepared), 'selection_sha256': digest(a.selection),
                'frozen_image_id': gate['image_id'], 'control_environment': environment, 'groups': groups,
                'candidate_source_hashes': {f"{r['replicate_id']}:{r['task_id']}:{r['assignment_id']}": r['developer_program_sha256'] for r in summary['records']}}
    target = out / 'setup.json'; encoded = (json.dumps(manifest, indent=2, ensure_ascii=False)+'\n').encode()
    if target.exists() and target.read_bytes() != encoded: raise ValueError(f'setup is immutable: {target}')
    if not target.exists(): target.write_bytes(encoded)
    print(json.dumps(manifest, ensure_ascii=False)); return 0
if __name__ == '__main__': raise SystemExit(main())
