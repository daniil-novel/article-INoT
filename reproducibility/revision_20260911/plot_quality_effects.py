"""Render registered quality contrasts from a completed evidence archive.

This presentation helper never computes a test or a confidence interval. Run
the archive's full statistical replay before using this separate renderer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

from reproducibility.evidence_manifest import verify

FACTORIAL = {
    "single_roles_minus_single_neutral": "SR − SN",
    "multi_roles_minus_multi_neutral": "MR − MN",
    "multi_neutral_minus_single_neutral": "MN − SN",
    "multi_roles_minus_single_roles": "MR − SR",
}
SCC = {
    "scc_author_2024_codex_transport-single_roles": "SCC − SR",
    "scc_author_2024_codex_transport-single_neutral": "SCC − SN",
}
FACTORIAL_ARMS = ["direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral"]
SCC_METHODS = ["single_roles", "single_neutral", "scc_author_2024_codex_transport"]


def _number(value, lower, upper):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError("Invalid finite numeric result")
    return float(value)


def chart_rows(summary):
    """Keep the registered family/order, exact bounds, and complete-pair n."""
    if summary.get("schema") == "scale1000-task-cluster-analysis-v1":
        study, names = "factorial", FACTORIAL
        if (summary.get("tasks") != 1000 or summary.get("planned_candidates") != 15000
                or summary.get("repeats") != [101, 102, 103]
                or summary.get("arms") != FACTORIAL_ARMS
                or summary.get("bootstrap") != {"resamples": 10000, "seed": 20260909}
                or summary.get("missingness", {}).get("assignments") != 15000
                or summary.get("missingness", {}).get("missing_rows") != 0
                or summary.get("inference", {}).get("holm_family_size") != 4
                or summary.get("inference", {}).get("holm_familywise_alpha") != 0.05):
            raise ValueError("Incomplete or incompatible factorial summary")
    elif summary.get("schema") == "scc-analysis-v2":
        study, names = "scc", SCC
        contract = summary.get("strict_contract", {})
        if (summary.get("rows") != 9000 or summary.get("task_count") != 1000
                or summary.get("task_cluster_count") != 1000 or summary.get("holm_alpha") != 0.05
                or contract.get("enabled") is not True or contract.get("expected_cells") != 9000
                or contract.get("methods") != SCC_METHODS
                or contract.get("replicates") != [101, 102, 103]
                or summary.get("primary_family") != list(SCC)):
            raise ValueError("Incomplete or incompatible SCC summary")
    else:
        raise ValueError("Unrecognized registered analysis schema")
    rows = []
    for key, label in names.items():
        result = summary["contrasts"][key]
        n = result["eligible_tasks" if study == "factorial" else "n_tasks"]
        if type(n) is not int or not 0 <= n <= 1000:
            raise ValueError("Invalid complete-pair task count")
        if study == "factorial":
            ids = result["task_ids"]
            if len(ids) != n or len(set(ids)) != n:
                raise ValueError("Complete-pair IDs disagree with task count")
            interval, p = result["bootstrap_95"], result["holm_p"]
        else:
            boot = result["bootstrap_task_sampling"]
            if (boot["n_tasks"] != n or boot["mean"] != result["mean_difference"]
                    or boot.get("resamples") != 10000 or boot.get("seed") != 20260911):
                raise ValueError("Bootstrap scope differs from the plotted contrast")
            interval, p = boot["ci95"], result["holm_adjusted_p"]
        mean = _number(result["mean_difference"], -1, 1)
        p = _number(p, 0, 1)
        if interval is None:
            lo, hi = None, None
        elif isinstance(interval, list) and len(interval) == 2:
            lo, hi = (_number(v, -1, 1) for v in interval)
        else:
            raise ValueError("Invalid interval shape")
        if (lo is None) != (hi is None) or (lo is not None and lo > hi):
            raise ValueError("Invalid interval bounds")
        if (n == 0 and any(v is not None for v in (mean, lo, hi, p))) or (n > 0 and mean is None):
            raise ValueError("Unavailable outcomes must not become numeric estimates")
        rows.append({"contrast": key, "label": label, "paired_tasks": n,
                     "mean_pp": None if mean is None else 100 * mean,
                     "lower_pp": None if lo is None else 100 * lo,
                     "upper_pp": None if hi is None else 100 * hi, "holm_p": p})
    return study, rows


def draw(rows, study, language):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    ru = language == "ru"
    titles = {"factorial": ("Факторный эксперимент", "Factorial experiment"),
              "scc": ("Сравнение полных процедур SCC/SR/SN", "SCC/SR/SN workflow comparison")}
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9,
                         "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False}):
        fig, ax = plt.subplots(figsize=(7.2, 2.4 + 0.48 * len(rows)))
        fig.subplots_adjust(left=0.25, right=0.97, bottom=0.34 if len(rows) == 2 else 0.29, top=0.86)
        ax.axvline(0, color="#777777", linewidth=0.8)
        labels, limits = [], [0.0]
        for y, row in enumerate(rows):
            p = row["holm_p"]
            ptext = "pH = NA" if p is None else ("pH < 0.0001" if p < 0.0001 else f"pH = {p:.4f}")
            labels.append(f"{row['label']}\nn = {row['paired_tasks']}; {ptext}")
            mean, lo, hi = row["mean_pp"], row["lower_pp"], row["upper_pp"]
            if lo is not None:
                ax.hlines(y, lo, hi, color="#285A78", linewidth=1.8)
                ax.plot([lo, hi], [y, y], "|", color="#285A78", markersize=7)
                limits.extend([lo, hi])
            if mean is not None:
                ax.plot(mean, y, "o", color="#285A78", markersize=5)
                limits.append(mean)
                if lo is None:
                    ax.text(0.98, y, "ДИ недоступен" if ru else "CI unavailable",
                            ha="right", va="center", transform=ax.get_yaxis_transform(), fontsize=8)
            else:
                ax.text(0.5, y, "Нет полных пар" if ru else "No complete pairs",
                        ha="center", va="center", transform=ax.get_yaxis_transform())
        span = max(max(limits) - min(limits), 1.0)
        ax.set_xlim(min(limits) - span * 0.12, max(limits) + span * 0.12)
        ax.set_ylim(len(rows) - 0.55, -0.55)
        ax.set_yticks(range(len(rows)), labels)
        ax.tick_params(axis="y", length=0, pad=9)
        ax.spines["left"].set_visible(False)
        ax.grid(axis="x", color="#E6E6E6", linewidth=0.5)
        ax.set_axisbelow(True)
        ax.set_xlabel("Разность вероятностей успеха, п.п." if ru else "Difference in success probability (percentage points)")
        fig.suptitle(titles[study][0 if ru else 1], fontsize=11, y=0.96)
        footer = ("Средние парные разности; 95% бутстрэп-ДИ по задачам без поправки за множественность.\n"
                  "n — полные пары задач (усреднены три повтора); pH — p с поправкой Холма.\n"
                  "ДИ условны на полных парах; пропуски и группы исходных задач анализируются отдельно."
                  if ru else
                  "Paired mean differences; unadjusted 95% task-bootstrap confidence intervals.\n"
                  "n: complete paired tasks (three repeats averaged per task); pH: Holm-adjusted p-value.\n"
                  "Intervals condition on complete pairs; missingness and source-group analyses are separate.")
        fig.text(0.025, 0.025, footer, fontsize=8.3, va="bottom", linespacing=1.5)
    return fig


def render(archive: Path, output: Path):
    archive, output = archive.resolve(), output.resolve()
    if output.is_relative_to(archive) or output.exists():
        raise ValueError("Use a new output directory outside the immutable archive")
    inventory = verify(archive)
    status_path, summary_path = archive / "generation/status.json", archive / "analysis/summary.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("state") != "generation_finished":
        raise ValueError("Generation must be finished before plotting")
    study, rows = chart_rows(json.loads(summary_path.read_text(encoding="utf-8")))
    output.mkdir(parents=True)
    with (output / "quality_effects.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    for language in ("en", "ru"):
        fig = draw(rows, study, language)
        fig.savefig(output / f"quality_effects_{language}.pdf", metadata={"CreationDate": None, "ModDate": None})
        fig.savefig(output / f"quality_effects_{language}.png", dpi=200)
        from matplotlib import pyplot as plt
        plt.close(fig)
    import matplotlib
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = {"study": study, "summary_sha256": sha(summary_path),
                  "generation_status_sha256": sha(status_path),
                  "evidence_manifest_sha256": sha(archive / "EVIDENCE_MANIFEST.json"),
                  "input_byte_inventory": inventory, "renderer_sha256": sha(Path(__file__)),
                  "python": platform.python_version(), "matplotlib": matplotlib.__version__,
                  "intervals": "registered marginal 95% percentile task-bootstrap intervals; no recomputation",
                  "verification_scope": "Input byte inventory and summary schema only; run the archive's full statistical replay separately.",
                  "outputs": {p.name: sha(p) for p in sorted(output.iterdir())}}
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.archive, args.output), ensure_ascii=False))
