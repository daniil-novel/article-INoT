from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path


def table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export(evidence_path: Path, output: Path):
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for model, key in [("Pro", "tracked_pro_humaneval_e3"), ("Flash-Lite", "flash_lite_humaneval_e3_replication")]:
        for ctx in ["256", "1024", "4096", "16384"]:
            b2 = evidence[key]["B2_ClassicalMAS"][ctx]
            b3 = evidence[key]["B3_HybridINoT"][ctx]
            rows.append({"model": model, "context_target_tokens": int(ctx), "n_per_architecture": b2["n"],
                         "b2_mean_tokens": b2["mean_tokens"], "b3_mean_tokens": b3["mean_tokens"],
                         "token_savings_pct": b3["token_savings_vs_b2_pct"],
                         "b2_pass_at_1": b2["pass_at_1"], "b3_pass_at_1": b3["pass_at_1"],
                         "b2_mean_cost_usd": b2["mean_cost_usd"], "b3_mean_cost_usd": b3["mean_cost_usd"]})
    table(output / "e3_measurements.csv", rows)
    table(output / "e4_profitability.csv", [{"suite": k, **{field: value for field, value in v.items() if not isinstance(value, dict)}} for k, v in evidence["new_e4"].items()])
    table(output / "e6_model_comparisons.csv", evidence["tracked_e6_comparisons"])
    e5 = evidence["inference_cost_extrapolation_from_tracked_e3"]
    table(output / "e5_price_sensitivity.csv", e5["price_sensitivity"])
    rows = []
    for cohort, key in [("Pro", "tracked_pro_humaneval_e3_pairwise"), ("Flash-Lite", "flash_lite_humaneval_e3_pairwise")]:
        for values in evidence[key]:
            rows.append({"model": cohort, **{k: json.dumps(v) if isinstance(v, list) else v for k, v in values.items()}})
    table(output / "e3_paired_statistics.csv", rows)
    # Retain complete original E2 aggregates rather than invent a new ablation convention.
    (output / "e2_aggregates.json").write_text(json.dumps({key: evidence[key] for key in ["tracked_e2_stats", "tracked_e2_pairwise", "tracked_e2_full_summary"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=Path(__file__).resolve().parents[1] / "article" / "reproducibility" / "evidence_snapshot.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "tables")
    args = parser.parse_args()
    export(args.evidence, args.output)
