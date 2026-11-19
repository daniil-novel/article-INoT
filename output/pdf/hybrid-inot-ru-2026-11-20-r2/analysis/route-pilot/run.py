"""Run the frozen local study. Results go in a new directory supplied as an argument."""
import argparse
import ast
import hashlib
import itertools
import json
import math
import platform
import random
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = "http://127.0.0.1:11434"
PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
TASKS = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
           ast.Name, ast.Load, ast.Constant, ast.Call, ast.Add, ast.Sub, ast.Mult,
           ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
           ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
FUNCTIONS = {"min": min, "max": max, "abs": abs, "int": int}
STEPS = ["Plan a solution and consider boundary cases.",
         "Implement the specified Python function.",
         "Review the implementation and correct any mistakes."]
CONTRACT = ("Return Python code for def solve({args}) with just one return expression. "
            "Use only integer literals, the named inputs, arithmetic (+, -, *, /, //, %), "
            "comparisons, booleans, conditional expressions, min, max, abs or int. "
            "Do not import modules or define other functions.")


def ceildiv(x, y):
    whole, remainder = divmod(x, y)
    return whole + int(bool(remainder))


def expected(kind, values):
    x, y, *more = values
    if kind == "pages":
        return ceildiv(x, y)
    if kind == "offset":
        return sum(y for _ in range(1, x))
    if kind == "index":
        return list(range(y))[x] if -y <= x < y else -1
    if kind == "delay":
        return 0 if x < 1 else min(y, sum(3 for _ in range(x)))
    if kind == "overlap":
        return len(set(range(x, y)).intersection(range(*more)))
    if kind == "blocks":
        return len(range(y, x, 15))
    z = more[0] if more else None
    if kind == "packs":
        return len(range(y, x, z))
    if kind == "slot":
        return next(t for t in range(x+1, x+y+1) if t % y == 0)
    if kind == "minutes":
        return math.trunc((x-y)/60)
    if kind == "ring":
        return divmod(x+y, z)[1] if z > 0 else -1
    if kind == "range":
        return x-1 if y <= 0 else min(range(x, x+y)[-1], z)
    if kind == "allowance":
        return 0 if x <= y else max(5, sum(z for _ in range(y, x)))
    raise ValueError(kind)


def expression(reply, names):
    fences = re.findall(r"\x60\x60\x60(?:python|py)?\s*\n(.*?)\x60\x60\x60", reply, re.I | re.S)
    source = (fences[-1] if fences else reply).strip()
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("expected a single function")
    f = tree.body[0]
    if (f.name != "solve" or [a.arg for a in f.args.args] != names or
        f.decorator_list or f.args.defaults or f.args.kwonlyargs or f.args.posonlyargs or
        f.args.vararg or f.args.kwarg):
        raise ValueError("signature")
    body = f.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
        raise ValueError("expected one return expression")
    expr = ast.Expression(body[0].value)
    valid_names = set(names) | set(FUNCTIONS)
    nodes = list(ast.walk(expr))
    if len(nodes) > 120:
        raise ValueError("expression size")
    for node in nodes:
        if not isinstance(node, ALLOWED):
            raise ValueError("operator outside contract")
        if isinstance(node, ast.Name) and node.id not in valid_names:
            raise ValueError("unknown identifier")
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, bool) or abs(node.value) > 100000):
            raise ValueError("literal outside contract")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords):
            raise ValueError("call outside contract")
    return compile(expr, "<integer expression>", "eval")


def grade(task, reply):
    _, args, _, kind, grid = task
    names = args.split(", ")
    n = math.prod(map(len, grid))
    try:
        code = expression(reply, names)
        for values in itertools.product(*grid):
            result = eval(code, {"__builtins__": {}, **FUNCTIONS}, dict(zip(names, values)))
            if type(result) is not int or result != expected(kind, values):
                return {"pass": 0, "case_count": n, "reason": "wrong value or type", "first_input": values}
        return {"pass": 1, "case_count": n}
    except (ArithmeticError, SyntaxError, ValueError, TypeError) as exc:
        return {"pass": 0, "case_count": n, "reason": type(exc).__name__ + ": " + str(exc)[:120]}


def api(route, payload=None):
    req = urllib.request.Request(HOST + route, None if payload is None else json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as response:
        return json.load(response)


def generate(prompt, limit):
    opts = dict(PROTOCOL["options"], num_predict=limit)
    response = api("/api/chat", {"model": PROTOCOL["model"], "messages": [{"role":"user","content":prompt}],
                                 "stream":False, "keep_alive":"30m", "options":opts})
    return {"prompt": prompt, "reply": response["message"]["content"],
            **{k:response.get(k) for k in ("model","done_reason","prompt_eval_count","eval_count",
                                           "total_duration","load_duration","prompt_eval_duration","eval_duration")}}


def dispatch(task, arm):
    start = time.perf_counter()
    tid, args, spec, _, _ = task
    separate = tid in PROTOCOL["separate_session_task_ids"]
    parallel = tid in PROTOCOL["parallel_task_ids"]
    multi = arm in ("MAS","MN") or (arm == "RouteMode" and (separate or parallel))
    labels = ["STAGE 1","STAGE 2","STAGE 3"] if arm in ("SN","MN") else ["PLANNER","IMPLEMENTER","REVIEWER"]
    steps = [label + ": " + step for label, step in zip(labels, STEPS)]
    context = "Task: " + spec + "\n" + CONTRACT.format(args=args)
    limit = PROTOCOL["options"]["num_predict"]
    calls = []
    try:
        if multi:
            calls.append(generate(context+"\n"+steps[0]+"\nOutput one short sentence only.", PROTOCOL["plan_limit"]))
            plan = calls[0]["reply"]
            calls.append(generate(context+"\nPlan:\n"+plan+"\n"+steps[1]+"\nOutput the function only.", limit))
            calls.append(generate(context+"\nPlan:\n"+plan+"\nDraft:\n"+calls[1]["reply"]+"\n"+steps[2]+"\nOutput the final function only.", limit))
        else:
            calls.append(generate(context+"\n"+"\n".join(steps)+"\nOutput the final function only.", limit))
        score = grade(task, calls[-1]["reply"])
        status = "complete"
    except (OSError, TimeoutError) as exc:
        score, status = {"pass":None,"error":str(exc)}, "service_error"
    elapsed = time.perf_counter()-start
    return {"id":tid,"arm":arm,"branch":"multi" if multi else "single","separate":separate,
            "parallel":parallel,"status":status,"wall_s":elapsed,"calls":calls,"grade":score}


def schedule():
    rng = random.Random(38521)
    task_seq = list(TASKS)
    rng.shuffle(task_seq)
    arms = list(PROTOCOL["arms"])
    rng.shuffle(arms)
    return [(task, arms[(i+j)%len(arms)]) for i,task in enumerate(task_seq) for j in range(len(arms))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=False)
    plan = schedule()
    info = {"start_utc":datetime.now(timezone.utc).isoformat(),"platform":platform.platform(),
            "ollama":api("/api/version"),"model":next(m for m in api("/api/tags")["models"] if m["name"]==PROTOCOL["model"]),
            "sha256":{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ("protocol.json","tasks.json","run.py")},
            "schedule":[[t[0],a] for t,a in plan]}
    (out/"manifest.json").write_text(json.dumps(info, indent=2),encoding="utf-8")
    generate("Reply with the single word ready.",8)
    with (out/"runs.jsonl").open("x",encoding="utf-8") as log:
        for task, arm in plan:
            record = dispatch(task,arm)
            log.write(json.dumps(record,ensure_ascii=True)+"\n")
            log.flush()
    (out/"finished.txt").write_text(datetime.now(timezone.utc).isoformat(),encoding="utf-8")


if __name__ == "__main__":
    main()
