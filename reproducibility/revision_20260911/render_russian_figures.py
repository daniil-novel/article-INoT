"""Render Russian labels for the four completed empirical figures.

The numerical inputs are completed-study summaries and the published rendered
held-out values. No live-series output is read and no source figure is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def make_plots(heldout_values: Path, heldout_summary: Path, segregation_summary: Path,
               heldout_records: Path, segregation_records: Path, out_audit: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = read_json(heldout_values)
    summary = read_json(heldout_summary)
    segregation = read_json(segregation_summary)

    record_counts = {
        "heldout": sum(bool(line.strip()) for line in heldout_records.read_text(encoding="utf-8").splitlines()),
        "segregation": sum(bool(line.strip()) for line in segregation_records.read_text(encoding="utf-8").splitlines()),
    }
    if record_counts != {"heldout": 996, "segregation": 320}:
        raise ValueError("Unexpected archived candidate-record counts")

    groups = values["groups"]
    expected = {"D": 199, "SN": 197, "SR": 200, "MN": 200, "MR": 200, "INoT*": 199}
    observed = {g["code"]: g["generated"] for g in groups}
    if observed != expected:
        raise ValueError(f"Unexpected held-out group counts: {observed}")
    if summary["assigned_attempts"] != 1000 or summary["recorded_attempts"] != 996:
        raise ValueError("Unexpected primary allocation")
    if segregation["assigned_candidates"] != 320:
        raise ValueError("Unexpected independent-study allocation")

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    out_dir = ROOT / "figures"

    # Primary paired quality effects: same means and intervals as the English figure.
    keys = ("roles_minus_neutral_single", "roles_minus_neutral_multi",
            "multi_minus_single_neutral", "multi_minus_single_roles")
    labels = ("SR − SN", "MR − MN", "MN − SN", "MR − SR")
    fig, ax = plt.subplots(figsize=(6.7, 3.1), layout="constrained")
    for y, key in enumerate(keys):
        q = summary["paired_contrasts"][key]["quality"]
        lo, hi = q["descriptive_task_bootstrap_95_interval"]
        mean = q["mean_paired_difference"]
        ax.plot([100 * lo, 100 * hi], [y, y], color="#0c6470", lw=2)
        ax.scatter(100 * mean, y, color="#0c6470", s=40, zorder=3)
    ax.axvline(0, color="#777777", ls="--", lw=1)
    ax.set(yticks=range(4), yticklabels=labels,
           xlabel="Парная разность долей успеха (п.п.)",
           ylim=(3.5, -0.5))
    ax.grid(axis="x", alpha=.18)
    fig.savefig(out_dir / "heldout_quality_effects_ru.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)

    # Primary token components: values are taken from the current rendered summary.
    fig, ax = plt.subplots(figsize=(6.7, 3.6), layout="constrained")
    x = list(range(len(groups)))
    base = [0.0] * len(groups)
    parts = (
        ("Вход без кеша", [g["input_tokens"] - g["cached_input_tokens"] for g in groups], "#476b85"),
        ("Кешированный вход", [g["cached_input_tokens"] for g in groups], "#9dc4d4"),
        ("Выход (включая токены рассуждения)", [g["output_tokens"] for g in groups], "#bf813e"),
    )
    for label, raw, color in parts:
        scaled = [v / 1000 for v in raw]
        ax.bar(x, scaled, bottom=base, label=label, color=color, width=.65)
        base = [a + b for a, b in zip(base, scaled)]
    ax.set(xticks=x, xticklabels=[g["code"] for g in groups],
           ylabel="Средний расход (тыс. токенов)\nна завершённую программу",
           ylim=(0, max(base) * 1.23))
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=1)
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    fig.savefig(out_dir / "heldout_token_components_ru.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)

    # Primary quality/resource means.
    colors = ["#0c6470", "#536e8a", "#378b70", "#a66d38", "#946396", "#333333"]
    fig, ax = plt.subplots(figsize=(6.7, 3.7), layout="constrained")
    for g, color in zip(groups, colors):
        ax.scatter(100 * g["api_equivalent_usd"], 100 * g["rate"], s=60,
                   color=color, marker="s" if g["code"] == "INoT*" else "o")
        offset = {"D": (5, -19), "SN": (7, 7), "SR": (5, -20),
                  "MN": (12, -19), "MR": (-25, 14), "INoT*": (-4, 12)}[g["code"]]
        ax.annotate(g["code"], (100 * g["api_equivalent_usd"], 100 * g["rate"]),
                    xytext=offset, textcoords="offset points", color=color,
                    arrowprops={"arrowstyle": "-", "color": color, "linewidth": .7})
    ax.set(xlabel="Средняя оценка по тарифам API (центы США на программу)",
           ylabel="Доля успешных программ (%)", ylim=(0, 100),
           xlim=(0, max(g["api_equivalent_usd"] for g in groups) * 120))
    ax.grid(alpha=.18)
    fig.savefig(out_dir / "heldout_cost_quality_ru.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)

    # Independent 80-task extension: same four contrasts and intervals as English figure.
    seg_keys = ("role_boundary_minus_neutral_boundary", "role_prose_minus_neutral_prose",
                "boundary_minus_prose_role", "boundary_minus_prose_neutral")
    seg_labels = ("RB − NB", "RP − NP", "RB − RP", "NB − NP")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.1), layout="constrained")
    for ax, metric, scale, xlabel in zip(
        axes, ("quality", "api_equivalent_usd"), (100, 100),
        ("Разность качества (п.п.)", "Средняя разность оценки (центы США)"),
    ):
        ax.axvline(0, color="#888888", lw=.8, zorder=0)
        for i, key in enumerate(seg_keys):
            r = segregation["contrasts"][key]
            if metric == "quality":
                mean = r["quality_difference"]
                lo, hi = r["quality_bootstrap_95"]
            else:
                mean = r["api_equivalent_usd"]["mean_difference"]
                lo, hi = r["api_equivalent_usd"]["descriptive_bootstrap_95"]
            color = "#145c75" if i < 2 else "#707070"
            ax.plot([lo * scale, hi * scale], [i, i], color=color, lw=1.6)
            ax.plot(mean * scale, i, "o", color=color, ms=5)
        ax.set(yticks=range(4), yticklabels=seg_labels, xlabel=xlabel)
        ax.invert_yaxis()
        ax.set_title(("A. Качество", "B. Ресурсы")[0 if metric == "quality" else 1],
                     loc="left", fontweight="bold")
        ax.grid(axis="x", alpha=.18)
    fig.savefig(out_dir / "segregation80" / "effects_ru.pdf",
                metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)

    audit = {
        "sources": {
            "heldout_rendered_values": str(heldout_values.relative_to(ROOT)),
            "heldout_summary": str(heldout_summary.relative_to(ROOT)),
            "segregation_summary": str(segregation_summary.relative_to(ROOT)),
            "heldout_candidate_records": str(heldout_records.relative_to(ROOT)),
            "segregation_candidate_records": str(segregation_records.relative_to(ROOT)),
        },
        "sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
                   (heldout_values, heldout_summary, segregation_summary, heldout_records, segregation_records)},
        "checks": {
            "heldout_groups": observed,
            "candidate_record_counts": record_counts,
            "heldout_recorded_attempts": summary["recorded_attempts"],
            "segregation_assigned_candidates": segregation["assigned_candidates"],
            "outputs": [
                "figures/heldout_quality_effects_ru.pdf",
                "figures/heldout_token_components_ru.pdf",
                "figures/heldout_cost_quality_ru.pdf",
                "figures/segregation80/effects_ru.pdf",
            ],
            "numeric_source": "completed-study summaries and heldout_rendered_values.json; no live-series outputs",
        },
    }
    out_audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--heldout-values", type=Path, default=ROOT / "reproducibility/revision/heldout_rendered_values.json")
    p.add_argument("--heldout-summary", type=Path, default=ROOT / "reproducibility/results/20260908_codex_mini_heldout200/analysis/summary.json")
    p.add_argument("--segregation-summary", type=Path, default=ROOT / "reproducibility/results/20260908_codex_mini_segregation80/analysis/summary.json")
    p.add_argument("--heldout-records", type=Path, default=ROOT / "reproducibility/results/20260908_codex_mini_heldout200/analysis/candidate_records.jsonl")
    p.add_argument("--segregation-records", type=Path, default=ROOT / "reproducibility/results/20260908_codex_mini_segregation80/analysis/candidate_records.jsonl")
    p.add_argument("--audit", type=Path, default=ROOT / "reproducibility/revision_20260911/russian_figure_audit.json")
    args = p.parse_args()
    make_plots(args.heldout_values, args.heldout_summary, args.segregation_summary,
               args.heldout_records, args.segregation_records, args.audit)
