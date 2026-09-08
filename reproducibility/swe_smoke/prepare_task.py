"""Prepare a deterministic SWE-bench runner task from a frozen retrieval packet.

The input packet is treated as immutable evidence. This module verifies the
checkout, source bytes, packet hashes, and selected-file hashes before writing
the exact ``task_id/prompt/context/benchmark/metadata`` schema expected by the
unchanged runner. It never reads patches, tests, hints, or reference files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


TASK_ID = "pvlib__pvlib-python-1606"
FORBIDDEN_FIELDS = ("hints_text", "patch", "test_patch", "gold_patch", "test", "reference")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(repo_root: Path, args: list[str]) -> bytes:
    return subprocess.run(["git", "-C", str(repo_root), *args], check=True, capture_output=True).stdout


def verify_checkout(repo_root: Path, base_commit: str, selected: list[dict], packet_files: Path, output: Path) -> dict:
    status = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain"], check=True, capture_output=True, text=True).stdout
    if status:
        raise ValueError(f"Repository checkout is not clean: {status!r}")
    actual_commit = git_output(repo_root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    if actual_commit != base_commit:
        raise ValueError(f"Repository HEAD {actual_commit} differs from base_commit {base_commit}")
    records = []
    for record in selected:
        path = record["path"]
        packet_bytes = (packet_files / path).read_bytes()
        checkout_bytes = (repo_root / path).read_bytes()
        git_bytes = git_output(repo_root, ["show", f"{base_commit}:{path}"])
        if sha256_bytes(packet_bytes) != record["sha256"]:
            raise ValueError(f"Tampered retrieval file hash: {path}")
        if packet_bytes != git_bytes or checkout_bytes != git_bytes:
            line_ending_note = "line-ending or checkout-byte mismatch" if packet_bytes.replace(b"\r\n", b"\n") == git_bytes.replace(b"\r\n", b"\n") else "content-byte mismatch"
            raise ValueError(f"Source byte verification failed for {path}: {line_ending_note}")
        records.append({"path": path, "rank": record["rank"], "bytes": len(packet_bytes), "sha256": sha256_bytes(packet_bytes), "git_show_match": True})
    result = {"repo_root": str(repo_root), "base_commit": base_commit, "tracked_status_clean": True, "files": records}
    output.mkdir(parents=True, exist_ok=True)
    (output / "checkout_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def prepare(packet: Path, repo_root: Path, output: Path) -> None:
    task_lines = [line for line in (packet / "task.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(task_lines) != 1:
        raise ValueError("Retrieval packet must contain exactly one task record")
    task = json.loads(task_lines[0])
    required = {"instance_id", "repo", "base_commit", "problem_statement", "version", "retrieval"}
    if set(task) != required or task["instance_id"] != TASK_ID:
        raise ValueError("Unexpected retrieval task schema or task ID")
    if any(field in task or field in task.get("retrieval", {}) for field in FORBIDDEN_FIELDS):
        raise ValueError("Forbidden test/reference field present in retrieval metadata")
    original_manifest = read_json(packet / "manifest.json")
    if original_manifest["instance_id"] != TASK_ID or original_manifest["source_commit"] != task["base_commit"]:
        raise ValueError("Retrieval manifest/task commit mismatch")
    for name in ("ranking", "limitations"):
        if sha256_file(packet / (name + ".json")) != original_manifest[name + "_sha256"]:
            raise ValueError(f"Frozen retrieval {name} changed")
    ranking = read_json(packet / "ranking.json")
    selected = [record for record in ranking if record.get("selected")]
    if selected != sorted(selected, key=lambda record: record["rank"]):
        raise ValueError("Selected ranking order is not stable")
    selected_paths = [record["path"] for record in selected]
    if selected_paths != [record["path"] for record in original_manifest["selected_file_records"]]:
        raise ValueError("Manifest and ranking selected-file records differ")
    if sum(record["bytes"] for record in selected) != original_manifest["selected_bytes"]:
        raise ValueError("Selected byte total does not match retrieval manifest")

    output.mkdir(parents=True, exist_ok=False)
    verification = verify_checkout(repo_root, task["base_commit"], selected, packet / "files", output)
    context_parts = []
    for record in selected:
        path = record["path"]
        content = (packet / "files" / path).read_bytes().decode("utf-8")
        context_parts.append(f"===== BEGIN RETRIEVED FILE: {path} =====\n{content}\n===== END RETRIEVED FILE: {path} =====")
    context = "\n\n".join(context_parts)
    prompt = (
        f"Repository: {task['repo']}\n"
        f"Base commit: {task['base_commit']}\n\n"
        "Problem statement (verbatim):\n"
        f"{task['problem_statement']}\n\n"
        "Using only the supplied task statement and retrieved context, implement the requested repository fix. "
        "Follow the assigned stage instructions. When a final solution is requested, return the complete applicable unified diff "
        "after the literal FINAL marker in exactly one fenced diff block."
    )
    metadata = {
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "base_commit": task["base_commit"],
        "version": task["version"],
        "problem_statement_sha256": sha256_bytes(task["problem_statement"].encode("utf-8")),
        "retrieval_manifest_sha256": sha256_file(packet / "manifest.json"),
        "ranking_sha256": sha256_file(packet / "ranking.json"),
        "limitations_sha256": sha256_file(packet / "limitations.json"),
        "retriever_sha256": original_manifest["retriever_sha256"],
        "selected_file_records": verification["files"],
    }
    runner_task = {"task_id": task["instance_id"], "prompt": prompt, "context": context, "benchmark": "swebench", "metadata": metadata}
    (output / "tasks.jsonl").write_text(json.dumps(runner_task, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    corrected_manifest = dict(original_manifest)
    corrected_manifest.pop("forbidden_columns_read", None)
    corrected_manifest["forbidden_columns_not_read"] = list(FORBIDDEN_FIELDS)
    corrected_manifest["prepared_task_sha256"] = sha256_bytes(canonical(runner_task))
    corrected_manifest["context_sha256"] = sha256_bytes(context.encode("utf-8"))
    corrected_manifest["checkout_verification_sha256"] = sha256_file(output / "checkout_verification.json")
    corrected_manifest["preparer_sha256"] = sha256_file(Path(__file__))
    (output / "manifest.json").write_text(json.dumps(corrected_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "context.txt").write_bytes(context.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=Path("reproducibility/runs/swe-smoke-dev1/retrieval"))
    parser.add_argument("--repo", type=Path, default=Path("reproducibility/vendor/pvlib-smoke"))
    parser.add_argument("--output", type=Path, default=Path("reproducibility/runs/swe-smoke-dev1/retrieval/runner"))
    args = parser.parse_args()
    prepare(args.packet, args.repo, args.output)


if __name__ == "__main__":
    main()
