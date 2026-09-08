"""Hash only mounted scale inputs and the pinned upstream source tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    files = [
        path for path in root.rglob("*")
        if path.is_file() and not ({".git", "__pycache__"} & set(path.relative_to(root).parts))
    ]
    files.sort(key=lambda path: path.relative_to(root).as_posix().encode("utf-8"))
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(path)))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--dockerfile", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({
        "vendor_tree_sha256": tree_sha256(args.vendor),
        "vendor_tree_hash_algorithm": "SHA256(sorted UTF-8 relative-path bytes + NUL + file-SHA256 bytes + LF; excludes .git and __pycache__)",
        "dataset_sha256": sha256(args.dataset),
        "prepared_split_sha256": sha256(args.prepared),
        "requirements_sha256": sha256(args.requirements),
        "dockerfile_sha256": sha256(args.dockerfile),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
