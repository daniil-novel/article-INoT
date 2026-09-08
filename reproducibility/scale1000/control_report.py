"""Produce a readable, immutable summary of the frozen scale-1000 controls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..heldout200.evidence import environment_from_gate


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _excerpt(value: Any) -> str:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, dict):
        for item in value.values():
            text = _excerpt(item)
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = _excerpt(item)
            if text:
                return text
    return ""


def _status_report(path: Path) -> dict[str, dict[str, Any]]:
    data = _read(path)
    result = data.get("eval")
    if not isinstance(result, dict):
        raise ValueError(f"native report has no eval map: {path}")
    out = {}
    for task_id, rows in result.items():
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError(f"native report row is not unique: {task_id}")
        row = rows[0]
        out[task_id] = {"status": row.get("status"), "details": row.get("details", {})}
    return out


def make_report(gate_dir: Path, selection_path: Path, out: Path) -> None:
    if out.exists():
        raise ValueError("refusing to overwrite report directory")
    gate_path = gate_dir / "heldout200_control_gate.json"
    gate = _read(gate_path)
    # This performs the full hash, environment, argv, staged-input and report
    # validation before any readable summary is emitted.
    environment_from_gate(gate_dir)
    ids = gate.get("assigned_task_ids")
    if not isinstance(ids, list) or len(ids) != 1000 or len(set(ids)) != 1000:
        raise ValueError("gate must contain exactly 1,000 unique assigned IDs")
    selection = _read(selection_path)
    if selection.get("assigned_task_ids") != ids:
        raise ValueError("selection assigned IDs differ from strict control gate")
    old = selection.get("prior_primary_task_ids")
    new = selection.get("new_task_ids")
    if not isinstance(old, list) or not isinstance(new, list) or len(old) != 200 or len(new) != 800:
        raise ValueError("selection must contain prior 200 and new 800 task IDs")
    if set(old) & set(new) or set(old) | set(new) != set(ids):
        raise ValueError("selection subgroups do not partition the control gate")
    subgroup = {task: "prior200" for task in old} | {task: "new800" for task in new}
    reports = {
        "gold": _status_report(gate_dir / "gold" / "input" / "samples_eval_results.json"),
        "incorrect": _status_report(gate_dir / "incorrect" / "input" / "samples_eval_results.json"),
    }
    status_by_task = gate.get("status_by_task", {})
    rows = []
    diagnostics = []
    eligible_ids = set(gate.get("evaluable_task_ids", []))
    for task_id in ids:
        statuses = status_by_task.get(task_id, {})
        gold, incorrect = statuses.get("gold"), statuses.get("incorrect")
        eligible = task_id in eligible_ids
        rows.append({"task_id": task_id, "subgroup": subgroup[task_id], "gold": gold,
                     "incorrect": incorrect, "eligible": eligible})
        for kind in ("gold", "incorrect"):
            if statuses.get(kind) != "pass":
                raw = reports[kind].get(task_id, {})
                reason = _excerpt(raw.get("details"))[:300] or str(raw.get("status") or "missing status")
                diagnostics.append({"diagnostic": "control_nonpass", "task_id": task_id,
                                    "kind": kind, "status": statuses.get(kind),
                                    "reason_excerpt": reason,
                                    "raw_report_relative_to_gate": f"{kind}/input/samples_eval_results.json"})
    out.mkdir(parents=True)
    csv_path = out / "scale1000_control_status.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("task_id", "subgroup", "gold", "incorrect", "eligible"))
        writer.writeheader()
        writer.writerows(rows)
    counts = {"all": {"assigned": len(rows), "gold_pass": sum(r["gold"] == "pass" for r in rows),
                       "incorrect_fail": sum(r["incorrect"] == "fail" for r in rows),
                       "eligible": sum(r["eligible"] for r in rows)},
              "subgroups": {}}
    for label in ("prior200", "new800"):
        subset = [r for r in rows if r["subgroup"] == label]
        counts["subgroups"][label] = {"assigned": len(subset), "gold_pass": sum(r["gold"] == "pass" for r in subset),
                                       "incorrect_fail": sum(r["incorrect"] == "fail" for r in subset),
                                       "eligible": sum(r["eligible"] for r in subset)}
    report = {"schema": "scale1000-control-readable-v1", "gate_schema": gate.get("schema"),
              "gate_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest(),
              "assigned_task_ids": ids, "selection_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
              "counts": counts, "diagnostics": diagnostics,
              "diagnostic_policy": "non-pass evidence is flattened for readability only; eligibility is copied from the strict gate and never recomputed from diagnostics",
              "status_source": "status_by_task in strict immutable gate"}
    (out / "scale1000_control_report.json").write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").replace("\r\n", "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    make_report(args.gate_dir, args.selection, args.out)


if __name__ == "__main__":
    main()
