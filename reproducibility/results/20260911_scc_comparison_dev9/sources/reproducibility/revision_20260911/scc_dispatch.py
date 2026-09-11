"""Resumable, process-isolated SCC author-code dispatcher.

The dispatcher keeps the upstream SCC controller intact and only supplies the
audited Luna text transport and isolated generated-test executor. It is kept
separate from the frozen factorial dispatcher because SCC has a dynamic
three-or-four-call trajectory.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import random
import os
from pathlib import Path
import subprocess
import sys
import time
import multiprocessing

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.external_baselines import scc  # noqa: E402
from reproducibility import benchmark_bridge as bridge  # noqa: E402
from reproducibility.record_codex_runtime import capture  # noqa: E402
from reproducibility.revision_20260911 import scc_controls  # noqa: E402

REPEATS = (101, 102, 103)
METHOD = "scc_author_2024_codex_transport"
METHODS = ("single_roles", "single_neutral", METHOD)
_TEST_SEMAPHORE = None


def _worker_init(test_semaphore):
    """Spawn initializer: each process gets its own SCC module globals."""
    global _TEST_SEMAPHORE
    _TEST_SEMAPHORE = test_semaphore


def _worker_docker_execute(folder: Path, code: str, report: str) -> str:
    if _TEST_SEMAPHORE is None:
        return scc.docker_execute(folder, code, report)
    acquired = _TEST_SEMAPHORE.acquire(timeout=600)
    if not acquired:
        raise scc.TransportAbort("generated-test semaphore timeout")
    try:
        return scc.docker_execute(folder, code, report)
    finally:
        _TEST_SEMAPHORE.release()


def run_assignment_worker(payload: dict) -> dict:
    """Execute exactly one assignment in a spawned process.

    The parent passes verified task/cell/command bytes. No upstream SCC module
    state is shared between workers; all evidence is written to the unique
    assignment directory before the result is returned.
    """
    assignment = Path(payload["assignment"])
    task = payload["task"]
    cell = payload["cell"]
    command = payload["command"]
    assignment.mkdir(parents=True, exist_ok=False)
    cli.save(assignment / "task.json", task); cli.save(assignment / "cell.json", cell)
    cli.save(assignment / "status.json", {"state": "initializing", "generation_complete": False,
                                            "started_unix": time.time()})
    calls: list[dict] = []; checks: list[str] = []; counted: set[Path] = set()

    def model_call(messages, **kwargs):
        index = len(calls); folder = assignment / "turns" / f"{index:03d}"
        record = {"messages": copy.deepcopy(messages), "upstream_kwargs": kwargs}
        calls.append(record); payload_text = scc.serialize_messages(messages)
        folder.parent.mkdir(parents=True, exist_ok=True)
        cli.save(folder.parent / f"{index:03d}.upstream_request.json", record)
        try:
            result = cli.archive_turn(folder, command, payload_text, 600)
        except Exception as exc:
            result = _accept_empty_completed(folder, command)
            if result is None: raise scc.TransportAbort(str(exc)) from exc
        record["result"] = result; counted.add(folder)
        return [result["final_text"]]

    def execute(code, report):
        folder = assignment / "generated_tests" / f"{len(checks):03d}"
        checks.append(str(folder.relative_to(assignment)))
        return _worker_docker_execute(folder, code, report)

    try:
        requirement = task["prompt"] + "\n" + task.get("context", "")
        if cell["method"] == METHOD:
            code, history = scc.run_session(requirement, model_call, execute,
                                             max_round=2, before_func="")
        else:
            prompt = cli.prompt_for(task, {"arm": cell["method"], "cli_turns": 1}, 0, [])
            folder = assignment / "turns" / "000"; folder.parent.mkdir(parents=True, exist_ok=True)
            cli.save(folder.parent / "000.upstream_request.json", {"prompt": prompt,
                     "method": cell["method"], "task_id": cell["task_id"], "written_before_call": True})
            try:
                result = cli.archive_turn(folder, command, prompt, 600)
            except Exception as exc:
                result = _accept_empty_completed(folder, command)
                if result is None: raise scc.TransportAbort(str(exc)) from exc
            calls.append({"result": result}); counted.add(folder)
            history = [result["final_text"]]
            code, extracted = bridge._extract_fenced_block(history[-1], "bigcodebench")
            if not extracted:
                (assignment / "observed_answer.txt").write_text(history[-1], encoding="utf-8")
                code = ""
        (assignment / "candidate.py").write_bytes(code.encode("utf-8"))
        cli.save(assignment / "session_history.json", history); cli.save(assignment / "requests.json", calls)
        status = {"state": "completed", "generation_complete": True, "task_id": cell["task_id"],
                  "calls_attempted": len(calls), "generated_test_runs": checks,
                  "format_extracted": bool(code and code != "error"),
                  "outcome_type": "native_pending", "candidate_is_upstream_selected": True,
                  "candidate_sha256": hashlib.sha256(code.encode()).hexdigest(),
                  "finished_unix": time.time()}
        cli.save(assignment / "status.json", status)
        valuation, unknown, invalid = _assignment_usage(assignment)
        if invalid:
            status.update({"state": "infrastructure_failure", "generation_complete": False,
                           "outcome_type": "unpriceable_or_invalid_usage", "format_extracted": False,
                           "unknown_usage_calls": unknown})
            cli.save(assignment / "status.json", status)
            return {"id": cell["id"], "state": "infrastructure_failure", "valuation": valuation,
                    "unknown_usage_calls": max(1, unknown), "stop_hint": "unpriceable_or_invalid_usage"}
        return {"id": cell["id"], "state": "completed", "valuation": valuation,
                "unknown_usage_calls": unknown}
    except BaseException as exc:
        cli.save(assignment / "requests.json", calls)
        kind = _failure_kind(exc)
        # Only a completed one-call malformed answer gets an empty candidate.
        if cell["method"] != METHOD and calls and calls[-1].get("result"):
            answer = calls[-1]["result"].get("final_text", "")
            (assignment / "observed_answer.txt").write_text(answer, encoding="utf-8")
            (assignment / "candidate.py").write_text("", encoding="utf-8")
        usage, unknown, invalid = _assignment_usage(assignment)
        status = {"state": kind, "generation_complete": False, "task_id": cell["task_id"],
                  "outcome_type": kind, "format_extracted": False,
                  "reason": str(exc), "exception_type": type(exc).__name__,
                  "calls_attempted": len(calls), "generated_test_runs": checks,
                  "observed_failed_turn_valuation": usage, "unknown_usage_calls": unknown,
                  "finished_unix": time.time()}
        cli.save(assignment / "status.json", status)
        retained = _retained_text(assignment).lower()
        hint = "unpriceable_or_invalid_usage" if invalid else ("quota_auth_or_unsupported_model" if any(x in retained for x in
                  ("usage limit", "quota", "unauthorized", "unsupported model")) else None)
        return {"id": cell["id"], "state": kind, "valuation": usage,
                "unknown_usage_calls": unknown, "stop_hint": hint}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cells(tasks: list[dict]) -> list[dict]:
    rng = random.Random(20260911)
    blocks = [(task["task_id"], rep) for task in tasks for rep in REPEATS]
    rng.shuffle(blocks)
    result = []
    for task_id, rep in blocks:
        ordered = list(METHODS); rng.shuffle(ordered)
        for method in ordered:
            cell = {"task_id": task_id, "replicate_id": rep,
                    "method": method, "max_upstream_round": 2 if method == METHOD else 0,
                    "cli_turns": 1 if method != METHOD else 4}
            result.append({**cell, "id": cli.digest(cell)[:24]})
    return result


def plan(inputs: Path, gate_dir: Path, manifest: Path) -> tuple[dict, list[dict]]:
    frozen = cli.read(manifest)
    current = scc_controls.plan(inputs, gate_dir)
    if frozen != current:
        raise ValueError("Frozen SCC manifest differs from current inputs or sources")
    tasks = cli.tasks_from(inputs / "input" / "prepared.jsonl")
    by_id = {t["task_id"] for t in tasks}
    planned = cells(tasks)
    if frozen.get("planned_assignments") != len(planned) or set(x["task_id"] for x in planned) != by_id:
        raise ValueError("SCC assignment inventory does not match frozen manifest")
    return frozen, planned


def _retained_text(folder: Path) -> str:
    pieces = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix in {".txt", ".json", ".jsonl"}:
            pieces.append(p.read_text(encoding="utf-8", errors="replace")[-12000:])
    return "\n".join(pieces)


def _raw_usage(folder: Path):
    path = folder / "events.jsonl"
    if not path.exists():
        return None
    found = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            found.append(event["usage"])
    if len(found) > 1:
        raise ValueError("Multiple usage completions in one fresh turn")
    if not found:
        return None
    usage = found[0]
    required = ("input_tokens", "cached_input_tokens", "output_tokens")
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in required):
        raise ValueError("Invalid usage counters")
    if usage["cached_input_tokens"] > usage["input_tokens"] or usage.get("cache_write_input_tokens", 0) != 0:
        raise ValueError("Invalid cache accounting")
    return usage


def parse_completed_empty(raw: bytes) -> dict:
    """Validate the whole fixed text-only stream before classifying empty output."""
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    messages = [e for e in events if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "agent_message"]
    if len(messages) > 1 or (messages and (not isinstance(messages[0]["item"].get("text"), str) or messages[0]["item"]["text"].strip())):
        raise ValueError("Not a terminal empty model response")
    original = messages[0]["item"]["text"] if messages else ""
    if messages: messages[0]["item"]["text"] = "EMPTY_RESPONSE_VALIDATION_SENTINEL"
    else: events.insert(0, {"type": "item.completed", "item": {"type": "agent_message", "text": "EMPTY_RESPONSE_VALIDATION_SENTINEL"}})
    parsed = cli.parse_events(b"\n".join(cli.canonical(event) for event in events))
    parsed.update(final_text=original, empty_model_response=True)
    return parsed


def _accept_empty_completed(folder: Path, command: list[str]) -> dict | None:
    """Reclassify only the specific parser rejection; retain the original status."""
    if not (folder / "status.json").is_file(): return None
    original = cli.read(folder / "status.json")
    if original.get("state") != "blocked" or original.get("reason") != "One completed turn and one complete answer required":
        return None
    try:
        if cli.read(folder / "argv.json") != command: return None
        result = parse_completed_empty((folder / "events.jsonl").read_bytes())
    except (ValueError, KeyError, OSError, TypeError):
        return None
    result.update(original_terminal_status=original, wall_seconds=None,
                  files_sha256={n: sha(folder / n) for n in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")})
    cli.save(folder / "empty_response_classification.json", result)
    cli.save(folder / "status.json", {"state": "completed", "empty_model_response": True})
    return result


def _assignment_usage(assignment: Path) -> tuple[float, int, bool]:
    valuation = 0.0; unknown = 0; invalid = False
    for turn in (assignment / "turns").iterdir() if (assignment / "turns").exists() else []:
        if not turn.is_dir(): continue
        try: raw = _raw_usage(turn)
        except ValueError: raw = None; invalid = True
        if raw is None: unknown += 1
        else: valuation += cli.value_usage(raw)
    return valuation, unknown, invalid


def _failure_kind(exc: BaseException) -> str:
    """Stable terminal classification for the assignment ledger."""
    if isinstance(exc, (scc.TransportAbort, FileNotFoundError, TimeoutError,
                        subprocess.TimeoutExpired, ConnectionError)):
        return "infrastructure_failure"
    return "model_or_workflow_failure"


def _known_from_turns(out: Path) -> float:
    """Price each emitted turn once, including failed/partial attempts."""
    total = 0.0
    for turn in out.glob("assignments/*/turns/*"):
        if not turn.is_dir():
            continue
        usage = _raw_usage(turn)
        if usage is not None:
            total += cli.value_usage(usage)
    return total


def _submission_capacity(pending: int, active: int, workers: int, known: float, guard: float) -> int:
    """Pure parent scheduling rule, useful for offline coordinator tests."""
    if known >= guard or pending <= 0:
        return 0
    return min(pending, max(0, workers - active))


def coordinate_assignments(pending: list[dict], payload_for, executor,
                           workers: int, known: float, guard: float) -> dict:
    """Coordinate futures with the same stop/replenish semantics as dispatch.

    `executor` only needs ``submit`` and the futures need ``result``; this
    deliberately small seam makes the parent policy testable without model or
    Docker calls.
    """
    if not 1 <= workers <= 8: raise ValueError("workers must be between 1 and 8")
    active = {}; results = []; stop_reason = None; failure_streak = 0
    while pending or active:
        while _submission_capacity(len(pending), len(active), workers, known, guard) and stop_reason is None:
            cell = pending.pop(0)
            active[executor.submit(run_assignment_worker, payload_for(cell))] = cell
        if not active: break
        done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
        for future in done:
            cell = active.pop(future)
            try:
                result = future.result()
            except BaseException as exc:
                result = {"id": cell["id"], "state": "infrastructure_failure", "valuation": 0.0,
                          "stop_hint": "worker_process_failure", "unknown_usage_calls": None, "reason": str(exc)}
            results.append((cell, result))
            known += float(result.get("valuation", 0.0))
            if result.get("stop_hint") and stop_reason is None: stop_reason = result["stop_hint"]
            if result.get("state") == "completed": failure_streak = 0
            else:
                failure_streak += 1
                if failure_streak >= 8 and stop_reason is None: stop_reason = "eight_consecutive_failures"
                if result.get("unknown_usage_calls", 0) and stop_reason is None: stop_reason = "unpriceable_or_invalid_usage"
            if known >= guard and stop_reason is None: stop_reason = "known_valuation_submission_guard"
    return {"pending": pending, "results": results, "known": known,
            "stop_reason": stop_reason, "max_inflight": workers}


@contextmanager
def dispatch_lock(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    lock_path = out / "DISPATCH.lock"
    try:
        handle = lock_path.open("x", encoding="utf-8")
        handle.write(str(__import__("os").getpid())); handle.close()
    except FileExistsError:
        raise ValueError("SCC dispatch already running")
    try:
        yield
    finally:
        try: lock_path.unlink()
        except FileNotFoundError: pass


def _dispatch_processes(inputs: Path, gate_dir: Path, manifest: Path, out: Path,
                       npm_root: Path, workers: int = 8, known_guard: float = 285.0,
                       prior_known: float = 0.0, prior_file: Path | None = None) -> dict:
    """Parent scheduler for process-isolated assignments.

    The parent owns ordering, quota guard and replenishment. Workers never
    share SCC globals; active assignments are allowed to finish after the
    parent stops submitting new work.
    """
    if not 1 <= workers <= 8: raise ValueError("workers must be between 1 and 8")
    frozen, planned = plan(inputs.resolve(), gate_dir.resolve(), manifest.resolve())
    if workers != frozen["workers"]:
        raise ValueError("Main-study worker count differs from the frozen plan")
    tasks = cli.tasks_from(inputs / "input" / "prepared.jsonl"); by_id = {x["task_id"]: x for x in tasks}
    out = out.resolve(); out.mkdir(parents=True, exist_ok=True)
    if (out / "manifest.json").exists() and cli.read(out / "manifest.json") != frozen:
        raise ValueError("Existing archive has a different manifest")
    if (out / "tasks.json").exists() and cli.read(out / "tasks.json") != tasks:
        raise ValueError("Saved task bytes changed")
    if not (out / "manifest.json").exists(): cli.save(out / "manifest.json", frozen)
    if not (out / "tasks.json").exists(): cli.save(out / "tasks.json", tasks)
    for name in frozen["source_files_sha256"]:
        target = out / "sources" / name
        data = (ROOT / name).read_bytes()
        if target.exists() and scc_controls.source_sha(target) != frozen["source_files_sha256"][name]:
            raise ValueError(f"Archived source changed: {name}")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    (out / "empty").mkdir(exist_ok=True)
    if any((out / "empty").iterdir()): raise ValueError("Task-free working directory must remain empty")
    os.environ["CODEX_STUDY_CLI_JS"] = str(npm_root.resolve() / "node_modules/@openai/codex/bin/codex.js")
    prefix = cli.resolved_prefix(); version = subprocess.check_output(prefix + ["--version"], text=True).strip()
    if version != cli.CLI_VERSION: raise ValueError("CLI version mismatch")
    auth = subprocess.run(prefix + ["login", "status"], capture_output=True, text=True)
    if auth.returncode or "ChatGPT" not in auth.stdout + auth.stderr: raise ValueError("ChatGPT login required")
    instruction_paths = {}
    for method, text in ((METHOD, scc.INSTRUCTIONS), ("single_roles", cli.BASE), ("single_neutral", cli.BASE)):
        path = out / f"instructions-{method}.txt"
        if path.exists() and path.read_bytes() != text.encode(): raise ValueError("Instruction bytes changed")
        if not path.exists(): path.write_bytes(text.encode("utf-8"))
        instruction_paths[method] = path
    legacy = out / "instructions.txt"
    if legacy.exists() and legacy.read_bytes() != cli.BASE.encode(): raise ValueError("Legacy instruction bytes changed")
    if not legacy.exists(): legacy.write_bytes(cli.BASE.encode("utf-8"))
    runtime = {"version": version, "prefix": prefix, "authentication": "chatgpt", "workers": workers,
               "timeout_seconds": 600, "started_unix": time.time(), "process_isolation": "spawn"}
    if not (out / "runtime.json").exists():
        cli.save(out / "runtime.json", runtime); capture(out, npm_root, Path(__file__))
    elif cli.read(out / "runtime.json")["prefix"] != prefix:
        raise ValueError("Runtime prefix changed on resume")
    else:
        provenance = cli.read(out / "runtime_provenance.json")
        if (sha(Path(provenance["native_executable_path"])) != provenance["native_executable_sha256"]
                or sha(Path(prefix[1])) != provenance["node_entry_sha256"]):
            raise ValueError("CLI binary changed since original runtime capture")
        if cli.read(out / "runtime.json")["workers"] != workers:
            raise ValueError("Worker count changed on resume")
    commands = {m: cli.cli_command(prefix, (out / "empty").resolve(), p.resolve()) for m, p in instruction_paths.items()}
    commands_file = out / "commands.json"
    if commands_file.exists() and cli.read(commands_file) != commands:
        raise ValueError("Runtime commands changed on resume")
    if not commands_file.exists(): cli.save(commands_file, commands)
    known = prior_known
    if (out / "prior_valuation.json").exists() and prior_known == 0 and prior_file is None:
        prior = cli.read(out / "prior_valuation.json"); known = prior["known_api_equivalent_usd"]; prior_file = Path(prior["source"])
    if prior_file is not None:
        if not prior_file.is_file(): raise FileNotFoundError(prior_file)
        if (out / "prior_valuation.json").exists() and prior_known == 0: prior_known = cli.read(out / "prior_valuation.json")["known_api_equivalent_usd"]; known = prior_known
        record = {"known_api_equivalent_usd": prior_known, "source": str(prior_file.resolve()), "source_sha256": sha(prior_file)}
        if (out / "prior_valuation.json").exists() and cli.read(out / "prior_valuation.json") != record: raise ValueError("Prior valuation changed")
        cli.save(out / "prior_valuation.json", record)
    if not 0 <= prior_known <= known_guard or not 15 < known_guard <= 285:
        raise ValueError("Invalid study valuation guard")
    known += _known_from_turns(out)
    submission_guard = known_guard - 15.0
    pending = []
    for cell in planned:
        status = out / "assignments" / cell["id"] / "status.json"
        if status.exists():
            state = cli.read(status).get("state")
            if state not in {"completed", "infrastructure_failure", "model_or_workflow_failure", "paused"}:
                raise ValueError(f"Nonterminal prior assignment requires documented recovery: {status}")
            continue
        if status.parent.exists():
            raise ValueError(f"Touched assignment lacks status; preserve and diagnose: {status.parent}")
        pending.append(cell)
    cli.save(out / "status.json", {"state": "running", "workers": workers,
                                    "pending_at_start": len(pending), "started_unix": time.time()})
    session = out / "sessions" / str(time.time_ns())
    session.mkdir(parents=True)
    cli.save(session / "pending.json", {"ids": [c["id"] for c in pending], "started_unix": time.time(),
             "prior_known_valuation": known, "submission_guard": submission_guard})
    cli.save(session / "commands.json", commands)
    stop_reason = None; completed = failures = 0; active = {}
    ctx = multiprocessing.get_context("spawn")
    manager = ctx.Manager(); semaphore = manager.BoundedSemaphore(frozen["generated_test_parallelism"])
    try:
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                                 initializer=_worker_init, initargs=(semaphore,)) as pool:
            def payload_for(cell):
                assignment = out / "assignments" / cell["id"]
                return {"assignment": str(assignment), "task": by_id[cell["task_id"]], "cell": cell,
                        "command": commands[cell["method"]]}
            coordinated = coordinate_assignments(pending, payload_for, pool, workers, known, submission_guard)
            pending = coordinated["pending"]; known = coordinated["known"]; stop_reason = coordinated["stop_reason"]
            for cell, result in coordinated["results"]:
                if result.get("state") == "completed": completed += 1
                else:
                    failures += 1
                    if result.get("stop_hint") == "worker_process_failure":
                        assignment = out / "assignments" / cell["id"]
                        assignment.mkdir(parents=True, exist_ok=True)
                        cli.save(assignment / "cell.json", cell); cli.save(assignment / "task.json", by_id[cell["task_id"]])
                        cli.save(assignment / "status.json", {"state": "infrastructure_failure", "generation_complete": False,
                                                               "outcome_type": "infrastructure_failure", "format_extracted": False,
                                                               "reason": result.get("reason", "worker process failure"),
                                                               "unknown_usage_calls": None, "finished_unix": time.time()})
    finally:
        manager.shutdown()
    untouched = len(pending) + sum(1 for c in active.values())
    status = {"state": "generation_finished" if not pending and not active else "paused",
              "completed_assignments": completed, "failed_assignments": failures,
              "untouched_assignments": untouched, "known_valuation": known,
              "stop_reason": stop_reason, "workers": workers, "finished_unix": time.time()}
    cli.save(session / "status.json", status)
    cli.save(out / "status.json", status)
    return status


def dispatch_processes(inputs: Path, gate_dir: Path, manifest: Path, out: Path,
                       npm_root: Path, workers: int = 8, known_guard: float = 285.0,
                       prior_known: float = 0.0, prior_file: Path | None = None) -> dict:
    with dispatch_lock(out):
        return _dispatch_processes(inputs, gate_dir, manifest, out, npm_root, workers,
                                   known_guard, prior_known, prior_file)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--gate-dir", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--npm-root", type=Path, default=Path("tmp/codex-runtime"))
    p.add_argument("--known-guard", type=float, default=285.0)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--prior-known-valuation", type=float, default=0.0)
    p.add_argument("--prior-valuation-file", type=Path)
    a = p.parse_args()
    print(json.dumps(dispatch_processes(a.inputs.resolve(), a.gate_dir.resolve(), a.manifest.resolve(),
                        a.out, a.npm_root, a.workers, a.known_guard, a.prior_known_valuation,
                        a.prior_valuation_file), ensure_ascii=False))


if __name__ == "__main__":
    main()
