"""Verify primary candidate programs, native reports, and control hashes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    ledger = {
        (row["arm"], int(row["replicate_id"]), row["task_id"]): row
        for row in jsonl(ROOT / "primary/assignment_outcomes.jsonl")
    }
    checked = 0
    for prediction_path in sorted((ROOT / "primary/evaluation/predictions").glob("*.jsonl")):
        arm, repeat_text = prediction_path.stem.rsplit("-r", 1)
        repeat = int(repeat_text)
        expected = {row["task_id"]: row["solution"] for row in jsonl(prediction_path)}
        native = ROOT / "primary/evaluation/native" / prediction_path.stem
        staged = {row["task_id"]: row["solution"] for row in jsonl(native / "input/samples.jsonl")}
        if staged != expected:
            raise SystemExit(f"staged programs differ from predictions: {prediction_path.stem}")

        meta = json.loads((native / "run-metadata.json").read_text(encoding="utf-8"))
        if meta.get("samples_source_sha256") != sha256(native / "input/samples.jsonl"):
            raise SystemExit(f"staged-program hash mismatch: {prediction_path.stem}")
        report_path = native / "input/samples_eval_results.json"
        if meta.get("report_sha256") != sha256(report_path):
            raise SystemExit(f"native-report hash mismatch: {prediction_path.stem}")
        report = json.loads(report_path.read_text(encoding="utf-8")).get("eval", {})
        if set(report) != set(expected):
            raise SystemExit(f"native-report task set mismatch: {prediction_path.stem}")
        for task_id, rows in report.items():
            if len(rows) != 1 or rows[0].get("solution") != expected[task_id]:
                raise SystemExit(f"evaluated program mismatch: {prediction_path.stem}/{task_id}")
            status = rows[0].get("status")
            record = ledger[(arm, repeat, task_id)]
            if status != record.get("native_status"):
                raise SystemExit(f"ledger status mismatch: {prediction_path.stem}/{task_id}")
            if record.get("quality") is not None and record.get("quality") is not (status == "pass"):
                raise SystemExit(f"ledger quality mismatch: {prediction_path.stem}/{task_id}")
            checked += 1

    gate_root = ROOT / "primary/evaluation/controls"
    gate = json.loads((gate_root / "heldout200_control_gate.json").read_text(encoding="utf-8"))
    for kind in ("gold", "incorrect"):
        paths = {
            "metadata": gate_root / kind / "run-metadata.json",
            "report": gate_root / kind / "input/samples_eval_results.json",
            "samples": gate_root / kind / "input/samples.jsonl",
        }
        for label, path in paths.items():
            if sha256(path) != gate[f"{kind}_{label}_sha256"]:
                raise SystemExit(f"control hash mismatch: {kind}/{label}")
    if not gate.get("controls_complete"):
        raise SystemExit("control gate is not complete")
    print(f"Verified {checked} candidate programs against native reports and the outcome ledger; control hashes passed.")


if __name__ == "__main__":
    main()
