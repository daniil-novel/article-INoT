"""Prepare complete-solution JSONL inputs for the upstream CLI, without execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TASK_IDS = [
    "BigCodeBench/325", "BigCodeBench/322", "BigCodeBench/1036",
    "BigCodeBench/1005", "BigCodeBench/361", "BigCodeBench/1087",
    "BigCodeBench/45", "BigCodeBench/309",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("gold", "incorrect"), required=True)
    args = parser.parse_args()
    rows = {json.loads(line)["task_id"]: json.loads(line)
            for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()}
    missing = [task_id for task_id in TASK_IDS if task_id not in rows]
    if missing:
        raise SystemExit(f"dataset missing selected IDs: {missing}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for task_id in TASK_IDS:
            problem = rows[task_id]
            solution = problem["complete_prompt"] + problem["canonical_solution"]
            if args.kind == "incorrect":
                solution += "\n\n# Deliberately incorrect pilot control.\ndef task_func(*args, **kwargs):\n    return None\n"
            handle.write(json.dumps({"task_id": task_id, "solution": solution},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
