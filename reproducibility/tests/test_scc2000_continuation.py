import json
from pathlib import Path

import pytest

from reproducibility.scc2000 import continuation as c


def schedule(n=2001):
    out = []
    for i in range(n):
        for method in c.METHODS:
            out.append({"id": f"{i:04d}-{method}", "task_id": f"t{i}",
                        "replicate_id": 101 + i % 3, "method": method})
    return out


def test_first_2000_whole_blocks_and_order():
    got = c.selected_prefix(schedule())
    assert len(got) == 6000
    assert got == schedule()[:6000]
    assert got[-1]["task_id"] == "t1999"


def test_partial_or_malformed_block_refused():
    with pytest.raises(ValueError):
        c.selected_prefix(schedule()[:5999])
    bad = schedule(); bad[1]["method"] = "outside"
    with pytest.raises(ValueError):
        c.selected_prefix(bad)


def test_adapter_submits_only_selected_and_restores(monkeypatch):
    calls = []
    def fake(pending, payload_for, executor, workers, known, guard, progress=None):
        calls.append([x["id"] for x in pending])
        return {"pending": [], "results": [], "known": known, "stop_reason": None, "max_inflight": workers}
    monkeypatch.setattr(c.scc_dispatch, "coordinate_assignments", fake)
    original = c.scc_dispatch.coordinate_assignments
    cells = [{"id": str(i)} for i in range(4)]
    with c.selection_adapter({"1", "3"}):
        result = c.scc_dispatch.coordinate_assignments(cells, None, None, 8, 0, 65)
    assert calls == [["1", "3"]]
    assert [x["id"] for x in result["pending"]] == ["0", "2"]
    assert c.scc_dispatch.coordinate_assignments is original


def test_status_requires_all_selected_terminal_and_no_lock(tmp_path):
    selected = {"a", "b"}
    for ident, state in (("a", "completed"), ("b", "paused")):
        folder = tmp_path / "assignments" / ident; folder.mkdir(parents=True)
        (folder / "status.json").write_text(json.dumps({"state": state}), encoding="utf-8")
    lock = tmp_path / "DISPATCH.lock"; lock.write_text("1", encoding="utf-8")
    assert c.continuation_status(root=tmp_path, selected_ids=selected, lock=lock)["state"] == "paused"
    lock.unlink()
    assert c.continuation_status(root=tmp_path, selected_ids=selected, lock=lock)["state"] == "completed"


def test_recovery_rejects_completed_turn_and_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "process_inventory", lambda *a: [])
    assignments = tmp_path / "assignments"
    for i in range(8):
        folder = assignments / str(i); turn = folder / "turns" / "000"; turn.mkdir(parents=True)
        (folder / "status.json").write_text(json.dumps({"state": "initializing"}), encoding="utf-8")
        (turn / "events.jsonl").write_text('{"type":"turn.started"}\n', encoding="utf-8")
    (assignments / "0" / "turns" / "000" / "result.json").write_text("{}", encoding="utf-8")
    (tmp_path / "DISPATCH.lock").write_text("26200", encoding="utf-8")
    pause = tmp_path / "pause.json"
    pause.write_text(json.dumps(dict(reason="user_subscription_reserve", remaining_percent=55, allow_model_work=False)), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly eight"):
        c.recover(original_root=tmp_path, recovery=tmp_path / "recovery", historical_pause=pause)
    assert not (tmp_path / "recovery").exists()


def test_mixed_task_block_refused():
    bad = schedule(); bad[1]["task_id"] = "foreign"
    with pytest.raises(ValueError, match="non-factorial"):
        c.selected_prefix(bad)


def test_windows_venv_recovery_parent_is_not_a_generator(tmp_path):
    c.assert_recovery_idle(tmp_path / "DISPATCH.lock", [dict(pid=123,module="reproducibility.scc2000.continuation",action="recover",cwd_matches=True)])
    with pytest.raises(RuntimeError):
        c.assert_recovery_idle(tmp_path / "DISPATCH.lock", [dict(pid=123,module="reproducibility.scc2000.continuation",action="generate",cwd_matches=True)])


@pytest.mark.parametrize("remaining,age,allow", [(65,0,True),(True,0,True),(float('nan'),0,True),(66,76,True),(66,0,False)])
def test_heartbeat_fails_closed(tmp_path, remaining, age, allow):
    path=tmp_path / "latest.json"
    path.write_text(json.dumps(dict(remaining_percent=remaining,reserve_percent=65,checked_unix=100-age,allow_model_work=allow)),encoding="utf-8")
    with pytest.raises(RuntimeError): c.require_fresh_heartbeat(path,now=100)


def test_heartbeat_valid_then_latched(tmp_path):
    path=tmp_path / "latest.json"
    path.write_text(json.dumps(dict(remaining_percent=66,reserve_percent=65,checked_unix=99,allow_model_work=True)),encoding="utf-8")
    c.require_fresh_heartbeat(path,now=100)
    (tmp_path / "PAUSED.json").write_text('{}')
    with pytest.raises(RuntimeError): c.require_fresh_heartbeat(path,now=100)


def test_inventory_retains_same_basename_in_different_turns(tmp_path):
    root = tmp_path / "assignments" / "a"
    for turn in ("000", "001"):
        path = root / "turns" / turn
        path.mkdir(parents=True)
        (path / "events.jsonl").write_text(turn, encoding="utf-8")
    inv = c._inventory(tmp_path, {"a"})["assignments"][0]["files_sha256"]
    assert set(inv) == {"turns/000/events.jsonl", "turns/001/events.jsonl"}
    assert len(set(inv.values())) == 2


@pytest.mark.parametrize("pid,module,cwd", [(26200, None, False), (99, "reproducibility.revision_20260911.scc_dispatch", True)])
def test_live_or_reused_pid_refused_before_mutation(tmp_path, monkeypatch, pid, module, cwd):
    lock = tmp_path / "DISPATCH.lock"; lock.write_text("26200", encoding="utf-8")
    monkeypatch.setattr(c, "process_inventory", lambda *a: [dict(pid=pid,module=module,cwd_matches=cwd)])
    with pytest.raises(RuntimeError, match="before mutation"):
        c.recover(original_root=tmp_path, recovery=tmp_path / "recovery", historical_pause=tmp_path / "missing")
    assert lock.read_text() == "26200"
    assert not (tmp_path / "recovery").exists()


def test_full_recovery_preserves_bytes_and_detects_tamper(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "process_inventory", lambda *a: [])
    root = tmp_path / "generation"; root.mkdir()
    (root / "DISPATCH.lock").write_text("26200", encoding="utf-8")
    for i in range(8):
        folder = root / "assignments" / str(i); turn = folder / "turns" / "000"; turn.mkdir(parents=True)
        (folder / "status.json").write_bytes(b'{"state":"initializing"}\r\n')
        (turn / "events.jsonl").write_bytes(b'{"type":"turn.started"}\n')
    pause = tmp_path / "pause.json"
    pause.write_text(json.dumps(dict(reason="user_subscription_reserve",remaining_percent=55,allow_model_work=False)),encoding="utf-8")
    selection = {"old_inventory": c._inventory(root, {str(i) for i in range(8)})}
    recovery = tmp_path / "recovery"
    result = c.recover(original_root=root, recovery=recovery, historical_pause=pause)
    assert result["recovered"] == 8 and not (root / "DISPATCH.lock").exists()
    assert c.validate_recovery(selection, recovery / "recovery_manifest.json")["old_assignments_verified"] == 8
    assert (recovery / "assignments/0/status.json").read_bytes() == b'{"state":"initializing"}\r\n'
    (root / "assignments/0/turns/000/events.jsonl").write_text("tampered",encoding="utf-8")
    with pytest.raises(ValueError, match="bytes changed"):
        c.validate_recovery(selection, recovery / "recovery_manifest.json")


def test_changed_manifest_source_is_refused(tmp_path, monkeypatch):
    frozen = {"planned_assignments": 9000, "order_seed": 20260911, "model": "gpt-5.6-luna", "reasoning_effort": "medium", "cli_version": "codex-cli 0.153.4", "workers": 8, "generated_test_parallelism": 1, "source_files_sha256": {}}
    monkeypatch.setattr(c, "_validate_frozen", lambda *a: (frozen, schedule(3000)))
    amendment = tmp_path / "amendment.md"; amendment.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Touched assignment"):
        touched = tmp_path / "old" / "assignments" / "outside"; touched.mkdir(parents=True)
        (touched / "status.json").write_text("{}", encoding="utf-8")
        c.prepare(original_root=tmp_path / "old", inputs=tmp_path / "inputs", gate_dir=tmp_path / "gate", manifest=tmp_path / "manifest", amendment=amendment, output=tmp_path / "out")
