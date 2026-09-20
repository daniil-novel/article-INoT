"""Create the allowlisted FSE upload directory without LaTeX build metadata."""
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
    UPLOAD.mkdir(exist_ok=True)
    for old in UPLOAD.iterdir():
        if old.is_file():
            old.unlink()
    for name, source in FILES.items():
        if not source.is_file():
            raise SystemExit(f"missing deliverable: {source}")
        shutil.copyfile(source, UPLOAD / name)
    lines = [f"{sha256(UPLOAD / name)}  {name}" for name in sorted(FILES)]
    (UPLOAD / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    (UPLOAD / "UPLOAD_README.txt").write_text(
        "FSE 2027 Research Track upload set\n"
        "Upload FSE2027-paper.pdf as the anonymous paper and "
        "FSE2027-supplement.zip as supplementary material.\n"
        "Only these two files belong in HotCRP; SHA256SUMS.txt is a local integrity record.\n",
        encoding="ascii",
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
