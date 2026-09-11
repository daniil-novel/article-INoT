"""Exercise real worker failure paths with recorded synthetic CLI streams."""
import json
from pathlib import Path

import pytest

from reproducibility.revision_20260911 import scc_dispatch as d


def stream(answer=None, completed=True):
    rows = [{"type": "thread.started"}, {"type": "turn.started"}]
    if answer is not None:
        rows.append({"type": "item.completed", "item": {"type": "agent_message", "text": answer}})
    if completed:
        rows.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 5}})
    return b"\n".join(d.cli.canonical(row) for row in rows)


def archive_fake(folder, command, prompt, answer=None, completed=True):
    folder.mkdir(parents=True)
    (folder / "prompt.txt").write_bytes(prompt.encode())
    d.cli.save(folder / "argv.json", command)
    (folder / "events.jsonl").write_bytes(stream(answer, completed))
    (folder / "stderr.txt").write_bytes(b"")
    d.cli.save(folder / "status.json", {"state": "completed" if completed else "blocked", "reason": "transport interruption"})
    if not completed:
        raise RuntimeError("transport interruption")
    result = d.cli.parse_events((folder / "events.jsonl").read_bytes())
    result.update(files_sha256={name: d.sha(folder / name) for name in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")})
    d.cli.save(folder / "result.json", result)
    return result


def payload(tmp_path, method):
    return {"assignment": str(tmp_path / "assignment"), "task": {"task_id": "BigCodeBench/1", "prompt": "Implement task_func(x).", "context": ""},
            "cell": {"id": "a", "method": method, "task_id": "BigCodeBench/1", "max_upstream_round": 2}, "command": []}


def test_transport_failure_before_any_answer_has_terminal_unknown_usage(tmp_path, monkeypatch):
    monkeypatch.setattr(d.cli, "archive_turn", lambda folder, command, prompt, timeout: archive_fake(folder, command, prompt, completed=False))
    result = d.run_assignment_worker(payload(tmp_path, "single_roles"))
    assert result["state"] == "infrastructure_failure"
    assert result["unknown_usage_calls"] == 1
    assert not (tmp_path / "assignment/candidate.py").exists()
    assert d.cli.read(tmp_path / "assignment/status.json")["generation_complete"] is False


def test_scc_late_transport_failure_retains_early_cost_and_no_fake_candidate(tmp_path, monkeypatch):
    calls = []
    def fake(folder, command, prompt, timeout):
        calls.append(prompt)
        if len(calls) == 3:
            return archive_fake(folder, command, prompt, completed=False)
        answer = "Plan: return x." if len(calls) == 1 else "```python\ndef task_func(x):\n    return x\n```"
        return archive_fake(folder, command, prompt, answer=answer)
    monkeypatch.setattr(d.cli, "archive_turn", fake)
    result = d.run_assignment_worker(payload(tmp_path, d.METHOD))
    one_turn = d.cli.value_usage({"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 5})
    assert len(calls) == 3
    assert result["state"] == "infrastructure_failure"
    assert result["valuation"] == pytest.approx(2 * one_turn)
    assert result["unknown_usage_calls"] == 1
    assert not (tmp_path / "assignment/candidate.py").exists()


def test_completed_malformed_single_answer_is_observed_empty_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(d.cli, "archive_turn", lambda folder, command, prompt, timeout: archive_fake(folder, command, prompt, answer="No program."))
    result = d.run_assignment_worker(payload(tmp_path, "single_neutral"))
    assert result["state"] == "completed"
    assert (tmp_path / "assignment/candidate.py").read_bytes() == b""
    status = d.cli.read(tmp_path / "assignment/status.json")
    assert status["generation_complete"] is True and status["format_extracted"] is False


def test_empty_response_reclassification_rejects_tools_and_bad_usage():
    assert d.parse_completed_empty(stream())["final_text"] == ""
    with pytest.raises(ValueError):
        d.parse_completed_empty(stream() + b'\n{"type":"item.completed","item":{"type":"command_execution"}}')
    with pytest.raises(ValueError):
        d.parse_completed_empty(b'{"type":"turn.completed","usage":{}}')


def test_dispatch_lock_is_exclusive_and_cleaned_on_failure(tmp_path):
    with pytest.raises(RuntimeError):
        with d.dispatch_lock(tmp_path):
            with pytest.raises(ValueError, match="already running"):
                with d.dispatch_lock(tmp_path):
                    pass
            raise RuntimeError("stop")
    assert not (tmp_path / "DISPATCH.lock").exists()
