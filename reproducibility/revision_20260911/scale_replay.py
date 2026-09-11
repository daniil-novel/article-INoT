"""Offline full replay of a completed Luna archive using its frozen source copy."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True


def sha(path: Path, *, lf=False) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if lf else data).hexdigest()


def install(archive: Path, repository: Path) -> None:
    """Copy the frozen implementation and its separately hashed protocol."""
    manifest = json.loads((archive / "generation/manifest.json").read_text(encoding="utf-8"))
    sources = archive / "replay-sources/reproducibility"
    for name, expected in manifest["source_sha256_lf"].items():
        original = archive / "generation/sources" / name
        if sha(original, lf=True) != expected:
            raise ValueError("Frozen source hash mismatch before replay installation: " + name)
        destination = sources / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
    protocol = archive / "protocols/PROTOCOL.md"
    if sha(protocol, lf=True) != manifest["protocol_sha256_lf"]:
        raise ValueError("Frozen Luna protocol differs")
    shutil.copyfile(protocol, sources / "scale1000_luna/PROTOCOL.md")
    shutil.copyfile(repository / "reproducibility/evidence_manifest.py", sources / "evidence_manifest.py")
    shutil.copyfile(repository / "reproducibility/requirements-publication.txt", archive / "requirements-publication.txt")
    destination = archive / "provenance/scale_replay.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__), destination)
    from reproducibility.revision_20260911.pricing_scope import write_sidecar
    write_sidecar(archive / "generation", archive / "pricing_scope.json")
    shutil.copyfile(repository / "reproducibility/revision_20260911/pricing_scope.py",
                    archive / "provenance/pricing_scope.py")


def verify(archive: Path) -> dict:
    archive = archive.resolve()
    source_root = archive / "replay-sources"
    sys.path.insert(0, str(source_root))
    # Refuse a cached checkout import: full replay must execute archived code.
    names = ("reproducibility.evidence_manifest", "reproducibility.codex_luna_subscription",
             "reproducibility.factorial_runner", "reproducibility.benchmark_bridge",
             "reproducibility.record_codex_runtime", "reproducibility.heldout200.evidence",
             "reproducibility.scale_env.validate_native", "reproducibility.scale1000_luna.dispatch",
             "reproducibility.scale1000_luna.collect", "reproducibility.scale1000.analyze")
    modules = {name: importlib.import_module(name) for name in names}
    for name, module in modules.items():
        if not Path(module.__file__).resolve().is_relative_to(source_root):
            raise ValueError("Replay loaded code outside the retained source tree: " + name)
    modules["reproducibility.evidence_manifest"].verify(archive)
    generation = archive / "generation"
    pricing = runpy.run_path(str(archive / "provenance/pricing_scope.py"))
    pricing["verify_saved"](generation, archive / "pricing_scope.json")
    if json.loads((generation / "status.json").read_text(encoding="utf-8")).get("state") != "generation_finished" or (generation / "DISPATCH.lock").exists():
        raise ValueError("Full replay requires a terminal published generation")
    frozen = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
    if frozen.get("planned_candidates") != 15000 or frozen.get("planned_cli_turns") != 27000:
        raise ValueError("Archive is not the frozen full Luna allocation")
    for name, expected in frozen["source_sha256_lf"].items():
        copied = source_root / "reproducibility" / name
        original = generation / "sources" / name
        if sha(copied, lf=True) != expected or copied.read_bytes() != original.read_bytes():
            raise ValueError("Replay source differs from frozen generation source: " + name)
    protocol = source_root / "reproducibility/scale1000_luna/PROTOCOL.md"
    if sha(protocol, lf=True) != frozen["protocol_sha256_lf"]:
        raise ValueError("Replay protocol differs from the frozen protocol")
    inputs = archive / "inputs/scale1000-v1"
    gate = archive / "controls/controls-v3"
    collector = modules["reproducibility.scale1000_luna.collect"]
    analyzer = modules["reproducibility.scale1000.analyze"]
    with tempfile.TemporaryDirectory(prefix="luna-full-replay-") as temporary:
        calculated = Path(temporary) / "analysis"
        collector.collect(generation, inputs, gate, generation / "manifest.json",
            archive / "predictions", archive / "native", calculated)
        for name in ("candidate_records.jsonl", "turn_usage.json", "native_audit.json"):
            if (calculated / name).read_bytes() != (archive / "analysis" / name).read_bytes():
                raise ValueError("Raw/native reconstruction differs from saved ledger: " + name)
        rows = [json.loads(line) for line in (calculated / "candidate_records.jsonl").read_text(encoding="utf-8").splitlines()]
        selection = json.loads((inputs / "selection.json").read_text(encoding="utf-8"))
        summary = analyzer.summarize(rows, selection)
        if summary != json.loads((archive / "analysis/summary.json").read_text(encoding="utf-8")):
            raise ValueError("Complete statistical summary differs from full replay")
    return {"ok": True, "assigned_rows": len(rows), "source_root": "replay-sources",
        "verified": ["all archive bytes", "frozen plan and sources", "raw requests and exposed answers",
                     "all submitted usage", "native reports and control gate", "complete assignment ledger",
                     "full registered statistical summary", "supplementary recorded-usage pricing scope"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.archive)))
