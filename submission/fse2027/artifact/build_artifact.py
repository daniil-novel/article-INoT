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
MINI_ROOT = REPO / "reproducibility/results/20260908_codex_mini_heldout200"
MINI_RECORDS = MINI_ROOT / "analysis/candidate_records.jsonl"
MINI_MANIFEST = MINI_ROOT / "protocols/heldout200_generation_manifest.json"
PRIMARY_ROOT = REPO / "reproducibility/results/20260912_scale1000_luna_full"

FILES = {
    "README.md": HERE / "README.md",
    "reproduce_tables.py": HERE / "reproduce_tables.py",
    "reproduce_full_analysis.py": HERE / "reproduce_full_analysis.py",
    "reproduce_source_sensitivity.py": HERE / "reproduce_source_sensitivity.py",
    "verify_native_evidence.py": HERE / "verify_native_evidence.py",
    "requirements.txt": HERE / "requirements.txt",
    "primary/assignment_outcomes.jsonl": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/candidate_records.jsonl",
    "primary/summary.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/summary.json",
    "primary/native_audit.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/analysis/native_audit.json",
    "primary/source_dependence_summary.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/source-task-audit/summary.json",
    "primary/source_partitions.json": REPO / "reproducibility/results/20260912_scale1000_luna_full/source-task-audit/partitions.json",
    "primary/selection.json": REPO / "reproducibility/scale1000/inputs-v1/selection.json",
    "primary/control_gate.json": PRIMARY_ROOT / "controls/controls-v3/heldout200_control_gate.json",
    "primary/PROTOCOL.md": REPO / "reproducibility/scale1000/PROTOCOL.md",
    "primary/MODEL_AMENDMENT.md": REPO / "reproducibility/scale1000_luna/MODEL_AMENDMENT.md",
    "primary/SOURCE_DEPENDENCE_PROTOCOL.md": REPO / "reproducibility/task_dependence/PROTOCOL.md",
    "primary/analyze.py": REPO / "reproducibility/scale1000/analyze.py",
    "primary/source_sensitivity.py": REPO / "reproducibility/task_dependence/sensitivity.py",
    "mini/summary.json": MINI_ROOT / "analysis/summary.json",
    "mini/analyze.py": REPO / "reproducibility/heldout200/analyze.py",
    "mini/PROTOCOL.md": MINI_ROOT / "protocols/HELDOUT200_PROTOCOL.md",
    "mini/EXECUTION_AMENDMENT.md": MINI_ROOT / "protocols/HELDOUT200_EXECUTION_AMENDMENT.md",
    "mini/frozen_prompt_material.json": MINI_ROOT / "protocols/frozen_prompt_material.json",
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
    "paper_tables/secondary_model.tex": REPO / "submission/fse2027/paper/secondary_model.tex",
    "paper_tables/related_comparison.tex": REPO / "submission/fse2027/paper/related_comparison.tex",
    "paper_tables/primary_resources.tex": REPO / "submission/fse2027/paper/primary_resources.tex",
    "paper_tables/scc_comparison.tex": REPO / "submission/fse2027/paper/scc_comparison.tex",
}

FORBIDDEN = [
    re.compile(pattern, re.I)
    for pattern in (
        r"daniil", r"privezentsev", r"gf62", r"daniil-novel",
        r"[a-z]:\\users\\", r"higher school of economics", r"springer-article", r"курсовая работа",
    )
]
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", re.I)
RUSSIAN_AFFILIATION = re.compile(r"вшэ", re.I)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def anonymize_json_paths(value):
    """Replace only machine-local path prefixes; preserve scientific payloads."""
    if isinstance(value, str):
        replacements = (
            (str(REPO), "<ANON_REPOSITORY>"),
            (str(REPO).replace("\\", "/"), "<ANON_REPOSITORY>"),
            (r"C:\Users\GF62", "<ANON_USER>"),
            ("C:/Users/GF62", "<ANON_USER>"),
        )
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [anonymize_json_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: anonymize_json_paths(item) for key, item in value.items()}
    return value


def main() -> None:
    missing = [str(source) for source in [*FILES.values(), SCC_RECORDS, MINI_RECORDS, MINI_MANIFEST] if not source.is_file()]
    if missing:
        raise SystemExit("missing inputs:\n" + "\n".join(missing))
    with tempfile.TemporaryDirectory(prefix="fse-artifact-") as temp:
        root = Path(temp)
        for relative, source in FILES.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        # Preserve the primary candidate-to-test evidence chain.  These are the
        # exact generated programs, staged evaluator inputs, native reports,
        # control records, and pinned evaluator materials used by the paper.
        evaluation = root / "primary/evaluation"
        shutil.copytree(PRIMARY_ROOT / "predictions", evaluation / "predictions",
                        ignore=shutil.ignore_patterns("export_manifest.json", "turn_usage.json"))
        shutil.copytree(PRIMARY_ROOT / "native", evaluation / "native")
        shutil.copytree(PRIMARY_ROOT / "controls/controls-v3", evaluation / "controls")
        shutil.copytree(PRIMARY_ROOT / "sources/bigcodebench", evaluation / "bigcodebench-source",
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        (evaluation / "dataset").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            PRIMARY_ROOT / "supplementary-sources/reproducibility/data/bigcodebench-v0.1.4.jsonl",
            evaluation / "dataset/bigcodebench-v0.1.4.jsonl",
        )
        shutil.copyfile(PRIMARY_ROOT / "environment/scale1000-v2-Dockerfile",
                        evaluation / "scale1000-v2-Dockerfile")
        shutil.copyfile(PRIMARY_ROOT / "environment/scale1000-v2-requirements.txt",
                        evaluation / "scale1000-v2-requirements.txt")
        shutil.copyfile(PRIMARY_ROOT / "licenses/BIGCODEBENCH-LICENSE.txt",
                        evaluation / "BIGCODEBENCH-LICENSE.txt")
        shutil.copytree(PRIMARY_ROOT / "source-family-sensitivity", root / "primary/source_sensitivity")

        sanitized: list[str] = []
        for path in sorted(evaluation.rglob("*.json")):
            original = json.loads(path.read_text(encoding="utf-8"))
            anonymous = anonymize_json_paths(original)
            if anonymous != original:
                path.write_text(json.dumps(anonymous, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                sanitized.append(path.relative_to(root).as_posix())
        # The control gate hashes its metadata files.  Bind it to the anonymous
        # metadata copies while leaving report and candidate hashes unchanged.
        gate_path = evaluation / "controls/heldout200_control_gate.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        for kind in ("gold", "incorrect"):
            gate[f"{kind}_metadata_sha256"] = digest(evaluation / f"controls/{kind}/run-metadata.json")
        gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
        (evaluation / "SANITIZATION.md").write_text(
            "# Anonymous metadata transformation\n\n"
            "Machine-local repository and user-profile prefixes in JSON string fields were replaced "
            "with `<ANON_REPOSITORY>` and `<ANON_USER>`. Candidate programs, staged inputs, native "
            "test reports, status values, environment identifiers, and report hashes were not changed. "
            "The control gate's two metadata-file hashes were recomputed over the anonymous copies.\n\n"
            "Transformed files:\n" + "".join(f"- `{name}`\n" for name in sanitized),
            encoding="utf-8",
        )

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

        # The earlier mini ledger carries full response text and a nested usage
        # object in addition to the scalar analysis fields.  Neither is read by
        # the retained analyzer, so omit both from the anonymous replay input.
        target = root / "mini/assignment_outcomes.jsonl"
        with MINI_RECORDS.open(encoding="utf-8") as source, target.open("w", encoding="utf-8", newline="\n") as output:
            for line in source:
                if line.strip():
                    row = json.loads(line)
                    row.pop("final_text", None)
                    row.pop("usage", None)
                    output.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        source_manifest = json.loads(MINI_MANIFEST.read_text(encoding="utf-8"))
        (root / "mini/selection.json").write_text(
            json.dumps({"assigned_task_ids": source_manifest["assigned_task_ids"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        # Make the retained analyzer standalone inside the review archive.
        analyzer = root / "mini/analyze.py"
        analyzer.write_text(
            analyzer.read_text(encoding="utf-8").replace(
                "from ..codex_subscription import ARMS, read, save",
                "from codex_subscription import ARMS, read, save",
            ),
            encoding="utf-8",
            newline="\n",
        )
        (root / "mini/codex_subscription.py").write_text(
            """from __future__ import annotations
import json
from pathlib import Path

ARMS = ('single_neutral', 'single_roles', 'multi_neutral', 'multi_roles', 'direct')

def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\\n'
    path.write_text(payload, encoding='utf-8', newline='\\n')
""",
            encoding="utf-8",
            newline="\n",
        )

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
            relative = path.relative_to(root).as_posix()
            if not relative.startswith("primary/evaluation/"):
                if EMAIL.search(text):
                    findings.append(f"{relative}: email address")
                if RUSSIAN_AFFILIATION.search(text):
                    findings.append(f"{relative}: affiliation")
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
