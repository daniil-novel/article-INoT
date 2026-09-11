"""Supplementary, offline audit of Luna turn-usage pricing scope.

This module reads only retained ``events.jsonl`` files.  It does not inspect
model text, call the CLI, or replace the frozen registered valuation.  The
reported valuation is the existing standard-scope counterfactual; a complete
claim is withheld when the retained evidence is incomplete or contains an
observed long-context/cache-write case.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


INPUT_RATE = 0.20
CACHED_INPUT_RATE = 0.02
OUTPUT_RATE = 1.20
LONG_CONTEXT_INPUT_TOKENS = 272_000


def _base_valuation(input_tokens: int, cached_input_tokens: int, output_tokens: int) -> float:
    return ((input_tokens - cached_input_tokens) * INPUT_RATE
            + cached_input_tokens * CACHED_INPUT_RATE
            + output_tokens * OUTPUT_RATE) / 1_000_000


def _usage_error(usage: Any) -> list[str]:
    if not isinstance(usage, dict):
        return ["usage_not_object"]
    errors = []
    required = ("input_tokens", "cached_input_tokens", "output_tokens")
    for name in required:
        value = usage.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{name}_not_nonnegative_integer")
        elif value < 0:
            errors.append(f"{name}_negative")
    if not errors:
        if usage["cached_input_tokens"] > usage["input_tokens"]:
            errors.append("cached_input_exceeds_input")
    return errors


def _cache_write(usage: Any) -> tuple[str, int | None, list[str]]:
    if not isinstance(usage, dict) or "cache_write_input_tokens" not in usage:
        return "not_reported", None, []
    value = usage["cache_write_input_tokens"]
    if isinstance(value, bool) or not isinstance(value, int):
        return "reported_invalid", None, ["cache_write_not_nonnegative_integer"]
    if value < 0:
        return "reported_invalid", None, ["cache_write_negative"]
    return ("reported_zero" if value == 0 else "reported_nonzero"), value, []


def _turn_record(path: Path, generation: Path) -> dict[str, Any]:
    event_path = path / "events.jsonl"
    raw = event_path.read_bytes() if event_path.is_file() else b""
    record: dict[str, Any] = {
        "turn_id": path.relative_to(generation).as_posix(),
        "events_sha256": hashlib.sha256(raw).hexdigest() if event_path.is_file() else None,
        "events_file_present": event_path.is_file(),
        "completion_count": 0,
        "usage_status": "unknown",
        "input_tokens": None,
        "cached_input_tokens": None,
        "output_tokens": None,
        "cache_write_state": "not_reported",
        "cache_write_input_tokens": None,
        "base_valuation_usd": None,
        "long_context_gt_272000": False,
        "invalid_reasons": [],
    }
    if not event_path.is_file():
        record["invalid_reasons"].append("events_file_missing")
        return record
    events: list[Any] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                record["invalid_reasons"].append(f"nonobject_event_line_{line_number}")
            else:
                events.append(event)
        except (json.JSONDecodeError, UnicodeDecodeError):
            record["invalid_reasons"].append(f"invalid_json_line_{line_number}")
    completions = [event for event in events
                   if isinstance(event, dict) and event.get("type") == "turn.completed"]
    record["completion_count"] = len(completions)
    if len(completions) == 0:
        if not record["invalid_reasons"]:
            record["invalid_reasons"].append("no_turn_completed")
            return record
        record["usage_status"] = "rejected"
        return record
    if len(completions) != 1:
        record["invalid_reasons"].append("duplicate_turn_completed")
        record["usage_status"] = "rejected"
        return record

    usage = completions[0].get("usage")
    errors = _usage_error(usage)
    cache_state, cache_value, cache_errors = _cache_write(usage)
    record["cache_write_state"] = cache_state
    record["cache_write_input_tokens"] = cache_value
    record["invalid_reasons"].extend(errors + cache_errors)
    if errors:
        record["usage_status"] = "rejected"
        return record

    record["input_tokens"] = usage["input_tokens"]
    record["cached_input_tokens"] = usage["cached_input_tokens"]
    record["output_tokens"] = usage["output_tokens"]
    record["long_context_gt_272000"] = usage["input_tokens"] > LONG_CONTEXT_INPUT_TOKENS
    record["base_valuation_usd"] = _base_valuation(
        usage["input_tokens"], usage["cached_input_tokens"], usage["output_tokens"])
    record["usage_status"] = "valid" if not record["invalid_reasons"] else "rejected"
    return record


def _submitted_turn_dirs(generation: Path) -> list[Path]:
    """Enumerate known scale/SCC submitted turn directories only."""
    turn_roots = []
    scale_root = generation / "turns"
    if scale_root.is_dir():
        turn_roots.extend(path for path in scale_root.iterdir() if path.is_dir())
    assignments = generation / "assignments"
    if assignments.is_dir():
        for assignment in sorted(path for path in assignments.iterdir() if path.is_dir()):
            turns = assignment / "turns"
            if turns.is_dir():
                turn_roots.extend(path for path in turns.iterdir() if path.is_dir())
    return sorted(turn_roots, key=lambda path: path.relative_to(generation).as_posix())


def audit(generation: Path) -> dict[str, Any]:
    """Return a deterministic scope audit for a generation directory."""
    generation = Path(generation).resolve()
    if not generation.is_dir():
        raise ValueError(f"generation directory is missing: {generation}")
    records = [_turn_record(path, generation) for path in _submitted_turn_dirs(generation)]
    valid = [row for row in records if row["usage_status"] == "valid"]
    unknown = [row for row in records if row["usage_status"] == "unknown"]
    rejected = [row for row in records if row["usage_status"] == "rejected"]
    long_context = [row for row in valid if row["long_context_gt_272000"]]
    nonzero_cache_write = [row for row in records if row["cache_write_state"] == "reported_nonzero"]
    invalid_cache_write = [row for row in records if row["cache_write_state"] == "reported_invalid"]
    base_total = sum(row["base_valuation_usd"] for row in valid)
    absent_cache_write = [row for row in valid if row["cache_write_state"] == "not_reported"]
    complete = bool(records) and not unknown and not rejected and not long_context \
        and not nonzero_cache_write and not absent_cache_write
    return {
        "schema": "luna-pricing-scope-audit-v1",
        "tariff_source": "https://developers.openai.com/api/docs/models/gpt-5.6-luna",
        "tariff_scope_checked_date": "2026-09-11",
        "generation_layout": "scale_turns" if (generation / "turns").is_dir() else "scc_assignments_turns",
        "rates_usd_per_million_standard": {
            "input": INPUT_RATE, "cached_input": CACHED_INPUT_RATE, "output": OUTPUT_RATE,
        },
        "long_context_threshold_input_tokens_exclusive": LONG_CONTEXT_INPUT_TOKENS,
        "records": records,
        "summary": {
            "turn_files": len(records),
            "events_files_present": sum(row["events_file_present"] for row in records),
            "events_files_missing": sum(not row["events_file_present"] for row in records),
            "valid_usage_turns": len(valid),
            "unknown_usage_turns": len(unknown),
            "rejected_usage_turns": len(rejected),
            "reported_cache_write_not_reported": sum(row["cache_write_state"] == "not_reported" for row in records),
            "reported_cache_write_zero": sum(row["cache_write_state"] == "reported_zero" for row in records),
            "reported_cache_write_nonzero": len(nonzero_cache_write),
            "reported_cache_write_invalid": len(invalid_cache_write),
            "known_turns_cache_write_not_reported": len(absent_cache_write),
            "long_context_gt_272000_turns": len(long_context),
            "max_input_tokens": max((row["input_tokens"] for row in valid), default=None),
            "max_cached_input_tokens": max((row["cached_input_tokens"] for row in valid), default=None),
            "base_valuation_usd_valid_turns": base_total if valid else None,
            "claimed_complete_base_valuation_usd": base_total if complete else None,
            "complete_standard_scope_claim": complete,
            "long_context_tariff_corrected_cost": None,
            "long_context_cost_status": "withheld_request_level_scope_unresolved",
            "scope_limitation": "CLI-turn totals are not a per-inference HTTP ledger; no actual invoice or corrected long-prompt cost is inferred.",
        },
    }


def write_sidecar(generation: Path, output: Path) -> dict[str, Any]:
    result = audit(generation)
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing sidecar: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def verify_saved(generation: Path, sidecar: Path) -> dict[str, Any]:
    """Recompute and compare a saved sidecar exactly."""
    sidecar = Path(sidecar)
    try:
        saved = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid pricing-scope sidecar: {sidecar}") from exc
    recomputed = audit(generation)
    if json.dumps(saved, sort_keys=True) != json.dumps(recomputed, sort_keys=True):
        raise ValueError("pricing-scope sidecar differs from deterministic recomputation")
    return recomputed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = (write_sidecar(args.generation, args.output)
              if args.output is not None else verify_saved(args.generation, args.verify))
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
