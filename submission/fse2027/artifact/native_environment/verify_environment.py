"""Fail closed if frozen Python versions or retained NLTK bytes differ."""
from __future__ import annotations
import argparse, hashlib, re
from importlib import metadata
from pathlib import Path

def verify(requirements: Path, resources: Path) -> None:
    failures=[]
    packages=0
    for line in requirements.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match=re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
        if not match:
            raise SystemExit(f"Unsupported frozen requirement: {line}")
        name, expected=match.groups()
        try:
            actual=metadata.version(name)
        except metadata.PackageNotFoundError:
            actual="MISSING"
        if actual != expected:
            failures.append(f"{name}: expected {expected}, observed {actual}")
        packages+=1
    files=0
    for line in resources.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative=line.split(None,1)
        path=Path(relative.strip())
        if not path.is_absolute() or not str(path).startswith("/opt/nltk_data/"):
            raise SystemExit(f"Unexpected retained resource path: {relative}")
        actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
        if actual != expected:
            failures.append(f"{path}: expected {expected}, observed {actual}")
        files+=1
    if failures:
        raise SystemExit("Environment differs from retained evidence:\n"+"\n".join(failures))
    print(f"Verified {packages} pinned Python package versions and {files} NLTK resource hashes.")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    args=parser.parse_args()
    verify(args.requirements,args.resources)
