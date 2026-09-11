"""Offline verifier for the retained nine-cell SCC development gate.

This module only reads archived generation/native evidence.  It never invokes
the model or the native runner; ``validate_native`` checks retained reports and
hashes against the recorded control environment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1] if (_HERE.parents[1] / "sources").is_dir() else _HERE.parents[2]
sys.path.insert(0, str(ROOT / "sources" if (ROOT / "sources").is_dir() else ROOT))
if (ROOT / "sources/reproducibility").is_dir():
    sys.path.insert(0, str(ROOT / "sources/reproducibility"))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.scale_env.validate_native import validate_native  # noqa: E402
from reproducibility.heldout200.evidence import environment_from_gate  # noqa: E402
from reproducibility.revision_20260911 import scc_export, scc_dispatch  # noqa: E402


def _rows(root: Path) -> list[dict]:
    generation = root / "generation"; manifest = cli.read(generation / "manifest.json")
    tasks = {t["task_id"]: t for t in cli.tasks_from(root / "native-preparation" / "prepared.jsonl")}
    result = []
    for cell in manifest["cells"]:
        row = scc_export._row_for(generation / "assignments" / cell["id"], cell, tasks[cell["task_id"]])
        if not row.get("generation_complete") or not row.get("observed_candidate"):
            raise ValueError(f"Incomplete development assignment: {cell['id']}")
        result.append(row)
    return result


def verify(root: Path) -> dict:
    root = root.resolve(); summary = cli.read(root / "summary.json")
    if summary.get("gate") != "passed" or summary.get("assigned") != 9 or summary.get("native_checked") != 9:
        raise ValueError("Development summary is not the completed 9-cell gate")
    if summary.get("model_calls") != 18 or abs(float(summary.get("known_api_equivalent_usd", 0)) - 0.02301176) > 1e-10:
        raise ValueError("Development call/cost contract changed")
    rows = _rows(root)
    saved = {(r["task_id"], r["method"], r["replicate_id"]): r for r in summary["rows"]}
    if len(saved) != 9:
        raise ValueError("Summary does not contain nine unique assignment rows")
    for row in rows:
        key = (row["task_id"], row["method"], row["replicate_id"]); old = saved.get(key)
        if old is None or old.get("candidate_sha256") != row.get("candidate_sha256") or old.get("resource_usage") != row.get("resource_usage"):
            raise ValueError(f"Stored summary differs from generation evidence: {key}")

    source = root / "native-preparation"; controls_root = root / "native-controls"
    meta = cli.read(controls_root / "gold" / "run-metadata.json")
    env = {**meta, **meta.get("provenance", {}), "upstream_commit": meta.get("upstream_commit_verified")}
    if env["image_id"] != scc_dispatch.scc.IMAGE:
        raise ValueError("Development native image differs from the pinned SCC image")
    controls = {}
    for label, filename, expected_state in (("gold", "gold.jsonl", "pass"), ("negative", "incorrect.jsonl", "fail")):
        expected = {x["task_id"]: x["solution"] for x in (json.loads(line) for line in (source / filename).read_text(encoding="utf-8").splitlines())}
        audit = validate_native(controls_root / label, expected, env)
        if not audit.get("ok") or set(audit.get("statuses", {}).values()) != {expected_state}:
            raise ValueError(f"Stored {label} control evidence failed replay")
        controls[label] = audit
    audits = {}
    for method in scc_dispatch.METHODS:
        samples = root / "predictions" / f"{method}.jsonl"
        generated = [row for row in rows if row["method"] == method]
        expected = {row["task_id"]: row["solution"] for row in generated}
        actual_samples = [json.loads(line) for line in samples.read_text(encoding="utf-8").splitlines()]
        if actual_samples != [{"task_id": row["task_id"], "solution": row["solution"]} for row in generated]:
            raise ValueError("Native development samples differ from the actual generated programs")
        audit = validate_native(root / "native" / method, expected, env)
        if not audit.get("ok") or set(audit.get("statuses", {}).values()) - {"pass", "fail", "timeout"}:
            raise ValueError(f"Stored native evidence failed replay: {method}")
        audits[method] = audit
        for row in rows:
            if row["method"] == method and row["task_id"] in audit["statuses"]:
                key = (row["task_id"], method, row["replicate_id"])
                if saved[key].get("native_status") != audit["statuses"][row["task_id"]]:
                    raise ValueError(f"Stored native status differs from report: {key}")
                quality = audit["statuses"][row["task_id"]] == "pass" and row["format_extracted"]
                if saved[key].get("quality") is not quality:
                    raise ValueError(f"Stored quality differs from native outcome and format: {key}")
    return {"ok": True, "assigned": 9, "model_calls": 18, "known_api_equivalent_usd": 0.02301176,
            "native_groups": 3, "controls": controls, "native_audits": audits}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    result = verify(parser.parse_args().root); print(json.dumps({"ok": result["ok"], "assigned": 9, "native_groups": 3}, ensure_ascii=False))


if __name__ == "__main__": main()
