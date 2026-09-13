"""Strict publication and raw/native/statistical replay of the SCC 2000-block amendment."""
from __future__ import annotations

import argparse
import hashlib
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
from reproducibility.scc2000 import analyze, continuation, finish
from reproducibility.task_dependence import audit
from reproducibility.task_dependence.package import SOURCE_FILES


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



def _same_tree(actual: Path, expected: Path, skip=()) -> None:
    def entries(root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix() not in skip}
    if entries(actual) != entries(expected):
        raise ValueError("Recomputed evidence differs: " + actual.name)


def _gate(root: Path, selection: Path, inputs: Path, manifest: Path, gate_dir: Path, amendment: Path) -> dict:
    generation = root / "generation"
    sel = continuation.load_selection(selection, amendment=amendment)
    if continuation.sha(manifest) != sel["original_manifest_sha256"]:
        raise ValueError("Original manifest differs from amendment binding")
    finish._verify_prefix(sel, inputs, manifest, gate_dir)
    finish._terminal_selected(generation, set(sel["selected_ids"]))
    calculated = continuation.continuation_status(root=generation, selected_ids=sel["selected_ids"], lock=generation / "DISPATCH.lock")
    saved = cli.read(generation / "continuation_status.json")
    if calculated != saved or saved["state"] != "completed":
        raise ValueError("Selected completion status differs from assignment evidence")
    if cli.read(generation / "status.json").get("state") != "paused":
        raise ValueError("Original 9000-cell dispatcher must remain administratively paused")
    for ident in set(sel["all_ids"]) - set(sel["selected_ids"]):
        if (generation / "assignments" / ident).exists():
            raise ValueError("An administratively unselected assignment was touched")
    return sel


def _selected_view(root: Path, selection: dict) -> None:
    rows = _load_rows(root)
    selected_ids = set(selection["selected_ids"])
    expected = [r for r in rows if r["id"] in selected_ids]
    if len(expected) != 6000 or len({r["id"] for r in expected}) != 6000:
        raise ValueError("Ledger does not contain every selected assignment exactly once")
    actual = [json.loads(x) for x in (root / "selected_assignment_records.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if actual != expected:
        raise ValueError("Selected view differs from the original ledger")


def _recompute_amended(root: Path, selection: Path, gate_dir: Path, source_audit: Path) -> None:
    saved_dir = root / "amended-analysis"
    saved = cli.read(saved_dir / "summary.json")
    with tempfile.TemporaryDirectory(prefix="scc2000-replay-") as td:
        out = Path(td) / "analysis"
        analyze.run_files(root / "candidate_records.jsonl", selection,
                          gate_dir / "heldout200_control_gate.json", source_audit, out)
        calculated = cli.read(out / "summary.json")
        # Python patch versions are provenance, not scientific statistics.
        # Input digests, numeric results, records and every draw must match.
        for value in (saved, calculated):
            value["provenance"].pop("python", None)
        if saved != calculated:
            raise ValueError("Amended statistics or input provenance differ on replay")
        _same_tree(saved_dir, out, skip={"summary.json"})


def _recompute_source_graph(archive: Path) -> None:
    retained = archive / "source-task-audit"
    verify_manifest(retained)
    old_root = audit.ROOT
    audit.ROOT = archive / "sources"
    try:
        with tempfile.TemporaryDirectory(prefix="scc2000-source-") as td:
            out = Path(td) / "audit"
            audit.run(archive / "sources/reproducibility/data/bigcodebench-v0.1.4.jsonl", archive / "inputs", out)
            _same_tree(retained, out)
    finally:
        audit.ROOT = old_root


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
        selection = archive / "amendment/selection_manifest.json"
        selected = _gate(archive, selection, inputs, manifest, gate, archive / "amendment/AMENDMENT.md")
        scc_export.validate_export(archive / "generation", inputs, manifest, archive / "predictions", gate)
        native = _native_gate(archive, inputs, gate, cli.read(manifest), archive / "predictions")
        _validate_join(archive, archive / "predictions", native)
        _recompute(archive, inputs, gate)
        _selected_view(archive, selected)
        _recompute_amended(archive, selection, gate, archive / "source-task-audit")
    _recompute_source_graph(archive)
    return {"ok": True, "manifest": str(archive / "EVIDENCE_MANIFEST.json")}


def publish(root: Path, inputs: Path, gate_dir: Path, manifest: Path, output: Path, selection: Path, source_audit: Path | None = None) -> dict:
    root, inputs, gate_dir, manifest, output = [p.resolve() for p in (root, inputs, gate_dir, manifest, output)]
    if output.exists(): raise FileExistsError(f"Refusing to overwrite existing SCC archive: {output}")
    generation = root / "generation"; status = generation / "status.json"
    selection = selection.resolve()
    source_audit = (source_audit or ROOT / "reproducibility/task_dependence/source-audit-v2").resolve()
    amendment = ROOT / "reproducibility/scc2000/AMENDMENT.md"
    selected = _gate(root, selection, inputs, manifest, gate_dir, amendment)
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
    _selected_view(root, selected)
    _recompute_amended(root, selection, gate_dir, source_audit)
    output.mkdir(parents=True)
    try:
        for name in ("generation", "native", "pipeline", "predictions", "analysis", "amended-analysis"):
            _copy_tree(root / name, output / name)
        for name in ("candidate_records.jsonl", "selected_assignment_records.jsonl", "resource_usage.jsonl", "native_audit.json"):
            _copy_file(root / name, output / name)
        _copy_tree(gate_dir, output / "controls")
        _copy_tree(inputs, output / "inputs")
        _copy_tree(source_audit, output / "source-task-audit")
        _copy_tree(ROOT / "reproducibility/scc2000/recovery-v1", output / "amendment/recovery-v1")
        _copy_tree(ROOT / "reproducibility/scc2000/execution-resume-v1", output / "amendment/execution-resume-v1")
        _copy_file(selection, output / "amendment/selection_manifest.json")
        _copy_file(amendment, output / "amendment/AMENDMENT.md")
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
        (output / "README.md").write_text("""# SCC fixed 2000-block comparison

The first 2000 randomized task-repeat blocks contain 6000 assigned method cells across 956 tasks. Every observed candidate has native test evidence; absent generation remains unknown. The original 9000-row ledger retains 3000 administratively unselected cells. Its dispatcher status remains paused. The amendment was adopted after generation began, before inspecting SCC quality.

Full requests, answers, programs, generated checks, native reports, controls and source data are retained. The original three-complete-repeat estimator and amended matched-selected-repeat estimator have separate fixed test families. Task and source-group bootstrap draws are retained in numeric files. API-equivalent valuations are not invoices.

Install requirements-publication.txt and requirements-external.txt in Python 3.11, then run:

```text
python provenance/publish_scc.py --verify --archive .
```

Verification checks exact inventories, regenerates exports, joins native reports, recomputes both estimators, every amended bootstrap draw, the source graph, and pricing scope without model calls. Python patch-version provenance may differ only when all numerical outputs and draws match exactly. This full research archive retains operational provenance and is not the anonymous conference supplement.
""", encoding="utf-8")
        files = set(SOURCE_FILES) | {
            f"reproducibility/scc2000/{name}.py" for name in ("publish", "finish", "analyze", "continuation", "resume_snapshot")}
        for rel in sorted(files): _copy_file(ROOT / rel, output / "sources" / rel)
        # The main offline verifier imports supplementary modules from this source tree.
        for name in ("audit.py", "sensitivity.py", "package.py", "PROTOCOL.md"):
            _copy_file(ROOT / "reproducibility/task_dependence" / name,
                output / "sources/reproducibility/task_dependence" / name)
        write_manifest(output); verify_archive(output)
        return {"archive": str(output), "rows": len(rows), "selected_cells": 6000, "native_groups": 9, "raw_native_original_and_amended_replayed": True}
    except Exception:
        (output / ".publish_failed.json").write_text('{"error":"publication preparation failed; retained for diagnosis"}\n', encoding="utf-8")
        raise


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--root"); p.add_argument("--inputs"); p.add_argument("--gate-dir"); p.add_argument("--manifest"); p.add_argument("--output"); p.add_argument("--selection"); p.add_argument("--source-audit", type=Path); p.add_argument("--verify", action="store_true"); p.add_argument("--archive")
    a = p.parse_args()
    if a.verify: print(verify_archive(Path(a.archive)))
    else: print(publish(Path(a.root), Path(a.inputs), Path(a.gate_dir), Path(a.manifest), Path(a.output), Path(a.selection), a.source_audit))


if __name__ == "__main__": main()
