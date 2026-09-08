"""Run one fixed SWE-bench development prediction through the pinned harness.

This launcher is intentionally narrow: it does not generate predictions and
does not alter the upstream evaluator, dataset, repository, or test patches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "pvlib__pvlib-python-1606"
UPSTREAM_COMMIT = "02e7a74ffd0b707aab73d203fe87bdc7c76afc8e"
CUSTOM_IMAGE = "swe-smoke-pvlib-numpy126:20260908"
CONTROLLER_IMAGE = "swe-smoke-controller:20260908-v3"
DEFAULT_DATASET = ROOT / "reproducibility/runs/swe-smoke-dev1/input/dev_custom_image.json"
DEFAULT_PROVENANCE = ROOT / "reproducibility/runs/swe-smoke-dev1/provenance.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_checked(args: list[str]) -> str:
    p = subprocess.run(args, check=True, capture_output=True, text=True)
    return p.stdout.strip()


def image_inspect(name: str) -> dict:
    raw = run_checked(["docker", "--context", "desktop-linux", "image", "inspect", name])
    return json.loads(raw)[0]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictions", type=Path, required=True, help="JSONL with one instance_id/model_patch record")
    p.add_argument("--out", type=Path, required=True, help="New empty output directory")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--outer-deadline", type=int, default=900)
    return p.parse_args()


def load_prediction(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(rows) != 1 or rows[0].get("instance_id") != TASK_ID:
        raise ValueError(f"predictions must contain exactly one record for {TASK_ID}")
    row = rows[0]
    if not isinstance(row.get("model_name_or_path"), str) or not row["model_name_or_path"]:
        raise ValueError("prediction model_name_or_path must be a non-empty string")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", row["model_name_or_path"]):
        raise ValueError("model_name_or_path must be a safe report label without path separators")
    patch = row.get("model_patch")
    if patch is not None and not isinstance(patch, str):
        raise ValueError("prediction model_patch must be a string or null")
    return row


def cleanup_owned(run_id: str, controller_name: str) -> None:
    task_name = f"sweb.eval.{TASK_ID.lower()}.{run_id}"
    subprocess.run(
        ["docker", "--context", "desktop-linux", "rm", "-f", controller_name, task_name],
        capture_output=True,
        text=True,
    )


def decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def equivalent_patch_bytes(left: bytes, right: bytes) -> bool:
    """Allow CRLF conversion and one evaluator-added final newline only."""
    left, right = left.replace(b"\r\n", b"\n"), right.replace(b"\r\n", b"\n")
    if left == right:
        return True
    return left.rstrip(b"\n") == right.rstrip(b"\n") and abs(len(left) - len(left.rstrip(b"\n")) - (len(right) - len(right.rstrip(b"\n")))) <= 1


def validate_join(report_dir: Path, task_id: str, model_label: str, patch_value: str | None, timed_out: bool) -> dict:
    results_path = report_dir / "results.json"
    report_path = report_dir / model_label / task_id / "report.json"
    task_dir = report_path.parent
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.is_file() else {}
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    task_report = report.get(task_id) if isinstance(report, dict) else None
    submitted_patch = (patch_value or "").encode("utf-8")
    report_patch = task_dir / "patch.diff"
    patch_equal = report_patch.is_file() and equivalent_patch_bytes(submitted_patch, report_patch.read_bytes())
    if isinstance(task_report, dict):
        report_flags = {key: task_report.get(key) for key in (
            "patch_is_None", "patch_exists", "patch_successfully_applied", "resolved", "infra_failure"
        )}
    else:
        report_flags = None
    artifact_hashes = {}
    for name in ("patch.diff", "eval.sh", "test_output.txt", "run_instance.log"):
        path = task_dir / name
        artifact_hashes[name] = sha256(path) if path.is_file() else None
    membership = task_id in results.get("completed_ids", []) + results.get("submitted_ids", []) + results.get("error_ids", []) + results.get("empty_patch_ids", [])
    infra_ids = set(results.get("infra_failure_ids", []))
    error_ids = set(results.get("error_ids", []))
    empty_patch_ids = set(results.get("empty_patch_ids", []))
    flags_valid = report_flags is not None and all(type(v) is bool for v in report_flags.values())
    task_exact = isinstance(task_report, dict) and set(report) == {task_id}
    log = task_dir / 'run_instance.log'
    log_text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    # The unchanged harness raises EvaluationError after all patch application
    # methods fail, before report.json exists. Preserve this as an application
    # rejection only when its exact submitted bytes and native marker agree.
    application_rejected = (not report_path.exists() and patch_equal and task_id in results.get('error_ids', [])
                            and task_id not in infra_ids
                            and '>>>>> Patch Apply Failed' in log_text and not timed_out)
    infrastructure_failure = task_id in infra_ids or (task_exact and task_report.get('infra_failure') is True)
    invalid_candidate_patch = (
        not timed_out
        and membership
        and not infrastructure_failure
        and not report_path.exists()
        and patch_value == ""
    )
    inconsistent_empty_patch_summary = task_id in empty_patch_ids and patch_value not in (None, "")
    candidate_failure = flags_valid and not task_report.get("infra_failure") and (
        not task_report.get("patch_successfully_applied") or not task_report.get("resolved")
    )
    evaluator_error = (
        not timed_out
        and membership
        and task_id in error_ids
        and not application_rejected
        and not invalid_candidate_patch
    )
    # A candidate with an explicitly empty patch is a failed candidate
    # once the evaluator records that it was submitted. A missing report for a
    # non-empty patch remains unknown: the evaluator may have failed before it
    # produced a trustworthy instance report. An absent prediction (None) does
    # not establish an observed empty model response.
    candidate_failure = candidate_failure or invalid_candidate_patch
    complete = results_path.is_file() and membership and not timed_out and not infrastructure_failure and not inconsistent_empty_patch_summary and (
        application_rejected or invalid_candidate_patch or (report_path.is_file() and task_exact and patch_equal and flags_valid
                                 and not task_report['infra_failure']))
    classification = ('native_application_rejection' if application_rejected else
                      'invalid_candidate_patch' if invalid_candidate_patch else
                      'candidate_test_or_patch_failure' if candidate_failure else 'completed') if complete else (
                      'evaluator_error' if evaluator_error and not infrastructure_failure and not inconsistent_empty_patch_summary else
                      'infrastructure_or_unknown')
    return {
        "run_id": report_dir.name,
        "task_id": task_id,
        "results_exists": results_path.is_file(),
        "report_exists": report_path.is_file(),
        "results_sha256": sha256(results_path) if results_path.is_file() else None,
        "report_sha256": sha256(report_path) if report_path.is_file() else None,
        "prediction_to_report_join": report_path.as_posix() if report_path.is_file() else None,
        "results_task_membership": membership,
        "report_task_id_exact": task_exact,
        "report_flags_valid": flags_valid,
        "native_application_rejection": application_rejected,
        "invalid_candidate_patch": invalid_candidate_patch,
        "evaluator_error": evaluator_error,
        "inconsistent_empty_patch_summary": inconsistent_empty_patch_summary,
        "patch_bytes_match": patch_equal,
        "report_flags": report_flags,
        "artifact_hashes": artifact_hashes,
        "candidate_status": "missing_patch" if patch_value is None else "empty_patch" if patch_value == "" else "submitted_patch",
        "classification": classification,
        "status": "complete" if complete else "missing",
    }


def main() -> int:
    ns = parse_args()
    prediction_path = ns.predictions.resolve()
    dataset_path = ns.dataset.resolve()
    out = ns.out.resolve()
    if not prediction_path.is_file() or not dataset_path.is_file():
        raise FileNotFoundError("predictions and dataset files must exist")
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"refusing non-empty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    prediction = load_prediction(prediction_path)
    snapshot = out / "input" / "predictions.jsonl"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(prediction_path.read_bytes())
    prediction_source_sha256 = sha256(prediction_path)
    prediction_snapshot_sha256 = sha256(snapshot)
    patch_value = prediction.get("model_patch")
    candidate_status = (
        "missing_patch" if "model_patch" not in prediction or patch_value is None
        else "empty_patch" if patch_value == ""
        else "submitted_patch"
    )
    provenance = json.loads(DEFAULT_PROVENANCE.read_text(encoding="utf-8"))

    source = (ROOT / "reproducibility/vendor/swebench").resolve()
    actual_commit = run_checked(["git", "-C", str(source), "rev-parse", "HEAD"])
    if actual_commit != UPSTREAM_COMMIT:
        raise RuntimeError(f"unexpected pinned source commit: {actual_commit}")
    clean = subprocess.run(
        ["git", "-C", str(source), "diff", "--quiet", "HEAD", "--"],
        capture_output=True,
        text=True,
    )
    if clean.returncode != 0:
        raise RuntimeError("pinned source checkout has tracked changes")
    original_dataset = ROOT / "reproducibility/data/swebench-lite/dev-00000-of-00001.parquet"
    expected_dataset = provenance["custom_input_hashes"]["dataset_json_sha256"]
    actual_dataset = sha256(dataset_path)
    if actual_dataset != expected_dataset:
        raise RuntimeError(f"custom dataset hash mismatch: {actual_dataset}")
    actual_parquet = sha256(original_dataset)
    if actual_parquet != provenance["dataset_parquet_sha256"]:
        raise RuntimeError(f"source parquet hash mismatch: {actual_parquet}")

    task_meta = image_inspect(CUSTOM_IMAGE)
    actual_image_id = task_meta["Id"]
    expected_image_id = provenance["custom_task_image"]["image_id"]
    if actual_image_id != expected_image_id:
        raise RuntimeError(f"custom task image mismatch: {actual_image_id}")
    frozen_image = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    frozen_rows = [row for row in frozen_image if row.get("instance_id") == TASK_ID]
    if len(frozen_rows) != 1 or frozen_rows[0].get("image") not in (CUSTOM_IMAGE, actual_image_id):
        raise RuntimeError("frozen custom dataset does not name the inspected task image")
    controller_meta = image_inspect(CONTROLLER_IMAGE)
    if controller_meta["Id"] != provenance["controller_image"]["image_id"]:
        raise RuntimeError("controller image ID mismatch")

    run_id = f"pred-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    controller_name = f"sweb.controller.{run_id}"
    task_name = f"sweb.eval.{TASK_ID.lower()}.{run_id}"
    controller_id = controller_meta["Id"]
    argv = [
        "docker", "--context", "desktop-linux", "run", "--rm", "--name", controller_name, "--network", "none",
        "--mount", f"type=bind,source={source},target=/workspace/swebench,readonly",
        "--mount", f"type=bind,source={dataset_path},target=/run/input/dataset.json,readonly",
        "--mount", f"type=bind,source={snapshot},target=/run/input/predictions.jsonl,readonly",
        "--mount", f"type=bind,source={out},target=/run/output",
        "--mount", "type=bind,source=//var/run/docker.sock,target=/var/run/docker.sock",
        "--workdir", "/run/output", "--env", "PYTHONPATH=/workspace/swebench",
        controller_id, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", "/run/input/dataset.json", "--split", "dev",
        "--predictions_path", "/run/input/predictions.jsonl", "--instance_ids", TASK_ID,
        "--max_workers", "1", "--timeout", "600", "--run_id", run_id,
    ]
    (out / "argv.json").write_text(json.dumps({"argv": argv, "run_id": run_id}, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "task_id": TASK_ID,
        "source_commit": actual_commit,
        "source_checkout": "git diff --quiet HEAD -- verified",
        "dataset_sha256": actual_dataset,
        "original_parquet_sha256": actual_parquet,
        "prediction_source_sha256": prediction_source_sha256,
        "prediction_snapshot_sha256": prediction_snapshot_sha256,
        "candidate_status": candidate_status,
        "custom_image_id": actual_image_id,
        "controller_image_id": controller_meta["Id"],
        "controller_name": controller_name,
        "task_container_name": task_name,
        "network": "controller none; child task network is unchanged upstream default",
        "model_calls": 0,
    }
    (out / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    timed_out = False
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=ns.outer_deadline)
        (out / "stdout.log").write_text(decode_output(proc.stdout), encoding="utf-8")
        (out / "stderr.log").write_text(decode_output(proc.stderr), encoding="utf-8")
        metadata["launcher_exit_code"] = proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        (out / "stdout.log").write_text(decode_output(e.stdout), encoding="utf-8")
        (out / "stderr.log").write_text(decode_output(e.stderr), encoding="utf-8")
        metadata["launcher_exit_code"] = None
        metadata["status"] = "outer_timeout"
    finally:
        cleanup_owned(run_id, controller_name)

    metadata['prediction_source_sha256_after'] = sha256(prediction_path)
    metadata['prediction_snapshot_sha256_after'] = sha256(snapshot)
    metadata['prediction_bytes_unchanged'] = (
        metadata['prediction_source_sha256_after'] == prediction_source_sha256
        == prediction_snapshot_sha256 == metadata['prediction_snapshot_sha256_after'])
    model_label = prediction["model_name_or_path"]
    join = validate_join(out / "logs/evaluation" / run_id, TASK_ID, model_label, patch_value, timed_out)
    (out / "join_validation.json").write_text(json.dumps(join, indent=2) + "\n", encoding="utf-8")
    metadata["join_status"] = join["status"]
    (out / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return 0 if metadata.get("launcher_exit_code") == 0 and join["status"] == "complete" and metadata['prediction_bytes_unchanged'] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"launcher error: {exc}", file=sys.stderr)
        raise SystemExit(2)
