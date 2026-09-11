"""Finish native SCC evaluation and join all 9,000 frozen assignments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.heldout200.evidence import environment_from_gate  # noqa: E402
from reproducibility.scale_env.validate_native import validate_native  # noqa: E402
from reproducibility.revision_20260911 import scc_analyze, scc_export  # noqa: E402


def _image_id(image: str) -> str:
    return subprocess.check_output(["docker", "--context", "default", "image", "inspect", image, "--format", "{{.Id}}"], text=True).strip()


def _run_native_stage(stage: Path, target: Path, argv: list[str]) -> dict:
    if (stage / "exit.json").is_file():
        if not (stage / "argv.json").is_file() or cli.read(stage / "argv.json") != argv:
            raise ValueError(f"Verified native stage command changed: {stage.name}")
        result = cli.read(stage / "exit.json")
        if result.get("returncode") != 0:
            raise ValueError(f"Previous native stage failed: {stage.name}")
        return result
    if target.exists():
        raise ValueError(f"Native output exists without verified stage exit: {target}")
    stage.mkdir(parents=True, exist_ok=False)
    cli.save(stage / "argv.json", argv)
    with (stage / "stdout.log").open("xb") as stdout, (stage / "stderr.log").open("xb") as stderr:
        proc = subprocess.run(argv, stdout=stdout, stderr=stderr)
    result = {"returncode": proc.returncode, "finished_unix": time.time()}
    cli.save(stage / "exit.json", result)
    if proc.returncode:
        raise RuntimeError(f"Native evaluator failed: {stage.name}; raw logs retained")
    return result


def _run_analysis_stage(root: Path, records: Path, inputs: Path, gate_dir: Path) -> Path:
    """Run the pinned offline analysis CLI with a resumable evidence stage."""
    stage = root / "pipeline" / "analyze"
    summary = root / "analysis" / "summary.json"
    argv = [sys.executable, "-X", "utf8", "-m", "reproducibility.revision_20260911.scc_analyze",
            "--records", str(records), "--out", str(summary), "--strict",
            "--selection", str(inputs / "selection.json"),
            "--control-gate", str(gate_dir / "heldout200_control_gate.json")]
    if (stage / "exit.json").is_file():
        if not (stage / "argv.json").is_file() or cli.read(stage / "argv.json") != argv:
            raise ValueError(f"Verified analysis stage command changed: {stage.name}")
        result = cli.read(stage / "exit.json")
        if result.get("returncode") != 0 or not summary.is_file():
            raise ValueError(f"Previous analysis stage is incomplete: {stage}")
        return summary
    if stage.exists() or summary.exists():
        raise ValueError(f"Analysis output exists without verified stage exit: {stage}")
    stage.mkdir(parents=True)
    cli.save(stage / "argv.json", argv)
    summary.parent.mkdir(parents=True, exist_ok=True)
    with (stage / "stdout.log").open("xb") as stdout, (stage / "stderr.log").open("xb") as stderr:
        proc = subprocess.run(argv, stdout=stdout, stderr=stderr)
    cli.save(stage / "exit.json", {"returncode": proc.returncode, "finished_unix": time.time()})
    if proc.returncode or not summary.is_file():
        raise RuntimeError("SCC analysis CLI failed; raw logs retained")
    return summary


def _records(export_dir: Path, audits: dict, eligible: set[str]) -> list[dict]:
    rows = [json.loads(line) for line in (export_dir / "assignment_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 9000 or len({(r["task_id"], r["method"], r["replicate_id"]) for r in rows}) != 9000:
        raise ValueError("SCC assignment ledger is not the complete unique 9,000-row matrix")
    for row in rows:
        if not row.get("observed_candidate"):
            if row.get("availability") == "never_started":
                row["outcome_type"] = "generation_unavailable"
            else:
                row["quality"] = None
                row["outcome_type"] = row.get("status_state", "submitted_incomplete")
            continue
        key = f"{row['method']}-r{row['replicate_id']}"; audit = audits.get(key, {}); status = audit.get("statuses", {}).get(row["task_id"])
        row["native_status"] = status
        if row["task_id"] not in eligible:
            row["quality"] = None; row["outcome_type"] = "control_ineligible"
        elif not row.get("format_extracted"):
            row["quality"] = False; row["outcome_type"] = "model_format_failure"
        elif status not in ("pass", "fail", "timeout"):
            row["quality"] = None; row["outcome_type"] = "native_unavailable"
        else:
            row["quality"] = status == "pass"; row["outcome_type"] = "native_outcome"
    return rows


def run(a: argparse.Namespace) -> dict:
    root = a.root.resolve(); generation = root / "generation"; export_dir = root / "predictions"
    if not (generation / "status.json").is_file() or cli.read(generation / "status.json").get("state") != "generation_finished":
        raise ValueError("Native finish requires all assignments terminal")
    if (generation / "DISPATCH.lock").exists():
        raise ValueError("Native finish refuses an active generation lock")
    if export_dir.exists():
        scc_export.validate_export(generation, a.inputs.resolve(), a.manifest.resolve(), export_dir, a.gate_dir.resolve())
    else:
        scc_export.export(generation, a.inputs.resolve(), a.manifest.resolve(), export_dir, a.gate_dir.resolve())
    gate = cli.read(a.gate_dir.resolve() / "heldout200_control_gate.json")
    env = environment_from_gate(a.gate_dir.resolve())
    actual_image = _image_id(a.image)
    if actual_image != gate.get("image_id") or actual_image != env.get("image_id"):
        raise ValueError("Native image identity differs from frozen control gate")
    methods = cli.read(a.manifest)["methods"]; repeats = cli.read(a.manifest)["replicate_ids"]; native = root / "native"; native.mkdir(exist_ok=True); pipeline = root / "pipeline"; pipeline.mkdir(exist_ok=True)
    audits: dict[str, dict] = {}
    for method in methods:
        for rep in repeats:
            key = f"{method}-r{rep}"; samples = export_dir / f"{key}.jsonl"; target = native / key; stage = pipeline / f"native-{key}"
            expected = {json.loads(line)["task_id"]: json.loads(line)["solution"] for line in samples.read_text(encoding="utf-8").splitlines() if line.strip()} if samples.exists() else {}
            if not expected:
                if stage.exists():
                    if not (stage / "exit.json").is_file() or cli.read(stage / "exit.json").get("returncode") != 0:
                        raise ValueError(f"Unfinished or failed empty native stage: {stage}")
                else:
                    stage.mkdir(); cli.save(stage / "exit.json", {"returncode": 0, "skipped": True, "finished_unix": time.time()})
                audits[key] = {"ok": True, "statuses": {}, "skipped": True}; continue
            argv = [sys.executable, "-X", "utf8", "-m", "reproducibility.heldout200.run_observed_native", "--dataset", str(a.inputs / "evaluator/evaluator_dataset.jsonl"), "--prepared", str(a.inputs / "input/prepared.jsonl"), "--samples", str(samples), "--output", str(target), "--selection", str(a.inputs / "selection.json"), "--image", a.image, "--requirements", a.requirements, "--dockerfile", a.dockerfile, "--deadline-seconds", "14400"]
            _run_native_stage(stage, target, argv)
            audit = validate_native(target, expected, env)
            if not audit["ok"]:
                raise ValueError(f"Native evidence invalid for {key}: {audit['errors']}")
            audits[key] = audit
    eligible = set(gate["evaluable_task_ids"]); rows = _records(export_dir, audits, eligible)
    (root / "candidate_records.jsonl").write_bytes(b"".join(cli.canonical(r) + b"\n" for r in rows))
    (root / "resource_usage.jsonl").write_bytes(b"".join(cli.canonical({"id": r["id"], "task_id": r["task_id"], "method": r["method"], "replicate_id": r["replicate_id"], "resource_usage": r["resource_usage"], "availability": r["availability"]}) + b"\n" for r in rows))
    cli.save(root / "native_audit.json", audits)
    summary = _run_analysis_stage(root, root / "candidate_records.jsonl", a.inputs.resolve(), a.gate_dir.resolve())
    return {"assignments": len(rows), "observed_candidates": sum(r.get("observed_candidate") for r in rows), "native_groups": len(audits), "analysis": str(summary)}


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--root", type=Path, required=True); p.add_argument("--inputs", type=Path, required=True); p.add_argument("--gate-dir", type=Path, required=True); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--image", default="bcb-scale1000:v2"); p.add_argument("--requirements", default="reproducibility/scale1000/environment-v2/requirements.txt"); p.add_argument("--dockerfile", default="reproducibility/scale1000/environment-v2/Dockerfile"); a = p.parse_args(); print(json.dumps(run(a), ensure_ascii=False))


if __name__ == "__main__": main()
