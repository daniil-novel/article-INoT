"""Frozen compression-free generation; official evaluation is a separate process."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time
import urllib.error
import urllib.request

ARMS = ("single_neutral", "single_roles", "multi_neutral", "multi_roles")
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
HARD_LIMIT = 300.0
STEPS = ("Analyze requirements and produce an implementation plan, including edge cases.",
         "Implement the requested program or repository change using the plan.",
         "Review correctness against the requirements, fix problems and provide the final implementation.")
FINAL = ("Return the complete final program in exactly one fenced python block, or, for a repository "
         "repair task, the complete unified diff in exactly one fenced diff block. "
         "Do not output other fenced blocks in this final answer. No test results are available.")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(canonical(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value, name: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"Invalid {name}")
    return float(value)


def config_from(path: Path) -> dict:
    c = read(path)
    required = {"model", "provider", "seeds", "arms", "temperature", "max_completion_tokens_total",
                "max_cost_usd", "input_usd_per_million", "output_usd_per_million",
                "max_context_tokens", "prompt_tokens_upper_bound"}
    if set(c) != required:
        raise ValueError(f"Config fields differ from schema: {set(c) ^ required}")
    if not isinstance(c["model"], str) or not c["model"].strip() or not isinstance(c["provider"], str):
        raise ValueError("Model and provider must be strings")
    for key in ("seeds", "arms"):
        if not isinstance(c[key], list) or not c[key] or len(c[key]) != len(set(c[key])):
            raise ValueError(f"Empty or duplicate {key}")
    if any(type(s) is not int for s in c["seeds"]) or not set(c["arms"]).issubset(ARMS):
        raise ValueError("Invalid seed or arm")
    for key in ("max_completion_tokens_total", "max_context_tokens", "prompt_tokens_upper_bound"):
        if type(c[key]) is not int or c[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if c["max_completion_tokens_total"] % 3:
        raise ValueError("Completion allowance must be divisible by three")
    for key in ("max_cost_usd", "input_usd_per_million", "output_usd_per_million", "temperature"):
        finite(c[key], key, positive=key == "max_cost_usd")
    if c["max_cost_usd"] > HARD_LIMIT:
        raise ValueError("Campaign hard limit is USD 300")
    return c


def tasks_from(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen = set()
    for t in rows:
        if set(t) != {"task_id", "prompt", "context", "benchmark", "metadata"}:
            raise ValueError("Task schema excludes reference solutions and tests")
        for key in ("task_id", "prompt", "context", "benchmark"):
            if not isinstance(t[key], str) or (key != "context" and not t[key].strip()):
                raise ValueError(f"Invalid task {key}")
        if t["task_id"] in seen or not isinstance(t["metadata"], dict):
            raise ValueError("Duplicate task or invalid metadata")
        seen.add(t["task_id"])
    if not rows:
        raise ValueError("Empty task dataset")
    return sorted(rows, key=lambda t: t["task_id"])


def build_manifest(c: dict, tasks: list[dict]) -> dict:
    rng = random.Random(20260908)
    blocks = [(t["task_id"], seed) for t in tasks for seed in c["seeds"]]
    rng.shuffle(blocks)
    cells = []
    for task_id, seed in blocks:
        arms = c["arms"].copy()
        rng.shuffle(arms)
        for arm in arms:
            cell = {"task_id": task_id, "seed": seed, "arm": arm}
            cells.append({**cell, "id": digest(cell)[:24], "calls": 1 if arm.startswith("single") else 3})
    calls = sum(cell["calls"] for cell in cells)
    worst = (calls*c["prompt_tokens_upper_bound"]*c["input_usd_per_million"]
             + len(cells)*c["max_completion_tokens_total"]*c["output_usd_per_million"])/1e6
    manifest = {"schema": 1, "source_sha256": file_hash(Path(__file__)), "config_sha256": digest(c),
                "tasks_sha256": digest(tasks), "cells": cells, "generation_count": len(cells),
                "call_count": calls, "worst_case_usd": worst, "randomization_seed": 20260908}
    return {**manifest, "manifest_sha256": digest(manifest)}


def payload(c: dict, task: dict, cell: dict, stage: int, history: list[str]) -> dict:
    roles = ["planner", "implementer", "reviewer"] if cell["arm"].endswith("roles") else ["stage 1", "stage 2", "stage 3"]
    single = cell["calls"] == 1
    instructions = [f"{roles[i]}: {STEPS[i]}" for i in (range(3) if single else [stage])]
    system = "Solve the supplied programming task.\n" + "\n".join(instructions)
    if single or stage == 2:
        system += "\n" + FINAL
    user = "TASK\n" + task["prompt"] + "\nFULL SUPPLIED CONTEXT\n" + task["context"]
    for i, output in enumerate(history):
        user += f"\nPREVIOUS STAGE {i+1} (COMPLETE OUTPUT)\n" + output
    return {"model": c["model"], "seed": cell["seed"], "temperature": c["temperature"],
            "max_tokens": c["max_completion_tokens_total"] // cell["calls"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "provider": {"order": [c["provider"]], "allow_fallbacks": False, "require_parameters": True,
                         "max_price": {"prompt": c["input_usd_per_million"], "completion": c["output_usd_per_million"], "request": 0}}}


def envelope(c: dict, request: dict) -> float:
    # Conservative byte-level bound, not an estimate of actual provider tokens.
    bound = sum(len(m["content"].encode("utf-8"))+128 for m in request["messages"]) + 256
    if bound > c["prompt_tokens_upper_bound"] or bound + request["max_tokens"] > c["max_context_tokens"]:
        raise ValueError("Full input exceeds conservative bounds; input was not shortened")
    return (bound*c["input_usd_per_million"] + request["max_tokens"]*c["output_usd_per_million"])/1e6


def transport(request: dict, key: str) -> dict:
    req = urllib.request.Request(ENDPOINT, data=canonical(request),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            status, raw = response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode("utf-8", errors="replace")
    return {"status": status, "body": raw, "started_unix": start, "latency_seconds": time.time()-start}


@contextmanager
def ledger_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def checked_manifest(manifest: dict, c: dict, tasks: list[dict]) -> None:
    if manifest != build_manifest(c, tasks):
        raise ValueError("Frozen manifest differs from current task/config/source bytes")


def audit(root: Path, require_complete: bool = True) -> dict:
    errors = []
    try:
        m, c, tasks = read(root/"manifest.json"), read(root/"config.json"), read(root/"tasks.json")
        index = read(root/"index.json")
        checked_manifest(m, c, tasks)
        expected = {f"{cell['id']}-{stage}": (cell, stage) for cell in m["cells"] for stage in range(cell["calls"])}
        if require_complete and set(index) != set(expected):
            errors.append("Incomplete expected call matrix")
        for call_id, record in index.items():
            if call_id not in expected:
                raise ValueError("Unexpected call")
            cell, stage = expected[call_id]
            for name, sha in record["files"].items():
                if Path(name).name != name or file_hash(root/"calls"/name) != sha:
                    raise ValueError(f"Artifact hash mismatch: {name}")
            response = read(root/"calls"/(call_id+".response.json"))
            raw = read(root/"calls"/(call_id+".transport.json"))
            if response != json.loads(raw["body"]):
                raise ValueError("Response differs from original transport body")
            if record["cost_usd"] != finite(response["usage"]["cost"], "cost"):
                raise ValueError("Recorded cost differs from response")
            history = [read(root/"calls"/f"{cell['id']}-{j}.response.json")["choices"][0]["message"]["content"] for j in range(stage)]
            actual = read(root/"calls"/(call_id+".request.json"))
            if actual != payload(c, next(t for t in tasks if t["task_id"]==cell["task_id"]), cell, stage, history):
                raise ValueError("Request differs from frozen treatment")
        status = read(root/"status.json")["status"]
        if require_complete and status != "completed":
            errors.append("Run status is not completed")
        if status == "blocked_unknown_charge":
            errors.append("Unreconciled request charge")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors}


def export_results(root: Path, m: dict, c: dict, index: dict) -> None:
    rows = []
    for cell in m["cells"]:
        ids = [f"{cell['id']}-{stage}" for stage in range(cell["calls"])]
        if not all(i in index for i in ids):
            continue
        responses = [read(root/"calls"/(i+".response.json")) for i in ids]
        rows.append({"task_id": cell["task_id"], "arm": cell["arm"], "seed": cell["seed"], "model": c["model"],
                     "final_text": responses[-1]["choices"][0]["message"]["content"],
                     "truncated": any(r["choices"][0].get("finish_reason")=="length" for r in responses),
                     "cost_usd": sum(index[i]["cost_usd"] for i in ids), "call_count": len(ids),
                     "total_tokens": sum(r["usage"]["total_tokens"] for r in responses)})
    temporary = root/"results.jsonl.tmp"
    temporary.write_bytes(b"".join(canonical(row)+b"\n" for row in rows))
    os.replace(temporary, root/"results.jsonl")


def run(config_path: Path, tasks_path: Path, manifest_path: Path, root: Path,
        ledger_path: Path, budget_usd: float, *, send=transport) -> dict:
    c, tasks, m = config_from(config_path), tasks_from(tasks_path), read(manifest_path)
    checked_manifest(m, c, tasks)
    finite(budget_usd, "attempt budget", positive=True)
    if budget_usd > c["max_cost_usd"] or budget_usd > HARD_LIMIT or not c["provider"].strip():
        raise ValueError("Budget out of bounds or provider not pinned")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY missing")
    with ledger_lock(ledger_path):
        ledger = read(ledger_path) if ledger_path.exists() else {"limit_usd":HARD_LIMIT,"spent_usd":0.0,"pending":{}}
        finite(ledger["spent_usd"], "ledger spend")
        if ledger["limit_usd"] != HARD_LIMIT or ledger["pending"]:
            raise ValueError("Ledger invalid or unknown charge needs reconciliation; no retry")
        if root.exists():
            if read(root/"manifest.json") != m:
                raise ValueError("Resume manifest mismatch")
            check = audit(root, require_complete=False)
            if not check["ok"]:
                raise ValueError(str(check["errors"]))
            index = read(root/"index.json")
            if read(root/"campaign.json")["ledger_path"] != str(ledger_path.resolve()):
                raise ValueError("Cannot switch budget ledger on resume")
        else:
            root.mkdir(parents=True)
            for name,value in [("manifest",m),("config",c),("tasks",tasks),("index",{}),
                               ("campaign",{"ledger_path":str(ledger_path.resolve())}),("status",{"status":"prepared"})]:
                save(root/(name+".json"),value)
            index = {}
        task_index = {t["task_id"]:t for t in tasks}
        status = "running"
        for cell in m["cells"]:
            history = []
            for stage in range(cell["calls"]):
                call_id = f"{cell['id']}-{stage}"
                prefix = root/"calls"/call_id
                if call_id in index:
                    history.append(read(prefix.with_suffix(".response.json"))["choices"][0]["message"]["content"])
                    continue
                if prefix.with_suffix(".request.json").exists():
                    raise ValueError("Pending request exists; reconcile before resume")
                request = payload(c,task_index[cell["task_id"]],cell,stage,history)
                reserve = envelope(c,request)
                if sum(r["cost_usd"] for r in index.values())+reserve > budget_usd or ledger["spent_usd"]+reserve > HARD_LIMIT:
                    status = "blocked_budget"
                    break
                save(prefix.with_suffix(".request.json"),request)
                ledger_id = str(prefix.resolve())
                ledger["pending"][ledger_id] = reserve
                save(ledger_path,ledger)
                save(root/"status.json",{"status":"pending","call_id":call_id})
                try:
                    raw = send(request,key)
                    raw["body"] = raw["body"].replace(key,"[REDACTED_CREDENTIAL]")
                    save(prefix.with_suffix(".transport.json"),raw)
                    response = json.loads(raw["body"])
                    save(prefix.with_suffix(".response.json"),response)
                    if raw["status"] != 200:
                        raise ValueError(f"HTTP {raw['status']}")
                    cost = finite(response["usage"]["cost"],"response cost")
                    content = response["choices"][0]["message"]["content"]
                    if not isinstance(content,str):
                        raise ValueError("Missing assistant content")
                    for counter in ("prompt_tokens","completion_tokens","total_tokens"):
                        if type(response["usage"][counter]) is not int or response["usage"][counter] < 0:
                            raise ValueError("Missing or invalid token accounting")
                    if response["usage"]["total_tokens"] != response["usage"]["prompt_tokens"]+response["usage"]["completion_tokens"]:
                        raise ValueError("Token total mismatch")
                except Exception as exc:
                    status = "blocked_unknown_charge"
                    save(prefix.with_suffix(".error.json"),{"error":str(exc).replace(key,"[REDACTED_CREDENTIAL]"),"type":type(exc).__name__})
                    break
                files = [prefix.with_suffix(suffix) for suffix in (".request.json",".transport.json",".response.json")]
                index[call_id] = {"cost_usd":cost,"files":{p.name:file_hash(p) for p in files}}
                save(root/"index.json",index)
                ledger["spent_usd"] += cost
                del ledger["pending"][ledger_id]
                save(ledger_path,ledger)
                history.append(content)
                if cost > reserve+1e-10 or response["usage"]["completion_tokens"] > request["max_tokens"]:
                    status = "blocked_provider_envelope_violation"
                    break
            if status.startswith("blocked"):
                break
        if status == "running":
            status = "completed"
        save(root/"status.json",{"status":status,"completed_calls":len(index),"expected_calls":m["call_count"]})
        export_results(root,m,c,index)
        return {"status":status,"completed_calls":len(index),"expected_calls":m["call_count"],
                "campaign_spent_usd":ledger["spent_usd"],"unknown_reserve_usd":sum(ledger["pending"].values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("plan")
    for flag in ("config","tasks","out"):
        p.add_argument("--"+flag,type=Path,required=True)
    r = sub.add_parser("run")
    for flag in ("config","tasks","manifest","archive","budget-ledger"):
        r.add_argument("--"+flag,type=Path,required=True)
    r.add_argument("--budget-usd",type=float,required=True)
    a = sub.add_parser("audit");a.add_argument("--archive",type=Path,required=True)
    args = parser.parse_args()
    if args.command == "plan":
        m=build_manifest(config_from(args.config),tasks_from(args.tasks));save(args.out,m)
        print(json.dumps({k:v for k,v in m.items() if k!="cells"},indent=2))
    elif args.command == "run":
        result=run(args.config,args.tasks,args.manifest,args.archive,args.budget_ledger,args.budget_usd)
        print(json.dumps(result,indent=2));return 0 if result["status"]=="completed" else 2
    else:
        result=audit(args.archive);print(json.dumps(result,indent=2));return 0 if result["ok"] else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
