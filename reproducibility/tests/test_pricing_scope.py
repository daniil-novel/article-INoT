import json

import pytest

from reproducibility.revision_20260911.pricing_scope import audit, verify_saved, write_sidecar


def _write_turn(generation, name, events):
    path = generation / "turns" / name / "events.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return path


def _completion(input_tokens=10, cached_input_tokens=2, output_tokens=5, **extra):
    usage = {"input_tokens": input_tokens, "cached_input_tokens": cached_input_tokens,
             "output_tokens": output_tokens, **extra}
    return {"type": "turn.completed", "usage": usage}


def test_audit_marks_exact_threshold_standard_scope(tmp_path):
    _write_turn(tmp_path, "exact", [_completion(input_tokens=272000, cache_write_input_tokens=0)])
    result = audit(tmp_path)
    row = result["records"][0]
    assert row["usage_status"] == "valid"
    assert row["long_context_gt_272000"] is False
    assert result["summary"]["claimed_complete_base_valuation_usd"] is not None


def test_audit_flags_threshold_exceedance_without_corrected_cost(tmp_path):
    _write_turn(tmp_path, "over", [_completion(input_tokens=272001)])
    result = audit(tmp_path)
    assert result["summary"]["long_context_gt_272000_turns"] == 1
    assert result["summary"]["claimed_complete_base_valuation_usd"] is None
    assert result["summary"]["long_context_tariff_corrected_cost"] is None


@pytest.mark.parametrize(
    ("extra", "state"),
    [({}, "not_reported"), ({"cache_write_input_tokens": 0}, "reported_zero"),
     ({"cache_write_input_tokens": 3}, "reported_nonzero")],
)
def test_cache_write_state_distinguishes_absent_zero_and_nonzero(tmp_path, extra, state):
    _write_turn(tmp_path, state, [_completion(**extra)])
    row = audit(tmp_path)["records"][0]
    assert row["cache_write_state"] == state
    assert row["invalid_reasons"] == []
    if state == "not_reported":
        assert audit(tmp_path)["summary"]["complete_standard_scope_claim"] is False


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": True, "cached_input_tokens": 0, "output_tokens": 1},
        {"input_tokens": -1, "cached_input_tokens": 0, "output_tokens": 1},
        {"input_tokens": 5, "cached_input_tokens": 6, "output_tokens": 1},
        {"input_tokens": 5, "cached_input_tokens": 0, "output_tokens": 1, "cache_write_input_tokens": True},
    ],
)
def test_invalid_usage_is_retained_and_complete_claim_withheld(tmp_path, usage):
    _write_turn(tmp_path, "invalid", [{"type": "turn.completed", "usage": usage}])
    result = audit(tmp_path)
    row = result["records"][0]
    assert row["usage_status"] in {"unknown", "rejected"}
    assert row["invalid_reasons"]
    assert result["summary"]["claimed_complete_base_valuation_usd"] is None


def test_duplicate_completion_is_rejected(tmp_path):
    _write_turn(tmp_path, "duplicate", [_completion(), _completion()])
    row = audit(tmp_path)["records"][0]
    assert row["usage_status"] == "rejected"
    assert "duplicate_turn_completed" in row["invalid_reasons"]


def test_no_completion_is_unknown(tmp_path):
    _write_turn(tmp_path, "missing", [{"type": "turn.started"}])
    row = audit(tmp_path)["records"][0]
    assert row["usage_status"] == "unknown"
    assert "no_turn_completed" in row["invalid_reasons"]


def test_missing_events_file_is_retained_as_unknown(tmp_path):
    (tmp_path / "turns" / "turn-without-events").mkdir(parents=True)
    result = audit(tmp_path)
    assert result["summary"]["events_files_missing"] == 1
    assert result["summary"]["unknown_usage_turns"] == 1
    assert result["summary"]["rejected_usage_turns"] == 0
    assert result["records"][0]["invalid_reasons"] == ["events_file_missing"]


def test_sidecar_verification_is_relocation_safe_and_detects_tamper(tmp_path):
    original = tmp_path / "original"; original.mkdir()
    _write_turn(original, "turn", [_completion(cache_write_input_tokens=0)])
    sidecar = tmp_path / "audit.json"
    write_sidecar(original, sidecar)
    relocated = tmp_path / "relocated"
    original.rename(relocated)
    verified = verify_saved(relocated, sidecar)
    assert verified["generation_layout"] == "scale_turns"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["records"][0]["input_tokens"] += 1
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="differs"):
        verify_saved(relocated, sidecar)


def test_scc_turn_layout_replays_without_checkout_and_refuses_overwrite(tmp_path):
    import shutil
    import subprocess
    import sys
    from reproducibility.revision_20260911 import pricing_scope
    archive = tmp_path / 'archive'
    folder = archive / 'generation/assignments/fixture/turns/000'
    folder.mkdir(parents=True)
    (folder / 'events.jsonl').write_text(json.dumps(_completion(cache_write_input_tokens=0)) + '\n')
    sidecar = archive / 'pricing_scope.json'
    write_sidecar(archive / 'generation', sidecar)
    with pytest.raises(FileExistsError):
        write_sidecar(archive / 'generation', sidecar)
    copied = archive / 'pricing_scope.py'
    shutil.copyfile(pricing_scope.__file__, copied)
    moved = tmp_path / 'moved'; archive.rename(moved)
    outside = tmp_path / 'outside'; outside.mkdir()
    result = subprocess.run([sys.executable, str(moved / 'pricing_scope.py'),
        '--generation', str(moved / 'generation'), '--verify', str(moved / 'pricing_scope.json')],
        cwd=outside, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['valid_usage_turns'] == 1
    assert not list(moved.rglob('__pycache__'))


def test_malformed_event_cannot_support_complete_pricing_scope(tmp_path):
    path = _write_turn(tmp_path, 'malformed', [[], _completion(cache_write_input_tokens=0)])
    result = audit(tmp_path)
    assert result['summary']['rejected_usage_turns'] == 1
    assert result['summary']['unknown_usage_turns'] == 0
    assert not result['summary']['complete_standard_scope_claim']
    path.write_text('{broken JSON\n' + json.dumps(_completion(cache_write_input_tokens=0)))
    assert audit(tmp_path)['summary']['rejected_usage_turns'] == 1


def test_completed_real_dev9_scope_replays_from_retained_events():
    from pathlib import Path
    repository = Path(__file__).resolve().parents[2]
    result = verify_saved(repository / 'reproducibility/results/20260911_scc_comparison_dev9/generation',
        repository / 'reproducibility/revision_20260911/scc_dev9_pricing_scope.json')
    assert result['summary']['turn_files'] == 18
    assert result['summary']['max_input_tokens'] == 4476
    assert result['summary']['base_valuation_usd_valid_turns'] == pytest.approx(0.02301176)
