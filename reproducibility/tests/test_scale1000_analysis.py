import pytest

from reproducibility.scale1000.analyze import summarize


ARMS = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
REPEATS = (101, 102, 103)


def _rows(n=1000):
    rows = []
    for i in range(n):
        for arm in ARMS:
            for repeat in REPEATS:
                value = ((i + repeat + len(arm)) % 3) == 0
                rows.append({"task_id": f"t{i}", "arm": arm, "replicate_id": repeat,
                             "quality": value, "generation_complete": True,
                             "total_tokens": 100 + i, "api_equivalent_usd": .001,
                             "uncached_sensitivity_usd": .002})
    return rows


def test_repeats_are_clustered_before_inference():
    out = summarize(_rows())
    assert out["tasks"] == 1000
    assert all(x["eligible_tasks"] == 1000 for x in out["contrasts"].values())
    assert out["inference"]["repeat_means_are_not_independent_tasks"] is True
    assert all(x["eligible_tasks"] == 1000 for c in out["resource_contrasts"].values() for x in c.values())


def test_missing_one_repeat_excludes_whole_task_from_each_affected_contrast():
    rows = _rows()
    rows = [r for r in rows if not (r["task_id"] == "t0" and r["arm"] in {"single_roles", "single_neutral"} and r["replicate_id"] == 103)]
    out = summarize(rows)
    assert out["contrasts"]["single_roles_minus_single_neutral"]["eligible_tasks"] == 999
    assert out["contrasts"]["multi_roles_minus_multi_neutral"]["eligible_tasks"] == 1000
    assert out["missingness"]["missing_rows"] == 2


def test_null_quality_is_missing_not_failure_and_selection_is_descriptive():
    rows = _rows()
    for row in rows:
        if row["task_id"] == "t1" and row["arm"] == "multi_roles":
            row["quality"] = None
    selection = {"prior_primary_task_ids": [f"t{i}" for i in range(200)],
                 "new_task_ids": [f"t{i}" for i in range(200, 1000)]}
    out = summarize(rows, selection)
    assert out["contrasts"]["multi_roles_minus_multi_neutral"]["eligible_tasks"] == 999
    assert out["missingness"]["quality_unknown_assignments"] == 3
    assert set(out["subgroups"]) == {"old200", "fresh800"}


def test_duplicate_repeat_rejected():
    rows = _rows()
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="duplicate assignment"):
        summarize(rows)


def test_incomplete_generation_cannot_be_labeled_quality():
    rows = _rows()
    rows[0]["generation_complete"] = False
    with pytest.raises(ValueError, match="incomplete generation"):
        summarize(rows)


def test_degenerate_quality_contrast_is_finite_and_reports_boundary():
    rows = _rows()
    for row in rows:
        row["quality"] = False
    out = summarize(rows)
    contrast = out["contrasts"]["single_roles_minus_single_neutral"]
    assert contrast["two_sided_p"] == 1.0
    assert contrast["t_statistic"] == 0.0
    assert contrast["degenerate_difference_vector"] is True
    assert all(out["contrasts"][name]["holm_p"] is not None for name in out["contrasts"])


def test_single_observed_task_cannot_be_significant_and_missing_bounds_keep_all_assignments():
    rows=_rows()
    for row in rows:
        if row['arm']=='single_roles' and row['task_id']!='t0':row['quality']=None
    rows=[r for r in rows if not(r['task_id']=='t999' and r['arm']=='single_roles' and r['replicate_id']==103)]
    out=summarize(rows)
    assert out['contrasts']['single_roles_minus_single_neutral']['eligible_tasks']==1
    assert out['contrasts']['single_roles_minus_single_neutral']['two_sided_p'] is None
    assert out['contrasts']['single_roles_minus_single_neutral']['holm_p'] is None
    arm=next(x for x in out['by_arm'] if x['arm']=='single_roles')
    assert arm['assigned']==3000 and arm['recorded_assignments']==2999
