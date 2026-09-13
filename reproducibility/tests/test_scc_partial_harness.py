import hashlib, json
from pathlib import Path
import pytest
from reproducibility.scc2000.partial_runner import validate_setup
from reproducibility.scc2000.partial_report import report
from reproducibility.scc2000.partial_candidate_audit import audit


@pytest.fixture(autouse=True)
def frozen_environment(monkeypatch):
    monkeypatch.setattr('reproducibility.scc2000.partial_runner.environment_from_gate', lambda _: {'image_id': 'sha256:frozen'})

def prepared(tmp_path, n=396):
    files={}
    for name in ('dataset','prepared','selection','control_gate'):
        p=tmp_path/name; p.write_text(name, encoding='utf-8'); files[name]=str(p); files[name+'_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    assigned=[f'BigCodeBench/{i}' for i in range(145)]
    selection=Path(files['selection']); selection.write_text(json.dumps({'assigned_task_ids': assigned})); files['selection_sha256']=hashlib.sha256(selection.read_bytes()).hexdigest()
    gate=Path(files['control_gate']); gate.write_text(json.dumps({'controls_complete':True,'image_id':'sha256:frozen','evaluable_task_ids': assigned})); files['control_gate_sha256']=hashlib.sha256(gate.read_bytes()).hexdigest()
    groups=[]; hashes={}; left=n
    for rep,count in ((101,140),(102,145),(103,111)):
        count=min(count,left); left-=count; p=tmp_path/f'{rep}.jsonl'; rows=[]
        for i in range(count):
            task=f'BigCodeBench/{i}'; code=f'def task_func(): return {i}'; rows.append({'task_id':task,'solution':code}); hashes[f'{rep}:{task}:a{rep}-{i}']=hashlib.sha256(code.encode()).hexdigest()
        p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n'); groups.append({'replicate_id':rep,'samples':str(p),'count':count,'native_outcome':'unassigned'})
    files.update({'frozen_image_id':'sha256:frozen','control_environment': {'image_id':'sha256:frozen'},'groups':groups,'candidate_source_hashes':hashes}); return files

def test_source_tampering_fails(tmp_path):
    s=prepared(tmp_path); Path(s['dataset']).write_text('tampered');
    with pytest.raises(ValueError, match='dataset'): validate_setup(s)

def test_tester_solution_or_hash_mismatch_fails(tmp_path):
    s=prepared(tmp_path); p=Path(s['groups'][0]['samples']); p.write_text(p.read_text().replace('def task_func','def check'))
    with pytest.raises(ValueError, match='solution'): validate_setup(s)

def test_identity_and_count_mismatch_fail(tmp_path):
    s=prepared(tmp_path); s['groups'][0]['count'] += 1
    with pytest.raises(ValueError, match='count'): validate_setup(s)

def test_wrong_gate_or_image_fails(tmp_path):
    s=prepared(tmp_path); s['frozen_image_id']='sha256:other'
    with pytest.raises(ValueError, match='gate'): validate_setup(s)

def test_missing_report_is_not_a_failure(tmp_path):
    s=prepared(tmp_path); p=tmp_path/'setup.json'; p.write_text(json.dumps(s))
    result=report(p)
    assert len(result['records']) == 396
    assert sum(g['status_counts']['unknown'] for g in result['groups']) == 396
    assert all(r['diagnostic_quality'] is None and r['primary_scc_quality'] is None for r in result['records'])


def test_repeated_tasks_across_groups_are_valid(tmp_path):
    validate_setup(prepared(tmp_path))


def test_native_allocation_order_is_required(tmp_path):
    s=prepared(tmp_path); p=Path(s['groups'][0]['samples'])
    p.write_text('\n'.join(reversed(p.read_text().splitlines()))+'\n')
    with pytest.raises(ValueError, match='ordered subset'): validate_setup(s)


def test_timeout_and_invalid_group_stay_distinct(tmp_path, monkeypatch):
    s=prepared(tmp_path); p=tmp_path/'setup.json'; p.write_text(json.dumps(s))
    def validator(folder, expected, env):
        valid=folder.name!='replicate-103'
        statuses={task: ('timeout' if i==0 else 'pass') for i,task in enumerate(expected)}
        return {'ok':valid,'statuses':statuses,'errors':[] if valid else ['tampered native report'],'report_sha256':'fixture'}
    monkeypatch.setattr('reproducibility.scc2000.partial_report.validate_native',validator)
    result=report(p)
    assert sum(g['status_counts']['timeout'] for g in result['groups'])==2
    assert sum(g['status_counts']['unknown'] for g in result['groups'])==111
    assert all(r['primary_scc_quality'] is None for r in result['records'])


def test_developer_input_is_selected_and_extra_input_rejected(tmp_path):
    root=tmp_path/'assignments'; d=root/'cell1'; source=d/'generated_tests/000'; source.mkdir(parents=True)
    cell={'id':'cell1','task_id':'BigCodeBench/1','replicate_id':101,'method':'scc_author_2024_codex_transport'}
    status={'state':'infrastructure_failure','reason':'container unavailable'}
    (d/'cell.json').write_text(json.dumps(cell)); (d/'status.json').write_text(json.dumps(status))
    program='def task_func(): return 2\n'; tester='def check(candidate): print(candidate())\n'
    (source/'input.json').write_text(json.dumps({'code':program,'report':tester}))
    manifest=tmp_path/'selection.json'; manifest.write_text(json.dumps({'selected_cells':[cell]}))
    inv=tmp_path/'inventory.json'; files={p.relative_to(d).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()}
    inv.write_text(json.dumps({'assignments':[{'id':'cell1','status_sha256':files['status.json'],'files_sha256':files}]}))
    result=audit(root,manifest,tmp_path/'audit',inv,expected_failures=1)
    assert (tmp_path/'audit/cell1/developer_program.py').read_bytes()==program.encode()
    assert result['records'][0]['developer_program_sha256']==hashlib.sha256(program.encode()).hexdigest()
    extra=d/'generated_tests/001'; extra.mkdir(); (extra/'input.json').write_text(json.dumps({'code':tester,'report':tester}))
    with pytest.raises(ValueError,match='outside the frozen inventory'): audit(root,manifest,tmp_path/'audit2',inv,expected_failures=1)
