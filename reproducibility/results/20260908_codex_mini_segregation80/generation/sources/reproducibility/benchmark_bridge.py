#!/usr/bin/env python3
"""Benchmark bridge CLI for reproducible prepare/export workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

SEED = 20260908
FENCE_RE = re.compile(r"```([a-zA-Z0-9_+-]*)[ \t]*\n(.*?)\n```", re.DOTALL)

ALLOWED_LANGUAGES = {
    "bigcodebench": {"python", "py"},
    "swebench": {"diff", "patch"},
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{no}: invalid JSONL object") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{no}: each record must be an object")
            rows.append(item)
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def _shuffle_ids(ids: List[str]) -> List[str]:
    ordered = sorted(ids)
    rng = random.Random(SEED)
    rng.shuffle(ordered)
    return ordered


def _split_task_ids(ids: List[str], dev_size: int) -> Tuple[List[str], List[str]]:
    shuffled = _shuffle_ids(ids)
    return shuffled[:dev_size], shuffled


def _prepare_output_row(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": str(task["task_id"]),
        "prompt": str(task["instruct_prompt"]),
        "context": str(task["code_prompt"]),
        "benchmark": "bigcodebench",
        "metadata": {"source": "bigcodebench"},
    }


def prepare_dataset(dataset: Path, output_dir: Path, dev_size: int) -> Dict[str, Any]:
    rows = _read_jsonl(dataset)
    if not rows:
        raise ValueError("dataset is empty")
    if dev_size < 0 or dev_size > len(rows):
        raise ValueError("dev-size must be between zero and dataset size")

    required = {"task_id", "instruct_prompt", "code_prompt"}
    tasks: Dict[str, Dict[str, Any]] = {}
    for idx, row in enumerate(rows, start=1):
        missing = required - set(row)
        if missing:
            raise ValueError(f"{dataset}:{idx}: missing required fields {sorted(missing)}")
        if any(not isinstance(row[k], str) or (k != "code_prompt" and not row[k].strip()) for k in required):
            raise ValueError("Task fields must contain text, not null or coerced objects")
        task_id = str(row["task_id"])
        if task_id in tasks:
            raise ValueError(f"duplicate task_id: {task_id}")
        tasks[task_id] = row

    all_ids = list(tasks.keys())
    dev_ids, all_shuffled = _split_task_ids(all_ids, min(dev_size, len(all_ids)))
    output_rows = [_prepare_output_row(tasks[task_id]) for task_id in dev_ids]

    output_path = output_dir / "prepared.jsonl"
    confirm_ids = all_shuffled[len(dev_ids):]
    confirm_path = output_dir / "confirmatory.jsonl"
    manifest_path = output_dir / "prepare_manifest.json"
    _write_jsonl(output_path, output_rows)
    _write_jsonl(confirm_path, [_prepare_output_row(tasks[t]) for t in confirm_ids])

    manifest = {
        "source_path": str(dataset),
        "output_path": str(output_path),
        "seed": SEED,
        "source_sha256": _sha256_path(dataset),
        "output_sha256": _sha256_path(output_path),
        "dev_size": dev_size,
        "source_task_count": len(all_ids),
        "all_task_ids": all_shuffled,
        "dev_task_ids": dev_ids,
        "confirmatory_task_ids": confirm_ids,
        "confirmatory_path": str(confirm_path),
        "confirmatory_sha256": _sha256_path(confirm_path),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _parse_standardized_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    required = {"task_id", "arm", "seed", "model", "final_text"}
    standardized = []
    seen = set()
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"missing required result fields: {sorted(missing)}")
        key = tuple(row[k] for k in ("task_id", "model", "arm", "seed"))
        if key in seen:
            raise ValueError("Duplicate result cell")
        seen.add(key)
        if type(row["seed"]) is not int or any(not isinstance(row[k], str) for k in ("task_id", "model", "arm", "final_text")):
            raise ValueError("Invalid result field types")
        standardized.append(
            {
                "task_id": str(row["task_id"]),
                "arm": str(row["arm"]),
                "seed": int(row["seed"]),
                "model": str(row["model"]),
                "final_text": str(row["final_text"]),
            }
        )
    return standardized


def _extract_fenced_block(text: str, benchmark: str) -> Tuple[str, bool]:
    blocks = [body.strip() for lang, body in FENCE_RE.findall(text or "") if lang.strip().lower() in ALLOWED_LANGUAGES[benchmark]]
    if len(blocks) != 1:
        return "", False
    return blocks[0], True


def _safe_component(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._")
    return (cleaned or fallback)[:40]


def _group_filename(benchmark: str, model: str, arm: str, seed: int) -> str:
    digest = hashlib.sha256(f"{benchmark}|{model}|{arm}|{seed}".encode("utf-8")).hexdigest()[:12]
    return f"{benchmark}_{_safe_component(model, 'model')}_{_safe_component(arm, 'arm')}_{seed}_{digest}.jsonl"


def _to_official_row(benchmark: str, task_id: str, model: str, final_text: str) -> Dict[str, str]:
    if benchmark == "bigcodebench":
        return {"task_id": task_id, "solution": final_text}
    return {"instance_id": task_id, "model_name_or_path": model, "model_patch": final_text}


def export_results(results: Path, benchmark: str, output_dir: Path) -> Dict[str, Any]:
    if benchmark not in ALLOWED_LANGUAGES:
        raise ValueError(f"unsupported benchmark: {benchmark}")

    source_rows = _parse_standardized_rows(_read_jsonl(results))
    standardized_rows: List[Dict[str, Any]] = []
    grouped: Dict[Tuple[str, str, int], List[Dict[str, str]]] = {}
    logs: List[str] = []
    failed = 0

    for row in source_rows:
        extracted, ok = _extract_fenced_block(row["final_text"], benchmark)
        if not ok:
            failed += 1
            logs.append(f"extract_failed: task_id={row['task_id']} model={row['model']} arm={row['arm']} seed={row['seed']}")
            extracted = ""
        standardized_rows.append(
            {
                "task_id": row["task_id"],
                "arm": row["arm"],
                "seed": row["seed"],
                "model": row["model"],
                "final_text": extracted,
            }
        )
        official = _to_official_row(benchmark, row["task_id"], row["model"], extracted)
        key = (row["model"], row["arm"], row["seed"])
        grouped.setdefault(key, []).append(official)

    standardized_path = output_dir / "standardized_results.jsonl"
    _write_jsonl(standardized_path, standardized_rows)

    groups = []
    for model, arm, seed in sorted(grouped):
        rows = grouped[(model, arm, seed)]
        path = output_dir / _group_filename(benchmark, model, arm, seed)
        _write_jsonl(path, rows)
        groups.append(
            {
                "model": model,
                "arm": arm,
                "seed": seed,
                "path": str(path),
                "rows": len(rows),
                "sha256": _sha256_path(path),
            }
        )

    if benchmark == "bigcodebench":
        for g in groups:
            task_ids = [r["task_id"] for r in grouped[(g["model"], g["arm"], g["seed"])]]
            g["evaluation_argv"] = ["python", "-m", "bigcodebench.evaluate", "--execution", "local", "--split", "instruct", "--subset", "full", "--samples", g["path"], "--selective_evaluate", ",".join(task_ids), "--calibrated=False", "--pass_k", "1", "--parallel", "2"]
            print(
                "Suggested official command:",
                "argv saved in export_manifest.json for", g["path"],
            )
    else:
        for g in groups:
            g["run_id"] = "inot_" + g["sha256"][:20]
            g["evaluation_argv"] = ["python", "-m", "swebench.harness.run_evaluation", "--dataset_name", "princeton-nlp/SWE-bench_Verified", "--predictions_path", g["path"], "--max_workers", "2", "--run_id", g["run_id"]]
            print(
                "Suggested official command:",
                f"python -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Verified --predictions_path \"{g['path']}\" --max_workers 2 --run_id {g['run_id']}",
            )

    print("Requires an isolated official environment and independent validation of results.")

    manifest = {
        "benchmark": benchmark,
        "source_path": str(results),
        "source_sha256": _sha256_path(results),
        "standardized_path": str(standardized_path),
        "ambiguous_or_missing_extractions": failed,
        "total_rows": len(standardized_rows),
        "groups": groups,
        "logs": logs,
    }
    manifest_path = output_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("benchmark-bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Convert BigCodeBench raw JSONL into internal schema.")
    p_prepare.add_argument("--dataset", required=True, type=Path)
    p_prepare.add_argument("--output-dir", required=True, type=Path)
    p_prepare.add_argument("--dev-size", required=True, type=int)

    p_export = sub.add_parser("export", help="Export standardized predictions to official formats.")
    p_export.add_argument("--results", required=True, type=Path)
    p_export.add_argument("--benchmark", required=True, choices=tuple(ALLOWED_LANGUAGES))
    p_export.add_argument("--output-dir", required=True, type=Path)

    return parser


def _main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "prepare":
        manifest = prepare_dataset(args.dataset, args.output_dir, args.dev_size)
        print(json.dumps({k:v for k,v in manifest.items() if not k.endswith("task_ids")}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "export":
        manifest = export_results(args.results, args.benchmark, args.output_dir)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
