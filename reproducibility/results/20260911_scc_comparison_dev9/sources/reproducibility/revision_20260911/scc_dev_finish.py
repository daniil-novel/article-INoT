"""Replay and native-check every assignment in the nine-cell development gate."""
import argparse
import json
from pathlib import Path
import sys

from reproducibility import codex_luna_subscription as cli
from reproducibility.scale_env.validate_native import validate_native
from reproducibility.revision_20260911 import scc_dev_smoke, scc_dispatch, scc_export, scc_finish

ROOT = Path(__file__).resolve().parents[2]


def finish(root: Path) -> dict:
    root = root.resolve()
    generation = root / "generation"
    if cli.read(generation / "status.json").get("state") != "generation_finished":
        raise ValueError("Development generation is not complete")
    if (root / "summary.json").exists():
        raise FileExistsError("Refuse to overwrite a development gate result")
    plan = cli.read(generation / "manifest.json")
    if plan["task_ids"] != list(scc_dev_smoke.IDS) or len(plan["cells"]) != 9:
        raise ValueError("Unexpected development allocation")
    source = ROOT / "reproducibility/results/20260909_scc_dev3"
    prep = source / "native-preparation"
    tasks = {t["task_id"]: t for t in cli.tasks_from(prep / "prepared.jsonl")}
    rows = [scc_export._row_for(generation / "assignments" / cell["id"], cell, tasks[cell["task_id"]]) for cell in plan["cells"]]
    if not all(r["generation_complete"] and r["observed_candidate"] for r in rows):
        raise ValueError("Development gate has incomplete assignments; preserve and diagnose")
    if any(r["resource_usage"]["unknown_turns"] for r in rows):
        raise ValueError("Development usage is incomplete")
    meta = cli.read(source / "native-controls/gold/run-metadata.json")
    env = {**meta, **meta["provenance"], "upstream_commit": meta["upstream_commit_verified"]}
    if scc_finish._image_id("bcb-scale1000:v2") != env["image_id"]:
        raise ValueError("Development native image differs from the control environment")
    controls = {}
    for label, samples in (("gold", "gold.jsonl"), ("negative", "incorrect.jsonl")):
        expected = {r["task_id"]: r["solution"] for r in (json.loads(line) for line in (prep / samples).read_text(encoding="utf-8").splitlines())}
        controls[label] = validate_native(source / "native-controls" / label, expected, env)
        if not controls[label]["ok"] or set(controls[label]["statuses"].values()) != ({"pass"} if label == "gold" else {"fail"}):
            raise ValueError("Recorded development controls do not pass replay")
    predictions = root / "predictions"
    predictions.mkdir(exist_ok=True)
    audits = {}
    for method in scc_dispatch.METHODS:
        ordered = sorted((r for r in rows if r["method"] == method), key=lambda r: list(scc_dev_smoke.IDS).index(r["task_id"]))
        expected = {r["task_id"]: r["solution"] for r in ordered}
        data = b"".join(cli.canonical({"task_id": r["task_id"], "solution": r["solution"]}) + b"\n" for r in ordered)
        samples = predictions / (method + ".jsonl")
        if samples.exists() and samples.read_bytes() != data:
            raise ValueError("Development prediction bytes changed")
        if not samples.exists(): samples.write_bytes(data)
        target = root / "native" / method
        stage = root / "pipeline" / method
        stage.parent.mkdir(exist_ok=True)
        argv = [sys.executable, "-X", "utf8", "-m", "reproducibility.heldout200.run_observed_native",
                "--dataset", str(prep / "evaluator_dataset.jsonl"), "--prepared", str(prep / "prepared.jsonl"),
                "--selection", str(prep / "selection.json"), "--samples", str(samples), "--output", str(target),
                "--image", "bcb-scale1000:v2", "--requirements", str(ROOT / "reproducibility/scale1000/environment-v2/requirements.txt"),
                "--dockerfile", str(ROOT / "reproducibility/scale1000/environment-v2/Dockerfile"), "--deadline-seconds", "1800"]
        scc_finish._run_native_stage(stage, target, argv)
        audits[method] = validate_native(target, expected, env)
        if not audits[method]["ok"]:
            raise ValueError(f"Native development evidence invalid: {method}: {audits[method]['errors']}")
        for row in ordered:
            row["native_status"] = audits[method]["statuses"][row["task_id"]]
            row["quality"] = row["native_status"] == "pass" and row["format_extracted"]
    summary = {"role": "development feasibility only; not a main-study performance estimate", "gate": "passed",
               "assigned": 9, "native_checked": 9, "task_ids": list(scc_dev_smoke.IDS),
               "model_calls": sum(r["resource_usage"]["turns"] for r in rows),
               "known_api_equivalent_usd": sum(r["resource_usage"]["known_api_equivalent_usd"] for r in rows),
               "rows": rows, "native_audits": audits, "controls": controls,
               "generation_plan_sha256": scc_dispatch.sha(generation / "manifest.json")}
    cli.save(root / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = finish(args.root)
    print(json.dumps({key: result[key] for key in ("gate", "assigned", "native_checked", "model_calls", "known_api_equivalent_usd")}))
