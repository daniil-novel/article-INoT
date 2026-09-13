import copy
import json
from pathlib import Path
import pytest
from reproducibility.scc2000.developer_diagnostic import ROOT, _load_utils, _old_record, extract_developer, sha256, validate_setup

@pytest.fixture
def utils():
    return _load_utils(ROOT / 'reproducibility/external_baselines/vendor/scc_2024/utils.py')

def case(tmp_path, bad_assembly=False):
    assignment = tmp_path/'generation/assignments/cell'
    developer = 'def task_func(x):\n    return x\n'
    tester = 'def check(candidate):\n    raise AssertionError("generated test must stay outside candidate")\n'
    def save(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')
    fence = chr(96)*3
    save(assignment/'turns/001/result.json', {'final_text': fence+'python\n'+developer+fence})
    save(assignment/'turns/002/result.json', {'final_text': fence+'python\n'+tester+fence})
    save(assignment/'turns/002.upstream_request.json', {'messages': []})
    combined = developer+'\n'+tester+'\ncheck('+('other' if bad_assembly else 'task_func')+')'
    path = assignment/'generated_tests/000/input.json'
    save(path, {'code': combined, 'report': ''})
    record = {'assignment_id': 'cell', 'task_id': 'BigCodeBench/1', 'method': 'scc_author_2024_codex_transport', 'replicate_id': 101, 'generated_test_input': str(path), 'generated_test_input_sha256': sha256(path), 'developer_program_sha256': sha256(combined.encode()), 'developer_program_bytes': len(combined.encode())}
    return record, developer

def test_actual_preparer_excludes_generated_checker(tmp_path, utils):
    source, developer = case(tmp_path)
    record = _old_record(source, tmp_path/'generation', tmp_path/'prepared', utils)
    assert Path(record['developer_program']).read_text() == developer
    assert record['developer_program_sha256'] == sha256(developer.encode())

def test_actual_preparer_rejects_changed_assembly(tmp_path, utils):
    source, _ = case(tmp_path, bad_assembly=True)
    with pytest.raises(ValueError, match='exact developer/tester assembly'):
        _old_record(source, tmp_path/'generation', tmp_path/'prepared', utils)

def test_analyst_plan_does_not_create_program(utils):
    with pytest.raises(ValueError, match='developer function'):
        extract_developer('{"plan": ["read input", "solve problem"]}', utils)

@pytest.fixture
def actual_setup():
    path = ROOT/'reproducibility/runs/scc-developer-diagnostic-20260913-v2/setup.json'
    if not path.is_file():
        pytest.skip('actual diagnostic preparation has not been frozen')
    return json.loads(path.read_text(encoding='utf-8'))

def test_actual_399_source_closure(actual_setup):
    validate_setup(actual_setup)

def test_actual_setup_rejects_sample_tampering(actual_setup, tmp_path):
    changed = copy.deepcopy(actual_setup)
    target = tmp_path/'samples.jsonl'
    target.write_text('{"task_id":"BigCodeBench/1","solution":"def task_func(): return 0"}\n')
    changed['groups'][0]['samples'] = str(target)
    changed['groups'][0]['samples_sha256'] = sha256(target)
    with pytest.raises(ValueError):
        validate_setup(changed)

def test_actual_setup_rejects_quality_imputation(actual_setup):
    changed = copy.deepcopy(actual_setup)
    changed['records'][0]['native_outcome'] = 'pass'
    with pytest.raises(ValueError, match='unknown'):
        validate_setup(changed)
