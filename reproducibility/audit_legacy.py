"""Recalculate historical metrics without claiming to replay absent solutions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import NormalDist, mean


def audit(source: Path) -> dict:
    rows = json.loads(source.read_text(encoding="utf-8"))
    keys = [(r["task_id"], r["architecture"], r["seed"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate historical cells")
    grouped: dict = defaultdict(list)
    for row in rows:
        if row["total_tokens"] != row["input_tokens"] + row["output_tokens"]:
            raise ValueError("Token accounting mismatch")
        if row["total_tokens"] != sum(u["input_tokens"] + u["output_tokens"] for u in row["usages"]):
            raise ValueError("Usage trace mismatch")
        grouped[(row["extra"]["context_target_tokens"], row["architecture"])].append(row)
    unique_tasks = sorted({r["task_id"].split("@ctx")[0] for r in rows})
    cells = []
    for (context, arm), values in sorted(grouped.items()):
        cells.append({"context": context, "arm": arm, "n": len(values),
                      "tokens": mean(r["total_tokens"] for r in values),
                      "input_tokens": mean(r["input_tokens"] for r in values),
                      "output_tokens": mean(r["output_tokens"] for r in values),
                      "cost_usd": mean(r["cost_usd"] for r in values),
                      "reported_pass_rate": mean(r["passed"] for r in values),
                      "mean_calls": mean(len(r["usages"]) for r in values)})
    contexts = sorted({c[0] for c in grouped})
    contrasts = []
    for context in contexts:
        arms = {c["arm"]: c for c in cells if c["context"] == context}
        b0, b2, b3 = (arms[a] for a in ("B0_SingleLarge", "B2_ClassicalMAS", "B3_HybridINoT"))
        contrasts.append({"context": context,
                          "b2_tokens": b2["tokens"], "b3_tokens": b3["tokens"],
                          "b0_tokens": b0["tokens"],
                          "b3_vs_b2_savings_pct": 100*(1-b3["tokens"]/b2["tokens"]),
                          "b3_vs_b0_token_change_pct": 100*(b3["tokens"]/b0["tokens"]-1)})
    n = len(unique_tasks)
    z = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.80)
    return {"source": source.as_posix(), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "scope": "arithmetic reanalysis only; no model generation or solution replay",
            "rows": len(rows), "unique_tasks": n, "seeds": sorted({r["seed"] for r in rows}),
            "cells": cells, "contrasts": contrasts,
            "retained_final_solution_count": sum(bool(r.get("final_solution")) for r in rows),
            "retained_response_count": sum(bool(r.get("response") or r.get("raw_response")) for r in rows),
            "reported_pass_counts": dict(Counter(str(r["passed"]) for r in rows)),
            "zero_harm_iid_upper_95": 1-.05**(1/n),
            "power_approximation": [{"discordance": d, "margin": .02,
                                      "n_continuous": z*z*d/.02**2} for d in [.05,.1,.2]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("reproducibility/results/20260726_flash_lite/e3/runs.json"))
    parser.add_argument("--output", type=Path, default=Path("reproducibility/revision/legacy_audit.json"))
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["contrasts"][0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["contrasts"])
    print(json.dumps({k:v for k,v in result.items() if k not in ("cells",)},indent=2))


if __name__ == "__main__":
    main()
