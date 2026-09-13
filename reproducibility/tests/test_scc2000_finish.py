import json

import pytest

from reproducibility.scc2000 import finish


def setup_generation(tmp_path, states):
    generation = tmp_path / "generation"
    for ident, state in states.items():
        folder = generation / "assignments" / ident; folder.mkdir(parents=True)
        (folder / "status.json").write_text(json.dumps({"state": state}), encoding="utf-8")
    (generation / "status.json").write_text(json.dumps({"state": "paused"}), encoding="utf-8")
    return generation


def selection(ids):
    return {"selected_ids": ids}


def test_finish_requires_all_selected_terminal(tmp_path):
    ids = [f"{i}" for i in range(6000)]; setup_generation(tmp_path, {"a": "completed"})
    sel = tmp_path / "selection.json"; sel.write_text(json.dumps(selection(ids)), encoding="utf-8")
    with pytest.raises(ValueError, match="untouched"):
        finish.run(root=tmp_path, inputs=tmp_path, gate_dir=tmp_path, manifest=tmp_path / "m", selection_manifest=sel)


def test_finish_refuses_lock_without_mutating(tmp_path):
    setup_generation(tmp_path, {"a": "completed"}); lock = tmp_path / "generation" / "DISPATCH.lock"; lock.write_bytes(b"123")
    sel = tmp_path / "selection.json"; sel.write_text(json.dumps(selection([f"{i}" for i in range(6000)])), encoding="utf-8")
    before = lock.read_bytes()
    with pytest.raises(ValueError, match="lock"):
        finish.run(root=tmp_path, inputs=tmp_path, gate_dir=tmp_path, manifest=tmp_path / "m", selection_manifest=sel)
    assert lock.read_bytes() == before


def test_selected_view_retains_only_prefix_rows(tmp_path):
    pred = tmp_path / "predictions"; pred.mkdir()
    rows = [{"id": "a", "task_id": "t", "method": "m", "replicate_id": 101}, {"id": "b", "task_id": "u", "method": "m", "replicate_id": 102}]
    (pred / "candidate_records.jsonl").write_bytes(b"".join(finish.cli.canonical(r) + b"\n" for r in rows))
    result = finish._write_selected_view(pred, {"a", "b"})
    assert result["rows"] == 2


def test_existing_partial_export_is_validated(tmp_path, monkeypatch):
    monkeypatch.setattr(finish,"_verify_prefix",lambda *a:None)
    ids = [f"{i}" for i in range(6000)]; setup_generation(tmp_path, {i: "completed" for i in ids}); sel = tmp_path / "selection.json"; sel.write_text(json.dumps(selection(ids)), encoding="utf-8")
    predictions = tmp_path / "predictions"; predictions.mkdir(); (predictions / "export_manifest.json").write_text("{}", encoding="utf-8")
    called = []
    monkeypatch.setattr(finish.scc_export, "validate_export", lambda *a: (_ for _ in ()).throw(ValueError("partial")))
    with pytest.raises(ValueError, match="partial"):
        finish.run(root=tmp_path, inputs=tmp_path, gate_dir=tmp_path, manifest=tmp_path / "m", selection_manifest=sel)


def test_finish_runs_all_nine_native_groups_and_uses_row_id(tmp_path, monkeypatch):
    monkeypatch.setattr(finish,"_verify_prefix",lambda *a:None)
    ids = [f"{i}" for i in range(6000)]; setup_generation(tmp_path, {i: "completed" for i in ids})
    sel = tmp_path / "selection.json"; sel.write_text(json.dumps(selection(ids)), encoding="utf-8")
    gate_dir = tmp_path / "gate"; gate_dir.mkdir(); (gate_dir / "heldout200_control_gate.json").write_text(json.dumps({"image_id": "img", "evaluable_task_ids": []}), encoding="utf-8")
    pred = tmp_path / "predictions"
    manifest = tmp_path / "manifest"; manifest.write_text(json.dumps({"methods": list(finish.scc_export.scc_dispatch.METHODS), "replicate_ids": [101, 102, 103]}), encoding="utf-8")
    monkeypatch.setattr(finish, "environment_from_gate", lambda p: {"image_id": "img"})
    monkeypatch.setattr(finish.scc_finish, "_image_id", lambda image: "img")
    monkeypatch.setattr(finish, "_read", lambda p: json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"state": "paused"})
    def fake_export(*args):
        pred.mkdir(); rows = [{"id": i, "task_id": "t", "method": "m", "replicate_id": 101} for i in ids]
        (pred / "assignment_records.jsonl").write_bytes(b"".join(finish.cli.canonical(r) + b"\n" for r in rows))
        for m in finish.scc_export.scc_dispatch.METHODS:
            for rep in (101, 102, 103): (pred / f"{m}-r{rep}.jsonl").write_text('{"task_id":"t","solution":"x"}\n', encoding="utf-8")
        return {"rows": 9000}
    calls = []
    monkeypatch.setattr(finish, "validate_native", lambda *a: {"ok": True, "statuses": {}})
    def fake_native(stage, target, argv): calls.append(stage.name); stage.mkdir(parents=True, exist_ok=True); finish.cli.save(stage / "exit.json", {"returncode": 0})
    monkeypatch.setattr(finish.scc_finish, "_run_analysis_stage", lambda *a: tmp_path / "analysis.json")
    monkeypatch.setattr(finish.scc_finish, "_records", lambda *a: [{"id": i, "task_id": "t", "method": "m", "replicate_id": 101, "resource_usage": {}, "availability": "completed"} for i in ids])
    amended_calls=[]
    def amended(*args): amended_calls.append(args); return tmp_path / "amended-analysis"
    result = finish.run(root=tmp_path, inputs=tmp_path, gate_dir=gate_dir, manifest=manifest, selection_manifest=sel, export_fn=fake_export, native_stage_fn=fake_native,analyze_fn=amended)
    assert len(calls) == 9 and result["native_groups"] == 9
    assert len(amended_calls)==1 and amended_calls[0][0]==tmp_path
    assert (tmp_path / "selected_assignment_records.jsonl").is_file()
    assert not (pred / "selected_assignment_records.jsonl").exists()


def test_finish_rejects_substituted_prefix(monkeypatch,tmp_path):
    monkeypatch.setattr(finish.scc_export,"_expected",lambda *a:({},[{"id":"a"}]))
    with pytest.raises(ValueError,match="prefix"):
        finish._verify_prefix({"selected_ids":["b"],"selected_cells":[{"id":"b"}]},tmp_path,tmp_path,tmp_path)
