import pytest

from reproducibility.scc2000.analyze import analyze, _digest, family_bootstrap, _t_test, _holm


METHODS = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")


def ledger():
    rows = []
    for block in range(2000):
        task = f"task-{block % 956}"
        rep = (101 + block % 3)
        for method in METHODS:
            rows.append({"id": f"{block}-{method}", "task_id": task, "replicate_id": rep,
                         "method": method, "quality": method != "single_neutral",
                         "generation_complete": True,"status_state":"completed",
                         "resource_usage":{"turns":1,"known_turns":1,"unknown_turns":0,"invalid_usage":[],
                            "input_tokens":10,"cached_input_tokens":0,"output_tokens":10 if method==METHODS[1] else 20,
                            "known_api_equivalent_usd":1 if method==METHODS[1] else 2}})
    return rows


@pytest.fixture
def inputs():
    rows = ledger(); ids = [r["id"] for r in rows]
    tasks = sorted({r["task_id"] for r in rows})
    cells=[{k:r[k] for k in ("id","task_id","method","replicate_id")} for r in rows]
    return rows, {"selected_ids":ids,"selected_cells":cells,"selected_cells_digest":_digest(cells)}, {
        "schema":"scale1000-control-gate-v1","selection_sha256":"synthetic","controls_complete":True,
        "assigned_task_ids":tasks,"evaluable_task_ids":tasks},{"schema":"source-task-overlap-v1",
        "selection_sha256":"synthetic","partitions":{"union_070_code_exact":{"assigned_components":[[t] for t in tasks]}}}


def test_task_means_and_unknown_are_preserved(inputs):
    rows, selection, gate, source = inputs
    for row in rows:
        if row["task_id"] == "task-0" and row["method"] == "single_neutral":
            row["quality"] = None
    out = analyze(rows, selection, gate, source, draws=9)
    contrast = out["contrasts"]["scc_author_2024_codex_transport-minus-single_neutral"]
    assert contrast["n_tasks"] < out["task_count"]
    assert out["unknown_is_not_false"] is True
    assert len(out["draws"]["quality"]["scc_author_2024_codex_transport-minus-single_neutral"]) == 9


def test_partial_resource_workflow_is_excluded(inputs):
    rows, selection, gate, source = inputs
    for row in rows:
        if row["task_id"] == "task-0" and row["method"] == "scc_author_2024_codex_transport":
            row["generation_complete"] = False
            row["resource_usage"].update(turns=2,known_turns=1,unknown_turns=1)
    out = analyze(rows, selection, gate, source, draws=5)
    assert out["resources"]["scc_author_2024_codex_transport-minus-single_neutral"]["complete_task_pairs"] < out["task_count"]


def test_duplicate_and_invalid_quality_fail_closed(inputs):
    rows, selection, gate, source = inputs
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="duplicate record ID"):
        analyze(rows, selection, gate, source, draws=3)
    rows, selection, gate, source = inputs
    rows[0]["quality"] = 1
    with pytest.raises(ValueError, match="quality"):
        analyze(rows, selection, gate, source, draws=3)


def test_component_bootstrap_keeps_related_tasks_together():
    entry,draws=family_bootstrap({"a":1.,"b":1.,"c":0.},[["a","b"],["c"]],draws=100)
    assert entry["component_count"]==2 and entry["task_count"]==3
    assert set(draws)<={0.,2/3,1.}
    with pytest.raises(ValueError): family_bootstrap({"a":1,"b":1},[["a"]],draws=3)


def test_unestimable_test_keeps_fixed_holm_slot():
    a=_t_test([1.,1.,1.]); assert a["p_two_sided"] is None
    assert _holm({"a":a["p_two_sided"],"b":.02})=={"b":.04,"a":1.}
    assert _t_test([0.,0.,0.])["p_two_sided"]==1.
