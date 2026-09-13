import json
from pathlib import Path

import pytest

from reproducibility.scc2000.presentation import appendix_table, display_code, render
from reproducibility.evidence_manifest import write as write_evidence
from reproducibility.scc2000.analyze import analyze, _digest


def test_display_codes_keep_unknown_and_separate_format_failure():
    base = {"control_eligible": True, "observed_candidate": True, "native_status": None,
            "format_extracted": None, "quality": None}
    assert display_code(base) == "N"
    fail = {**base, "quality": False, "format_extracted": False}
    assert display_code(fail) == "X"
    unavailable = {**base, "observed_candidate": False}
    assert display_code(unavailable) == "G"
    ineligible = {**base, "control_eligible": False}
    assert display_code(ineligible) == "U"


def _archive(tmp_path: Path) -> Path:
    root = tmp_path / "archive"
    for directory in (root / "analysis", root / "amended-analysis", root / "generation", root / "amendment", root / "controls"):
        directory.mkdir(parents=True)
    rows, ids, cells = [], [], []
    # 956 tasks and 2,000 blocks: 88 tasks have three selected repeats, the rest two.
    for task_no in range(956):
        reps = (101, 102, 103) if task_no < 88 else (101, 102)
        for rep in reps:
            for method in ("scc_author_2024_codex_transport", "single_roles", "single_neutral"):
                ident = f"cell-{task_no}-{method}-{rep}"; ids.append(ident)
                cells.append({"id": ident, "task_id": f"BigCodeBench/{task_no}", "method": method, "replicate_id": rep})
                rows.append({"id": ident, "task_id": f"BigCodeBench/{task_no}", "method": method,
                             "replicate_id": rep, "generation_complete": True,
                             "observed_candidate": True, "availability": True,
                             "format_extracted": True, "native_status": "pass", "quality": True,
                             "outcome_type": "success", "status_state": "completed",
                             "resource_usage": {"turns":1,"known_turns":1,"unknown_turns":0,"invalid_usage":[],
                                 "input_tokens":100,"cached_input_tokens":0,"output_tokens":100,
                                 "known_api_equivalent_usd":0.001 if method=='single_neutral' else 0.002}})
    assert len(rows) == 6000
    tasks = [f'BigCodeBench/{i}' for i in range(956)]
    eligible = tasks[:941]
    for row in rows:
        if row['task_id'] not in eligible:
            row['quality'] = None
    selection = {'selected_ids': ids, 'selected_cells': cells, 'selected_cells_digest': _digest(cells)}
    gate = {'schema':'scale1000-control-gate-v1', 'controls_complete':True, 'assigned_task_ids':tasks,
        'evaluable_task_ids':eligible, 'selection_sha256':'synthetic'}
    source = {'schema':'source-task-overlap-v1', 'selection_sha256':'synthetic',
        'partitions':{key:{'assigned_components':[[task] for task in tasks]} for key in
            ('union_070_code_exact','prompt_050','prompt_070','prompt_090')}}
    summary = analyze(rows, selection, gate, source, draws=19)
    summary = {key:value for key,value in summary.items() if key not in ('draws','per_task_contrasts','assignment_diagnostics')}
    (root / "selected_assignment_records.jsonl").write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    (root / "amendment" / "selection_manifest.json").write_text(json.dumps(selection), encoding="utf-8")
    (root / "controls" / "heldout200_control_gate.json").write_text(json.dumps(gate), encoding="utf-8")
    (root / "generation" / "manifest.json").write_text("{}", encoding="utf-8")
    (root / "generation" / "status.json").write_text(json.dumps({"state": "paused"}), encoding="utf-8")
    (root / "generation" / "continuation_status.json").write_text(json.dumps({"state": "completed"}), encoding="utf-8")
    (root / "amended-analysis" / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    write_evidence(root)
    return root


def test_render_writes_exact_selected_csv_and_em_dash_appendix(tmp_path):
    root = _archive(tmp_path)
    output = tmp_path / "presentation"
    report = render(root, output)
    assert report["selected_rows"] == 6000
    assert sum(1 for _ in (output / "selected_6000_rows.csv").open(encoding="utf-8")) == 6001
    appendix = (output / "appendix_en.tex").read_text(encoding="utf-8")
    assert "—" in appendix
    assert r'\multicolumn{3}{c}{SCC}' in appendix and '101 & 102 & 103' in appendix
    assert appendix.count("\\begin{table}") == 24
    assert appendix.count("\\clearpage") == 24


def test_render_requires_completed_final_analysis_and_manifest(tmp_path):
    root = tmp_path / "archive"; root.mkdir()
    with pytest.raises(ValueError, match="final analysis/manifest"):
        render(root, tmp_path / "output")


def test_appendix_rejects_invalid_language():
    with pytest.raises(ValueError):
        appendix_table([], "xx")


def test_render_rejects_tampered_selected_identity(tmp_path):
    root = _archive(tmp_path)
    path = root / "selected_assignment_records.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0]); first["method"] = "single_neutral"
    lines[0] = json.dumps(first); path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # The evidence manifest binds bytes, so tampering is caught before projection.
    with pytest.raises(ValueError, match="EVIDENCE_MANIFEST"):
        render(root, tmp_path / "output")
