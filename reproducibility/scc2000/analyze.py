"""Bounded, offline analysis for the amended SCC-2000 comparison.

The module accepts already exported ledger rows and metadata.  It never imports
the continuation worker (or any model client); ``analyze`` is consequently
usable from a host Python installation and in synthetic tests.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import stats

METHODS = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")
SCC, SR, SN = METHODS[2], METHODS[0], METHODS[1]
REPLICATES = (101, 102, 103)
PRIMARY = ((SCC, SR), (SCC, SN))
QUALITY_SEED = 20260911
RESOURCE_DIFF_SEED = 20260912
RESOURCE_RATIO_SEED = 20260913
RESOURCE_ROM_SEED = 20260914
BOOTSTRAP_DRAWS = 10_000


def _canonical(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(x: Any) -> str:
    return hashlib.sha256(_canonical(x) if not isinstance(x, bytes) else x).hexdigest()


def _finite_number(x: Any) -> bool:
    return type(x) in (int, float) and not isinstance(x, bool) and math.isfinite(float(x))


def _quality(row: dict[str, Any]) -> bool | None:
    q = row.get("quality")
    if q is not None and type(q) is not bool:
        raise ValueError("quality must be boolean or null")
    if q is None and row.get("outcome_type") in {"format_failure", "model_format_failure"}:
        return False
    return q


def _cell_id(row: dict[str, Any]) -> str:
    for key in ("id", "cell_id", "assignment_id"):
        if row.get(key) is not None:
            return str(row[key])
    raise ValueError("record missing assignment id")


def _selected_ids(selection: dict[str, Any]) -> set[str]:
    ids = selection.get("selected_ids")
    if not isinstance(ids, list) or len(ids) != 6000 or len(set(map(str, ids))) != 6000:
        raise ValueError("selection must contain exactly 6000 unique selected_ids")
    return set(map(str, ids))


def _resource(row: dict[str, Any]) -> tuple[float, float] | None:
    """Return (tokens, USD) only for a complete priced workflow."""
    u = row.get("resource_usage") if isinstance(row.get("resource_usage"), dict) else {}
    if not u: return None
    turns, known, unknown = (u.get(k) for k in ("turns", "known_turns", "unknown_turns"))
    if any(type(x) is not int or x < 0 for x in (turns, known, unknown)):
        raise ValueError("invalid resource counters")
    if known + unknown != turns:
        raise ValueError("invalid resource counters")
    tokens = [u.get(k) for k in ("input_tokens", "cached_input_tokens", "output_tokens")]
    if any(type(x) is not int or x < 0 for x in tokens) or tokens[1] > tokens[0]:
        raise ValueError("invalid resource counters")
    usd = u.get("known_api_equivalent_usd")
    if not _finite_number(usd) or usd < 0: raise ValueError("invalid known resource valuation")
    complete = (row.get("generation_complete") is True and row.get("status_state") == "completed"
                and turns > 0 and known == turns and unknown == 0 and not u.get("invalid_usage"))
    return (float(tokens[0] + tokens[2]), float(usd)) if complete else None


def _percentile(values: np.ndarray) -> list[float] | None:
    return [float(x) for x in np.quantile(values, [.025, .975])] if len(values) else None


def _bootstrap(values: list[float], seed: int, draws: int) -> tuple[dict[str, Any], np.ndarray]:
    n = len(values)
    if not n:
        samples = np.array([], dtype=float)
    else:
        rng = np.random.default_rng(seed)
        samples = np.asarray(values, dtype=float)[rng.integers(0, n, size=(draws, n))].mean(axis=1)
    return {"n_tasks": n, "mean": float(statistics.fmean(values)) if values else None,
            "ci95": _percentile(samples), "seed": seed, "draws": draws,
            "percentile_method": "numpy.quantile (linear)"}, samples


def _t_test(values: list[float]) -> dict[str, Any]:
    n = len(values); mean = float(statistics.fmean(values)) if values else None
    sd = float(statistics.stdev(values)) if n > 1 else None
    if n <= 1:
        p = t = None; status = "unestimable"
    elif sd == 0:
        t = 0.0 if mean == 0 else None; p = 1.0 if mean == 0 else None
        status = "estimable" if p is not None else "unestimable_constant_nonzero"
    else:
        t = mean / (sd / math.sqrt(n)); p = float(2 * stats.t.sf(abs(t), n - 1)); status = "estimable"
    return {"n_tasks": n, "mean_difference": mean, "sd_task_differences": sd,
            "t_statistic": t, "p_two_sided": p, "test_status": status}


def _holm(pvalues: dict[str, float | None]) -> dict[str, float]:
    # Fixed two-test family: unavailable tests occupy their slot with p=1.
    ordered = sorted(((k, 1.0 if v is None else float(v)) for k, v in pvalues.items()), key=lambda z: z[1])
    out = {}; running = 0.0; m = len(ordered)
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p)); out[name] = running
    return out


def _component_bootstrap(contrasts: dict, source: dict, draws: int) -> tuple[dict, dict]:
    reports, vectors = {}, {}
    for graph in ("union_070_code_exact", "prompt_050", "prompt_070", "prompt_090"):
        if graph not in source["partitions"]: continue
        partition=source["partitions"][graph]
        groups = partition["assigned_components"]
        reports[graph], vectors[graph] = {}, {}
        for name, entry in contrasts.items():
            report, vector = family_bootstrap(entry["task_differences"], groups, draws=draws)
            reports[graph][name], vectors[graph][name] = report, vector
    return reports, vectors


def family_bootstrap(values: dict[str, float], groups: list[list[str]], *, draws: int = BOOTSTRAP_DRAWS,
                     seed: int = QUALITY_SEED) -> tuple[dict[str, Any], np.ndarray]:
    """Component bootstrap retaining all tasks in each sampled source family."""
    flat = [str(t) for g in groups for t in g]
    if len(flat) != len(set(flat)) or not set(values) <= set(flat):
        raise ValueError("source components overlap or omit observed tasks")
    kept = [[str(t) for t in g if str(t) in values] for g in groups]
    kept = [g for g in kept if g]
    sizes = np.asarray([len(g) for g in kept], dtype=int); total = int(sizes.sum())
    report = {"component_count": len(kept), "task_count": total,
              "largest_component_share": float(sizes.max()/total) if total else None,
              "effective_component_count": float(total*total/(sizes@sizes)) if total else None,
              "seed": seed, "draws": draws, "status": "unestimable"}
    if len(kept) < 2:
        return report, np.array([], dtype=float)
    rng = np.random.default_rng(seed); indices = rng.integers(0, len(kept), size=(draws, len(kept)))
    sums = np.asarray([sum(values[t] for t in g) for g in kept], dtype=float)
    arr = sums[indices].sum(axis=1) / sizes[indices].sum(axis=1)
    report.update({"status": "estimated", "ci95": _percentile(arr), "bootstrap_variance": float(np.var(arr, ddof=1)),
                   "degenerate_draws": bool(np.ptp(arr) == 0)})
    return report, arr


def _validate_metadata(selection: dict[str, Any], gate: dict[str, Any], source: dict[str, Any] | None) -> set[str]:
    selected = _selected_ids(selection)
    cells = selection.get("selected_cells")
    if not isinstance(cells, list) or len(cells) != 6000 or selection.get("selected_cells_digest") != _digest(cells):
        raise ValueError("selected-cell digest does not match manifest")
    if [c["id"] for c in cells] != selection["selected_ids"]:
        raise ValueError("selected-cell order differs from IDs")
    if gate.get("controls_complete") is not True or gate.get("schema") != "scale1000-control-gate-v1":
        raise ValueError("existing control gate is incomplete or invalid")
    assigned = gate.get("assigned_task_ids")
    eligible = gate.get("evaluable_task_ids", gate.get("eligible_task_ids"))
    if (not isinstance(assigned, list) or not isinstance(eligible, list) or not set(eligible) <= set(assigned)
            or len(assigned) != len(set(assigned)) or len(eligible) != len(set(eligible))
            or not {c["task_id"] for c in cells} <= set(assigned)):
        raise ValueError("control gate must provide assigned and eligible task IDs")
    if source is None:
        raise ValueError("source-audit-v2 metadata is required")
    if source.get("schema") != "source-task-overlap-v1" or not source.get("partitions"):
        raise ValueError("source metadata is not source-audit-v2")
    if not source.get("selection_sha256") or source["selection_sha256"] != gate.get("selection_sha256"):
        raise ValueError("source audit belongs to another selection")
    return selected


def analyze(records: Iterable[dict[str, Any]], selection: dict[str, Any], control_gate: dict[str, Any],
            source_audit: dict[str, Any], draws: int = BOOTSTRAP_DRAWS) -> dict[str, Any]:
    selected = _validate_metadata(selection, control_gate, source_audit)
    cells_by_id = {c["id"]: c for c in selection["selected_cells"]}
    if draws < 1: raise ValueError("draws must be positive")
    rows = list(records); index: dict[tuple[str, str, int], dict[str, Any]] = {}; by_id = {}
    for row in rows:
        if not isinstance(row, dict): raise ValueError("ledger rows must be objects")
        ident = _cell_id(row)
        if ident in by_id: raise ValueError("duplicate record ID")
        by_id[ident] = row
        if ident not in selected:
            # Outside-prefix ledger rows are retained administratively and never analyzed.
            continue
        if any(row.get(k) != v for k, v in cells_by_id[ident].items()):
            raise ValueError("selected assignment identity differs from allocation")
        try: method = row["method"]; rep = int(row["replicate_id"]); task = str(row["task_id"])
        except (KeyError, TypeError, ValueError) as exc: raise ValueError("malformed selected assignment") from exc
        if method not in METHODS or rep not in REPLICATES: raise ValueError("invalid selected method or replicate")
        key = (task, method, rep)
        if key in index: raise ValueError("duplicate selected task/method/replicate")
        _quality(row); _resource(row); index[key] = row
    if selected - set(by_id): raise ValueError("missing selected record ID")
    outside = set(by_id) - selected
    known_outside = set(selection.get("all_ids", [])) - selected
    if outside and outside != known_outside: raise ValueError("foreign or incomplete original record IDs")
    # Selected cells must be complete three-method blocks for their task/repeat.
    blocks = {}
    for (task, method, rep), row in index.items(): blocks.setdefault((task, rep), set()).add(method)
    if any(methods != set(METHODS) for methods in blocks.values()): raise ValueError("selected cells do not form whole three-method blocks")
    reps_by_task = {}
    for task, rep in blocks:
        reps_by_task.setdefault(task, []).append(rep)
    reps_by_task = {t: sorted(reps) for t,reps in reps_by_task.items()}
    tasks = sorted({task for task, _, _ in index}); eligible = set(map(str, control_gate["evaluable_task_ids"]))
    for (task, method, rep), row in index.items():
        if task not in eligible and _quality(row) is not None: raise ValueError("control-ineligible quality is observed")
    task_rows = []
    quality_draws = {}; contrasts = {}; pvalues = {}
    for left, right in PRIMARY:
        name = f"{left}-minus-{right}"; diffs = []; contributing = []; repeat_counts = []
        for task in tasks:
            pairs = []
            reps = reps_by_task[task]
            for rep in reps:
                a, b = index[(task, left, rep)], index[(task, right, rep)]
                qa, qb = _quality(a), _quality(b)
                if qa is not None and qb is not None: pairs.append((rep, int(qa)-int(qb)))
            if pairs and task in eligible:
                value = statistics.fmean(v for _, v in pairs); diffs.append(value); contributing.append(task); repeat_counts.append(len(pairs))
                task_rows.append({"task_id": task, "contrast": name, "difference": value, "replicate_ids": [r for r, _ in pairs]})
        test = _t_test(diffs); boot, vector = _bootstrap(diffs, QUALITY_SEED, draws); key = name
        test["bootstrap"] = boot; test["contributing_task_ids"] = contributing; test["matched_repeat_counts"] = repeat_counts
        test["task_differences"] = dict(zip(contributing, diffs))
        contrasts[key] = test; quality_draws[key] = vector; pvalues[key] = test["p_two_sided"]
    holm = _holm(pvalues)
    for k, v in holm.items(): contrasts[k]["holm_adjusted_p"] = v
    bounds = {}
    for scope, subset in (("eligible_selected", [t for t in tasks if t in eligible]), ("all_selected", tasks)):
        bounds[scope] = {}
        for left, right in PRIMARY:
            lo = hi = 0.0; excluded = 0
            for task in subset:
                reps = reps_by_task[task]
                av = [_quality(index[(task,left,r)]) for r in reps]; bv = [_quality(index[(task,right,r)]) for r in reps]
                denominator = len(reps) or 1
                ak = sum(int(x) for x in av if x is not None); bk = sum(int(x) for x in bv if x is not None)
                lo += ak/denominator - (bk + denominator - sum(x is not None for x in bv))/denominator
                hi += (ak + denominator - sum(x is not None for x in av))/denominator - bk/denominator
                excluded += int(any(x is None for x in av+bv))
            n = len(subset); bounds[scope][f"{left}-minus-{right}"] = {"task_count": n, "lower": lo/n if n else None, "upper": hi/n if n else None, "unknown_task_pairs": excluded}
    resources = {}; resource_draws = {}
    for left, right in PRIMARY:
        name = f"{left}-minus-{right}"; diffs=[]; ratios=[]; pair_rows=[]
        for task in tasks:
            per_rep=[]
            reps = reps_by_task[task]
            for rep in reps:
                a, b = _resource(index[(task,left,rep)]), _resource(index[(task,right,rep)])
                if a is not None and b is not None: per_rep.append((rep,a,b))
            if per_rep:
                am=statistics.fmean(x[1][1] for x in per_rep); bm=statistics.fmean(x[2][1] for x in per_rep)
                diffs.append(am-bm); pair_rows.append((task, am, bm, [x[0] for x in per_rep]));
                if bm > 0: ratios.append(am/bm)
        token_diffs = []
        for task in tasks:
            reps = reps_by_task[task]
            pairs = [(_resource(index[(task,left,r)]), _resource(index[(task,right,r)])) for r in reps]
            pairs = [(a,b) for a,b in pairs if a is not None and b is not None]
            if pairs: token_diffs.append(statistics.fmean(a[0] for a,b in pairs)-statistics.fmean(b[0] for a,b in pairs))
        db, dv = _bootstrap(diffs, RESOURCE_DIFF_SEED, draws); rb, rv = _bootstrap(ratios, RESOURCE_RATIO_SEED, draws)
        den=sum(x[2] for x in pair_rows); num=sum(x[1] for x in pair_rows); rom = num/den if den>0 else None
        rom_values = [x[1] for x in pair_rows]; rom_den=[x[2] for x in pair_rows]
        if pair_rows:
            rr = np.random.default_rng(RESOURCE_ROM_SEED).integers(0, len(pair_rows), size=(draws, len(pair_rows)))
            numerators = np.asarray(rom_values)[rr].sum(axis=1)
            denominators = np.asarray(rom_den)[rr].sum(axis=1)
            rom_vec = np.divide(numerators,denominators,out=np.full(draws,np.nan),where=denominators>0)
        else:
            rom_vec = np.array([], dtype=float)
        token_boot, token_vec = _bootstrap(token_diffs, RESOURCE_DIFF_SEED, draws)
        resources[name] = {"complete_task_pairs": len(pair_rows), "mean_difference": db, "token_mean_difference": token_boot, "mean_task_ratio": rb,
                           "ratio_of_paired_means": rom, "ratio_of_means_bootstrap": {**({"ci95": _percentile(rom_vec[np.isfinite(rom_vec)])} if len(rom_vec) else {"ci95": None}), "seed": RESOURCE_ROM_SEED, "draws": draws, "undefined_draws": int((~np.isfinite(rom_vec)).sum())},
                           "paired_task_values": [{"task_id":t,"left_usd":a,"right_usd":b,"replicate_ids":r} for t,a,b,r in pair_rows],
                           "positive_ratio_denominator_pairs": len(ratios), "excluded_nonpositive_ratio_denominators": len(pair_rows)-len(ratios)}
        resource_draws[name] = {"difference": dv, "token_difference": token_vec, "mean_task_ratio": rv, "ratio_of_means": rom_vec}
    component, component_draws = _component_bootstrap(contrasts, source_audit, draws)
    old_ids = {r["id"] for r in selection.get("old_inventory", {}).get("assignments", [])}
    segments = {ident: "before" if ident in old_ids else "after" for ident in selected}
    block_segments = {}
    positions = {}
    for pos in range(0, len(selection["selected_cells"]), 3):
        cells = selection["selected_cells"][pos:pos+3]
        values = {segments[c["id"]] for c in cells}
        key = (cells[0]["task_id"], cells[0]["replicate_id"])
        block_segments[key] = next(iter(values)) if len(values) == 1 else "spanning"
        positions[key] = pos // 3 + 1
    diagnostics = []
    for ident in selection["selected_ids"]:
        row=by_id[ident]; u=row.get("resource_usage") or {}; task=row["task_id"]; rep=row["replicate_id"]
        diagnostics.append({"id":ident,"task_id":task,"method":row["method"],"replicate_id":rep,
            "block_position":positions[(task,rep)],"assignment_segment":segments[ident],
            "block_segment":block_segments[(task,rep)],"generation_complete":row.get("generation_complete") is True,
            "outcome_type":row.get("outcome_type"),"quality":_quality(row),"resource_usage":u})
    grouped = {}
    for row in diagnostics:
        key=(row["method"],row["assignment_segment"])
        value=grouped.setdefault(key,dict(method=key[0],segment=key[1],assigned=0,generation_complete=0,
            quality_observed=0,passes=0,known_turns=0,unknown_turns=0,unknown_usage_assignments=0,
            known_input_tokens=0,known_cached_input_tokens=0,known_output_tokens=0,known_api_equivalent_usd=0.0))
        value["assigned"]+=1; value["generation_complete"]+=row["generation_complete"]
        q=row["quality"]; value["quality_observed"]+=q is not None; value["passes"]+=q is True
        u=row["resource_usage"]
        value["unknown_usage_assignments"]+=not u or u.get("unknown_turns",0)>0
        for field in ("known_turns","unknown_turns","known_api_equivalent_usd"):
            value[field]+=u.get(field,0)
        for field in ("input_tokens","cached_input_tokens","output_tokens"):
            value["known_"+field]+=u.get(field,0)
    segment_effects={}
    for segment in ("before","after","spanning"):
        segment_effects[segment]={}
        for left,right in PRIMARY:
            values=[]
            for task in tasks:
                if task not in eligible: continue
                pairs=[]
                for rep in reps_by_task[task]:
                    if block_segments[(task,rep)]!=segment: continue
                    a,b=_quality(index[(task,left,rep)]),_quality(index[(task,right,rep)])
                    if a is not None and b is not None: pairs.append(int(a)-int(b))
                if pairs: values.append(statistics.fmean(pairs))
            segment_effects[segment][f"{left}-minus-{right}"]={"task_count":len(values),"mean_difference":statistics.fmean(values) if values else None}
    return {"schema":"scc2000-analysis-v1","analysis":"amended-prefix","rows":len(rows),
        "selected_rows":len(index),"task_count":len(tasks),"eligible_task_count":len(set(tasks)&eligible),
        "selected_ids_digest":_digest(sorted(selected)),"quality_seeds":{"bootstrap":QUALITY_SEED},
        "resource_seeds":{"difference":RESOURCE_DIFF_SEED,"mean_task_ratio":RESOURCE_RATIO_SEED,"ratio_of_means":RESOURCE_ROM_SEED},
        "rng":"numpy.random.Generator(PCG64); numpy.quantile(linear)","contrasts":contrasts,
        "holm_adjusted_p":holm,"bounds":bounds,"resources":resources,"source_component_bootstrap":component,
        "restart_diagnostics":{"known_subtotals_by_method_segment":list(grouped.values()),
            "block_counts":{segment:list(block_segments.values()).count(segment) for segment in ("before","after","spanning")},
            "matched_quality_effects_descriptive":segment_effects},
        "draws":{"quality":quality_draws,"resources":resource_draws,"source_components":component_draws},
        "per_task_contrasts":task_rows,"assignment_diagnostics":diagnostics,"unknown_is_not_false":True}


def _load(path: Path) -> Any:
    if path.is_dir():
        value = json.loads((path / "summary.json").read_text(encoding="utf-8"))
        partitions = path / "partitions.json"
        if partitions.is_file(): value["partitions"] = json.loads(partitions.read_text(encoding="utf-8"))
        return value
    return json.loads(path.read_text(encoding="utf-8"))

def save_analysis(result: dict, records: list[dict], selection: dict, out: Path) -> None:
    if out.exists(): raise FileExistsError(f"Refusing existing output directory: {out}")
    out.mkdir(parents=True)
    excluded={"draws","per_task_contrasts","assignment_diagnostics"}
    (out/"summary.json").write_text(json.dumps({k:v for k,v in result.items() if k not in excluded},allow_nan=False,indent=2)+"\n",encoding="utf-8")
    selected=_selected_ids(selection)
    for name,values in (("selected_assignment_rows",[r for r in records if _cell_id(r) in selected]),
                        ("per_task_contrasts",result["per_task_contrasts"]),
                        ("assignment_diagnostics",result["assignment_diagnostics"])):
        (out/(name+".jsonl")).write_text("".join(json.dumps(r,sort_keys=True,allow_nan=False)+"\n" for r in values),encoding="utf-8")
    def write_vectors(value: Any, folder: Path) -> None:
        folder.mkdir()
        for name,child in value.items():
            if isinstance(child,dict): write_vectors(child,folder/name)
            else:
                vector=np.asarray(child)
                if vector.ndim!=1 or vector.dtype.kind not in "fi": raise ValueError("Draw vectors must be one-dimensional numeric arrays")
                np.save(folder/(name+".npy"),vector,allow_pickle=False)
    write_vectors(result["draws"],out/"draws")


def run_files(records_path: Path, selection_path: Path, gate_path: Path, source_path: Path, out: Path, draws: int=BOOTSTRAP_DRAWS) -> dict:
    records=[json.loads(x) for x in records_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    selection=_load(selection_path)
    result=analyze(records,selection,_load(gate_path),_load(source_path),draws)
    paths={"records":records_path,"selection":selection_path,"control_gate":gate_path}
    if source_path.is_dir():
        paths.update({"source_"+p.name:p for p in sorted(source_path.iterdir()) if p.is_file()})
    else: paths["source_audit"]=source_path
    result["provenance"]={"input_sha256":{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},
        "python":platform.python_version(),"numpy":np.__version__,"scipy":importlib.metadata.version("scipy")}
    save_analysis(result,records,selection,out)
    return {"rows":result["rows"],"selected_rows":result["selected_rows"],"tasks":result["task_count"]}


def main() -> None:
    p=argparse.ArgumentParser()
    for name in ("records","selection","control-gate","source-audit","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--draws",type=int,default=BOOTSTRAP_DRAWS); a=p.parse_args()
    print(json.dumps(run_files(a.records,a.selection,a.control_gate,a.source_audit,a.out,a.draws)))


if __name__ == "__main__": main()
