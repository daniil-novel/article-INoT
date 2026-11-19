"""Validate recorded completions and report task-paired descriptive estimates."""
import argparse
import ast
import hashlib
import json
import statistics
from pathlib import Path

from run import HERE, PROTOCOL, TASKS, grade, schedule


def allow_guard_clause(task, reply):
    """Secondary check: treat a guard return followed by a return as one conditional."""
    baseline = grade(task, reply)
    if baseline.get("reason") != "ValueError: expected one return expression":
        return baseline
    module = ast.parse(reply.strip())
    function = module.body[0]
    if len(function.body) != 2:
        return baseline
    guard, tail = function.body
    if not (isinstance(guard, ast.If) and not guard.orelse and len(guard.body) == 1
            and isinstance(guard.body[0], ast.Return) and isinstance(tail, ast.Return)):
        return baseline
    conditional = ast.IfExp(test=guard.test, body=guard.body[0].value, orelse=tail.value)
    function.body = [ast.Return(value=conditional)]
    return grade(task, ast.unparse(ast.fix_missing_locations(module)))


def summarize(folder):
    records = [json.loads(line) for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["sha256"].items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Protocol or implementation differs from the recorded version: " + name)
    if [[r["id"], r["arm"]] for r in records] != manifest["schedule"]:
        raise ValueError("Incomplete or reordered ledger")
    by_task = {t[0]:t for t in TASKS}
    assert manifest["schedule"] == [[t[0],a] for t,a in schedule()]
    for r in records:
        assert r["status"] == "complete" and r["wall_s"] > 0
        assert r["grade"] == json.loads(json.dumps(grade(by_task[r["id"]],r["calls"][-1]["reply"])))
        expected_multi = r["arm"] in ("MAS","MN") or (r["arm"]=="RouteMode" and r["id"] in PROTOCOL["separate_session_task_ids"]+PROTOCOL["parallel_task_ids"])
        assert len(r["calls"]) == (3 if expected_multi else 1)
        for c in r["calls"]:
            assert c["model"]==PROTOCOL["model"] and c["prompt_eval_count"]>0 and c["eval_count"]>0
    summary = {}
    for arm in PROTOCOL["arms"]:
        rr = [r for r in records if r["arm"]==arm]
        inputs = sum(c["prompt_eval_count"] for r in rr for c in r["calls"])
        outputs = sum(c["eval_count"] for r in rr for c in r["calls"])
        passed = sum(r["grade"]["pass"] for r in rr)
        cost = (0.20*inputs+1.20*outputs)/1_000_000
        times = [r["wall_s"] for r in rr]
        behavior = sum(allow_guard_clause(by_task[r["id"]],r["calls"][-1]["reply"])["pass"] for r in rr)
        summary[arm] = {"n":len(rr),"successes":passed,"successes_allowing_guard_return":behavior,
                        "calls":sum(len(r["calls"]) for r in rr),
                        "input":inputs,"output":outputs,"tokens_per_run":(inputs+outputs)/len(rr),
                        "reference_usd_per_1000_runs":1000*cost/len(rr),"total_reference_usd":cost,
                        "mean_wall_s":statistics.mean(times),"median_wall_s":statistics.median(times)}
    pairs = {}
    for a,b in (("RouteMode","SR"),("RouteMode","MAS"),("SR","SN"),("MAS","MN")):
        wins, losses, ties = [], [], []
        for tid in by_task:
            by_arm = {r["arm"]:r["grade"]["pass"] for r in records if r["id"]==tid}
            (wins if by_arm[a]>by_arm[b] else losses if by_arm[a]<by_arm[b] else ties).append(tid)
        pairs[a+"-"+b] = {"wins":wins,"losses":losses,"ties":len(ties)}
    return {"per_arm":summary,"paired":pairs,
            "record_sha256":hashlib.sha256((folder/"runs.jsonl").read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path,nargs="?",default=HERE/"recorded")
    args=parser.parse_args()
    print(json.dumps(summarize(args.directory),ensure_ascii=False,indent=2))
