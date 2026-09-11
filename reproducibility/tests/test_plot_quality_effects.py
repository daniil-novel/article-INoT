"""Software fixtures only: no real running-study outcomes are read here."""
import hashlib
import json

import pytest

from reproducibility import evidence_manifest
from reproducibility.revision_20260911 import plot_quality_effects as plots


def factorial_fixture():
    return {"schema": "scale1000-task-cluster-analysis-v1", "tasks": 1000,
            "planned_candidates": 15000, "repeats": [101, 102, 103],
            "missingness": {"assignments": 15000, "missing_rows": 0},
            "inference": {"holm_family_size": 4},
            "contrasts": {key: {"eligible_tasks": 8, "task_ids": [f"fixture/{i}" for i in range(8)],
                                "mean_difference": -0.02, "bootstrap_95": [-0.071, 0.013],
                                "holm_p": 0.42} for key in plots.FACTORIAL}}


def scc_fixture():
    return {"schema": "scc-analysis-v2", "rows": 9000, "task_count": 1000,
            "strict_contract": {"enabled": True, "expected_cells": 9000, "replicates": [101, 102, 103]},
            "primary_family": list(plots.SCC),
            "contrasts": {key: {"n_tasks": 7, "mean_difference": 0.03,
                                "bootstrap_task_sampling": {"n_tasks": 7, "mean": 0.03, "ci95": [-0.01, 0.09]},
                                "holm_adjusted_p": 0.25} for key in plots.SCC}}


def test_units_asymmetry_and_registered_family():
    summary = factorial_fixture()
    summary["contrasts"]["irrelevant_descriptive_result"] = {"mean_difference": 999}
    study, rows = plots.chart_rows(summary)
    assert study == "factorial" and len(rows) == 4
    assert rows[0]["mean_pp"] == pytest.approx(-2)
    assert rows[0]["lower_pp"] == pytest.approx(-7.1)
    assert rows[0]["upper_pp"] == pytest.approx(1.3)
    assert rows[0]["paired_tasks"] == 8 and rows[0]["holm_p"] == 0.42
    study, rows = plots.chart_rows(scc_fixture())
    assert study == "scc" and [r["label"] for r in rows] == ["SCC − SR", "SCC − SN"]
    assert rows[0]["paired_tasks"] == 7


def test_unavailable_estimate_and_interval_stay_unavailable():
    summary = scc_fixture()
    result = summary["contrasts"][next(iter(plots.SCC))]
    result.update(n_tasks=0, mean_difference=None, holm_adjusted_p=None,
                  bootstrap_task_sampling={"n_tasks": 0, "mean": None, "ci95": [None, None]})
    _, rows = plots.chart_rows(summary)
    assert [rows[0][k] for k in ("mean_pp", "lower_pp", "upper_pp", "holm_p")] == [None] * 4
    result["mean_difference"] = 0
    result["bootstrap_task_sampling"]["mean"] = 0
    with pytest.raises(ValueError, match="Unavailable"):
        plots.chart_rows(summary)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, 1.1])
def test_invalid_numeric_results_rejected(bad):
    summary = factorial_fixture()
    summary["contrasts"][next(iter(plots.FACTORIAL))]["holm_p"] = bad
    with pytest.raises(ValueError, match="numeric"):
        plots.chart_rows(summary)


def test_pair_count_and_bootstrap_population_must_match():
    summary = factorial_fixture()
    summary["contrasts"][next(iter(plots.FACTORIAL))]["eligible_tasks"] = 24
    with pytest.raises(ValueError, match="task count"):
        plots.chart_rows(summary)
    summary = scc_fixture()
    summary["contrasts"][next(iter(plots.SCC))]["bootstrap_task_sampling"]["n_tasks"] = 21
    with pytest.raises(ValueError, match="scope"):
        plots.chart_rows(summary)


def test_renderer_keeps_interval_even_when_it_excludes_point():
    from matplotlib import pyplot as plt
    _, rows = plots.chart_rows(factorial_fixture())
    rows[0].update(mean_pp=0.2, lower_pp=0.3, upper_pp=0.8)
    fig = plots.draw(rows, "factorial", "en")
    try:
        segment = fig.axes[0].collections[0].get_segments()[0]
        assert segment[:, 0].tolist() == [0.3, 0.8]
        assert any(list(line.get_xdata()) == [0.2] for line in fig.axes[0].lines)
    finally:
        plt.close(fig)


def test_archived_inputs_must_be_terminal_and_unchanged(tmp_path):
    archive = tmp_path / "artificial-archive"
    (archive / "generation").mkdir(parents=True)
    (archive / "analysis").mkdir()
    status = archive / "generation/status.json"
    status.write_text(json.dumps({"state": "paused"}), encoding="utf-8")
    summary = archive / "analysis/summary.json"
    summary.write_text(json.dumps(factorial_fixture()), encoding="utf-8")
    evidence_manifest.write(archive)
    with pytest.raises(ValueError, match="finished"):
        plots.render(archive, tmp_path / "plots")
    status.write_text(json.dumps({"state": "generation_finished"}), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence bytes"):
        plots.render(archive, tmp_path / "plots")
    evidence_manifest.write(archive)
    with pytest.raises(ValueError, match="outside"):
        plots.render(archive, archive / "plots")


def test_incomplete_summary_is_not_a_completed_study():
    summary = factorial_fixture()
    summary["missingness"]["assignments"] = 14999
    with pytest.raises(ValueError, match="Incomplete"):
        plots.chart_rows(summary)
    summary = scc_fixture()
    summary["strict_contract"]["enabled"] = False
    with pytest.raises(ValueError, match="Incomplete"):
        plots.chart_rows(summary)


def test_export_provenance_and_csv_keep_exact_values(tmp_path):
    archive = tmp_path / "artificial-archive"
    (archive / "generation").mkdir(parents=True)
    (archive / "analysis").mkdir()
    (archive / "generation/status.json").write_text('{"state":"generation_finished"}', encoding="utf-8")
    (archive / "analysis/summary.json").write_text(json.dumps(scc_fixture()), encoding="utf-8")
    evidence_manifest.write(archive)
    output = tmp_path / "software-test-output"
    provenance = plots.render(archive, output)
    assert len(provenance["outputs"]) == 5
    assert all(hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
               for name, digest in provenance["outputs"].items())
    assert "paired_tasks,mean_pp,lower_pp,upper_pp,holm_p" in (output / "quality_effects.csv").read_text()
    assert ",7,3.0,-1.0,9.0,0.25" in (output / "quality_effects.csv").read_text()
    with pytest.raises(ValueError, match="new output"):
        plots.render(archive, output)
