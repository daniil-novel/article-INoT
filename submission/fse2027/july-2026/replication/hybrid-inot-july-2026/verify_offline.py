from __future__ import annotations
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
    (output / "verification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
