"""Copy allowlisted submission deliverables without deleting unrelated local files."""
from __future__ import annotations
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload"
FILES = {
    "FSE2027-paper.pdf": ROOT / "paper/main.pdf",
    "FSE2027-supplement.zip": ROOT / "artifact/fse2027-anonymous-analysis-artifact.zip",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    for source in FILES.values():
        if not source.is_file():
            raise SystemExit(f"missing deliverable: {source}")
    UPLOAD.mkdir(exist_ok=True)
    for name, source in FILES.items():
        shutil.copyfile(source, UPLOAD / name)
    lines = [f"{sha256(UPLOAD / name)}  {name}" for name in sorted(FILES)]
    (UPLOAD / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    (UPLOAD / "UPLOAD_README.txt").write_text(
        "FSE 2027 Research Track upload set\n"
        "Upload FSE2027-paper.pdf as the anonymous paper. The live HotCRP form has no separate supplement field.\n"
        "The replication package is available through the anonymous link in the PDF's Data Availability section:\n"
        "https://anonymous.4open.science/r/role-calls-replication-2026/\n"
        "FSE2027-supplement.zip is available there for download. SHA256SUMS.txt is a local integrity record.\n"
        "These are the current local revision files; their presence does not confirm a live HotCRP replacement.\n",
        encoding="ascii",
    )
    print("\n".join(lines))

if __name__ == "__main__":
    main()
