"""Immutable export of the complete 9,000-assignment SCC ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reproducibility import benchmark_bridge as bridge  # noqa: E402
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.revision_20260911 import scc_controls, scc_dispatch  # noqa: E402


class _ReplayAbort(scc_dispatch.scc.TransportAbort):
    """Evidence mismatch must escape upstream broad Exception handlers."""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _code_from_final(text: str) -> tuple[str, bool]:
    code, ok = bridge._extract_fenced_block(text, "bigcodebench")
    if ok:
        return code, True
    # The dispatcher writes an empty candidate when the required fenced
    # format is absent; do not invent a candidate from an unmarked response.
    return "", False


def _raw_turns(assignment: Path) -> tuple[list[str], list[dict[str, Any]]]:
    texts: list[str] = []
    usages: list[dict[str, Any]] = []
    turns = sorted((p for p in (assignment / "turns").iterdir() if p.is_dir()), key=lambda p: p.name) if (assignment / "turns").is_dir() else []
    for turn in turns:
        if not (turn / "events.jsonl").is_file() or not (turn / "status.json").is_file():
            raise ValueError(f"Turn evidence is incomplete: {turn}")
        try:
            raw = (turn / "events.jsonl").read_bytes()
            parsed = (scc_dispatch.parse_completed_empty(raw) if (turn / "empty_response_classification.json").exists()
                      else cli.parse_events(raw))
        except Exception:
            # A transport failure may have no parseable final response, but its
            # raw usage still belongs in the ledger and must not block export.
            try:
                usage = scc_dispatch._raw_usage(turn)
            except ValueError:
                usage = None
            if usage is not None:
                usages.append(usage)
            continue
        texts.append(parsed.get("final_text", ""))
        if isinstance(parsed.get("usage"), dict):
            usages.append(parsed["usage"])
    return texts, usages


def _validate_terminal_artifacts(assignment: Path, cell: dict[str, Any], state: str) -> None:
    """Accept both dispatcher result spellings, while checking their identity.

    Process workers normally use the assignment status file only.  Older
    resumptions and external coordinator snapshots may additionally retain
    ``result.json`` or ``terminal_result.json``.  Those files are evidence,
    so a malformed or contradictory copy must not be silently ignored.
    """
    terminal_states = {"completed", "infrastructure_failure", "model_or_workflow_failure", "paused"}
    for name in ("result.json", "terminal_result.json"):
        path = assignment / name
        if not path.is_file():
            continue
        try:
            data = cli.read(path)
        except Exception as exc:
            raise ValueError(f"Invalid {name}: {path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Invalid {name}: expected object")
        for key in ("id", "cell_id"):
            if key in data and data[key] != cell["id"]:
                raise ValueError(f"{name} identity differs from frozen cell: {path}")
        if "task_id" in data and data["task_id"] != cell["task_id"]:
            raise ValueError(f"{name} task identity differs from frozen cell: {path}")
        result_state = data.get("state")
        if result_state in {"failed", "error", "incomplete", "running", "started", "initializing"}:
            if state == "completed":
                raise ValueError(f"Completed assignment has nonterminal {name}: {path}")
        elif result_state is not None and result_state not in terminal_states | {"success"}:
            raise ValueError(f"Unknown state in {name}: {result_state!r}")


def _validate_generated_tests(assignment: Path, status: dict[str, Any], assignment_state: str) -> None:
    listed = status.get("generated_test_runs", [])
    if not isinstance(listed, list):
        raise ValueError(f"generated_test_runs must be a list: {assignment}")
    for rel in listed:
        path = (assignment / str(rel).replace("\\", "/")).resolve()
        if assignment.resolve() not in path.parents:
            raise ValueError(f"Generated-test path escapes assignment: {assignment}")
        if not (path / "status.json").is_file():
            raise ValueError(f"Generated-test evidence lacks status.json: {path}")
        check_state = cli.read(path / "status.json").get("state")
        if check_state not in {"completed", "infrastructure_failure"}:
            raise ValueError(f"Generated-test evidence is unfinished: {path}")
        if assignment_state == "completed" and check_state != "completed":
            raise ValueError(f"Completed assignment has failed generated-test evidence: {path}")
        if check_state == "completed":
            if not (path / "input.json").is_file() or not (path / "stdout.txt").is_file() or not (path / "argv.json").is_file():
                raise ValueError(f"Completed generated test lacks input/stdout/argv evidence: {path}")
            try:
                stdout_result = cli.read(path / "stdout.txt")
            except Exception as exc:
                raise ValueError(f"Generated-test stdout is not JSON evidence: {path}") from exc
            status_data = cli.read(path / "status.json")
            if stdout_result.get("report") != status_data.get("report"):
                raise ValueError(f"Generated-test stdout report differs from status: {path}")
            report_file = path / "report_from_stdout.json"
            if report_file.is_file() and cli.read(report_file) != stdout_result:
                raise ValueError(f"Generated-test report archive differs from stdout: {path}")


def _validate_turn_evidence(assignment: Path, cell: dict[str, Any], task: dict[str, Any], status: dict[str, Any]) -> None:
    turns = sorted((p for p in (assignment / "turns").iterdir() if p.is_dir()), key=lambda p: p.name) if (assignment / "turns").is_dir() else []
    requests = cli.read(assignment / "requests.json") if (assignment / "requests.json").is_file() else []
    if status.get("state") == "completed" and len(turns) != len(requests):
        raise ValueError(f"Completed assignment request/turn count differs: {assignment}")
    commands = {}
    commands_path = assignment.parent.parent / "commands.json"
    if commands_path.is_file():
        commands = cli.read(commands_path)
    for i, turn in enumerate(turns):
        result_path = turn / "result.json"
        if not result_path.exists() and (turn / "empty_response_classification.json").exists():
            result_path = turn / "empty_response_classification.json"
        turn_status = cli.read(turn / "status.json")
        if turn_status.get("state") == "completed":
            if not result_path.is_file():
                raise ValueError(f"Completed turn lacks result.json: {turn}")
            result = cli.read(result_path)
            raw = (turn / "events.jsonl").read_bytes()
            try:
                parsed = cli.parse_events(raw)
            except Exception:
                parsed = scc_dispatch.parse_completed_empty(raw)
            for key in ("final_text", "usage", "api_equivalent_usd", "uncached_sensitivity_usd"):
                if key not in result or result[key] != parsed[key]:
                    raise ValueError(f"Turn result differs from raw stream: {turn}")
            files = result.get("files_sha256", {})
            required = ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")
            if set(files) != set(required) or any(not (turn / n).is_file() or sha(turn / n) != files[n] for n in required):
                raise ValueError(f"Turn file hashes are incomplete or changed: {turn}")
        if i >= len(requests):
            continue
        request = requests[i]
        if cell["method"] == scc_dispatch.METHOD:
            messages = request.get("messages")
            # cli.save canonicalizes object-key order; restore the
            # upstream role/content order before reproducing prompt bytes.
            ordered = ([{"role": m["role"], "content": m["content"]} for m in messages]
                       if isinstance(messages, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in messages) else None)
            if ordered is None or not (turn / "prompt.txt").is_file() or (turn / "prompt.txt").read_text(encoding="utf-8") != scc_dispatch.scc.serialize_messages(ordered):
                raise _ReplayAbort(f"SCC archived prompt differs from messages: {turn}")
        else:
            expected_prompt = cli.prompt_for(task, {"arm": cell["method"], "cli_turns": 1}, 0, [])
            if i != 0 or (turn / "prompt.txt").read_bytes() != expected_prompt.encode("utf-8"):
                raise _ReplayAbort(f"Single-arm raw prompt differs from frozen method: {turn}")
        if commands and cell["method"] in commands and (turn / "argv.json").is_file() and cli.read(turn / "argv.json") != commands[cell["method"]]:
            raise ValueError(f"Turn argv differs from frozen command: {turn}")
        if result_path.is_file() and request.get("result") is not None and cli.read(result_path) != request["result"]:
            raise _ReplayAbort(f"Archived request result differs from turn result: {turn}")


def _replay_scc_assignment(assignment: Path, task: dict[str, Any], cell: dict[str, Any], actual: str) -> None:
    """Replay upstream SCC transitions from archived responses and reports."""
    if cell["method"] != scc_dispatch.METHOD:
        return
    requests = cli.read(assignment / "requests.json")
    history_expected = cli.read(assignment / "session_history.json")
    response_i = 0
    checks = sorted((assignment / "generated_tests").iterdir(), key=lambda p: p.name) if (assignment / "generated_tests").is_dir() else []
    check_i = 0

    def model_call(messages, **kwargs):
        nonlocal response_i
        if response_i >= len(requests):
            raise _ReplayAbort("SCC replay produced more model calls than archived requests")
        record = requests[response_i]
        if record.get("messages") != messages:
            raise _ReplayAbort("SCC replay prompt differs from archived messages")
        if "upstream_kwargs" in record and record["upstream_kwargs"] != kwargs:
            raise _ReplayAbort("SCC replay upstream kwargs differ from archive")
        result = record.get("result") or {}
        response_i += 1
        return [result.get("final_text", "")]

    def execute(code, report):
        nonlocal check_i
        if check_i >= len(checks):
            raise _ReplayAbort("SCC replay produced more generated tests than archived")
        folder = checks[check_i]; check_i += 1
        if (folder / "input.json").is_file():
            inp = cli.read(folder / "input.json")
            if inp.get("code") != code or inp.get("report") != report:
                raise _ReplayAbort("SCC replay generated-test input differs from archive")
        terminal = cli.read(folder / "status.json")
        if terminal.get("state") != "completed":
            raise _ReplayAbort("Completed SCC assignment contains non-completed generated test")
        try:
            stdout_report = cli.read(folder / "stdout.txt").get("report")
        except Exception as exc:
            raise _ReplayAbort("Generated-test stdout evidence is not replayable") from exc
        if stdout_report != terminal.get("report"):
            raise _ReplayAbort("Generated-test stdout report differs from status")
        return stdout_report or ""

    replay, history = scc_dispatch.scc.run_session(task["prompt"] + "\n" + task.get("context", ""),
                                                   model_call, execute,
                                                   max_round=cell["max_upstream_round"], before_func="")
    if response_i != len(requests) or check_i != len(checks):
        raise _ReplayAbort("SCC replay did not consume all archived upstream evidence")
    if replay != actual or history != history_expected:
        raise _ReplayAbort("SCC selected candidate/history differs from archived evidence")


def _validate_single_prompt(assignment: Path, task: dict[str, Any], cell: dict[str, Any]) -> None:
    expected = cli.prompt_for(task, {"arm": cell["method"], "cli_turns": 1}, 0, [])
    requests = sorted(assignment.glob("turns/*.upstream_request.json"))
    if not requests:
        raise ValueError(f"Single-arm assignment lacks archived prompt: {assignment}")
    found = False
    for path in requests:
        data = cli.read(path)
        if data.get("prompt") == expected:
            found = True
            break
    if not found:
        raise ValueError("Single-arm prompt differs from frozen prompt_for output")


def _resource(assignment: Path) -> dict[str, Any]:
    _, usages = _raw_turns(assignment)
    turns = [p for p in (assignment / "turns").iterdir() if p.is_dir()] if (assignment / "turns").is_dir() else []
    invalid = []
    for turn in turns:
        try: scc_dispatch._raw_usage(turn)
        except ValueError as exc: invalid.append({"turn": turn.name, "reason": str(exc)})
    result = {"turns": len(turns), "known_turns": len(usages), "unknown_turns": len(turns) - len(usages), "invalid_usage": invalid,
              "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "known_api_equivalent_usd": 0.0}
    for usage in usages:
        for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
            result[key] += int(usage.get(key, 0))
        result["known_api_equivalent_usd"] += cli.value_usage(usage)
    return result


def _expected(inputs: Path, manifest: Path, gate_dir: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    frozen = cli.read(manifest)
    gate = (gate_dir or (ROOT / "reproducibility/runs/scale1000-v1/controls-v3")).resolve()
    if frozen != scc_controls.plan(inputs, gate):
        raise ValueError("Frozen SCC manifest differs from current inputs, gate, or sources")
    tasks = cli.tasks_from(inputs / "input" / "prepared.jsonl")
    planned = scc_dispatch.cells(tasks)
    if len(planned) != 9000:
        raise ValueError("SCC frozen schedule must contain exactly 9,000 assignments")
    return frozen, planned


def _row_for(assignment: Path | None, cell: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    base = {**cell, "generation_complete": False, "observed_candidate": False,
            "native_status": None, "quality": None, "format_extracted": False,
            "outcome_type": "generation_unavailable", "resource_usage": {}}
    if assignment is None:
        return base | {"availability": "never_started"}
    for name in ("cell.json", "task.json", "status.json"):
        if not (assignment / name).is_file():
            raise ValueError(f"Assignment lacks required identity/status file: {assignment / name}")
    if cli.read(assignment / "cell.json") != cell or cli.read(assignment / "task.json") != task:
        raise ValueError(f"Assignment identity changed: {assignment}")
    status = cli.read(assignment / "status.json"); state = status.get("state")
    if state not in {"completed", "infrastructure_failure", "model_or_workflow_failure", "paused"}:
        raise ValueError(f"Assignment has nonterminal state: {assignment}")
    _validate_terminal_artifacts(assignment, cell, state)
    _validate_generated_tests(assignment, status, state)
    if "generation_complete" in status and bool(status["generation_complete"]) != (state == "completed"):
        raise ValueError(f"Assignment generation_complete disagrees with terminal state: {assignment}")
    if state == "completed":
        _validate_turn_evidence(assignment, cell, task, status)
    row = base | {"availability": "completed" if state == "completed" else "submitted_incomplete",
                  "status_state": state, "resource_usage": _resource(assignment)}
    texts, _ = _raw_turns(assignment); candidate = assignment / "candidate.py"
    # Only a completed assignment has a candidate eligible for native export.
    # A partial candidate left beside a transport failure is retained as raw
    # evidence but cannot become a fabricated benchmark sample.
    if state == "completed" and candidate.is_file() and texts:
        actual = candidate.read_text(encoding="utf-8")
        if state == "completed":
            if status.get("candidate_sha256") and status["candidate_sha256"] != sha(candidate):
                raise ValueError(f"Candidate hash differs from terminal status: {assignment}")
            if cell["method"] == scc_dispatch.METHOD:
                _replay_scc_assignment(assignment, task, cell, actual)
                extracted = bool(actual and actual != "error")
            else:
                _validate_single_prompt(assignment, task, cell)
                replay, extracted = _code_from_final(texts[-1])
                if actual != replay:
                    raise ValueError(f"Candidate differs from raw final response: {assignment}")
        row.update({"observed_candidate": True, "solution": actual, "candidate_sha256": sha(candidate),
                    "task_prompt_sha256": cli.digest(task["prompt"]), "format_extracted": bool(extracted and actual),
                    "outcome_type": "native_pending" if bool(extracted and actual) else "model_format_failure"})
    elif state != "completed":
        row["outcome_type"] = state
    if state == "completed":
        if not candidate.is_file() or not texts:
            raise ValueError(f"Completed assignment lacks replayable final response: {assignment}")
        row["generation_complete"] = True
    return row


def _rows(archive: Path, inputs: Path, manifest: Path, gate_dir: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    frozen, planned = _expected(inputs, manifest, gate_dir)
    archive_manifest = archive / "manifest.json"
    if not archive_manifest.is_file() or cli.read(archive_manifest) != frozen:
        raise ValueError("SCC archive manifest differs from frozen generation manifest")
    commands = cli.read(archive / "commands.json")
    runtime = cli.read(archive / "runtime.json")
    if set(commands) != set(frozen["methods"]) or runtime.get("version") != cli.CLI_VERSION:
        raise ValueError("SCC archive runtime identity differs")
    for method, argv in commands.items():
        instruction_arg = next(json.loads(x.split("=", 1)[1]) for x in argv if x.startswith("model_instructions_file="))
        cwd = argv[argv.index("--cd") + 1]
        if argv != cli.cli_command(runtime["prefix"], cwd, instruction_arg):
            raise ValueError("SCC archive transport settings differ")
        expected = scc_dispatch.scc.INSTRUCTIONS if method == scc_dispatch.METHOD else cli.BASE
        if (archive / f"instructions-{method}.txt").read_bytes() != expected.encode("utf-8"):
            raise ValueError("Archived model policy differs")
    tasks = {t["task_id"]: t for t in cli.tasks_from(inputs / "input" / "prepared.jsonl")}
    assignments = archive / "assignments"
    return frozen, [_row_for((assignments / c["id"]) if (assignments / c["id"]).exists() else None, c, tasks[c["task_id"]]) for c in planned]


def _write_method_exports(out: Path, rows: list[dict[str, Any]], inputs: Path, methods: list[str], repeats: list[int]) -> dict[str, str]:
    order = {task_id: i for i, task_id in enumerate(cli.read(inputs / "selection.json")["assigned_task_ids"])}; hashes = {}
    for method in methods:
        for rep in repeats:
            key = f"{method}-r{rep}"; selected = [r for r in rows if r["method"] == method and r["replicate_id"] == rep and r.get("observed_candidate")]
            selected.sort(key=lambda r: order[r["task_id"]])
            path = out / f"{key}.jsonl"; path.write_bytes(b"".join(cli.canonical({"task_id": r["task_id"], "solution": r.get("solution", "")}) + b"\n" for r in selected)); hashes[key] = sha(path)
    return hashes


def _expected_method_bytes(rows: list[dict[str, Any]], inputs: Path, method: str, rep: int) -> bytes:
    order = {task_id: i for i, task_id in enumerate(cli.read(inputs / "selection.json")["assigned_task_ids"])}
    selected = [r for r in rows if r["method"] == method and r["replicate_id"] == rep and r.get("observed_candidate")]
    selected.sort(key=lambda r: order[r["task_id"]])
    return b"".join(cli.canonical({"task_id": r["task_id"], "solution": r.get("solution", "")}) + b"\n" for r in selected)


def export(archive: Path, inputs: Path, manifest: Path, out: Path, gate_dir: Path | None = None) -> dict[str, Any]:
    archive = archive.resolve(); inputs = inputs.resolve(); manifest = manifest.resolve(); out = out.resolve()
    if not (archive / "status.json").is_file() or cli.read(archive / "status.json").get("state") == "running":
        raise ValueError("Cannot export while SCC dispatcher is running")
    if (archive / "DISPATCH.lock").exists():
        raise ValueError("Cannot export while SCC dispatch lock exists")
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite SCC export: {out}")
    frozen, rows = _rows(archive, inputs, manifest, gate_dir); out.mkdir(parents=True)
    try:
        (out / "assignment_records.jsonl").write_bytes(b"".join(cli.canonical(r) + b"\n" for r in rows))
        hashes = _write_method_exports(out, rows, inputs, frozen["methods"], frozen["replicate_ids"])
        cli.save(out / "export_manifest.json", {"schema": "scc-export-v2", "generation_manifest_sha256": sha(manifest),
            "assignment_rows": len(rows), "planned_assignments": 9000, "completed": sum(r["generation_complete"] for r in rows),
            "observed_candidates": sum(r["observed_candidate"] for r in rows), "sample_hashes": hashes})
        return {"rows": len(rows), "completed": sum(r["generation_complete"] for r in rows), "observed_candidates": sum(r["observed_candidate"] for r in rows), "export": str(out)}
    except Exception:
        cli.save(out / ".export_failed.json", {"error": "export failed; inspect partial output"})
        raise


def validate_export(archive: Path, inputs: Path, manifest: Path, out: Path, gate_dir: Path | None = None) -> dict[str, Any]:
    if not out.is_dir() or not (out / "export_manifest.json").is_file() or not (out / "assignment_records.jsonl").is_file():
        raise ValueError("SCC export is incomplete")
    frozen, expected = _rows(archive, inputs, manifest, gate_dir)
    actual = [json.loads(x) for x in (out / "assignment_records.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if actual != expected:
        raise ValueError("SCC export differs from immutable generation evidence")
    metadata = cli.read(out / "export_manifest.json")
    if metadata.get("generation_manifest_sha256") != sha(manifest) or metadata.get("assignment_rows") != len(expected):
        raise ValueError("SCC export metadata does not match frozen generation")
    expected_hashes = {}
    for method in frozen["methods"]:
        for rep in frozen["replicate_ids"]:
            key = f"{method}-r{rep}"; data = _expected_method_bytes(expected, inputs, method, rep)
            expected_hashes[key] = hashlib.sha256(data).hexdigest()
            path = out / f"{key}.jsonl"
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError(f"SCC method export differs from assignment ledger: {key}")
    if metadata.get("sample_hashes") != expected_hashes:
        raise ValueError("SCC method export hash metadata differs from derived bytes")
    for key, expected_hash in expected_hashes.items():
        path = out / f"{key}.jsonl"
        if not path.is_file() or sha(path) != expected_hash:
            raise ValueError(f"SCC method export changed: {key}")
    return metadata


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--archive", type=Path, required=True); p.add_argument("--inputs", type=Path, required=True); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--out", type=Path, required=True); a = p.parse_args()
    print(json.dumps(export(a.archive, a.inputs, a.manifest, a.out), ensure_ascii=False))


if __name__ == "__main__": main()
