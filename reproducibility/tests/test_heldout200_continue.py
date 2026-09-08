import json
from pathlib import Path

import pytest

from reproducibility.heldout200 import continue_unsubmitted as cont


def make_parent(tmp_path: Path):
    parent = tmp_path / "parent"
    (parent / "shards").mkdir(parents=True)
    (parent / "inputs").mkdir()
    cells = []
    for i in range(4):
        name = f"r4-s{i}"
        shard = parent / "shards" / name
        (shard / "turns").mkdir(parents=True)
        (shard / "cells").mkdir()
        (parent / "inputs" / name).mkdir()
        cell = {"id": f"cell-{i}", "task_id": f"task-{i}", "replicate_id": 4,
                "arm": "direct", "cli_turns": 1}
        cells.append(cell)
        json.dump({"cells": [cell]}, (shard / "manifest.json").open("w"))
        json.dump({"state": "completed"}, (shard / "status.json").open("w"))
        json.dump({"state": "completed"}, (parent / "inputs" / name / "completion.json").open("w"))
    json.dump({"state": "completed"}, (parent / "status.json").open("w"))
    json.dump({"shards": [{"name": f"r4-s{i}", "manifest": {"cells": [cells[i]]}} for i in range(4)]}, (parent / "manifest.json").open("w"))
    return parent, cells


def source_files(tmp_path: Path):
    root = tmp_path / "src"
    for name in cont.DEPENDENCIES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    protocol = tmp_path / "protocol.md"; protocol.write_text("fixture", encoding="utf-8")
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("\n".join(json.dumps({"task_id": f"task-{i}", "prompt": "p", "context": "c", "benchmark": "bigcodebench", "metadata": {}}) for i in range(4)) + "\n", encoding="utf-8")
    return root, protocol, tasks


def test_stage_zero_exists_is_never_pending(tmp_path):
    parent, cells = make_parent(tmp_path)
    (parent / "shards" / "r4-s0" / "turns" / "cell-0-0").mkdir()
    inventory = cont.original_inventory(parent)
    assert [x["id"] for x in cont.pending_cells(parent, inventory)] == ["cell-1", "cell-2", "cell-3"]


def test_nonterminal_parent_is_rejected(tmp_path):
    parent, _ = make_parent(tmp_path)
    (parent / "status.json").write_text('{"state":"started"}', encoding="utf-8")
    with pytest.raises(ValueError, match="parent archive is not terminal"):
        cont.original_inventory(parent)


def test_changed_parent_archive_is_rejected(tmp_path):
    parent, _ = make_parent(tmp_path); source, protocol, tasks = source_files(tmp_path)
    json.dump([json.loads(line) for line in tasks.read_text(encoding="utf-8").splitlines()], (parent / "tasks.json").open("w"))
    frozen = tmp_path / "continuation.json"
    cont.freeze(tasks, parent, protocol, source, frozen)
    (parent / "manifest.json").write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="parent archive changed|shard manifest differs"):
        cont.validate_frozen(cont.read_json(frozen), tasks, parent, protocol, source)


def test_failed_cell_is_not_retried_and_next_cell_runs(tmp_path):
    archive = tmp_path / "archive"; archive.mkdir()
    tasks = {f"task-{i}": {"task_id": f"task-{i}", "prompt": "p", "context": "c"} for i in range(2)}
    cells = [{"id": f"cell-{i}", "task_id": f"task-{i}", "replicate_id": 4, "arm": "direct", "cli_turns": 1} for i in range(2)]
    calls = []

    def fake_transport(folder, command, prompt, timeout):
        calls.append(folder.name)
        if folder.name.startswith("cell-0"):
            raise ValueError("CLI timeout")
        return {"final_text": "ok", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}, "api_equivalent_usd": 0.0, "uncached_sensitivity_usd": 0.0, "wall_seconds": 0.0}

    result = cont.run_shard_cells("r4-s0", cells, tasks, archive, ["codex"], archive / "instructions.txt", transport=fake_transport)
    assert calls.count("cell-0-0") == 1
    assert calls.count("cell-1-0") == 1
    assert result["completed_generations"] == 1
    assert len(result["failures"]) == 1
    assert result["allocation_exhausted"] is True


def test_transport_uses_explicit_cli_prefix(tmp_path, monkeypatch):
    archive = tmp_path / "archive"; archive.mkdir(); seen = []
    tasks = {"task-0": {"task_id": "task-0", "prompt": "p", "context": "c"}}
    cell = {"id": "cell-0", "task_id": "task-0", "replicate_id": 4, "arm": "direct", "cli_turns": 1}
    original = cont.c.cli_command
    monkeypatch.setattr(cont.c, "cli_command", lambda prefix, cwd, instructions: seen.append(prefix) or original(prefix, cwd, instructions))
    def ok(folder, command, prompt, timeout):
        return {"final_text": "ok", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}, "api_equivalent_usd": 0.0, "uncached_sensitivity_usd": 0.0, "wall_seconds": 0.0}
    cont.run_shard_cells("r4-s0", [cell], tasks, archive, ["node", "explicit/codex.js"], archive / "instructions.txt", transport=ok)
    assert seen == [["node", "explicit/codex.js"]]


def test_generic_archived_provider_error_stops_continuation(tmp_path):
    turn = tmp_path / "turn"; turn.mkdir(); (turn / "stderr.txt").write_text("provider returned quota exceeded", encoding="utf-8")
    assert cont._failure_stops("CLI exit 1", turn) is True


def test_changed_task_source_is_rejected(tmp_path):
    parent, _ = make_parent(tmp_path); source, protocol, tasks = source_files(tmp_path)
    json.dump([json.loads(line) for line in tasks.read_text(encoding="utf-8").splitlines()], (parent / "tasks.json").open("w"))
    frozen = tmp_path / "continuation.json"; cont.freeze(tasks, parent, protocol, source, frozen)
    tasks.write_text(tasks.read_text(encoding="utf-8").replace('"task-0"', '"task-changed"'), encoding="utf-8")
    with pytest.raises(ValueError, match="task/protocol source changed"):
        cont.validate_frozen(cont.read_json(frozen), tasks, parent, protocol, source)
