"""External account-reserve guard; does not modify frozen experiment sources.

Only account/rateLimits/read is requested. No model turn, reset, or paid API call
is made. A pause is latched and requires an explicit user-authorized recovery.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
MODULES = {
    "reproducibility.scale1000_luna.dispatch",
    "reproducibility.revision_20260911.scc_dispatch",
}
RESERVE = 55.0


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def remaining_percent(payload: dict) -> float:
    """Use the current codex bucket, never the unused separate Spark bucket."""
    by_id = payload.get("rateLimitsByLimitId")
    if by_id is not None and not isinstance(by_id, dict):
        raise ValueError("Invalid multi-bucket rate limits")
    bucket = by_id.get("codex") if by_id else payload.get("rateLimits")
    if not isinstance(bucket, dict) or bucket.get("limitId") != "codex":
        raise ValueError("Main codex quota is unavailable")
    windows = []
    for name in ("primary", "secondary"):
        window = bucket.get(name)
        if window is None:
            continue
        used = window.get("usedPercent") if isinstance(window, dict) else None
        if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
            raise ValueError("Invalid usage percentage")
        windows.append(max(0.0, min(100.0, 100.0 - used)))
    if not windows:
        raise ValueError("No observed codex quota window")
    return min(windows)


def read_limits(executable: Path, cwd: Path, timeout: float = 20) -> dict:
    """Read the documented app-server endpoint using subscription login."""
    env = {k: v for k, v in os.environ.items()
           if k not in {"OPENAI_API_KEY", "OPENROUTER_API_KEY", "CODEX_API_KEY"}}
    process = subprocess.Popen(
        [str(executable), "app-server"],
        cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    messages: queue.Queue = queue.Queue()

    def receive():
        try:
            for line in process.stdout:
                try:
                    messages.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        finally:
            messages.put(None)

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout

    def send(value):
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()

    def response(request_id):
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Quota reader deadline exceeded")
            value = messages.get(timeout=remaining)
            if value is None:
                raise RuntimeError("Quota reader ended before a response")
            if value.get("id") != request_id:
                continue
            if "error" in value:
                raise RuntimeError("Quota endpoint rejected the request")
            result = value.get("result")
            if not isinstance(result, dict):
                raise ValueError("Invalid quota response")
            return result

    try:
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {
            "name": "hybrid_inot_subscription_guard", "version": "1.0.0"}}})
        response(1)
        send({"method": "initialized"})
        send({"id": 2, "method": "account/rateLimits/read"})
        result = response(2)
        # Retain quota evidence, not credentials or account identifiers.
        return {k: result.get(k) for k in ("rateLimits", "rateLimitsByLimitId")}
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=2)
        for stream in (process.stdin, process.stdout):
            stream.close()


def is_study_dispatcher(process: psutil.Process, root: Path) -> bool:
    try:
        command = process.cmdline()
        index = command.index("-m")
        return command[index + 1] in MODULES and Path(process.cwd()).resolve() == root.resolve()
    except (ValueError, IndexError, psutil.Error, OSError):
        return False


def stop_study_generators(root: Path) -> dict:
    """Stop only verified dispatchers in this checkout and their descendants.

    Suspend each dispatcher before enumerating children so it cannot replenish
    work while the stop is being applied. Retain Process handles, whose psutil
    identity checks protect against PID reuse. Leave native evaluators alone.
    """
    stopped, errors = [], []
    for process in psutil.process_iter():
        if not is_study_dispatcher(process, root):
            continue
        record = {"pid": process.pid}
        try:
            record.update(created=process.create_time(), command=process.cmdline())
            process.suspend()
            children = process.children(recursive=True)
            record["children"] = []
            for child in children:
                try:
                    record["children"].append({"pid": child.pid, "created": child.create_time()})
                except psutil.NoSuchProcess:
                    pass
            process.terminate()
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs([process, *children], timeout=5)
            for survivor in alive:
                survivor.kill()
            _, still_alive = psutil.wait_procs(alive, timeout=5)
            record["surviving_pids"] = [p.pid for p in still_alive]
            stopped.append(record)
        except psutil.NoSuchProcess:
            stopped.append({**record, "already_exited": True})
        except psutil.Error as exc:
            errors.append({**record, "error_type": type(exc).__name__})
    return {"stopped": stopped, "errors": errors}


def snapshot(executable: Path, root: Path) -> dict:
    start = time.time()
    try:
        payload = read_limits(executable, root)
        remaining = remaining_percent(payload)
        return {"checked_unix": start, "remaining_percent": remaining,
                "reserve_percent": RESERVE, "allow_model_work": remaining > RESERVE,
                "reason": "above_reserve" if remaining > RESERVE else "user_subscription_reserve",
                "quota": payload}
    except Exception as exc:
        return {"checked_unix": start, "remaining_percent": None,
                "reserve_percent": RESERVE, "allow_model_work": False,
                "reason": "quota_unavailable", "error_type": type(exc).__name__}


def watch(executable: Path, root: Path, out: Path, interval: float) -> None:
    out.mkdir(parents=True, exist_ok=True)
    lock = out / "watch.lock"
    with lock.open("x", encoding="utf-8") as handle:
        json.dump({"pid": os.getpid(), "created": psutil.Process().create_time()}, handle)
    try:
        while True:
            started = time.monotonic()
            latch = out / "PAUSED.json"
            if latch.exists():
                pause = json.loads(latch.read_text(encoding="utf-8"))
                enforcement = stop_study_generators(root)
                if enforcement["stopped"] or enforcement["errors"]:
                    save(out / "stops" / f"{time.time_ns()}.json", enforcement)
                save(out / "status.json", {"state": "paused", "pid": os.getpid(),
                    "checked_unix": time.time(), "reason": pause["reason"]})
                time.sleep(2)
                continue
            check = snapshot(executable, root)
            save(out / "checks" / f"{time.time_ns()}.json", check)
            save(out / "latest.json", check)
            if not check["allow_model_work"]:
                save(latch, {**check, "policy": "User-authorized recovery required; no automatic reset or resume."})
                print(json.dumps({"state": "pausing", "reason": check["reason"],
                                  "remaining_percent": check["remaining_percent"]}), flush=True)
                continue
            save(out / "status.json", {"state": "watching", "pid": os.getpid(),
                "checked_unix": check["checked_unix"], "remaining_percent": check["remaining_percent"]})
            print(json.dumps({"state": "watching", "remaining_percent": check["remaining_percent"]}), flush=True)
            time.sleep(max(0, interval - (time.monotonic() - started)))
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "watch", "inventory"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()
    root = args.root.resolve()
    out = (args.out or root / "reproducibility/runs/subscription_guard").resolve()
    if args.command == "inventory":
        print(json.dumps([{"pid": p.pid, "command": p.cmdline()} for p in psutil.process_iter()
                          if is_study_dispatcher(p, root)]))
        return 0
    if args.command == "check" and (out / "PAUSED.json").exists():
        print(json.dumps({"allow_model_work": False, "reason": "latched_user_pause"}))
        return 3
    provenance = root / "reproducibility/runs/scale1000-luna-v1/generation/runtime_provenance.json"
    executable = args.executable or Path(json.loads(provenance.read_text(encoding="utf-8"))["native_executable_path"])
    if args.command == "check":
        result = snapshot(executable.resolve(strict=True), root)
        print(json.dumps(result))
        return 0 if result["allow_model_work"] else 3
    if not 1 <= args.interval <= 60:
        parser.error("Watch interval must be between 1 and 60 seconds")
    watch(executable.resolve(strict=True), root, out, args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
