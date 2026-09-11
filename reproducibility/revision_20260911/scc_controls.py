"""Offline freeze/check controls for the contemporaneous SCC arm.

This module does not call the model, execute candidates, or mutate frozen
scale1000 files. It validates the exact task/control identity consumed by the
SCC dispatcher and records a standalone manifest in the revision directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "reproducibility" / "revision_20260911"
sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.heldout200.evidence import environment_from_gate  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def plan(inputs: Path, gate_dir: Path, out: Path | None = None) -> dict:
    tasks = cli.tasks_from(inputs / "input" / "prepared.jsonl")
    selection = cli.read(inputs / "selection.json")
    gate = cli.read(gate_dir / "heldout200_control_gate.json")
    environment_from_gate(gate_dir)
    ids = selection.get("assigned_task_ids")
    task_ids = [t.get("task_id") for t in tasks]
    if len(tasks) != 1000 or len(ids or []) != 1000 or len(set(ids or [])) != 1000:
        raise ValueError("SCC requires the fixed 1000-task allocation")
    if set(task_ids) != set(ids):
        raise ValueError("Prepared task IDs differ from selection")
    if gate.get("assigned_task_ids") != ids or not gate.get("controls_complete"):
        raise ValueError("Native control gate is incomplete or has different IDs")
    if len(gate.get("evaluable_task_ids", [])) != 985:
        raise ValueError("Expected the established 985-task quality-eligible gate")
    if cli.MODEL != "gpt-5.6-luna" or cli.CLI_VERSION != "codex-cli 0.153.4":
        raise ValueError("Common Luna runtime pin changed")
    source_files = [
        "reproducibility/revision_20260911/scc_controls.py",
        "reproducibility/revision_20260911/scc_dispatch.py",
        "reproducibility/revision_20260911/scc_dev_gate.py",
        "reproducibility/revision_20260911/scc_revision_tests.py",
        "reproducibility/revision_20260911/scc_dev_smoke.py",
        "reproducibility/revision_20260911/scc_dev_finish.py",
        "reproducibility/revision_20260911/scc_dev_replay.py",
        "reproducibility/revision_20260911/start_scc_study.py",
        "reproducibility/revision_20260911/scc_protocol.md",
        "reproducibility/revision_20260911/scc_analyze.py",
        "reproducibility/revision_20260911/scc_export.py",
        "reproducibility/revision_20260911/scc_finish.py",
        "reproducibility/revision_20260911/tests_scc_analysis.py",
        "reproducibility/tests/test_scc_native_pipeline.py",
        "reproducibility/tests/test_scc_dispatch_runtime.py",
        "reproducibility/external_baselines/requirements.txt",
        "reproducibility/external_baselines/scc.py",
        "reproducibility/codex_luna_subscription.py",
        "reproducibility/factorial_runner.py",
        "reproducibility/benchmark_bridge.py",
        "reproducibility/record_codex_runtime.py",
        "reproducibility/heldout200/evidence.py",
        "reproducibility/heldout200/run_observed_native.py",
        "reproducibility/scale_env/validate_native.py",
        "reproducibility/external_baselines/vendor/scc_2024/SOURCE_MANIFEST.json",
        "reproducibility/external_baselines/vendor/scc_2024/session.py",
        "reproducibility/external_baselines/vendor/scc_2024/core/interface.py",
        "reproducibility/external_baselines/vendor/scc_2024/roles/coder.py",
        "reproducibility/external_baselines/vendor/scc_2024/roles/analyst.py",
        "reproducibility/external_baselines/vendor/scc_2024/roles/tester.py",
    ]
    from reproducibility.scale1000_luna.dispatch import DEPENDENCIES
    source_files.extend("reproducibility/" + name for name in DEPENDENCIES)
    vendor = ROOT / "reproducibility/external_baselines/vendor/scc_2024"
    source_files.extend("reproducibility/external_baselines/vendor/scc_2024/" + name
                        for name in cli.read(vendor / "SOURCE_MANIFEST.json")["files"])
    source_hashes = {name: source_sha(ROOT / name) for name in sorted(set(source_files))}
    manifest = {
        "schema": "scc-contemporaneous-v1",
        "methods": ["single_roles", "single_neutral", "scc_author_2024_codex_transport"],
        "model": cli.MODEL,
        "reasoning_effort": "medium",
        "cli_version": cli.CLI_VERSION,
        "task_count": 1000,
        "replicate_ids": [101, 102, 103],
        "planned_assignments": 9000,
        "maximum_model_calls": 18000,
        "order_seed": 20260911,
        "model_seed_supported": False,
        "tasks_sha256": cli.digest(tasks),
        "selection_sha256": sha(inputs / "selection.json"),
        "prepared_sha256": sha(inputs / "input" / "prepared.jsonl"),
        "control_gate_sha256": sha(gate_dir / "heldout200_control_gate.json"),
        "scc_source_sha256": source_sha(ROOT / "reproducibility" / "external_baselines" / "scc.py"),
        "vendor_manifest_sha256": sha(ROOT / "reproducibility" / "external_baselines" / "vendor" / "scc_2024" / "SOURCE_MANIFEST.json"),
        "source_files_sha256": source_hashes,
        "source_hash_normalization": "CRLF converted to LF for cross-platform source verification only; raw vendor files retained",
        "protocol_sha256": source_sha(REV / "scc_protocol.md"),
        "development_gate_sha256": sha(ROOT / "reproducibility/results/20260911_scc_comparison_dev9/summary.json"),
        "known_valuation_submission_guard_usd": 285.0,
        "workers": 8,
        "generated_test_parallelism": 1,
        "inflight_reserve_usd": 15.0,
        "timeout_seconds": 600,
        "resume_policy": "untouched assignments only; submitted attempts immutable",
        "quality_eligible_count": 985,
        "inference_unit": "task cluster; mean of three repeat outcomes",
        "primary_family": ["SCC-SR", "SCC-SN"],
        "primary_test": "two-sided one-sample t-test on paired task-level mean differences",
        "familywise_alpha": 0.05,
        "multiplicity": "Holm, fixed family size two",
        "bootstrap_resamples": 10000,
        "bootstrap_seed": 20260911,
    }
    manifest["manifest_sha256"] = cli.digest(manifest)
    if out is not None:
        if out.exists():
            raise FileExistsError(f"Refusing to overwrite frozen SCC manifest: {out}")
        cli.save(out, manifest)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["check", "freeze"])
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--gate-dir", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    if a.command == "freeze":
        result = plan(a.inputs.resolve(), a.gate_dir.resolve(), a.manifest.resolve())
    else:
        result = plan(a.inputs.resolve(), a.gate_dir.resolve())
        frozen = cli.read(a.manifest)
        if frozen != result:
            raise ValueError("Frozen SCC manifest differs from current inputs or sources")
    print(json.dumps({"ok": True, "manifest_sha256": result["manifest_sha256"],
                      "planned_assignments": result["planned_assignments"],
                      "quality_eligible_count": result["quality_eligible_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
