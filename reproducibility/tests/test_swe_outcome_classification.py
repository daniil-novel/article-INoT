import json
from pathlib import Path
from unittest.mock import patch

import pytest

from reproducibility.analyze_factorial import load_outcomes
from reproducibility.collect_outcomes import collect, sha

TASK = 'example__repo-1'
MODEL = 'mock/model'
PATCH = 'diff --git a/a b/a'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + '\n', encoding='utf-8')


def fixture(tmp_path, cells):
    archive = tmp_path/'archive'
    generations, groups = [], []
    for arm, response, exported, summary in cells:
        row = dict(task_id=TASK, arm=arm, seed=1, model=MODEL, cost_usd=.01,
                   total_tokens=100, truncated=False)
        if response is not None:
            row['final_text'] = response
        generations.append(row)
        pred = tmp_path/(arm+'.jsonl')
        write_json(pred, dict(instance_id=TASK, model_name_or_path=MODEL, model_patch=exported))
        groups.append(dict(model=MODEL, arm=arm, seed=1, path=str(pred), sha256=sha(pred), run_id=arm))
        if summary is not None:
            write_json(tmp_path/'reports'/arm/'results.json', summary)
    archive.mkdir()
    (archive/'results.jsonl').write_text(''.join(json.dumps(g)+'\n' for g in generations), encoding='utf-8')
    write_json(archive/'manifest.json', {'cells':generations})
    write_json(archive/'config.json', {'model':MODEL})
    export = tmp_path/'export.json'
    write_json(export, dict(benchmark='swebench', source_sha256=sha(archive/'results.jsonl'), groups=groups))
    return archive, export, tmp_path/'reports'


def collected(paths):
    # Isolate outcome classification from the separately tested generation audit.
    with patch('reproducibility.collect_outcomes.audit', return_value={'ok':True}):
        return collect(*paths)


def reload_outcomes(tmp_path, rows):
    path = tmp_path/'outcomes.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
    return load_outcomes(path, rows)


@pytest.mark.parametrize('response', ['', 'No patch can be produced.', '```diff\n\n```'])
def test_observed_invalid_format_keeps_failure_in_denominator(tmp_path, response):
    rows = collected(fixture(tmp_path, [('a', response, '', None)]))
    assert rows[0]['resolved'] is False
    assert rows[0]['outcome_type'] == 'candidate_invalid_patch'
    assert reload_outcomes(tmp_path, rows) == rows


@pytest.mark.parametrize('response', [None, '```diff\n'+PATCH+'\n```'])
def test_absent_response_or_corrupted_empty_export_is_unknown(tmp_path, response):
    rows = collected(fixture(tmp_path, [('a', response, '', None)]))
    assert rows[0]['resolved'] is None
    assert rows[0]['outcome_type'] == 'invalid_export_join'


def rejection_fixture(tmp_path):
    paths = fixture(tmp_path, [('a', '```diff\n'+PATCH+'\n```', PATCH, {'error_ids':[TASK]})])
    native = paths[2]/'a'/'mock__model'/TASK
    native.mkdir(parents=True)
    (native/'patch.diff').write_text(PATCH+'\n', encoding='utf-8')
    (native/'run_instance.log').write_text('>>>>> Patch Apply Failed', encoding='utf-8')
    return paths


def test_native_application_rejection_replays_without_instance_report(tmp_path):
    rows = collected(rejection_fixture(tmp_path))
    assert rows[0]['resolved'] is False
    assert rows[0]['outcome_type'] == 'native_application_rejection'
    assert reload_outcomes(tmp_path, rows) == rows


@pytest.mark.parametrize('kind', ['generation', 'prediction', 'patch', 'application_log', 'run_results'])
def test_modified_failure_evidence_cannot_enter_analysis(tmp_path, kind):
    rows = collected(rejection_fixture(tmp_path))
    proof = Path(rows[0][kind+'_path'])
    proof.write_bytes(proof.read_bytes()+b' ')
    with pytest.raises(ValueError, match='evidence changed'):
        reload_outcomes(tmp_path, rows)


def test_rehashed_export_still_must_match_observed_response(tmp_path):
    rows = collected(rejection_fixture(tmp_path))
    proof = Path(rows[0]['prediction_path'])
    value = json.loads(proof.read_text(encoding='utf-8'))
    value['model_patch'] = ''
    write_json(proof, value)
    rows[0]['prediction_sha256'] = sha(proof)
    with pytest.raises(ValueError, match='differs from the observed response'):
        reload_outcomes(tmp_path, rows)


def test_each_group_uses_its_own_summary_and_native_log(tmp_path):
    response = '```diff\n'+PATCH+'\n```'
    paths = fixture(tmp_path, [('a', response, PATCH, {'error_ids':[TASK]}),
                              ('b', response, PATCH, {'infra_failure_ids':[TASK]})])
    for arm in ('a','b'):
        native = paths[2]/arm/'mock__model'/TASK
        native.mkdir(parents=True)
        (native/'patch.diff').write_text(PATCH, encoding='utf-8')
        (native/'run_instance.log').write_text('>>>>> Patch Apply Failed', encoding='utf-8')
    rows = collected(paths)
    assert rows[0]['resolved'] is False
    assert rows[0]['outcome_type'] == 'native_application_rejection'
    assert rows[1]['resolved'] is None
    assert rows[1]['outcome_type'] == 'infrastructure_unknown'


def test_infrastructure_summary_prevents_empty_patch_failure(tmp_path):
    rows = collected(fixture(tmp_path, [('a', '', '', {'infra_failure_ids':[TASK]})]))
    assert rows[0]['resolved'] is None


def test_nonempty_patch_with_contradictory_empty_summary_is_unknown(tmp_path):
    rows = collected(fixture(tmp_path, [('a', '```diff\n'+PATCH+'\n```', PATCH, {'empty_patch_ids':[TASK]})]))
    assert rows[0]['resolved'] is None
    assert rows[0]['missing_reason'] == 'contradictory_empty_patch_summary'
