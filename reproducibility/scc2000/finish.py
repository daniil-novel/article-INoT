"""Resumable SCC-2000 finishing stages.

The frozen exporter retains the complete 9,000-row ledger.  This wrapper adds
an explicit 6,000-cell view for the amended prefix while leaving the legacy
root status paused for the 3,000 administrative cells.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import subprocess
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.revision_20260911 import scc_export, scc_finish  # noqa: E402
from reproducibility.scale_env.validate_native import validate_native  # noqa: E402
from reproducibility.heldout200.evidence import environment_from_gate  # noqa: E402


def _read(path: Path) -> Any:
    return cli.read(path)


def _selected_rows(records: Path, selected_ids: set[str]) -> list[dict]:
    rows = [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [row for row in rows if row.get("id") in selected_ids]
    if len(selected) != len(selected_ids):
        raise ValueError("Selected continuation cells are missing from the 9,000-row export")
    return selected


def _write_selected_view(root: Path, selected_ids: set[str]) -> dict:
    source = root / "candidate_records.jsonl"
    rows = _selected_rows(source, selected_ids)
    target = root / "selected_assignment_records.jsonl"
    if target.exists():
        if target.read_bytes() != b"".join(cli.canonical(r) + b"\n" for r in rows):
            raise ValueError("Selected assignment view changed")
    else:
        target.write_bytes(b"".join(cli.canonical(r) + b"\n" for r in rows))
    return {"rows": len(rows), "selected_view": str(target)}


def _terminal_selected(generation: Path, selected_ids: set[str]) -> None:
    if (generation / "DISPATCH.lock").exists():
        raise ValueError("Finish refuses an active dispatcher lock")
    for ident in selected_ids:
        status = generation / "assignments" / ident / "status.json"
        if not status.is_file() or _read(status).get("state") not in {"completed", "infrastructure_failure", "model_or_workflow_failure", "paused"}:
            raise ValueError("Selected continuation has untouched or nonterminal cells")


def _verify_prefix(selection: dict, inputs: Path, manifest: Path, gate: Path) -> None:
    frozen,planned=scc_export._expected(inputs,manifest,gate)
    selected=planned[:6000]
    if selection.get("selected_cells")!=selected or selection.get("selected_ids")!=[c["id"] for c in selected]:
        raise ValueError("Finish selection differs from frozen schedule prefix")


def _amended_analysis(root: Path, selection: Path, gate: Path, source: Path) -> Path:
    stage=root / "pipeline/analyze-amended"
    output=root / "amended-analysis"
    argv=[sys.executable,"-X","utf8","-m","reproducibility.scc2000.analyze",
        "--records",str(root / "candidate_records.jsonl"),"--selection",str(selection),
        "--control-gate",str(gate / "heldout200_control_gate.json"),"--source-audit",str(source),"--out",str(output)]
    if stage.exists():
        if not (stage / "exit.json").is_file() or cli.read(stage / "exit.json").get("returncode")!=0:
            raise ValueError("Unfinished amended analysis; inspect preserved evidence")
        if cli.read(stage / "argv.json")!=argv or not (output / "summary.json").is_file():
            raise ValueError("Amended analysis command or output changed")
        return output
    if output.exists(): raise ValueError("Amended analysis output exists without a completed stage")
    stage.mkdir(parents=True)
    cli.save(stage / "argv.json",argv)
    with (stage / "stdout.log").open("xb") as out,(stage / "stderr.log").open("xb") as err:
        proc=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
    cli.save(stage / "exit.json",{"returncode":proc.returncode,"finished_unix":time.time()})
    if proc.returncode: raise RuntimeError("Amended analysis failed; logs preserved")
    return output


def run(*, root: Path, inputs: Path, gate_dir: Path, manifest: Path,
        selection_manifest: Path, image: str = "bcb-scale1000:v2",
        requirements: str = "reproducibility/scale1000/environment-v2/requirements.txt",
        dockerfile: str = "reproducibility/scale1000/environment-v2/Dockerfile",
        export_fn: Callable = scc_export.export,
        analyze_fn: Callable | None = None,
        source_audit: Path = ROOT / "reproducibility/task_dependence/source-audit-v2",
        native_stage_fn: Callable | None = None,
        image_id_fn: Callable | None = None) -> dict:
    root, inputs, gate_dir, manifest, selection_manifest = [p.resolve() for p in (root, inputs, gate_dir, manifest, selection_manifest)]
    selection = _read(selection_manifest)
    selected_ids = set(selection.get("selected_ids", []))
    if len(selected_ids) != 6000:
        raise ValueError("Continuation selection must contain exactly 6,000 cells")
    generation = root / "generation"
    _terminal_selected(generation, selected_ids)
    _verify_prefix(selection,inputs,manifest,gate_dir)
    predictions = root / "predictions"
    if predictions.exists():
        exported = scc_export.validate_export(generation, inputs, manifest, predictions, gate_dir)
    else:
        exported = export_fn(generation, inputs, manifest, predictions, gate_dir)
    gate = _read(gate_dir / "heldout200_control_gate.json")
    env = environment_from_gate(gate_dir)
    actual_image = (image_id_fn or scc_finish._image_id)(image)
    if actual_image != gate.get("image_id") or actual_image != env.get("image_id"):
        raise ValueError("Native image identity differs from frozen control gate")
    frozen = _read(manifest); audits = {}; native = root / "native"; native.mkdir(exist_ok=True)
    for method in frozen["methods"]:
        for rep in frozen["replicate_ids"]:
            key = f"{method}-r{rep}"; samples = predictions / f"{key}.jsonl"; target = native / key; stage = root / "pipeline" / f"native-{key}"
            expected = {json.loads(line)["task_id"]: json.loads(line)["solution"] for line in samples.read_text(encoding="utf-8").splitlines() if line.strip()} if samples.exists() else {}
            if expected:
                argv = [sys.executable, "-X", "utf8", "-m", "reproducibility.heldout200.run_observed_native", "--dataset", str(inputs / "evaluator/evaluator_dataset.jsonl"), "--prepared", str(inputs / "input/prepared.jsonl"), "--samples", str(samples), "--output", str(target), "--selection", str(inputs / "selection.json"), "--image", image, "--requirements", requirements, "--dockerfile", dockerfile, "--deadline-seconds", "14400"]
                (native_stage_fn or scc_finish._run_native_stage)(stage, target, argv)
                audit = validate_native(target, expected, env)
                if not audit["ok"]: raise ValueError(f"Native evidence invalid for {key}: {audit['errors']}")
                audits[key] = audit
            else:
                if stage.exists() and (not (stage / "exit.json").is_file() or cli.read(stage / "exit.json").get("returncode")!=0): raise ValueError(f"Incomplete empty native stage: {stage}")
                if not stage.exists(): stage.mkdir(parents=True); cli.save(stage / "exit.json", {"returncode": 0, "skipped": True})
                audits[key] = {"ok": True, "statuses": {}, "skipped": True}
    eligible = set(gate["evaluable_task_ids"]); rows = scc_finish._records(predictions, audits, eligible)
    (root / "candidate_records.jsonl").write_bytes(b"".join(cli.canonical(r) + b"\n" for r in rows))
    (root / "resource_usage.jsonl").write_bytes(b"".join(cli.canonical({"id": r["id"], "task_id": r["task_id"], "method": r["method"], "replicate_id": r["replicate_id"], "resource_usage": r["resource_usage"], "availability": r["availability"]}) + b"\n" for r in rows))
    cli.save(root / "native_audit.json", audits)
    view = _write_selected_view(root, selected_ids)
    analysis = scc_finish._run_analysis_stage(root, root / "candidate_records.jsonl", inputs, gate_dir)
    selected_analysis = (analyze_fn or _amended_analysis)(root,selection_manifest,gate_dir,source_audit.resolve())
    return {"assignments": exported.get("rows", 9000), "selected_cells": 6000,
            "legacy_root_status": _read(generation / "status.json").get("state"),
            "export": exported, "selected_view": view, "native_groups": len(audits),
            "analysis": str(analysis), "selected_analysis": str(selected_analysis) if selected_analysis else None}


def main() -> None:
    p = argparse.ArgumentParser(description="Finish the frozen SCC ledger and selected 2000-block view")
    for name in ("root", "inputs", "gate-dir", "manifest", "selection-manifest"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--image", default="bcb-scale1000:v2"); p.add_argument("--requirements", default="reproducibility/scale1000/environment-v2/requirements.txt"); p.add_argument("--dockerfile", default="reproducibility/scale1000/environment-v2/Dockerfile")
    a = p.parse_args()
    print(json.dumps(run(root=a.root, inputs=a.inputs, gate_dir=a.gate_dir, manifest=a.manifest, selection_manifest=a.selection_manifest, image=a.image, requirements=a.requirements, dockerfile=a.dockerfile), ensure_ascii=False))


if __name__ == "__main__":
    main()
