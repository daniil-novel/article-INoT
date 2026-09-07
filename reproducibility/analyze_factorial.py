"""Task-cluster analysis of independently evaluated outcomes; never scores model prose."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta

ARMS = ("single_neutral", "single_roles", "multi_neutral", "multi_roles")
CONTRASTS = {"roles_single": [-1,1,0,0], "roles_multi": [0,0,-1,1],
             "topology_neutral": [1,0,-1,0], "topology_roles": [0,1,0,-1],
             "interaction": [-1,1,1,-1]}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_outcomes(path: Path, expected: list[dict]) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    keys = [(r["task_id"],r["arm"],r["seed"]) for r in rows]
    required = {(r["task_id"],r["arm"],r["seed"]) for r in expected}
    if len(keys) != len(set(keys)) or set(keys) != required:
        raise ValueError("Outcomes must cover exactly the frozen task/arm/seed matrix, including missing outcomes")
    if len({r['model'] for r in rows}) != 1:
        raise ValueError('Analyze each model separately')
    for row in rows:
        if row["resolved"] is not None and type(row["resolved"]) is not bool:
            raise ValueError("Resolved must be boolean or null, not a model score")
        if row["resolved"] is not None:
            report = Path(row["report_path"])
            if not report.is_absolute(): report = path.parent/report
            if sha(report) != row["report_sha256"]:
                raise ValueError("Official report is absent or changed")
            if row["evaluator"] not in ("bigcodebench", "swebench"):
                raise ValueError("Unsupported evaluator; surrogate checks are not official outcomes")
        cost = row["cost_usd"]
        if type(cost) not in (int,float) or not math.isfinite(cost) or cost < 0:
            raise ValueError("Cost must be finite, nonnegative and reconciled")
    return rows


def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    adjusted = np.empty(len(order));maximum = 0.0
    for rank,i in enumerate(order):
        maximum = max(maximum,(len(order)-rank)*pvalues[i])
        adjusted[i] = min(1.0,maximum)
    return adjusted.tolist()


def analyze(rows: list[dict], draws: int = 10000, seed: int = 20260908) -> dict:
    tasks = sorted({r["task_id"] for r in rows});seeds = sorted({r["seed"] for r in rows})
    lookup = {(r['task_id'],r['arm'],r['seed']):r for r in rows}
    q = np.full((len(tasks),4,len(seeds)),np.nan)
    cost = np.zeros_like(q)
    for i,task in enumerate(tasks):
        for j,arm in enumerate(ARMS):
            for k,s in enumerate(seeds):
                r = lookup[(task,arm,s)]
                if r['resolved'] is not None:q[i,j,k] = r['resolved']
                cost[i,j,k] = r['cost_usd']
    complete = np.isfinite(q).all(axis=(1,2))
    n = int(complete.sum())
    low, high = np.nan_to_num(q,nan=0).mean((0,2)),np.nan_to_num(q,nan=1).mean((0,2))
    result = {"assigned_tasks":len(tasks),"seeds":seeds,"complete_tasks":n,
              "missing_outcomes":int(np.isnan(q).sum()),"cell_quality_bounds":{a:[float(low[j]),float(high[j])] for j,a in enumerate(ARMS)},
              "status":"incomplete" if n < len(tasks) else "complete",
              "inference":"Task-cluster percentile bootstrap and paired sign-flip sensitivity; no population sampling guarantee",
              "draws":draws,"random_seed":seed,"contrasts":{}}
    if n < 2:return result
    y = q[complete].mean(2);c = cost[complete].mean(2)
    rng = np.random.default_rng(seed)
    # All treatment contrasts share the same task resamples.
    boot = np.empty((draws,4));cost_boot = np.empty((draws,4))
    signed = np.empty((draws,5))
    matrix = np.array(list(CONTRASTS.values()),dtype=float).T
    per_task = y@matrix
    for b in range(draws):
        indices = rng.integers(0,n,n)
        boot[b] = y[indices].mean(0);cost_boot[b] = c[indices].mean(0)
        signed[b] = (per_task*rng.choice([-1,1],size=(n,1))).mean(0)
    pvals=[]
    for j,(name,w) in enumerate(CONTRASTS.items()):
        estimate=float((y@w).mean());distribution=boot@w
        p=float((1+(np.abs(signed[:,j])>=abs(estimate)-1e-14).sum())/(draws+1))
        pvals.append(p)
        result['contrasts'][name]={"quality_difference":estimate,"quality_ci95":np.quantile(distribution,[.025,.975]).tolist(),
                                   "cost_difference_usd":float((c@w).mean()),"cost_ci95":np.quantile(cost_boot@w,[.025,.975]).tolist(),
                                   "sign_flip_p":p,"quality_missing_bounds":[float(low@np.maximum(w,0)+high@np.minimum(w,0)),float(high@np.maximum(w,0)+low@np.minimum(w,0))]}
    for name,adjusted in zip(CONTRASTS,holm(pvals)):result['contrasts'][name]['holm_p']=adjusted
    # Conservative independent-task bound on the prespecified first seed.
    a,b=q[complete,1,0],q[complete,3,0]
    harm=int(((a==0)&(b==1)).sum());benefit=int(((a==1)&(b==0)).sum())
    benefit_lower=0.0 if benefit==0 else float(beta.ppf(.0125,benefit,n-benefit+1))
    harm_upper=1.0 if harm==n else float(beta.ppf(.9875,harm+1,n-harm))
    conservative_lower=benefit_lower-harm_upper
    boot_lower=result['contrasts']['topology_roles']['quality_ci95'][0]
    result['quality_preservation']={"margin":.02,"first_seed":seeds[0],"harmful_pairs":harm,"beneficial_pairs":benefit,
                                    "first_seed_conservative_lower97_5":conservative_lower,
                                    "seed_mean_bootstrap_lower97_5":boot_lower,
                                    "decision":"supported_by_both_bounds" if n==len(tasks) and conservative_lower>-.02 and boot_lower>-.02 else "inconclusive",
                                    "scope":"Conservative gate also requires the fixed first seed; not an exact interval for the multi-seed mean"}
    result['cells']={a:{"mean_single_attempt_success":float(y[:,j].mean()),"mean_usd":float(cost[:,j,:].mean()),
                        "cost_per_resolved_task":float(c[:,j].sum()/y[:,j].sum()) if n==len(tasks) and y[:,j].sum()>0 else None} for j,a in enumerate(ARMS)}
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outcomes',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--draws',type=int,default=10000)
    args=p.parse_args()
    if args.draws<1000:raise ValueError('At least 1000 resamples required')
    m=json.loads(args.manifest.read_text());rows=load_outcomes(args.outcomes,m['cells'])
    result=analyze(rows,args.draws)
    result['source_hashes']={'outcomes':sha(args.outcomes),'manifest':sha(args.manifest),'analysis':sha(Path(__file__))}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'complete_tasks':result['complete_tasks'],'assigned_tasks':result['assigned_tasks']}))


if __name__=='__main__':main()
