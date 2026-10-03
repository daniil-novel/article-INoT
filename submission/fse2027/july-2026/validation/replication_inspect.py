"""Owner-side archive and provenance validation; never placed in the review ZIP."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parents[1]
REPLICATION = BASE / "replication"
PAYLOAD = REPLICATION / "hybrid-inot-july-2026"
ARCHIVE = REPLICATION / "hybrid-inot-july-2026-anonymous.zip"
PROVENANCE = REPLICATION / "provenance"
PREFIX = "hybrid-inot-july-2026/"
FORBIDDEN = re.compile(r"daniil|privezentsev|daprivezentsev|GF62|JarvisSonoma|springer-article|010211ee5775185e8330ab6cde06e912c2adcb9e|173a16c3|(?<![A-Za-z])[A-Za-z]:[\\/](?!/)", re.I)


def main() -> None:
    original = json.loads((PROVENANCE / "original_evidence_snapshot_PRIVATE.json").read_text(encoding="utf-8"))
    anonymous = json.loads((PAYLOAD / "article/reproducibility/evidence_snapshot.json").read_text(encoding="utf-8"))
    scientific_keys = original.keys() - {"research_repository", "research_commit", "input_files"}
    scientific_exact = all(original[key] == anonymous[key] for key in scientific_keys)
    manifest = json.loads((PAYLOAD / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {PREFIX + entry["path"] for entry in manifest["files"]} | {PREFIX + "MANIFEST.json"}
    violations = []
    metadata = {}
    with zipfile.ZipFile(ARCHIVE) as zipped:
        names = zipped.namelist()
        if set(names) != expected or len(names) != len(expected):
            violations.append("ZIP entries do not match payload manifest")
        if any("provenance" in name or "PRIVATE" in name or ".git/" in name or "__pycache__" in name for name in names):
            violations.append("private or executable-cache metadata included")
        for info in zipped.infolist():
            raw = zipped.read(info.filename)
            relative = info.filename.removeprefix(PREFIX)
            if raw != (PAYLOAD / relative).read_bytes():
                violations.append(relative + ": ZIP bytes differ from extracted payload")
            if info.filename.endswith((".json", ".py", ".md", ".txt", ".tex", ".yaml", ".toml")):
                if FORBIDDEN.search(raw.decode("utf-8")):
                    violations.append(relative + ": identifying text")
            if info.filename.endswith(".png"):
                with Image.open(BytesIO(raw)) as picture:
                    textual_info = {key: value for key, value in picture.info.items() if isinstance(value, str)}
                    metadata[relative] = textual_info
                    if FORBIDDEN.search(json.dumps(textual_info)):
                        violations.append(relative + ": identifying image metadata")
        zip_test = zipped.testzip()
    report = {
        "passed": scientific_exact and not violations and zip_test is None,
        "scientific_snapshot_exactly_preserved": scientific_exact,
        "archived_scientific_fields_compared": sorted(scientific_keys),
        "zip_entry_count": len(expected), "zip_crc_integrity_passed": zip_test is None,
        "zip_equals_extracted_payload": not any("ZIP bytes differ" in item for item in violations),
        "private_provenance_excluded": not any("metadata included" in item for item in violations),
        "text_and_png_metadata_anonymity_passed": not any("identifying" in item for item in violations),
        "violations": violations, "png_text_metadata": metadata,
        "zip_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
    }
    (BASE / "validation/replication_archive_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "png_text_metadata"}, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
