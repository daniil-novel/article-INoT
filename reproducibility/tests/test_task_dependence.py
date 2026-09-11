import json

import numpy as np
import pytest

from reproducibility.task_dependence import audit, sensitivity


def test_ast_removes_docstrings_but_preserves_behavioral_literals():
    left = audit.code_features('def f(x):\n    "explanation"\n    return x + 1\n')
    same = audit.code_features('def f(x):\n    # another explanation\n    return x + 1\n')
    other = audit.code_features('def f(x):\n    return x + 2\n')
    assert left == same
    assert left["ast_sha256"] != other["ast_sha256"]
    assert '"explanation"' not in left["tokens"]


def test_shared_starter_is_not_identical_task_instruction():
    starter = audit.STARTER + "\n```\ndef task_func(x):\n```"
    a, sa = audit.prompt_features("Sort these values into ascending order.\n" + starter)
    b, sb = audit.prompt_features("Plot these values as a scatter graph.\n" + starter)
    assert a != b and sa.isdisjoint(sb)
    assert audit.jaccard(set(), set()) == (0, 0)


def test_graph_connectivity_keeps_transitive_groups_and_singletons():
    assert audit.components(["d", "c", "b", "a"], [("a", "b"), ("b", "c")]) == [["a", "b", "c"], ["d"]]


def test_family_resampling_keeps_task_weighted_estimand():
    report, draws = sensitivity.family_bootstrap({"a": 0, "b": 0, "c": 0, "d": 1},
        [["a", "b", "c"], ["d"]], draws=10000)
    assert report["mean_task_difference"] == .25
    assert report["family_balanced_difference"] == .5
    assert set(draws) == {0, .25, 1}
    assert report["ci95"] == [0, 1] and report["families"] == 2
    assert report["size_effective_family_count"] == 1.6


def test_family_overlap_and_missing_ids_are_rejected():
    with pytest.raises(ValueError, match="overlap"):
        sensitivity.family_bootstrap({"a": 0}, [["a"], ["a"]])
    with pytest.raises(ValueError, match="omit"):
        sensitivity.family_bootstrap({"a": 0, "b": 1}, [["a"]])
    result, draws = sensitivity.family_bootstrap({"a": 0}, [["a"]])
    assert result["ci95"] is None and draws.size == 0


def test_repeats_are_averaged_before_families_and_missing_pair_is_not_filled():
    rows = []
    for task in ("a", "b"):
        for method in ("single_roles", "single_neutral", "multi_roles", "multi_neutral", "direct"):
            for repeat in sensitivity.REPEATS:
                quality = method == "single_roles" and repeat == 101
                if task == "b" and method == "single_neutral" and repeat == 102: quality = None
                rows.append({"task_id": task, "arm": method, "replicate_id": repeat, "quality": quality})
    actual = sensitivity.paired_means(rows, {"a", "b"}, {"a", "b"}, "factorial")
    assert actual["single_roles_minus_single_neutral"] == {"a": 1 / 3}
    with pytest.raises(ValueError, match="complete"):
        sensitivity.paired_means(rows[:-1], {"a", "b"}, {"a", "b"}, "factorial")


def test_active_generation_is_never_analyzed(tmp_path):
    run = tmp_path / "run"; (run / "generation").mkdir(parents=True)
    (run / "generation/status.json").write_text(json.dumps({"state": "running"}))
    with pytest.raises(ValueError, match="not terminal"):
        sensitivity.run(run, "factorial", tmp_path / "audit", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_identical_differences_flag_degenerate_bootstrap():
    report, draws = sensitivity.family_bootstrap({"a": 0, "b": 0}, [["a"], ["b"]])
    assert report["degenerate_draws"] and report["interval_status"] == "degenerate"
    assert np.array_equal(draws, np.zeros(10000))
