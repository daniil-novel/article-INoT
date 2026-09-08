import json
from pathlib import Path
from unittest.mock import patch

from reproducibility.swe_smoke.completion_evidence import audit_native, audit_prediction


def test_empty_prediction_is_valid_join_for_format_failure(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "predictions").mkdir(parents=True)
    cell = {"id": "cell1", "task_id": "pvlib__pvlib-python-1606", "arm": "direct", "replicate_id": 1}
    row = {"final_text": "an answer without a fenced diff"}
    pred = archive / "predictions" / "cell1.jsonl"
    pred.write_text(json.dumps({"instance_id": cell["task_id"], "model_name_or_path": "completion-direct--r1", "model_patch": ""}) + "\n")
    result = audit_prediction(archive, cell, row)
    assert result["prediction_status"] == "valid"
    assert result["format_valid"] is False


def test_missing_native_join_is_not_complete(tmp_path: Path):
    result = audit_native(tmp_path / "evaluation", None)
    assert result["native_status"] == "missing"


def test_complete_native_application_failure_is_resolved_false(tmp_path: Path):
    evaluation = tmp_path / "evaluation"
    (evaluation / "input").mkdir(parents=True)
    (evaluation / "logs" / "evaluation" / "run-1").mkdir(parents=True)
    prediction = evaluation / "source.jsonl"
    payload = {"instance_id": "pvlib__pvlib-python-1606", "model_name_or_path": "m", "model_patch": ""}
    raw = (json.dumps(payload) + "\n").encode()
    prediction.write_bytes(raw)
    (evaluation / "input" / "predictions.jsonl").write_bytes(raw)
    (evaluation / "provenance.json").write_text(json.dumps({"run_id": "run-1", "status": "completed"}))
    (evaluation / "argv.json").write_text("{}")
    recomputed = {
        "classification": "native_application_rejection",
        "status": "complete",
        "report_sha256": None,
        "results_sha256": "results",
        "report_task_id_exact": False,
        "report_flags_valid": False,
        "patch_bytes_match": True,
        "artifact_hashes": {},
    }
    (evaluation / "join_validation.json").write_text(json.dumps(recomputed))
    with patch("reproducibility.swe_smoke.evaluate_predictions.validate_join", return_value=recomputed):
        result = audit_native(evaluation, {"prediction_path": str(prediction)})
    assert result["native_status"] == "complete"
    assert result["classification"] == "native_application_rejection"
    assert result["resolved"] is False
