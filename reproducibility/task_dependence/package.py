"""Attach supplementary evidence only after the main publisher's raw/native replay."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

from . import audit, sensitivity
from reproducibility.evidence_manifest import verify

LAYOUT = {
    "factorial": ("inputs/scale1000-v1", "controls/controls-v3"),
    "scc": ("inputs", "controls"),
}
SOURCE_FILES = (
    "reproducibility/task_dependence/audit.py",
    "reproducibility/task_dependence/sensitivity.py",
    "reproducibility/task_dependence/package.py",
    "reproducibility/task_dependence/PROTOCOL.md",
    "reproducibility/evidence_manifest.py",
    "reproducibility/data/bigcodebench-v0.1.4.jsonl",
    "reproducibility/data/BIGCODEBENCH-LICENSE.txt",
    "reproducibility/data/README.md",
    "reproducibility/data/bigcodebench-split/prepare_manifest.json",
    "reproducibility/segregation80/inputs-v2/selection.json",
    "reproducibility/requirements-publication.txt",
)


def verify_archive(archive: Path) -> dict:
    """Verify source graph and all draws from archive paths; no model/native execution."""
    archive = archive.resolve()
    metadata = json.loads((archive / "source-family-package.json").read_text(encoding="utf-8"))
    study = metadata["study"]
    inputs, gate = [archive / value for value in LAYOUT[study]]
    sources = archive / "supplementary-sources"
    for name, expected in metadata["source_sha256"].items():
        if audit.digest((sources / name).read_bytes()) != expected:
            raise ValueError("Supplementary replay source or dependency declaration changed")
    if set(metadata["source_sha256"]) != set(SOURCE_FILES):
        raise ValueError("Supplementary source closure is incomplete")
    retained = archive / "source-task-audit"
    verify(retained)
    # audit.source_inputs checks the frozen hashes of these subset definitions.
    old_root = audit.ROOT
    audit.ROOT = sources
    try:
        with tempfile.TemporaryDirectory(prefix="source-graph-replay-") as temporary:
            calculated = Path(temporary) / "audit"
            audit.run(sources / "reproducibility/data/bigcodebench-v0.1.4.jsonl", inputs, calculated)
            for path in calculated.iterdir():
                if path.read_bytes() != (retained / path.name).read_bytes():
                    raise ValueError("Source graph differs from retained source-only audit")
    finally:
        audit.ROOT = old_root
    result = sensitivity.verify_saved(archive, study, retained, archive / "source-family-sensitivity",
        selection_path=inputs / "selection.json", gate_path=gate / "heldout200_control_gate.json")
    return {"ok": True, "scope": "source graph and supplementary intervals; run main replay separately", **result}


def attach(run_root: Path, archive: Path, study: str, inputs: Path, gate: Path, source_root: Path) -> None:
    """Called after raw/native replay and before the enclosing evidence inventory."""
    retained = source_root / "reproducibility/task_dependence/source-audit-v2"
    saved = run_root / "source-family-sensitivity"
    if not saved.is_dir():
        raise ValueError("Completed source-family sensitivity is required before publication")
    sensitivity.verify_saved(run_root, study, retained, saved,
        selection_path=inputs / "selection.json", gate_path=gate / "heldout200_control_gate.json")
    shutil.copytree(retained, archive / "source-task-audit")
    shutil.copytree(saved, archive / "source-family-sensitivity")
    hashes = {}
    for name in SOURCE_FILES:
        destination = archive / "supplementary-sources" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / name, destination)
        hashes[name] = audit.digest(destination.read_bytes())
    (archive / "source-family-package.json").write_bytes(audit.encoded({
        "schema": "source-family-package-v1", "study": study, "source_sha256": hashes,
        "prerequisite": "Enclosing publisher verifies the complete raw/native ledger before attachment."}))
    (archive / "source_family_replay.py").write_text(
        '"""Offline supplementary replay; install retained publication requirements first."""\n'
        'import json, sys\nfrom pathlib import Path\n'
        'sys.dont_write_bytecode = True\n'
        'root = Path(__file__).resolve().parent\n'
        'sys.path.insert(0, str(root / "supplementary-sources"))\n'
        'from reproducibility.task_dependence.package import verify_archive\n'
        'print(json.dumps(verify_archive(root)))\n', encoding="utf-8", newline="\n")
    verify_archive(archive)
