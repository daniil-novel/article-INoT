"""Prepare gold and deliberately incorrect samples for the frozen dev-40 IDs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    selected = [row["task_id"] for row in read_rows(args.prepared)[:40]]
    if len(selected) != 40 or len(set(selected)) != 40:
        raise SystemExit("prepared split does not contain exactly 40 unique development IDs")

    wanted = set(selected)
    official = {}
    with args.official.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            task_id = row.get("task_id")
            if task_id in wanted:
                official[task_id] = row
    if set(official) != wanted:
        raise SystemExit(f"official dataset missing development IDs: {sorted(wanted - set(official))}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    official_output = args.output_dir / "official_dev40.jsonl"
    with official_output.open("w", encoding="utf-8", newline="\n") as handle:
        for task_id in selected:
            handle.write(json.dumps(official[task_id], ensure_ascii=False,
                                    separators=(",", ":")) + "\n")
    for kind in ("gold", "incorrect"):
        output = args.output_dir / f"{kind}.jsonl"
        with output.open("w", encoding="utf-8", newline="\n") as handle:
            for task_id in selected:
                problem = official[task_id]
                solution = problem["complete_prompt"] + problem["canonical_solution"]
                if kind == "incorrect":
                    solution += (
                        "\n\n# Deliberately incorrect scale control.\n"
                        "def task_func(*args, **kwargs):\n    return None\n"
                    )
                handle.write(json.dumps({"task_id": task_id, "solution": solution},
                                        ensure_ascii=False, separators=(",", ":")) + "\n")
        print(json.dumps({
            "kind": kind,
            "rows": 40,
            "task_ids_sha256": hashlib.sha256("\n".join(selected).encode()).hexdigest(),
            "samples_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "path": str(output),
        }))


if __name__ == "__main__":
    main()
