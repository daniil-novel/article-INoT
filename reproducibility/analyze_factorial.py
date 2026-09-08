"""Legacy exploratory API analysis; not the published held-out inference procedure.

The executed primary study uses heldout200.analyze.summarize. This legacy
module reports descriptive intervals and explicitly labelled sign-flip
sensitivity only; it cannot certify quality preservation or monetary superiority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ARMS = ("single_neutral", "single_roles", "multi_neutral", "multi_roles")
CONTRASTS = {"roles_single": [-1,1,0,0], "roles_multi": [0,0,-1,1],
             "topology_neutral": [1,0,-1,0], "topology_roles": [0,1,0,-1],
             "interaction": [-1,1,1,-1]}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_candidate_failure(row: dict, outcomes_path: Path) -> None:
    """Validate a SWE candidate failure that legitimately has no report.json."""
    try:
        from .benchmark_bridge import _extract_fenced_block
    except ImportError:
        from benchmark_bridge import _extract_fenced_block

    def evidence(kind):
        p = Path(row[kind+'_path'])
        if not p.is_absolute():p = outcomes_path.parent/p
        if sha(p) != row[kind+'_sha256']:
            raise ValueError('Candidate failure evidence changed: '+kind)
        return p

    if row['evaluator'] != 'swebench' or row['resolved'] is not False:
        raise ValueError('Only explicit failed SWE candidates may lack a native report')
    generations = [json.loads(line) for line in evidence('generation').read_text(encoding='utf-8').splitlines() if line.strip()]
    matched = [g for g in generations if (g['task_id'],g['arm'],g['seed'],g['model']) ==
               (row['task_id'],row['arm'],row['seed'],row['model'])]
    if len(matched) != 1 or not isinstance(matched[0].get('final_text'),str):
        raise ValueError('Candidate failure lacks an exact observed response')
    expected, _ = _extract_fenced_block(matched[0]['final_text'],'swebench')
    predictions = [json.loads(line) for line in evidence('prediction').read_text(encoding='utf-8').splitlines() if line.strip()]
    matched = [p for p in predictions if p.get('instance_id')==row['task_id'] and p.get('model_name_or_path')==row['model']]
    if len(matched) != 1 or matched[0].get('model_patch') != expected:
        raise ValueError('Candidate failure prediction differs from the observed response')
    summary = json.loads(evidence('run_results').read_text(encoding='utf-8')) if row.get('run_results_path') else {}
    if row['task_id'] in summary.get('infra_failure_ids',[]):
        raise ValueError('Infrastructure failure is not a candidate failure')
    if row.get('report_sha256'):
        report = json.loads(evidence('report').read_text(encoding='utf-8'))
        if report[row['task_id']].get('infra_failure'):
            raise ValueError('Infrastructure report cannot support a candidate failure')
    if row['outcome_type']=='candidate_invalid_patch':
        if expected != '':raise ValueError('Invalid-patch classification has a nonempty exported patch')
    else:
        if not expected or row['task_id'] not in summary.get('error_ids',[]):
            raise ValueError('Native application rejection lacks a matching error summary')
        actual=evidence('patch').read_text(encoding='utf-8')
        if actual.replace('\r\n','\n').rstrip('\n') != expected.replace('\r\n','\n').rstrip('\n'):
            raise ValueError('Rejected native patch differs from the observed response')
        if '>>>>> Patch Apply Failed' not in evidence('application_log').read_text(encoding='utf-8'):
            raise ValueError('Native application rejection lacks the upstream failure marker')


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
            if row["evaluator"] not in ("bigcodebench", "swebench"):
                raise ValueError("Unsupported evaluator; surrogate checks are not official outcomes")
            if row.get('outcome_type') in ('candidate_invalid_patch','native_application_rejection'):
                _verify_candidate_failure(row,path)
            else:
                report = Path(row["report_path"])
                if not report.is_absolute(): report = path.parent/report
                if sha(report) != row["report_sha256"]:
                    raise ValueError("Official report is absent or changed")
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
              "analysis_role":"legacy_exploratory_only",
              "primary_analysis_entrypoint":"reproducibility.heldout200.analyze.summarize",
              "inference":"Descriptive task-cluster intervals; Holm applies only to five sign-flip sensitivity contrasts, not to a primary test",
              "quality_preservation":{"margin":None,"decision":"not_assessed",
                                      "reason":"No externally justified quality-loss margin was registered for this legacy analysis"},
              "monetary_superiority":{"decision":"not_assessed",
                                      "reason":"Cost means and intervals are descriptive; no confirmatory economic decision rule was registered"},
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
    for name,adjusted in zip(CONTRASTS,holm(pvals)):
        result['contrasts'][name]['holm_sign_flip_sensitivity_p']=adjusted
    result['cells']={a:{"mean_single_attempt_success":float(y[:,j].mean()),"mean_usd":float(cost[:,j,:].mean()),
                        "cost_per_resolved_task":float(c[:,j].sum()/y[:,j].sum()) if n==len(tasks) and y[:,j].sum()>0 else None} for j,a in enumerate(ARMS)}
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy-exploratory',action='store_true',
                   help='Acknowledge that this is not the published primary analysis')
    p.add_argument('--outcomes',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--draws',type=int,default=10000)
    args=p.parse_args()
    if not args.legacy_exploratory:
        p.error('Use heldout200.assemble collect for the published primary study; this archived procedure requires --legacy-exploratory')
    if args.draws<1000:raise ValueError('At least 1000 resamples required')
    m=json.loads(args.manifest.read_text());rows=load_outcomes(args.outcomes,m['cells'])
    result=analyze(rows,args.draws)
    result['source_hashes']={'outcomes':sha(args.outcomes),'manifest':sha(args.manifest),'analysis':sha(Path(__file__))}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'complete_tasks':result['complete_tasks'],'assigned_tasks':result['assigned_tasks']}))


if __name__=='__main__':main()
