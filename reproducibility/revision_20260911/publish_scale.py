"""Publish a completed Luna scale study into a new, portable evidence archive.

The publisher is intentionally inert until the generation archive is terminal and
all finish stages have succeeded.  It copies evidence bytes; it never runs the
model, Docker, or the native evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
import tempfile
from typing import Any

from reproducibility.evidence_manifest import write as write_evidence_manifest


ARMS = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
REPEATS = (101, 102, 103)
STAGES = ("export", *(f"native-{arm}-r{rep}" for rep in REPEATS for arm in ARMS), "collect", "analyze")
SECRET_MARKERS = (b"sk-", b"-----begin ", b"bearer ey", b"authorization: bearer ")
REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        fail(f"required directory is missing: {source}")
    shutil.copytree(source, destination)


def copy_sessions(source: Path, destination: Path) -> None:
    if not source.is_dir():
        fail(f"required directory is missing: {source}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("runtime.json"))


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        fail(f"required file is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def assert_no_secret_blob(path: Path) -> None:
    """Reject accidental secret/auth material in files selected for publication."""
    if path.suffix.lower() not in {".json", ".txt", ".md", ".py", ".jsonl", ".toml", ".yml", ".yaml"}:
        return
    data = path.read_bytes()
    lowered = data.lower()
    for marker in SECRET_MARKERS:
        if marker in lowered:
            fail(f"secret/auth marker in publish candidate: {path}")


def validate_terminal_generation(generation: Path, frozen_manifest: Path) -> dict[str, Any]:
    status_path = generation / "status.json"
    if not status_path.is_file():
        fail("generation status is missing")
    status = read_json(status_path)
    if status.get("state") != "generation_finished":
        fail("refusing publication while generation is not generation_finished")
    if (generation / "DISPATCH.lock").exists():
        fail("refusing publication while DISPATCH.lock exists")

    archived_manifest = read_json(generation / "manifest.json")
    frozen = read_json(frozen_manifest)
    if archived_manifest != frozen:
        fail("generation manifest differs from frozen manifest")
    if archived_manifest.get("planned_candidates") != 15000 or archived_manifest.get("planned_cli_turns") != 27000:
        fail("frozen plan is not the 15,000-candidate / 27,000-turn Luna plan")

    cells = archived_manifest.get("inner_manifest", {}).get("cells", [])
    if len(cells) != 15000 or len({c.get("id") for c in cells}) != 15000:
        fail("frozen manifest does not contain 15,000 unique cells")
    return {c["id"]: c for c in cells}


def validate_finish(root: Path, cell_map: dict[str, Any]) -> dict[str, Any]:
    pipeline = root / "pipeline"
    if not pipeline.is_dir():
        fail("finish pipeline directory is missing")
    exits: dict[str, Any] = {}
    for stage in STAGES:
        path = pipeline / f"{stage}.exit.json"
        if not path.is_file():
            fail(f"finish stage is missing: {stage}")
        result = read_json(path)
        if result.get("returncode") != 0:
            fail(f"finish stage did not succeed: {stage}")
        exits[stage] = result

    analysis = root / "analysis"
    records_path = analysis / "candidate_records.jsonl"
    ledger_path = analysis / "turn_usage.json"
    native_path = analysis / "native_audit.json"
    summary_path = analysis / "summary.json"
    for path in (records_path, ledger_path, native_path, summary_path):
        if not path.is_file():
            fail(f"required finish artifact is missing: {path}")

    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 15000:
        fail(f"candidate ledger has {len(records)} rows, expected all 15,000 assignments")
    keys = {(r.get("task_id"), r.get("arm"), r.get("replicate_id")) for r in records}
    if len(keys) != 15000 or any(k[0] is None or k[1] not in ARMS or k[2] not in REPEATS for k in keys):
        fail("candidate ledger is not a unique 1,000 x 5 x 3 assignment matrix")
    if {r.get("id") for r in records} != set(cell_map):
        fail("candidate ledger cell identities differ from the frozen allocation")
    for row in records:
        cell = cell_map[row["id"]]
        if any(row.get(key) != cell[key] for key in ("task_id", "arm", "replicate_id")):
            fail("candidate ledger relabels a frozen cell")

    generation = root / "generation"
    turn_dirs = [p for p in (generation / "turns").iterdir() if p.is_dir()] if (generation / "turns").is_dir() else []
    for folder in turn_dirs:
        status_path = folder / "status.json"
        if not status_path.is_file():
            fail(f"turn evidence has no status.json: {folder.name}")
        status = read_json(status_path)
        for required in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt"):
            if not (folder / required).is_file():
                fail(f"turn evidence is incomplete ({required}): {folder.name}")
        if status.get("state") == "completed" and not ((folder / "result.json").is_file() or (folder / "empty_response_classification.json").is_file()):
            fail(f"completed turn lacks accepted result: {folder.name}")

    audits = read_json(native_path)
    observed = [r for r in records if r.get("generation_complete") is True]
    for row in observed:
        key = f"{row['arm']}-r{row['replicate_id']}"
        audit = audits.get(key)
        if not isinstance(audit, dict) or not isinstance(audit.get("statuses"), dict):
            fail(f"native audit missing for observed candidate group: {key}")
        if row["task_id"] not in audit["statuses"]:
            fail(f"observed candidate lacks native status: {row['task_id']} / {key}")

    ledger = read_json(ledger_path)
    if not isinstance(ledger, list):
        fail("turn_usage.json is not a list")
    # A complete finish must retain every submitted turn.  The collector already
    # enforces this join; this independent check catches a truncated publication.
    turn_dirs = [p for p in (generation / "turns").iterdir() if p.is_dir()] if (generation / "turns").is_dir() else []
    ledger_keys = {(x.get("cell_id"), x.get("stage")) for x in ledger}
    expected_keys = set()
    for folder in turn_dirs:
        stem, stage = folder.name.rsplit("-", 1)
        expected_keys.add((stem, int(stage)))
    if len(ledger_keys) != len(ledger) or ledger_keys != expected_keys:
        fail("turn usage ledger does not cover every submitted turn")
    return {"records": len(records), "observed": len(observed), "turn_rows": len(ledger), "finish_stages": exits}


def validate_full_replay(root: Path, inputs: Path, gate: Path, manifest: Path) -> None:
    """Rejoin raw responses and native bytes and recompute the full frozen analysis."""
    from reproducibility.scale1000_luna.collect import collect
    from reproducibility.scale1000.analyze import summarize

    # The collector writes only into this new temporary directory. Original
    # traces, native reports, and previously computed results remain immutable.
    with tempfile.TemporaryDirectory(prefix="inot-publication-replay-") as directory:
        replay = Path(directory) / "analysis"
        collect(root / "generation", inputs, gate, manifest,
                root / "predictions", root / "native", replay)
        for name in ("candidate_records.jsonl", "turn_usage.json", "native_audit.json"):
            if (replay / name).read_bytes() != (root / "analysis" / name).read_bytes():
                fail(f"raw/native reconstruction differs from saved analysis: {name}")
        records = [json.loads(line) for line in (replay / "candidate_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        recalculated = summarize(records, read_json(inputs / "selection.json"))
        if recalculated != read_json(root / "analysis" / "summary.json"):
            fail("full statistical replay differs from saved summary")


def validate_hash_bindings(generation: Path, frozen_manifest: Path, inputs: Path, gate: Path) -> dict[str, Any]:
    manifest = read_json(generation / "manifest.json")
    def normalized_sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

    if sha256(inputs / "selection.json") != manifest["selection_sha256"]:
        fail("selection hash differs from frozen plan")
    if sha256(inputs / "input" / "prepared.jsonl") != manifest["prepared_sha256"]:
        fail("prepared input hash differs from frozen plan")
    if sha256(gate / "heldout200_control_gate.json") != manifest["control_gate_sha256"]:
        fail("control gate hash differs from frozen plan")
    source_hashes = manifest.get("source_sha256_lf", {})
    for relative, expected in source_hashes.items():
        source = generation / "sources" / relative
        if not source.is_file():
            fail(f"archived frozen source is missing: {relative}")
        if normalized_sha(source) != expected:
            fail(f"archived frozen source hash differs: {relative}")
    runtime = generation / "runtime.json"
    provenance = generation / "runtime_provenance.json"
    if not runtime.is_file() or not provenance.is_file():
        fail("runtime identity/provenance is incomplete")
    runtime_obj = read_json(runtime)
    if runtime_obj.get("version") != "codex-cli 0.153.4" or runtime_obj.get("authentication") != "chatgpt":
        fail("runtime identity does not match the frozen Luna runtime")
    # Verify the recorded runtime files contain no secret values before recording
    # their hashes.  They are kept out of the portable copy below.
    assert_no_secret_blob(runtime)
    assert_no_secret_blob(provenance)
    return {
        "frozen_manifest_sha256": sha256(frozen_manifest),
        "archived_manifest_sha256": sha256(generation / "manifest.json"),
        "selection_sha256": sha256(inputs / "selection.json"),
        "prepared_sha256": sha256(inputs / "input" / "prepared.jsonl"),
        "control_gate_sha256": sha256(gate / "heldout200_control_gate.json"),
        "runtime_sha256": sha256(runtime),
        "runtime_provenance_sha256": sha256(provenance),
        "source_sha256_lf": source_hashes,
    }


def write_byte_verifier(path: Path) -> None:
    path.write_text(
        '''#!/usr/bin/env python3
"""Offline byte verifier for a published scale1000 Luna evidence archive."""
import hashlib, json, sys
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
actual = {}
for path in sorted(root.rglob("*")):
    if path.is_file() and path.name != "EVIDENCE_MANIFEST.json":
        data = path.read_bytes()
        actual[path.relative_to(root).as_posix()] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
expected = {item["path"]: {"bytes": item["bytes"], "sha256": item["sha256"]} for item in manifest["files"]}
if actual != expected:
    raise SystemExit("evidence verification failed: missing, unexpected, or changed bytes")
print(json.dumps({"ok": True, "files": len(actual), "bytes": sum(v["bytes"] for v in actual.values())}))
''',
        encoding="utf-8",
        newline="\n",
    )


def write_replay_verifier(path: Path) -> None:
    path.write_text(
        '''#!/usr/bin/env python3
"""Dependency-free structural and primary-contrast replay verifier."""
import json, math, sys
from pathlib import Path

root = Path(__file__).resolve().parent
records = [json.loads(line) for line in (root / "analysis/candidate_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
summary = json.loads((root / "analysis/summary.json").read_text(encoding="utf-8"))
arms = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
repeats = (101, 102, 103)
if len(records) != 15000:
    raise SystemExit(f"expected 15000 candidate rows, got {len(records)}")
index = {}
tasks = []
for row in records:
    key = (row["task_id"], row["arm"], row["replicate_id"])
    if key in index:
        raise SystemExit(f"duplicate assignment: {key}")
    index[key] = row
    if row["task_id"] not in tasks:
        tasks.append(row["task_id"])
if len(tasks) != 1000:
    raise SystemExit(f"expected 1000 task clusters, got {len(tasks)}")
contrasts = {
    "single_roles_minus_single_neutral": ("single_roles", "single_neutral"),
    "multi_roles_minus_multi_neutral": ("multi_roles", "multi_neutral"),
    "multi_neutral_minus_single_neutral": ("multi_neutral", "single_neutral"),
    "multi_roles_minus_single_roles": ("multi_roles", "single_roles"),
}
checked = {}
for name, (left, right) in contrasts.items():
    diffs = []
    for task in tasks:
        lv = [index[(task, left, repeat)]["quality"] for repeat in repeats]
        rv = [index[(task, right, repeat)]["quality"] for repeat in repeats]
        if all(type(x) is bool for x in lv + rv):
            diffs.append(sum(lv) / 3 - sum(rv) / 3)
    mean = sum(diffs) / len(diffs) if diffs else None
    stored = summary["contrasts"][name]
    if stored["eligible_tasks"] != len(diffs) or (mean is not None and not math.isclose(stored["mean_difference"], mean, rel_tol=0, abs_tol=1e-12)):
        raise SystemExit(f"primary contrast mismatch: {name}")
    checked[name] = {"eligible_tasks": len(diffs), "mean_difference": mean}
print(json.dumps({"ok": True, "records": len(records), "task_clusters": len(tasks), "primary_recomputed": checked}, sort_keys=True))
''',
        encoding="utf-8",
        newline="\n",
    )


def publish(root: Path, output: Path, inputs: Path, gate: Path, frozen_manifest: Path) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    inputs = inputs.resolve()
    gate = gate.resolve()
    frozen_manifest = frozen_manifest.resolve()
    if output.exists():
        fail(f"refuse to overwrite existing output: {output}")
    generation = root / "generation"
    cells = validate_terminal_generation(generation, frozen_manifest)
    binding = validate_hash_bindings(generation, frozen_manifest, inputs, gate)
    completion = validate_finish(root, cells)
    validate_full_replay(root, inputs, gate, frozen_manifest)

    output.mkdir(parents=True)
    try:
        # Full raw traces and archived source copies are required for replay.
        copy_tree(generation / "turns", output / "generation" / "turns")
        for name in ("cells", "failures", "sources", "empty"):
            copy_tree(generation / name, output / "generation" / name)
        copy_sessions(generation / "sessions", output / "generation" / "sessions")
        for name in ("manifest.json", "tasks.json", "instructions.txt", "results.jsonl", "status.json", "runtime.json", "runtime_provenance.json"):
            copy_file(generation / name, output / "generation" / name)
        # Runtime files can contain authentication-adjacent configuration. Their
        # exact hashes are recorded in provenance, while secret/auth blobs and
        # package binaries are deliberately excluded from the portable archive.
        (output / "provenance").mkdir()
        (output / "provenance" / "runtime_hashes.json").write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        runtime_obj = read_json(generation / "runtime.json")
        provenance_obj = read_json(generation / "runtime_provenance.json")
        safe_runtime = {
            "version": runtime_obj.get("version"),
            "workers": runtime_obj.get("workers"),
            "timeout_seconds": runtime_obj.get("timeout_seconds"),
            "authentication_mode": runtime_obj.get("authentication"),
            "prefix": runtime_obj.get("prefix"),
            "cli_version": provenance_obj.get("cli_version"),
            "package_version": provenance_obj.get("package_version"),
            "auth_material_archived": provenance_obj.get("auth_material_archived"),
            "ambient_sensitive_setting_presence": provenance_obj.get("ambient_sensitive_setting_presence"),
            "native_executable_sha256": provenance_obj.get("native_executable_sha256"),
            "node_entry_sha256": provenance_obj.get("node_entry_sha256"),
            "npm_lock_sha256": provenance_obj.get("npm_lock_sha256"),
            "package_json_sha256": provenance_obj.get("package_json_sha256"),
            "source_runtime_files_are_retained_without_credentials": True,
        }
        (output / "provenance" / "runtime_identity_noauth.json").write_text(json.dumps(safe_runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        copy_tree(root / "pipeline", output / "pipeline")
        copy_tree(root / "predictions", output / "predictions")
        copy_tree(root / "native", output / "native")
        copy_tree(root / "analysis", output / "analysis")
        copy_tree(gate, output / "controls" / "controls-v3")
        copy_tree(inputs, output / "inputs" / "scale1000-v1")
        copy_tree(REPO_ROOT / "reproducibility/vendor/bigcodebench", output / "sources" / "bigcodebench")
        for rel in ("BIGCODEBENCH-LICENSE.txt",):
            copy_file(REPO_ROOT / "reproducibility/results/20260908_codex_mini_heldout200" / rel, output / "licenses" / rel)
        for rel in ("PROTOCOL.md", "RUNBOOK.md", "MODEL_AMENDMENT.md"):
            copy_file(REPO_ROOT / "reproducibility/scale1000_luna" / rel, output / "protocols" / rel)
        for rel in ("PROTOCOL.md", "ENVIRONMENT_AMENDMENT.md"):
            copy_file(REPO_ROOT / "reproducibility/scale1000" / rel, output / "protocols" / f"scale1000-{rel}")
        for rel in ("Dockerfile", "requirements.txt"):
            copy_file(REPO_ROOT / "reproducibility/scale1000/environment-v2" / rel, output / "environment" / f"scale1000-v2-{rel}")
        for rel in ("test_scale1000_luna.py", "test_scale1000_analysis.py", "test_scale1000_evidence.py", "test_evidence_manifest.py", "test_scale_native.py"):
            copy_file(REPO_ROOT / "reproducibility/tests" / rel, output / "tests" / rel)
        copy_file(Path(__file__).resolve(), output / "provenance" / "publish_scale.py")
        copy_file(REPO_ROOT / "reproducibility/evidence_manifest.py", output / "provenance" / "evidence_manifest.py")
        write_byte_verifier(output / "verify_bytes.py")
        write_replay_verifier(output / "replay_verify.py")
        (output / "README.md").write_text(
            "# Scale1000 Luna evidence archive\n\n"
            "This archive contains the completed GPT-5.6 Luna subscription study, raw generation traces, native reports, controls, inputs, frozen sources, and analysis. It is a new model study under the Luna amendment, not a same-model replication of the rejected mini attempt.\n\n"
            "Run `python verify_bytes.py` for an offline byte-level check and `python replay_verify.py` for a dependency-free structural/primary-contrast recomputation against `analysis/summary.json`. The archive intentionally excludes CLI package binaries, Docker layers, and authentication credentials; runtime metadata is retained without credentials. Reproduce the native environment with the recorded image and source hashes in `provenance/runtime_hashes.json` and `controls/controls-v3`.\n",
            encoding="utf-8",
        )
        (output / "COMMANDS.md").write_text(
            "# Offline and native replay commands\n\n"
            "```powershell\n"
            "python verify_bytes.py\n"
            "python replay_verify.py\n"
            "python provenance/evidence_manifest.py verify .\n"
            "```\n\n"
            "The original generation and native commands are recorded in each turn `argv.json`, in `generation/sessions/*/command.json`, and in native provenance. Native replay requires Docker image `bcb-scale1000:v2`, the pinned BigCodeBench source, and the recorded environment inputs; this archive does not redistribute Docker binaries or authentication state.\n",
            encoding="utf-8",
        )
        write_evidence_manifest(output)
        return {"output": str(output), "completion": completion, "hash_bindings": binding}
    except Exception as exc:
        (output / ".publish_failed.json").write_text(
            json.dumps({"error": str(exc), "traceback": traceback.format_exc()}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("reproducibility/runs/scale1000-luna-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, default=Path("reproducibility/scale1000/inputs-v1"))
    parser.add_argument("--gate-dir", type=Path, default=Path("reproducibility/runs/scale1000-v1/controls-v3"))
    parser.add_argument("--manifest", type=Path, default=Path("reproducibility/scale1000_luna/generation_manifest.json"))
    args = parser.parse_args()
    print(json.dumps(publish(args.root, args.output, args.inputs, args.gate_dir, args.manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
