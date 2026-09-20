"""Build and audit the anonymous FSE analysis artifact."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTPUT = HERE / "fse2027-anonymous-analysis-artifact.zip"
SCC_RECORDS = REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/candidate_records.jsonl"

FILES = {
    "README.md": HERE / "README.md",
    "reproduce_tables.py": HERE / "reproduce_tables.py",
    "reproduce_full_analysis.py": HERE / "reproduce_full_analysis.py",
    "requirements.txt": HERE / "requirements.txt",
    "primary/assignment_outcomes.jsonl": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/candidate_records.jsonl",
    "primary/summary.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/summary.json",
    "primary/native_audit.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/native_audit.json",
    "primary/source_dependence_summary.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/source-task-audit/summary.json",
    "primary/source_partitions.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/source-task-audit/partitions.json",
    "primary/selection.json": REPO / "reproducibility/scale1000/inputs-v1/selection.json",
    "primary/PROTOCOL.md": REPO / "reproducibility/scale1000/PROTOCOL.md",
    "primary/MODEL_AMENDMENT.md": REPO / "reproducibility/scale1000_luna/MODEL_AMENDMENT.md",
    "primary/SOURCE_DEPENDENCE_PROTOCOL.md": REPO / "reproducibility/task_dependence/PROTOCOL.md",
    "primary/analyze.py": REPO / "reproducibility/scale1000/analyze.py",
    "primary/source_sensitivity.py": REPO / "reproducibility/task_dependence/sensitivity.py",
    "scc/summary.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/amended-analysis/summary.json",
    "scc/per_task_contrasts.jsonl": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/amended-analysis/per_task_contrasts.jsonl",
    "scc/AMENDMENT.md": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/amendment/AMENDMENT.md",
    "scc/PROTOCOL.md": REPO / "reproducibility/revision_20260911/scc_protocol.md",
    "scc/analyze.py": REPO / "reproducibility/scc2000/analyze.py",
    "scc/selection_manifest.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/amendment/selection_manifest.json",
    "scc/control_gate.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/controls/heldout200_control_gate.json",
    "scc/source_audit/edges.jsonl": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/source-task-audit/edges.jsonl",
    "scc/source_audit/EVIDENCE_MANIFEST.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/source-task-audit/EVIDENCE_MANIFEST.json",
    "scc/source_audit/fingerprints.jsonl": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/source-task-audit/fingerprints.jsonl",
    "scc/source_audit/partitions.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/source-task-audit/partitions.json",
    "scc/source_audit/summary.json": REPO / "reproducibility/results/20260913_scc2000_luna_full_v2/source-task-audit/summary.json",
    "paper_tables/primary_quality.tex": REPO / "submission/fse2027/paper/primary_quality.tex",
    "paper_tables/primary_contrasts.tex": REPO / "submission/fse2027/paper/primary_contrasts.tex",
    "paper_tables/direct_contrasts.tex": REPO / "submission/fse2027/paper/direct_contrasts.tex",
    "paper_tables/subgroup_sensitivity.tex": REPO / "submission/fse2027/paper/subgroup_sensitivity.tex",
    "paper_tables/primary_resources.tex": REPO / "submission/fse2027/paper/primary_resources.tex",
    "paper_tables/scc_comparison.tex": REPO / "submission/fse2027/paper/scc_comparison.tex",
}

FORBIDDEN = [
    re.compile(pattern, re.I)
    for pattern in (
        r"daniil", r"privezentsev", r"gf62", r"daniil-novel",
        r"[a-z]:\\users\\", r"[a-z]:\\", r"вшэ", r"higher school of economics",
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
    )
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    missing = [str(source) for source in [*FILES.values(), SCC_RECORDS] if not source.is_file()]
    if missing:
        raise SystemExit("missing inputs:\n" + "\n".join(missing))
    with tempfile.TemporaryDirectory(prefix="fse-artifact-") as temp:
        root = Path(temp)
        for relative, source in FILES.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        # Candidate source text is unnecessary for the statistics and can contain
        # task-authored example addresses.  Keep every assigned outcome, status,
        # resource counter, and hash while removing the source-text field.
        target = root / "scc/assignment_outcomes.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        with SCC_RECORDS.open(encoding="utf-8") as source, target.open("w", encoding="utf-8", newline="\n") as output:
            for line in source:
                if line.strip():
                    row = json.loads(line)
                    row.pop("solution", None)
                    output.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

        findings: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in FORBIDDEN:
                if pattern.search(text):
                    findings.append(f"{path.relative_to(root).as_posix()}: {pattern.pattern}")
        if findings:
            raise SystemExit("anonymity scan failed:\n" + "\n".join(findings))

        records = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                records.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
        manifest = {
            "schema": "fse2027-anonymous-analysis-artifact-v1",
            "algorithm": "SHA-256 over exact file bytes",
            "anonymity_scan": "passed",
            "files": records,
        }
        (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        OUTPUT.unlink(missing_ok=True)
        with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())

    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
    print(json.dumps({"output": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "files": len(records) + 1}, indent=2))


if __name__ == "__main__":
    main()
