"""Recover and package the selected July evidence; owner-only build helper."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parents[1]
ARTICLE_REV = "173a16c3"
RESEARCH = Path(r"E:\JarvisSonoma\hybrid_inot_research")
RESEARCH_REV = "010211ee5775185e8330ab6cde06e912c2adcb9e"
REPLICATION = BASE / "replication"
PAYLOAD = REPLICATION / "hybrid-inot-july-2026"
PROVENANCE = REPLICATION / "provenance"
RECORDS = []
PRIVATE_PATTERNS = [
    r"daniil", r"privezentsev", r"daprivezentsev", r"GF62", r"JarvisSonoma",
    r"springer-article", re.escape(RESEARCH_REV), r"173a16c3",
    r"(?<![A-Za-z])[A-Za-z]:[\\/](?!/)", r"https?://github\.com/daniil-novel",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(repo: Path, revision: str, relative: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{revision}:{relative}"])


def git_names(repo: Path, revision: str) -> list[str]:
    return subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", revision], text=True
    ).splitlines()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def anonymous_text(text: str) -> str:
    text = re.sub(r"https://github\.com/daniil-novel/INoT_Research", "anonymous research snapshot", text, flags=re.I)
    text = text.replace(RESEARCH_REV, "anonymous-source-snapshot")
    text = re.sub(r"^authors\s*=.*\n", "", text, flags=re.M)
    text = re.sub(r"\bDaniil Privezentsev\b", "Anonymous authors", text, flags=re.I)
    text = re.sub(r"\bPrivezentsev\b", "Anonymous authors", text, flags=re.I)
    return text


def recover(repo: Path, revision: str, origin: str, target: str, transform=None) -> None:
    original = git_blob(repo, revision, origin)
    packaged = original if transform is None else transform(original)
    destination = PAYLOAD / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(packaged)
    RECORDS.append({
        "repository": str(repo), "revision": revision, "source_path": origin,
        "packaged_path": target, "git_blob_sha256": digest(original),
        "packaged_sha256": digest(packaged), "bytes_changed": original != packaged,
        "adaptation": None if transform is None else transform.__name__,
    })


def clean_text(data: bytes) -> bytes:
    return anonymous_text(data.decode("utf-8")).encode("utf-8")


def adapt_builder(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("import subprocess\n", "import socket\n")
    text = re.sub(r'EXPECTED_COMMIT = "[^"]+"\n', "", text)
    start = text.index("def git_commit(root: Path) -> str:")
    end = text.index("def read_e3_rows", start)
    text = text[:start] + '''def verify_packaged_inputs(research_root: Path) -> None:
    package_root = research_root.parent
    manifest = read_json(package_root / "MANIFEST.json")
    for entry in manifest["files"]:
        target = package_root / entry["path"]
        if not target.is_file() or sha256(target) != entry["sha256"]:
            raise ValueError("package integrity check failed: " + entry["path"])


def block_network() -> None:
    def blocked(*args, **kwargs):
        raise RuntimeError("This evidence rebuild is offline; network access is disabled")
    socket.create_connection = blocked
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked


''' + text[end:]
    start = text.index("    commit = git_commit(args.research_root)")
    end = text.index("    flash_e3_paths", start)
    text = text[:start] + "    block_network()\n    verify_packaged_inputs(args.research_root)\n\n" + text[end:]
    text = text.replace('        "research_repository": "https://github.com/daniil-novel/INoT_Research",\n', "")
    text = text.replace('        "research_commit": commit,\n', "")
    text = text.replace('"path": str(path),', '"path": path.resolve().relative_to(args.research_root.parent.resolve()).as_posix(),')
    text = text.replace('"humaneval_input_profile": humaneval_input_profile(args.research_root),', '''"humaneval_input_profile": read_json(
            Path(__file__).resolve().parent / "evidence_snapshot.json"
        )["humaneval_input_profile"],''')
    return anonymous_text(text).encode("utf-8")


EXPORT = '''from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path


def table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export(evidence_path: Path, output: Path):
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for model, key in [("Pro", "tracked_pro_humaneval_e3"), ("Flash-Lite", "flash_lite_humaneval_e3_replication")]:
        for ctx in ["256", "1024", "4096", "16384"]:
            b2 = evidence[key]["B2_ClassicalMAS"][ctx]
            b3 = evidence[key]["B3_HybridINoT"][ctx]
            rows.append({"model": model, "context_target_tokens": int(ctx), "n_per_architecture": b2["n"],
                         "b2_mean_tokens": b2["mean_tokens"], "b3_mean_tokens": b3["mean_tokens"],
                         "token_savings_pct": b3["token_savings_vs_b2_pct"],
                         "b2_pass_at_1": b2["pass_at_1"], "b3_pass_at_1": b3["pass_at_1"],
                         "b2_mean_cost_usd": b2["mean_cost_usd"], "b3_mean_cost_usd": b3["mean_cost_usd"]})
    table(output / "e3_measurements.csv", rows)
    table(output / "e4_profitability.csv", [{"suite": k, **{field: value for field, value in v.items() if not isinstance(value, dict)}} for k, v in evidence["new_e4"].items()])
    table(output / "e6_model_comparisons.csv", evidence["tracked_e6_comparisons"])
    e5 = evidence["inference_cost_extrapolation_from_tracked_e3"]
    table(output / "e5_price_sensitivity.csv", e5["price_sensitivity"])
    rows = []
    for cohort, key in [("Pro", "tracked_pro_humaneval_e3_pairwise"), ("Flash-Lite", "flash_lite_humaneval_e3_pairwise")]:
        for values in evidence[key]:
            rows.append({"model": cohort, **{k: json.dumps(v) if isinstance(v, list) else v for k, v in values.items()}})
    table(output / "e3_paired_statistics.csv", rows)
    # Retain complete original E2 aggregates rather than invent a new ablation convention.
    (output / "e2_aggregates.json").write_text(json.dumps({key: evidence[key] for key in ["tracked_e2_stats", "tracked_e2_pairwise", "tracked_e2_full_summary"]}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=Path(__file__).resolve().parents[1] / "article" / "reproducibility" / "evidence_snapshot.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "tables")
    args = parser.parse_args()
    export(args.evidence, args.output)
'''


VERIFY = '''from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import socket
import subprocess
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(expected, actual, path="", differences=None):
    differences = [] if differences is None else differences
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            differences.append(path + ": dictionary keys differ")
        for key in expected.keys() & actual.keys():
            compare(expected[key], actual[key], path + "/" + key, differences)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            differences.append(path + ": list length differs")
        for index, (a, b) in enumerate(zip(expected, actual)):
            compare(a, b, path + "/" + str(index), differences)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool) and isinstance(actual, (int, float)):
        if not math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-14):
            differences.append(path + ": numeric value differs")
    elif expected != actual:
        differences.append(path + ": value differs")
    return differences


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    integrity_errors = [item["path"] for item in manifest["files"] if not (root / item["path"]).is_file() or sha(root / item["path"]) != item["sha256"]]
    if integrity_errors:
        raise SystemExit("Integrity check failed: " + ", ".join(integrity_errors))
    # The adapted builder itself disables socket connections before analysis.
    environment = dict(os.environ)
    environment.pop("OPENROUTER_API_KEY", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["MPLCONFIGDIR"] = str(output / "plot-cache")
    command = [sys.executable, str(root / "article/reproducibility/build_article_evidence.py"),
               "--research-root", str(root / "research"), "--new-results", str(root / "article/reproducibility/results/20260726_flash_lite"),
               "--output-root", str(output / "reproducibility")]
    subprocess.run(command, check=True, env=environment, capture_output=True, text=True)
    expected = json.loads((root / "article/reproducibility/evidence_snapshot.json").read_text(encoding="utf-8"))
    actual = json.loads((output / "reproducibility/evidence_snapshot.json").read_text(encoding="utf-8"))
    differences = compare(expected, actual)
    subprocess.run([sys.executable, str(root / "scripts/export_tables.py"), "--evidence", str(output / "reproducibility/evidence_snapshot.json"), "--output", str(output / "tables")], check=True, env=environment)
    csv_checks = {p.name: p.read_bytes() == (output / "tables" / p.name).read_bytes() for p in (root / "tables").iterdir() if p.is_file()}
    from PIL import Image
    figures = {}
    for source in sorted((root / "article/figures/generated").glob("*.png")):
        regenerated = output / "figures/generated" / source.name
        with Image.open(source) as a, Image.open(regenerated) as b:
            figures[source.name] = {"archived_size": list(a.size), "regenerated_size": list(b.size),
                                    "pixel_identical": a.convert("RGBA").tobytes() == b.convert("RGBA").tobytes(),
                                    "regenerated_exists": regenerated.is_file()}
    report = {"passed": not differences and all(csv_checks.values()), "network_disabled_by_builder": True,
              "new_model_calls": 0, "manifest_files_verified": len(manifest["files"]),
              "evidence_comparison": {"float_tolerance_relative": 1e-12, "float_tolerance_absolute": 1e-14,
                                      "differences": differences}, "table_byte_checks": csv_checks, "figures": figures,
              "input_profile": "archived profile retained; benchmark/tokenizer caches are not bundled",
              "environment": {"python": sys.version.split()[0], "packages": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "matplotlib", "Pillow"]}}}
    (output / "verification_report.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
'''


def main() -> None:
    PAYLOAD.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    article_paths = git_names(ROOT, ARTICLE_REV)
    research_paths = git_names(RESEARCH, RESEARCH_REV)
    for name in article_paths:
        if name.startswith("reproducibility/results/20260726_flash_lite/") or (name.startswith("figures/") and (name.endswith(".png") or name.endswith("_en.tex"))):
            recover(ROOT, ARTICLE_REV, name, "article/" + name, clean_text if name.endswith((".md", ".tex")) else None)
    for name in research_paths:
        if name.startswith(("src/", "tests/", "docs/", "results/")) and not name.endswith(".gitkeep"):
            recover(RESEARCH, RESEARCH_REV, name, "research/" + name, clean_text if name.endswith((".py", ".md", ".txt")) else None)
    recover(RESEARCH, RESEARCH_REV, "config.yaml", "research/config.yaml", clean_text)
    recover(RESEARCH, RESEARCH_REV, "pyproject.toml", "research/pyproject.toml", clean_text)
    recover(ROOT, ARTICLE_REV, "reproducibility/inot_flash_lite_real.yaml", "article/reproducibility/inot_flash_lite_real.yaml", clean_text)
    recover(ROOT, ARTICLE_REV, "reproducibility/build_article_evidence.py", "article/reproducibility/build_article_evidence.py", adapt_builder)
    original_snapshot = json.loads(git_blob(ROOT, ARTICLE_REV, "reproducibility/evidence_snapshot.json"))
    snapshot = json.loads(json.dumps(original_snapshot))
    snapshot.pop("research_repository")
    snapshot.pop("research_commit")
    input_provenance = {}
    for key, values in snapshot["input_files"].items():
        old_path = values["path"]
        if "hybrid_inot_research" in old_path:
            relative = "research/" + old_path.split("hybrid_inot_research\\", 1)[1].replace("\\", "/")
        else:
            relative = "article/" + old_path.replace("\\", "/")
        raw = (PAYLOAD / relative).read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        crlf_hash = digest(lf.replace(b"\n", b"\r\n"))
        recorded = values["sha256"]
        relation = "byte_identical" if digest(raw) == recorded else "CRLF_to_LF_only" if crlf_hash == recorded else "MISMATCH"
        if relation == "MISMATCH":
            raise RuntimeError("Historical evidence input mismatch: " + key)
        input_provenance[key] = {"recorded_path": old_path, "recorded_sha256": recorded,
                                 "packaged_path": relative, "git_blob_sha256": digest(raw),
                                 "reconstructed_crlf_sha256": crlf_hash, "relation": relation}
        snapshot["input_files"][key] = {"path": relative, "sha256": digest(raw)}
    write_json(PAYLOAD / "article/reproducibility/evidence_snapshot.json", snapshot)
    RECORDS.append({"repository": str(ROOT), "revision": ARTICLE_REV,
                    "source_path": "reproducibility/evidence_snapshot.json", "packaged_path": "article/reproducibility/evidence_snapshot.json",
                    "git_blob_sha256": digest(git_blob(ROOT, ARTICLE_REV, "reproducibility/evidence_snapshot.json")),
                    "packaged_sha256": digest((PAYLOAD / "article/reproducibility/evidence_snapshot.json").read_bytes()),
                    "bytes_changed": True, "adaptation": "remove identifying provenance and rewrite only paths/input hashes; numeric content preserved"})
    (PAYLOAD / "scripts").mkdir(exist_ok=True)
    (PAYLOAD / "scripts/export_tables.py").write_text(EXPORT, encoding="utf-8", newline="\n")
    (PAYLOAD / "verify_offline.py").write_text(VERIFY, encoding="utf-8", newline="\n")
    readme = '''# Anonymous July 2026 replication package

This package contains the code, configurations, saved metrics and usage records underpinning the July 2026 manuscript. It is an evidence-replay package: its default verification makes no model calls and disables network connections in the analysis builder.

## Contents

- `research/src/`, `research/config.yaml`, `research/pyproject.toml`: the frozen experimental harness and declared dependency constraints.
- `research/results/`: retained Pro E2/E3 and controlled Pro/Flash-Lite E6 records and original summaries.
- `article/reproducibility/results/20260726_flash_lite/`: retained Flash-Lite E3 and small-model profitability E4 records.
- `article/reproducibility/evidence_snapshot.json`: anonymized archived July aggregate snapshot and nine packaged-input checksums.
- `article/figures/`: archived original article diagrams and all six localized quantitative figures.
- `tables/`: machine-readable exports of the empirical table values and paired statistics; complete E2 aggregate objects are retained separately.
- `MANIFEST.json`: checksums of every review payload file except the manifest itself.

## Offline verification

Use an existing Python 3.10+ environment with NumPy, SciPy, Matplotlib and Pillow. The exact versions used to validate this package are in `ENVIRONMENT.json`; `requirements-offline-verified.txt` pins that validation environment. Package installation is a separate setup step and is not performed by the verification command.

From this directory:

```text
python verify_offline.py --output-dir reproduced
```

This checks every packaged checksum, reruns the archived statistical formulas and figure generation, compares all evidence fields with the preserved snapshot, and exports the empirical tables. It reports numerical comparisons with tight floating-point tolerances. Figure file/pixel identity is reported separately because fonts and renderer versions can differ; regenerated plots use the same archived numerical arrays. Output files are placed only in the chosen output directory.

The evidence builder has narrow adaptations: repository-history validation is replaced by packaged-file checksum validation; identifying source metadata is omitted; file paths become relative; the already archived HumanEval context profile is retained. The statistical formulas and original figure functions are unchanged. `scripts/export_tables.py` only exports the resulting data.

## Scope and limitations

The saved runs contain task identifiers, metrics, role usage, costs and latencies, but not full generated solutions. This package cannot retrospectively reconstruct or independently regrade those missing responses. HumanEval benchmark data and tokenizer caches are not bundled, so the archived context-input profile is preserved, not newly reconstructed during offline verification. The original task/context loader is included for inspection.

The Pro E3 pilot has five tasks per context; Flash-Lite E3 has twenty tasks per context with one seed (42). Controlled E6 covers ten base cases from three task families and has ceiling pass@1. The original approximate SWE-bench Lite check is not the official repository/container harness. The E5 figure is an API-cost extrapolation from E3, not a new measured E5 run or full TCO. Incomplete seed-123 E3 and separate E5 attempts were excluded. API model names are aliases rather than immutable weight snapshots; no new API evaluation was performed for this package.

## Source and data integrity

All research and article inputs come from the selected historical July sources. Two article JSON inputs were stored with LF line endings while the archived evidence recorded their original CRLF checksums; their parsed numerical records are unchanged. The review manifest uses packaged-byte checksums. Identifying provenance is deliberately outside this review payload. No credentials, account identifiers, personal repository links or author commit identifiers are included.
'''
    (PAYLOAD / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    (PAYLOAD / "ADAPTATIONS.md").write_text(
        "# Packaging adaptations\n\nAuthor metadata, personal source links and author revision identifiers are removed. Comments carrying author names are anonymized. Numeric JSON inputs are copied unchanged from their stored historical bytes. The preserved aggregate snapshot changes only identifying provenance, paths and checksums required by LF packaging. The offline builder validates packaged hashes and retains the archived context profile without downloading benchmark data. Computation formulas and plotted numerical series are preserved.\n",
        encoding="utf-8", newline="\n")
    write_json(PROVENANCE / "origin_manifest_PRIVATE.json", {"article_revision": ARTICLE_REV,
        "research_revision": RESEARCH_REV, "files": RECORDS, "nine_evidence_inputs": input_provenance,
        "notice": "PRIVATE: not included in the anonymous review archive"})
    write_json(PROVENANCE / "original_evidence_snapshot_PRIVATE.json", original_snapshot)
    subprocess.run([sys.executable, str(PAYLOAD / "scripts/export_tables.py")], check=True)
    # Keep declared historical requirements distinct from exact current replay versions.
    import importlib.metadata as metadata
    versions = {name: metadata.version(name) for name in ["numpy", "scipy", "matplotlib", "Pillow"]}
    write_json(PAYLOAD / "ENVIRONMENT.json", {"python": sys.version.split()[0], "offline_validation_packages": versions,
        "original_generation_environment": "not fully locked in the historical source; declared constraints are preserved in research/pyproject.toml",
        "dependencies_for_offline_replay": list(versions)})
    (PAYLOAD / "requirements-offline-verified.txt").write_text("\n".join(f"{name}=={version}" for name, version in versions.items()) + "\n", encoding="utf-8")
    manifest = {"format": "anonymous-july-2026-review-payload-v1", "evidence_date": "2026-07-26",
                "files": [{"path": str(p.relative_to(PAYLOAD)).replace("\\", "/"), "sha256": digest(p.read_bytes()), "size": p.stat().st_size}
                          for p in sorted(PAYLOAD.rglob("*")) if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts]}
    write_json(PAYLOAD / "MANIFEST.json", manifest)
    findings = []
    for path in PAYLOAD.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(PAYLOAD).as_posix()
        if ".git" in path.parts or "__pycache__" in path.parts:
            findings.append({"path": relative, "reason": "unwanted metadata"})
        if path.suffix.lower() in {".py", ".json", ".md", ".toml", ".yaml", ".txt", ".tex"}:
            text = path.read_text(encoding="utf-8")
            for pattern in PRIVATE_PATTERNS:
                if re.search(pattern, text, flags=re.I):
                    findings.append({"path": relative, "pattern": pattern})
    write_json(BASE / "validation/replication_anonymity_failures.json", findings)
    if findings:
        raise RuntimeError("Review payload anonymity scan found identifying text")
    archive = REPLICATION / "hybrid-inot-july-2026-anonymous.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in sorted(PAYLOAD.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            info = zipfile.ZipInfo("hybrid-inot-july-2026/" + path.relative_to(PAYLOAD).as_posix(), date_time=(2026, 7, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, path.read_bytes())
    report = {"archive": str(archive), "archive_sha256": digest(archive.read_bytes()),
              "archive_bytes": archive.stat().st_size, "payload_files": len(manifest["files"]) + 1,
              "anonymity_scan_passed": True, "input_relations": {k: v["relation"] for k, v in input_provenance.items()},
              "numeric_inputs_preserved": True, "new_model_calls": 0, "provenance_is_outside_zip": True}
    write_json(BASE / "validation/replication_build_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
