"""Reproduce and validate every numerical table in the FSE paper.

This reviewer replay intentionally performs no model calls and executes no
generated programs. It validates frozen analysis outputs against the paper's
registered values and emits a compact Markdown rendering.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def close(actual: float, expected: float, tolerance: float = 5e-12) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"expected {expected}, got {actual}")


def main() -> None:
    primary = load("primary/summary.json")
    mini = load("mini/summary.json")
    scc = load("scc/summary.json")

    assert primary["tasks"] == 1000
    assert primary["planned_candidates"] == 15000
    completed = sum(row["generation_complete"] for row in primary["by_arm"])
    assert completed == 14961

    expected = {
        "single_roles_minus_single_neutral": (-0.007467752885268159, 982),
        "multi_roles_minus_multi_neutral": (0.013485477178423237, 964),
        "multi_neutral_minus_single_neutral": (-0.04166666666666668, 968),
        "multi_roles_minus_single_roles": (-0.021283899759697907, 971),
    }
    for name, (effect, tasks) in expected.items():
        row = primary["contrasts"][name]
        close(row["mean_difference"], effect)
        assert row["eligible_tasks"] == tasks

    direct_expected = {
        "direct_minus_single_neutral": (0.0027210884353741508, 980),
        "direct_minus_single_roles": (0.009533537623425263, 979),
        "direct_minus_multi_neutral": (0.04589371980676329, 966),
        "direct_minus_multi_roles": (0.031958762886597936, 970),
    }
    for name, (effect, tasks) in direct_expected.items():
        row = primary["descriptive_direct_contrasts"][name]
        close(row["mean_difference"], effect)
        assert row["eligible_tasks"] == tasks

    for subset, count in (("old200", 200), ("fresh800", 800)):
        assert len(primary["subgroups"][subset]) == 4
        # The neutral topology estimate is exactly -4.1667 pp in both subsets.
        close(primary["subgroups"][subset]["multi_neutral_minus_single_neutral"]["mean_difference"], -1 / 24)

    mini_expected = {
        "roles_minus_neutral_single": (-0.010471204188481676, 191),
        "roles_minus_neutral_multi": (0.010362694300518135, 193),
        "multi_minus_single_neutral": (-0.04712041884816754, 191),
        "multi_minus_single_roles": (-0.02072538860103627, 193),
    }
    for name, (effect, tasks) in mini_expected.items():
        row = mini["paired_contrasts"][name]["quality"]
        close(row["mean_paired_difference"], effect)
        assert row["complete_task_clusters"] == tasks

    assert scc["selected_rows"] == 6000
    assert scc["task_count"] == 956
    assert scc["eligible_task_count"] == 941
    scc_expected = {
        "scc_author_2024_codex_transport-minus-single_roles": (-0.02680256700641752, 883),
        "scc_author_2024_codex_transport-minus-single_neutral": (-0.02475434618291761, 882),
    }
    for name, (effect, tasks) in scc_expected.items():
        row = scc["contrasts"][name]
        close(row["mean_difference"], effect)
        assert row["n_tasks"] == tasks

    lines = [
        "# Reproduced table checkpoint",
        "",
        f"- Primary assignments: {primary['planned_candidates']:,}",
        f"- Completed candidates: {completed:,}",
        f"- Task clusters: {primary['tasks']:,}",
        "- Primary effects (percentage points): "
        + ", ".join(f"{name}={100*primary['contrasts'][name]['mean_difference']:+.2f}" for name in expected),
        "- Direct effects (percentage points): "
        + ", ".join(f"{name}={100*primary['descriptive_direct_contrasts'][name]['mean_difference']:+.2f}" for name in direct_expected),
        "- Mini corroboration (percentage points): "
        + ", ".join(f"{name}={100*mini['paired_contrasts'][name]['quality']['mean_paired_difference']:+.2f}" for name in mini_expected),
        f"- SCC selected rows: {scc['selected_rows']:,} across {scc['task_count']} tasks",
        "- SCC effects (percentage points): "
        + ", ".join(f"{name}={100*scc['contrasts'][name]['mean_difference']:+.2f}" for name in scc_expected),
        "",
        "All registered checks passed.",
    ]
    output = ROOT / "REPRODUCED_TABLES.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
