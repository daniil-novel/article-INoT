"""Strict publisher and offline verifier for the completed SCC 1,000-task study.

This file is future-facing: it refuses to publish until generation, all nine
native groups, the 9,000-row ledger, and strict analysis are complete. It never
starts a model or native evaluator.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
import sys
from contextlib import contextmanager

sys.dont_write_bytecode = True
_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1] if (_HERE.parents[1] / "sources").is_dir() else _HERE.parents[2]
sys.path.insert(0, str(ROOT / "sources" if (ROOT / "sources").is_dir() else ROOT))
if (ROOT / "sources/reproducibility").is_dir():
    sys.path.insert(0, str(ROOT / "sources/reproducibility"))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.evidence_manifest import write as write_manifest, verify as verify_manifest  # noqa: E402
from reproducibility.heldout200.evidence import environment_from_gate  # noqa: E402
from reproducibility.scale_env.validate_native import validate_native  # noqa: E402
from reproducibility.revision_20260911 import scc_analyze, scc_export, scc_finish  # noqa: E402


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir(): raise FileNotFoundError(src)
    shutil.copytree(src, dst, copy_function=shutil.copy2)


def _copy_file(src: Path, dst: Path) -> None:
    if not src.is_file(): raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)


def _safe_json(src: Path, dst: Path) -> None:
    data = json.loads(src.read_text(encoding="utf-8"))
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()
                    if not any(x in k.lower() for x in ("secret", "password", "authorization", "api_key"))}
        if isinstance(value, list): return [clean(v) for v in value]
        return value
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(json.dumps(clean(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_rows(root: Path) -> list[dict]:
    path = root / "candidate_records.jsonl"
    if not path.is_file(): raise ValueError("SCC candidate ledger is missing")
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    keys = {(r.get("task_id"), r.get("method"), r.get("replicate_id")) for r in rows}
    if len(rows) != 9000 or len(keys) != 9000: raise ValueError("SCC ledger must contain 9,000 unique cells")
    return rows


def _native_gate(root: Path, inputs: Path, gate_dir: Path, manifest: dict, predictions: Path) -> dict:
    gate = cli.read(gate_dir / "heldout200_control_gate.json")
    env = environment_from_gate(gate_dir)
    audits = cli.read(root / "native_audit.json") if (root / "native_audit.json").is_file() else {}
    if set(audits) != {f"{m}-r{r}" for m in manifest["methods"] for r in manifest["replicate_ids"]}:
        raise ValueError("Native audit does not contain all nine method/repeat groups")
    for key in audits:
        target = root / "native" / key; stage = root / "pipeline" / f"native-{key}"
        if not target.is_dir() or not (stage / "exit.json").is_file() or cli.read(stage / "exit.json").get("returncode") != 0:
            raise ValueError(f"Native stage is incomplete: {key}")
        samples = predictions / f"{key}.jsonl"
        if not samples.is_file(): raise ValueError(f"Native sample export missing: {key}")
        expected = {json.loads(x)["task_id"]: json.loads(x)["solution"] for x in samples.read_text(encoding="utf-8").splitlines() if x.strip()}
        checked = validate_native(target, expected, env)
        if not checked.get("ok") or checked.get("statuses") != audits[key].get("statuses"):
            raise ValueError(f"Native audit differs from retained reports: {key}")
    return {"image_id": gate.get("image_id"), "groups": len(audits), "audits": audits, "eligible": set(gate.get("evaluable_task_ids", []))}


def _validate_join(root: Path, predictions: Path, native: dict) -> None:
    actual = [json.loads(x) for x in (root / "candidate_records.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    derived = scc_finish._records(predictions, native["audits"], native["eligible"])
    if actual != derived:
        raise ValueError("Saved candidate/resource ledger differs from raw export and native audits")
    resource_path = root / "resource_usage.jsonl"
    if not resource_path.is_file(): raise ValueError("SCC resource ledger is missing")
    expected_resource = [{"id": r["id"], "task_id": r["task_id"], "method": r["method"],
                         "replicate_id": r["replicate_id"], "resource_usage": r["resource_usage"],
                         "availability": r["availability"]} for r in derived]
    stored_resource = [json.loads(x) for x in resource_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if stored_resource != expected_resource:
        raise ValueError("Saved resource ledger differs from raw export")


@contextmanager
def _archive_source_context(archive: Path):
    from reproducibility.revision_20260911 import scc_controls, scc_export
    old_root, old_rev, old_export_root = scc_controls.ROOT, scc_controls.REV, scc_export.ROOT
    scc_controls.ROOT = archive / "sources"
    scc_controls.REV = archive / "sources/reproducibility/revision_20260911"
    scc_export.ROOT = archive
    try:
        yield
    finally:
        scc_controls.ROOT, scc_controls.REV, scc_export.ROOT = old_root, old_rev, old_export_root


def _recompute(root: Path, inputs: Path, gate_dir: Path) -> None:
    saved = cli.read(root / "analysis" / "summary.json")
    with tempfile.TemporaryDirectory(prefix="scc-analysis-") as td:
        out = Path(td) / "summary.json"
        selection = cli.read(inputs / "selection.json")
        gate = cli.read(gate_dir / "heldout200_control_gate.json")
        recomputed = scc_analyze.analyze(root / "candidate_records.jsonl", strict=True,
                                         selection=selection, control_gate=gate)
        out.write_text(json.dumps(recomputed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if json.loads(out.read_text(encoding="utf-8")) != saved:
            raise ValueError("Saved SCC analysis differs from strict offline recomputation")


def verify_archive(archive: Path) -> dict:
    archive = archive.resolve(); verify_manifest(archive)
    import runpy
    pricing = runpy.run_path(str(archive / "provenance/pricing_scope.py"))
    pricing["verify_saved"](archive / "generation", archive / "pricing_scope.json")
    if not (archive / "README.md").is_file() or not (archive / "analysis/summary.json").is_file():
        raise ValueError("Published SCC archive lacks README or analysis")
    manifest = archive / "generation/manifest.json"; inputs = archive / "inputs"; gate = archive / "controls"
    # The public source tree is self-contained; context also restores globals.
    with _archive_source_context(archive):
        scc_export.validate_export(archive / "generation", inputs, manifest, archive / "predictions", gate)
        native = _native_gate(archive, inputs, gate, cli.read(manifest), archive / "predictions")
        _validate_join(archive, archive / "predictions", native)
        _recompute(archive, inputs, gate)
    from reproducibility.task_dependence.package import verify_archive as verify_supplement
    verify_supplement(archive)
    return {"ok": True, "manifest": str(archive / "EVIDENCE_MANIFEST.json")}


def publish(root: Path, inputs: Path, gate_dir: Path, manifest: Path, output: Path) -> dict:
    root, inputs, gate_dir, manifest, output = [p.resolve() for p in (root, inputs, gate_dir, manifest, output)]
    if output.exists(): raise FileExistsError(f"Refusing to overwrite existing SCC archive: {output}")
    generation = root / "generation"; status = generation / "status.json"
    if not status.is_file() or cli.read(status).get("state") != "generation_finished":
        raise ValueError("SCC publication requires generation_finished")
    if (generation / "DISPATCH.lock").exists(): raise ValueError("SCC publication refuses active dispatch lock")
    frozen = cli.read(manifest)
    rows = _load_rows(root)
    if not (root / "analysis/summary.json").is_file() or not (root / "native_audit.json").is_file():
        raise ValueError("SCC publication requires saved native audit and analysis")
    # Validate the immutable export and all native groups before creating output.
    predictions = root / "predictions"
    with tempfile.TemporaryDirectory(prefix="scc-export-") as td:
        regenerated = Path(td) / "predictions"
        scc_export.export(generation, inputs, manifest, regenerated, gate_dir)
        for path in predictions.rglob("*"):
            if path.is_file() and path.relative_to(predictions).as_posix() not in {"export_manifest.json"}:
                peer = regenerated / path.relative_to(predictions)
                if not peer.is_file() or peer.read_bytes() != path.read_bytes():
                    raise ValueError("Existing predictions differ from regenerated immutable export")
    native = _native_gate(root, inputs, gate_dir, frozen, predictions)
    _validate_join(root, predictions, native); _recompute(root, inputs, gate_dir)
    output.mkdir(parents=True)
    try:
        for name in ("generation", "native", "pipeline", "predictions", "analysis"):
            _copy_tree(root / name, output / name)
        for name in ("candidate_records.jsonl", "resource_usage.jsonl", "native_audit.json"):
            _copy_file(root / name, output / name)
        _copy_tree(gate_dir, output / "controls")
        _copy_tree(inputs, output / "inputs")
        for rel in frozen.get("source_files_sha256", {}): _copy_file(ROOT / rel, output / "sources" / rel)
        for rel in ("reproducibility/scale_env/validate_native.py", "reproducibility/evidence_manifest.py"):
            _copy_file(ROOT / rel, output / "sources" / rel)
        for rel in ("reproducibility/scale1000/environment-v2/requirements.txt", "reproducibility/scale1000/environment-v2/Dockerfile"):
            _copy_file(ROOT / rel, output / "sources" / rel)
        _copy_file(ROOT / "reproducibility/results/20260911_scc_comparison_dev9/summary.json",
                   output / "sources/reproducibility/results/20260911_scc_comparison_dev9/summary.json")
        _copy_file(ROOT / "reproducibility/requirements-publication.txt", output / "requirements-publication.txt")
        _copy_file(ROOT / "reproducibility/external_baselines/requirements.txt", output / "requirements-external.txt")
        if (root / "prior_studies_valuation.json").is_file():
            _copy_file(root / "prior_studies_valuation.json", output / "prior_studies_valuation.json")
        if (root / "launcher").is_dir():
            _copy_tree(root / "launcher", output / "launcher")
        for name in ("BIGCODEBENCH_LICENSE", "SCC_LICENSE", "LICENSE"):
            candidate = ROOT / "reproducibility/results/20260909_scc_dev3" / name
            if candidate.is_file(): _copy_file(candidate, output / "licenses" / name)
        for name in ("runtime.json", "runtime_provenance.json", "commands.json"):
            if (generation / name).is_file(): _safe_json(generation / name, output / "runtime" / name)
        _copy_file(Path(__file__), output / "provenance" / "publish_scc.py")
        from reproducibility.revision_20260911.pricing_scope import write_sidecar
        write_sidecar(output / "generation", output / "pricing_scope.json")
        _copy_file(ROOT / "reproducibility/revision_20260911/pricing_scope.py",
                   output / "provenance/pricing_scope.py")
        readme = """# SCC Luna 1,000-task study\n\nThis archive is publishable only after all 9,000 assignments, nine native method/repeat groups, and strict offline analysis passed. It retains raw generation turns, requests, session histories, generated tests, native reports, controls, inputs, runtime metadata, source hashes, and licenses. Secrets, authentication material, virtual environments, binaries, and Git metadata are excluded.\n\nOffline verification does not call models or native evaluators:\n\n```text\npython provenance/publish_scc.py --verify --archive .\npython sources/reproducibility/evidence_manifest.py verify .\n```\n\nPrimary contrasts are the preregistered SCC/SR and SCC/SN family. Missing or unavailable outcomes remain distinct from observed native failures.\n"""
        (output / "README.md").write_text(readme, encoding="utf-8")
        with (output / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n`pricing_scope.json` separately audits each submitted turn's retained usage, missing counters, and long-input/cache-write scope. Recompute it with `python provenance/pricing_scope.py --generation generation --verify pricing_scope.json`. The main archive verifier requires this check. It preserves registered base valuations and does not infer a per-inference tariff or subscription invoice.\n")
        from reproducibility.task_dependence.package import attach
        attach(root, output, "scc", inputs, gate_dir, ROOT)
        with (output / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\nSupplementary source-family intervals retain every draw and the complete source graph. Run `python source_family_replay.py` to reconstruct both using the retained publication dependencies. This supplements the main raw/native replay.\n")
        # The main offline verifier imports supplementary modules from this source tree.
        for name in ("audit.py", "sensitivity.py", "package.py", "PROTOCOL.md"):
            _copy_file(ROOT / "reproducibility/task_dependence" / name,
                output / "sources/reproducibility/task_dependence" / name)
        write_manifest(output); verify_archive(output)
        return {"archive": str(output), "rows": len(rows), "native_groups": 9}
    except Exception:
        (output / ".publish_failed.json").write_text('{"error":"publication preparation failed; retained for diagnosis"}\n', encoding="utf-8")
        raise


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--root"); p.add_argument("--inputs"); p.add_argument("--gate-dir"); p.add_argument("--manifest"); p.add_argument("--output"); p.add_argument("--verify", action="store_true"); p.add_argument("--archive")
    a = p.parse_args()
    if a.verify: print(verify_archive(Path(a.archive)))
    else: print(publish(Path(a.root), Path(a.inputs), Path(a.gate_dir), Path(a.manifest), Path(a.output)))


if __name__ == "__main__": main()
