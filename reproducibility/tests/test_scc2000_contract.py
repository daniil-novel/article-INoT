"""Independent contract tests for the amended SCC analyzer.

Rows are synthetic.  Only frozen allocation/control/source metadata are read;
candidate responses and benchmark outcomes are never loaded.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from reproducibility.scc2000.analyze import analyze

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "reproducibility/scc2000/freeze-v3"
METHODS = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")


def _metadata():
    selection = json.loads((FREEZE / "selection_manifest.json").read_text(encoding="utf-8"))
    gate = json.loads((FREEZE / "control_gate.json").read_text(encoding="utf-8"))
    source_dir = ROOT / "reproducibility/task_dependence/source-audit-v2"
    source = json.loads((source_dir / "summary.json").read_text(encoding="utf-8"))
    source["partitions"] = json.loads((source_dir / "partitions.json").read_text(encoding="utf-8"))
    tasks = sorted({c["task_id"] for c in selection["selected_cells"]})
    eligible = set(map(str, gate["evaluable_task_ids"])) & set(tasks)
    return selection, gate, source, tasks, eligible


def _rows():
    selection, gate, source, tasks, eligible = _metadata()
    rows = []
    for i,cell in enumerate(selection["selected_cells"]):
        method = cell["method"]
        task = cell["task_id"]
        quality = None if task not in eligible else (method != "single_neutral" or i % 5 != 0)
        rows.append({**cell, "quality": quality,
                     "resource_usage": {"turns": 2, "known_turns": 2, "unknown_turns": 0,
                                         "input_tokens": 10 + i, "cached_input_tokens": 0,
                                         "output_tokens": 20, "known_api_equivalent_usd": 0.01},
                     "generation_complete": True,"status_state":"completed"})
    return rows, selection, gate, source, tasks, eligible


def test_actual_metadata_synthetic_mix_and_matched_repeats():
    rows, selection, gate, source, tasks, eligible = _rows()
    out = analyze(rows, selection, gate, source, draws=7)
    c = out["contrasts"]["scc_author_2024_codex_transport-minus-single_neutral"]
    assert out["selected_rows"] == 6000
    assert out["task_count"] == 956
    assert out["eligible_task_count"] == 941
    assert c["n_tasks"] <= 941
    assert set(c["contributing_task_ids"]) <= eligible
    assert len(out["draws"]["quality"]["scc_author_2024_codex_transport-minus-single_neutral"]) == 7


def test_identity_and_control_ineligible_quality_rejected():
    rows, selection, gate, source, tasks, eligible = _rows()
    selection["selected_cells"][0]["task_id"] = "tampered"
    with pytest.raises(ValueError):
        analyze(rows, selection, gate, source, draws=3)
    rows, selection, gate, source, tasks, eligible = _rows()
    excluded = next(t for t in tasks if t not in eligible)
    next(r for r in rows if r["task_id"] == excluded)["quality"] = False
    with pytest.raises(ValueError, match="control-ineligible"):
        analyze(rows, selection, gate, source, draws=3)


def test_known_counters_do_not_make_incomplete_workflow_resource_complete():
    rows, selection, gate, source, *_ = _rows()
    target = rows[0]
    baseline=analyze(rows,selection,gate,source,draws=3)
    for row in rows:
        if row["task_id"]==target["task_id"] and row["method"]=="single_roles":
            row["generation_complete"] = False
    out = analyze(rows, selection, gate, source, draws=3)
    resource = out["resources"]["scc_author_2024_codex_transport-minus-single_roles"]
    assert baseline["resources"]["scc_author_2024_codex_transport-minus-single_roles"]["complete_task_pairs"]==956
    assert resource["complete_task_pairs"]==955


def test_cli_writes_numeric_draws_without_pickle_or_extra_workspace_files(tmp_path):
    rows, selection, gate, source, *_ = _rows()
    records = tmp_path / "records.jsonl"
    records.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    paths = {}
    for name, value in (("selection.json", selection), ("gate.json", gate), ("source.json", source)):
        path = tmp_path / name; path.write_text(json.dumps(value), encoding="utf-8"); paths[name] = path
    out = tmp_path / "out"
    before = sorted(p.name for p in tmp_path.iterdir())
    subprocess.run([sys.executable, "-m", "reproducibility.scc2000.analyze", "--records", str(records),
                    "--selection", str(paths["selection.json"]), "--control-gate", str(paths["gate.json"]),
                    "--source-audit", str(paths["source.json"]), "--out", str(out), "--draws", "7"],
                   cwd=ROOT, check=True)
    assert (out / "summary.json").is_file()
    arrays = list((out / "draws").rglob("*.npy"))
    assert arrays and all(np.load(path, allow_pickle=False).dtype.kind == "f" for path in arrays)
    assert sorted(p.name for p in tmp_path.iterdir() if p != out) == before


def test_pairing_uses_only_same_repeat_and_bounds_keep_assigned_denominator():
    rows,selection,gate,source,tasks,eligible=_rows()
    task=next(t for t in tasks if t in eligible and sum(r["task_id"]==t for r in rows)==9)
    for row in rows:
        if row["task_id"]==task:
            if row["method"]==METHODS[2]: row["quality"]={101:True,102:False,103:None}[row["replicate_id"]]
            if row["method"]==METHODS[1]: row["quality"]={101:None,102:True,103:False}[row["replicate_id"]]
    out=analyze(rows,selection,gate,source,draws=5)
    name=METHODS[2]+"-minus-"+METHODS[1]
    entry=next(x for x in out["per_task_contrasts"] if x["task_id"]==task and x["contrast"]==name)
    assert entry["replicate_ids"]==[102] and entry["difference"]==-1
    bounds=out["bounds"]["eligible_selected"][name]
    assert bounds["upper"]-bounds["lower"]==pytest.approx(2/(3*941))
