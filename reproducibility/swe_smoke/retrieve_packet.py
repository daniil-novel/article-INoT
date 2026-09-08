"""Deterministic, non-LLM retrieval packet builder for the SWE smoke task.

This script reads only the explicitly permitted metadata columns from the
SWE-bench parquet. It never reads patches/tests, executes repository code, or
truncates a source file. Retrieval uses a documented BM25 score over complete
tracked Python files after path-component exclusions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import pandas as pd


TASK_ID = "pvlib__pvlib-python-1606"
METADATA_COLUMNS = [
    "instance_id",
    "repo",
    "base_commit",
    "problem_statement",
    "version",
]
MAX_PACKET_BYTES = 24_000
BM25_K1 = 1.5
BM25_B = 0.75
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
EXCLUDED_COMPONENTS = {"tests", "test", "examples", "example", "docs", "doc", "benchmarks", "benchmark"}
EXCLUDED_FILENAME_MARKERS = ("example",)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def tokenize(text: str) -> list[str]:
    """Lowercase ASCII identifier tokens; punctuation and string whitespace drop out."""
    return [token.lower() for token in TOKEN_RE.findall(text)]


def bm25_score(query_tokens: list[str], document_tokens: list[str], document_frequency: dict[str, int], document_count: int, average_length: float) -> float:
    frequencies: dict[str, int] = {}
    for token in document_tokens:
        frequencies[token] = frequencies.get(token, 0) + 1
    length = len(document_tokens)
    norm = BM25_K1 * (1.0 - BM25_B + BM25_B * length / average_length) if average_length else BM25_K1
    score = 0.0
    for token in query_tokens:
        tf = frequencies.get(token, 0)
        if not tf:
            continue
        df = document_frequency.get(token, 0)
        idf = math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
        score += idf * (tf * (BM25_K1 + 1.0)) / (tf + norm)
    return score


def load_task(parquet: Path) -> dict:
    frame = pd.read_parquet(parquet, columns=METADATA_COLUMNS)
    matches = frame[frame["instance_id"] == TASK_ID]
    if len(matches) != 1:
        raise ValueError(f"Expected one metadata row for {TASK_ID}, found {len(matches)}")
    row = matches.iloc[0]
    return {column: (row[column].item() if hasattr(row[column], "item") else row[column]) for column in METADATA_COLUMNS}


def tracked_python_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--stage", "--", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        fields = line.split("\t", 1)
        if len(fields) != 2:
            continue
        path = Path(fields[1])
        if any(component.casefold() in EXCLUDED_COMPONENTS for component in path.parts[:-1]):
            continue
        if any(marker in path.name.casefold() for marker in EXCLUDED_FILENAME_MARKERS):
            continue
        paths.append(repo_root / path)
    return sorted(paths, key=lambda path: path.relative_to(repo_root).as_posix())


def git_source_commit(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_packet(parquet: Path, repo_root: Path, output: Path) -> None:
    task = load_task(parquet)
    source_commit = git_source_commit(repo_root)
    if source_commit != task["base_commit"]:
        raise ValueError(f"Repository HEAD {source_commit} differs from task base_commit {task['base_commit']}")

    files = tracked_python_files(repo_root)
    documents = []
    for path in files:
        data = path.read_bytes()
        text = data.decode("utf-8")
        documents.append({
            "path": path.relative_to(repo_root).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "tokens": tokenize(text),
        })
    query_tokens = tokenize(task["problem_statement"])
    document_frequency: dict[str, int] = {}
    for document in documents:
        for token in set(document["tokens"]):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    average_length = sum(len(document["tokens"]) for document in documents) / len(documents) if documents else 0.0
    for document in documents:
        document["bm25"] = bm25_score(query_tokens, document["tokens"], document_frequency, len(documents), average_length)
    documents.sort(key=lambda document: (-document["bm25"], document["path"]))

    selected = []
    limitations = []
    used = 0
    for rank, document in enumerate(documents, start=1):
        document["rank"] = rank
        if document["bytes"] <= MAX_PACKET_BYTES - used:
            selected.append(document)
            used += document["bytes"]
            document["selected"] = True
            document["selection_reason"] = "ranked greedy inclusion within byte budget"
        else:
            document["selected"] = False
            document["selection_reason"] = "whole file does not fit in remaining byte budget"
            limitations.append({
                "path": document["path"],
                "rank": rank,
                "bytes": document["bytes"],
                "remaining_bytes": MAX_PACKET_BYTES - used,
                "reason": "relevant source file could not fit as a complete file; no truncation or budget change",
            })

    output.mkdir(parents=True, exist_ok=False)
    packet_dir = output / "files"
    packet_dir.mkdir()
    for document in selected:
        destination = packet_dir / document["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((repo_root / document["path"]).read_bytes())

    task_record = {
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "base_commit": task["base_commit"],
        "version": task["version"],
        "problem_statement": task["problem_statement"],
        "retrieval": {
            "source_commit": source_commit,
            "max_packet_bytes": MAX_PACKET_BYTES,
            "selected_bytes": used,
            "selected_files": [
                {"path": document["path"], "rank": document["rank"], "bytes": document["bytes"], "sha256": document["sha256"]}
                for document in selected
            ],
            "retriever": "reproducibility/swe_smoke/retrieve_packet.py",
        },
    }
    (output / "task.jsonl").write_text(json.dumps(task_record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output / "ranking.json").write_text(json.dumps(documents, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "limitations.json").write_text(json.dumps(limitations, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "swe-smoke-retrieval-v1",
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "source_commit": source_commit,
        "base_commit": task["base_commit"],
        "parquet": str(parquet.as_posix()),
        "metadata_columns_read": METADATA_COLUMNS,
        "forbidden_columns_read": ["hints_text", "patch", "test_patch", "gold_patch", "test"],
        "tokenizer": "lowercase ASCII identifier regex [A-Za-z_][A-Za-z0-9_]*",
        "bm25": {"k1": BM25_K1, "b": BM25_B, "idf": "log(1 + (N-df+0.5)/(df+0.5))"},
        "excluded_path_components": sorted(EXCLUDED_COMPONENTS),
        "excluded_filename_markers": list(EXCLUDED_FILENAME_MARKERS),
        "max_packet_bytes": MAX_PACKET_BYTES,
        "selected_bytes": used,
        "selected_files": [document["path"] for document in selected],
        "selected_file_records": [
            {"path": document["path"], "rank": document["rank"], "bytes": document["bytes"], "sha256": document["sha256"]}
            for document in selected
        ],
        "ranking_sha256": sha256_file(output / "ranking.json"),
        "limitations_sha256": sha256_file(output / "limitations.json"),
        "retriever_sha256": sha256_file(Path(__file__)),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, default=Path("reproducibility/data/swebench-lite/dev-00000-of-00001.parquet"))
    parser.add_argument("--repo", type=Path, default=Path("reproducibility/vendor/pvlib-smoke"))
    parser.add_argument("--output", type=Path, default=Path("reproducibility/runs/swe-smoke-dev1/retrieval"))
    args = parser.parse_args()
    build_packet(args.parquet, args.repo, args.output)


if __name__ == "__main__":
    main()
