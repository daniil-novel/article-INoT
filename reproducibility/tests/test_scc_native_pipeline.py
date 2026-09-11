import json
from argparse import Namespace
import subprocess
import sys
import hashlib
import copy

import pytest

from reproducibility import codex_luna_subscription as cli
from reproducibility.revision_20260911 import scc_export, scc_finish
from reproducibility.revision_20260911 import scc_dispatch


def _cell():
    return {"id": "cell-1", "task_id": "BigCodeBench/1", "replicate_id": 101,
            "method": "single_roles", "max_upstream_round": 0, "cli_turns": 1}


def _task():
    return {"task_id": "BigCodeBench/1", "prompt": "Implement task", "context": "", "benchmark": "bigcodebench", "metadata": {}}


def _completed_assignment(tmp_path, answer=None):
    assignment = tmp_path / "cell-1"; (assignment / "turns/000").mkdir(parents=True)
    cell, task = _cell(), _task(); cli.save(assignment / "cell.json", cell); cli.save(assignment / "task.json", task)
    answer = answer or "```python\ndef task_func(x):\n    return x\n```"
    events = [{"type": "thread.started"}, {"type": "turn.started"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": answer}},
              {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 5}}]
    prompt = cli.prompt_for(task, {"arm": cell["method"], "cli_turns": 1}, 0, [])
    turn = assignment / "turns/000"
    (turn / "events.jsonl").write_bytes(b"\n".join(cli.canonical(x) for x in events) + b"\n")
    (turn / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    cli.save(turn / "argv.json", ["codex", "test"])
    (turn / "stderr.txt").write_bytes(b"")
    parsed = cli.parse_events((turn / "events.jsonl").read_bytes())
    result = {**parsed,
              "files_sha256": {n: hashlib.sha256((turn / n).read_bytes()).hexdigest()
                               for n in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")}}
    cli.save(turn / "result.json", result)
    cli.save(turn / "status.json", {"state": "completed"})
    cli.save(assignment / "requests.json", [{"prompt": prompt, "result": result}])
    cli.save(assignment / "turns/000.upstream_request.json", {"prompt": prompt})
    (assignment / "candidate.py").write_text("def task_func(x):\n    return x\n", encoding="utf-8")
    cli.save(assignment / "status.json", {"state": "completed"})
    return assignment, cell, task


def test_export_refuses_running_or_locked_generation(tmp_path):
    archive = tmp_path / "generation"; archive.mkdir(); cli.save(archive / "status.json", {"state": "running"})
    with pytest.raises(ValueError, match="running"):
        scc_export.export(archive, tmp_path / "inputs", tmp_path / "manifest", tmp_path / "out")
    cli.save(archive / "status.json", {"state": "paused"}); (archive / "DISPATCH.lock").write_text("1")
    with pytest.raises(ValueError, match="lock"):
        scc_export.export(archive, tmp_path / "inputs", tmp_path / "manifest", tmp_path / "out2")


def test_export_rejects_missing_status_and_candidate_tamper(tmp_path):
    assignment, cell, task = _completed_assignment(tmp_path)
    (assignment / "status.json").unlink()
    with pytest.raises(ValueError, match="required identity/status"):
        scc_export._row_for(assignment, cell, task)
    cli.save(assignment / "status.json", {"state": "completed"})
    (assignment / "candidate.py").write_text("def task_func(x):\n    return 99\n", encoding="utf-8")
    with pytest.raises(ValueError, match="raw final response"):
        scc_export._row_for(assignment, cell, task)


def test_export_distinguishes_observed_format_failure_from_missing_generation(tmp_path):
    assignment, cell, task = _completed_assignment(tmp_path, answer="not code")
    (assignment / "candidate.py").write_text("", encoding="utf-8")
    cli.save(assignment / "status.json", {"state": "completed", "generation_complete": True,
                                           "format_extracted": False})
    format_row = scc_export._row_for(assignment, cell, task)
    assert format_row["observed_candidate"] is True
    assert format_row["outcome_type"] == "model_format_failure"
    missing_row = scc_export._row_for(None, cell, task)
    assert missing_row["observed_candidate"] is False
    assert missing_row["outcome_type"] == "generation_unavailable"


def test_incomplete_transport_candidate_never_enters_native_samples(tmp_path):
    assignment, cell, task = _completed_assignment(tmp_path)
    cli.save(assignment / "status.json", {"state": "infrastructure_failure",
                                           "generation_complete": False})
    # A partial file may exist after a worker crash; it remains evidence only.
    (assignment / "candidate.py").write_text("def task_func(x): return x\n", encoding="utf-8")
    row = scc_export._row_for(assignment, cell, task)
    assert row["observed_candidate"] is False
    assert row["quality"] is None
    assert row["outcome_type"] == "infrastructure_failure"


def test_finish_preserves_submitted_transport_and_never_started_states(tmp_path):
    rows = [{"task_id": f"t{i}", "method": "single_roles", "replicate_id": 101,
             "availability": "never_started", "observed_candidate": False, "quality": None,
             "outcome_type": "generation_unavailable"} for i in range(9000)]
    rows[0].update(availability="submitted_incomplete", status_state="infrastructure_failure")
    rows[2].update(availability="completed", observed_candidate=True, format_extracted=False)
    rows[3].update(availability="completed", observed_candidate=True, format_extracted=True)
    rows[4].update(availability="completed", observed_candidate=True, format_extracted=False)
    # _records mutates the immutable export rows only at the terminal join.
    export = tmp_path / "assignment_records.jsonl"
    export.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    out = scc_finish._records(tmp_path, {}, {"t2", "t3"})
    assert out[0]["outcome_type"] == "infrastructure_failure"
    assert out[1]["outcome_type"] == "generation_unavailable"
    assert out[2]["outcome_type"] == "model_format_failure" and out[2]["quality"] is False
    assert out[3]["outcome_type"] == "native_unavailable" and out[3]["quality"] is None
    assert out[4]["outcome_type"] == "control_ineligible" and out[4]["quality"] is None


def test_export_accepts_dispatcher_terminal_result_and_rejects_tampered_identity(tmp_path):
    assignment, cell, task = _completed_assignment(tmp_path)
    answer = "```python\ndef task_func(x):\n    return x\n```"
    replay, _ = scc_export._code_from_final(answer)
    (assignment / "candidate.py").write_text(replay, encoding="utf-8")
    cli.save(assignment / "terminal_result.json", {"id": cell["id"], "task_id": task["task_id"], "state": "completed"})
    row = scc_export._row_for(assignment, cell, task)
    assert row["generation_complete"] is True
    cli.save(assignment / "result.json", {"id": "other-cell", "state": "completed"})
    with pytest.raises(ValueError, match="identity"):
        scc_export._row_for(assignment, cell, task)


def test_export_rejects_unfinished_generated_test_evidence(tmp_path):
    assignment, cell, task = _completed_assignment(tmp_path)
    check = assignment / "generated_tests" / "000"
    check.mkdir(parents=True)
    cli.save(assignment / "status.json", {"state": "completed", "generated_test_runs": ["generated_tests/000"]})
    cli.save(check / "status.json", {"state": "started"})
    with pytest.raises(ValueError, match="unfinished"):
        scc_export._row_for(assignment, cell, task)


def test_export_replays_archived_upstream_scc_trajectory_without_model(tmp_path):
    pytest.importorskip("tqdm")
    assignment = tmp_path / "scc-cell"; assignment.mkdir()
    cell = {"id": "scc-cell", "task_id": "BigCodeBench/1", "replicate_id": 101,
            "method": scc_dispatch.METHOD, "max_upstream_round": 2, "cli_turns": 4}
    task = _task(); cli.save(assignment / "cell.json", cell); cli.save(assignment / "task.json", task)
    calls = []; checks = []
    responses = ["plan", "def task_func(x):\n    return x", "tests"]
    def model(messages, **kwargs):
        i = len(calls); record = {"messages": copy.deepcopy(messages), "result": {"final_text": responses[i]}}
        calls.append(record); return [responses[i]]
    def execute(code, report):
        checks.append((code, report)); return "Code Test Passed."
    candidate, history = scc_dispatch.scc.run_session(task["prompt"] + "\n" + task.get("context", ""), model, execute, max_round=2, before_func="")
    cli.save(assignment / "requests.json", calls); cli.save(assignment / "session_history.json", history)
    check = assignment / "generated_tests" / "000"; check.mkdir(parents=True)
    cli.save(check / "input.json", {"code": checks[0][0], "report": checks[0][1]})
    (check / "stdout.txt").write_text(json.dumps({"report": "Code Test Passed."}), encoding="utf-8")
    cli.save(check / "argv.json", ["docker", "synthetic"])
    cli.save(check / "status.json", {"state": "completed", "report": "Code Test Passed."})
    (assignment / "candidate.py").write_text(candidate, encoding="utf-8")
    cli.save(assignment / "status.json", {"state": "completed", "generated_test_runs": ["generated_tests/000"]})
    for i, call in enumerate(calls):
        turn = assignment / "turns" / f"{i:03d}"; turn.mkdir(parents=True)
        usage = {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}
        events = [{"type": "thread.started"}, {"type": "turn.started"},
                  {"type": "item.completed", "item": {"type": "agent_message", "text": call["result"]["final_text"]}},
                  {"type": "turn.completed", "usage": usage}]
        (turn / "events.jsonl").write_bytes(b"\n".join(cli.canonical(e) for e in events) + b"\n")
        prompt = scc_dispatch.scc.serialize_messages(call["messages"])
        (turn / "prompt.txt").write_bytes(prompt.encode("utf-8"))
        cli.save(turn / "argv.json", ["codex", "test"]); (turn / "stderr.txt").write_bytes(b"")
        result = {**cli.parse_events((turn / "events.jsonl").read_bytes()),
                  "files_sha256": {n: hashlib.sha256((turn / n).read_bytes()).hexdigest()
                                   for n in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")}}
        cli.save(turn / "result.json", result); cli.save(turn / "status.json", {"state": "completed"})
        calls[i]["result"] = result
    cli.save(assignment / "requests.json", calls)
    row = scc_export._row_for(assignment, cell, task)
    assert row["generation_complete"] is True and row["solution"] == candidate
    tampered = cli.read(assignment / "requests.json")
    tampered[0]["result"]["final_text"] = "tampered"
    cli.save(assignment / "requests.json", tampered)
    with pytest.raises(scc_dispatch.scc.TransportAbort):
        scc_export._row_for(assignment, cell, task)


def test_new_analyze_cli_reconstructs_strict_9000_cell_matrix(tmp_path):
    records = tmp_path / "records.jsonl"; out = tmp_path / "summary.json"
    selection = tmp_path / "selection.json"; gate = tmp_path / "gate.json"
    methods = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")
    task_ids = [f"t{task}" for task in range(1000)]
    cli.save(selection, {"prior_primary_task_ids": task_ids[:200], "new_task_ids": task_ids[200:]})
    cli.save(gate, {"assigned_task_ids": task_ids, "evaluable_task_ids": task_ids[:985]})
    with records.open("w", encoding="utf-8") as handle:
        for task in range(1000):
            for method in methods:
                for rep in (101, 102, 103):
                    handle.write(json.dumps({"task_id": f"t{task}", "method": method,
                        "replicate_id": rep, "quality": None, "outcome_type": "generation_unavailable"}) + "\n")
    proc = subprocess.run([sys.executable, "-m", "reproducibility.revision_20260911.scc_analyze",
                           "--records", str(records), "--out", str(out), "--strict",
                           "--selection", str(selection), "--control-gate", str(gate)],
                          capture_output=True, text=True, check=True)
    assert json.loads(out.read_text(encoding="utf-8"))["strict_contract"]["enabled"] is True
    assert '"rows": 9000' in proc.stdout


def test_finish_rejects_image_that_differs_from_control_gate(tmp_path, monkeypatch):
    root = tmp_path / "run"; (root / "generation").mkdir(parents=True)
    cli.save(root / "generation/status.json", {"state": "generation_finished"})
    inputs, gate, manifest = tmp_path / "inputs", tmp_path / "gate", tmp_path / "manifest.json"
    inputs.mkdir(); gate.mkdir(); cli.save(gate / "heldout200_control_gate.json", {"image_id": "sha256:gate", "evaluable_task_ids": []})
    manifest.write_text("{}")
    monkeypatch.setattr(scc_export, "validate_export", lambda *args: {})
    monkeypatch.setattr(scc_export, "export", lambda *args: None)
    monkeypatch.setattr(scc_finish, "environment_from_gate", lambda _: {"image_id": "sha256:gate"})
    monkeypatch.setattr(scc_finish, "_image_id", lambda _: "sha256:other")
    with pytest.raises(ValueError, match="image identity"):
        scc_finish.run(Namespace(root=root, inputs=inputs, gate_dir=gate, manifest=manifest,
                                 image="bcb-scale1000:v2", requirements="req", dockerfile="Dockerfile"))


def test_finish_does_not_reuse_verified_stage_with_changed_command(tmp_path):
    stage = tmp_path / "stage"; stage.mkdir()
    cli.save(stage / "argv.json", ["python", "old"])
    cli.save(stage / "exit.json", {"returncode": 0})
    with pytest.raises(ValueError, match="command changed"):
        scc_finish._run_native_stage(stage, tmp_path / "native", ["python", "new"])
