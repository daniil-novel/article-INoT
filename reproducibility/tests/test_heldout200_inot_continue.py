import json
from pathlib import Path

import pytest

from reproducibility.heldout200 import inot_continue as cont


def fixture(tmp_path: Path):
    parent = tmp_path / "parent"; (parent / "turns").mkdir(parents=True); (parent / "cells").mkdir()
    tasks = [{"task_id": f"task-{i}", "prompt": "p", "context": "c", "benchmark": "bigcodebench", "metadata": {}} for i in range(2)]
    (parent / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")
    cells = [{"task_id": f"task-{i}", "arm": cont.inot.TREATMENT, "replicate_id": 5, "cli_turns": 1, "id": f"cell-{i}"} for i in range(2)]
    manifest = {"cells": cells, "task_ids": [t["task_id"] for t in tasks]}
    (parent / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (parent / "status.json").write_text('{"state":"blocked"}', encoding="utf-8")
    for name in ("protocol.md", "selection.json", "control-gate.json", "inot_source.py", "factorial_runner.py", "record_codex_runtime.py", "audit_codex_pilot.py", "runner_source.py", "runtime.json", "runtime_provenance.json", "npm-package.json", "npm-package-lock.json", "cli-package.json"):
        (parent / name).write_text(name, encoding="utf-8")
    source = tmp_path / "source"
    for name in cont.DEPENDENCIES:
        p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name, encoding="utf-8")
    paths = {"tasks": tmp_path / "tasks.jsonl", "protocol": tmp_path / "protocol.md", "selection": tmp_path / "selection.json", "gate": tmp_path / "gate.json"}
    paths["tasks"].write_text("\n".join(json.dumps(t) for t in tasks) + "\n", encoding="utf-8")
    for k in ("protocol", "selection", "gate"): paths[k].write_text(k, encoding="utf-8")
    (source/"revision").mkdir()
    (source/"revision/INOT_EXECUTION_AMENDMENT.md").write_text("fixture amendment")
    return parent, source, paths, cells, tasks


def test_timeout_cell_is_not_retried_and_next_runs(tmp_path):
    archive = tmp_path / "archive"; archive.mkdir(); (archive / "turns").mkdir(); (archive / "cells").mkdir(); (archive / "empty").mkdir()
    cells = [{"task_id": f"task-{i}", "arm": cont.inot.TREATMENT, "replicate_id": 5, "cli_turns": 1, "id": f"cell-{i}"} for i in range(2)]
    tasks = [{"task_id": f"task-{i}", "prompt": "p", "context": "c"} for i in range(2)]; calls=[]
    def fake(folder, command, prompt, timeout):
        calls.append(folder.name)
        if folder.name == "cell-0": raise ValueError("CLI timeout")
        return {"final_text":"ok", "usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}, "api_equivalent_usd":0,"uncached_sensitivity_usd":0,"wall_seconds":0}
    result=cont.run_cells(cells,tasks,archive,["node","codex.js"],archive/"instructions.txt",fake)
    assert calls == ["cell-0", "cell-1"]
    assert result["allocation_exhausted"] is True and result["completed"] == 1


def test_parent_change_rejected_after_freeze(tmp_path, monkeypatch):
    parent, source, paths, _, _ = fixture(tmp_path)
    monkeypatch.setattr(cont.inot_audit, "audit", lambda *args: {"status":"partial"})
    out = tmp_path / "continuation.json"
    cont.freeze(parent, paths["tasks"], paths["protocol"], paths["selection"], paths["gate"], source, out)
    (parent / "status.json").write_text('{"state":"blocked","changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="original INoT archive changed"):
        cont.validate(cont.c.read(out), parent, paths["tasks"], paths["protocol"], paths["selection"], paths["gate"], source)


def test_frozen_source_provenance_is_recorded(tmp_path, monkeypatch):
    parent, source, paths, _, _ = fixture(tmp_path)
    monkeypatch.setattr(cont.inot_audit, "audit", lambda *args: {"status":"partial"})
    out = tmp_path / "continuation.json"; manifest=cont.freeze(parent, paths["tasks"], paths["protocol"], paths["selection"], paths["gate"], source, out)
    assert manifest["pending_count"] == 2
    assert set(manifest["dependency_sha256"]) == set(cont.DEPENDENCIES)
