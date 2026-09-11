"""Meaningful offline tests for the revision runner and analysis contract."""
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from reproducibility.revision_20260911 import scc_dispatch as d
from reproducibility import benchmark_bridge as bridge


class RevisionContracts(unittest.TestCase):
    def test_schedule_uses_one_rng_and_mixed_method_orders(self):
        tasks = [{"task_id": f"BigCodeBench/{i}"} for i in range(12)]
        rows = d.cells(tasks)
        orders = [tuple(x["method"] for x in rows[i:i+3]) for i in range(0, len(rows), 3)]
        self.assertGreater(len(set(orders)), 1)
        self.assertEqual(len(rows), 12 * 3 * 3)
        self.assertEqual(len({x["id"] for x in rows}), len(rows))

    def test_full_allocation_has_9000_distinct_schema_cells(self):
        rows = d.cells([{"task_id": f"BigCodeBench/{i}"} for i in range(1000)])
        self.assertEqual(len(rows), 9000)
        self.assertEqual(len({r["id"] for r in rows}), 9000)
        self.assertEqual({r["method"] for r in rows}, set(d.METHODS))
        self.assertEqual({(r["task_id"], r["replicate_id"]) for r in rows},
                         {(f"BigCodeBench/{i}", rep) for i in range(1000) for rep in d.REPEATS})

    def test_usage_rejects_cache_write_and_unknown_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            self.assertIsNone(d._raw_usage(folder))
            (folder / "events.jsonl").write_text(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2, "cached_input_tokens": 0, "output_tokens": 1, "cache_write_input_tokens": 1}}))
            with self.assertRaises(ValueError): d._raw_usage(folder)

    def test_completed_empty_turn_becomes_observed_model_failure(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "turn"; folder.mkdir()
            (folder / "prompt.txt").write_text("p")
            (folder / "argv.json").write_text("[]")
            (folder / "stderr.txt").write_text("")
            d.cli.save(folder / "status.json", {"state": "blocked", "reason": "One completed turn and one complete answer required"})
            events = [{"type": "thread.started"}, {"type": "turn.started"}, {"type": "turn.completed", "usage": {"input_tokens": 4, "cached_input_tokens": 0, "output_tokens": 0}}]
            (folder / "events.jsonl").write_bytes(b"\n".join(d.cli.canonical(e) for e in events))
            result = d._accept_empty_completed(folder, [])
            self.assertTrue(result["empty_model_response"])
            self.assertEqual(d.cli.read(folder / "status.json")["state"], "completed")

    def test_failed_turn_usage_is_counted_once(self):
        with tempfile.TemporaryDirectory() as td:
            turn = Path(td) / "assignments" / "a" / "turns" / "000"
            turn.mkdir(parents=True)
            (turn / "events.jsonl").write_text(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 5}}))
            self.assertAlmostEqual(d._known_from_turns(Path(td)), 10 * .20 / 1e6 - 2 * .18 / 1e6 + 5 * 1.20 / 1e6)

    def test_transport_and_workflow_failures_are_distinct(self):
        self.assertEqual(d._failure_kind(d.scc.TransportAbort("quota")), "infrastructure_failure")
        self.assertEqual(d._failure_kind(ValueError("malformed answer")), "model_or_workflow_failure")
        self.assertEqual(d._failure_kind(subprocess.TimeoutExpired("codex", 600)), "infrastructure_failure")

    def test_process_scheduler_caps_eight_and_leaves_pending_at_guard(self):
        self.assertEqual(d._submission_capacity(100, 0, 8, 0, 285), 8)
        self.assertEqual(d._submission_capacity(100, 8, 8, 0, 285), 0)
        self.assertEqual(d._submission_capacity(100, 0, 8, 285, 285), 0)

    def test_mock_parent_drains_active_after_quota_without_new_submissions(self):
        class Future:
            def __init__(self, value): self.value = value
            def result(self): return self.value
        class Executor:
            def __init__(self): self.submitted = []; self.max_active = 0
            def submit(self, fn, payload):
                future = Future(payload["result"]); self.submitted.append(future)
                self.max_active = max(self.max_active, len(self.submitted)); return future
        executor = Executor()
        pending = [{"id": str(i), "result": {"state": "completed", "valuation": 1.0,
                                                "stop_hint": "quota_auth_or_unsupported_model" if i == 0 else None}}
                   for i in range(20)]
        def payload(cell): return cell
        def fake_wait(active, return_when):
            # One completion at a time models active processes draining.
            return ({next(iter(active))}, set())
        with patch.object(d, "wait", side_effect=fake_wait):
            result = d.coordinate_assignments(pending, payload, executor, 8, 0.0, 285.0)
        self.assertEqual(executor.max_active, 8)
        self.assertEqual(result["stop_reason"], "quota_auth_or_unsupported_model")
        self.assertEqual(len(executor.submitted), 8)
        self.assertEqual(len(result["pending"]), 12)

    def test_mock_parent_counts_prior_and_failed_raw_usage_before_submit(self):
        class Future:
            def __init__(self, value): self.value = value
            def result(self): return self.value
        class Executor:
            def __init__(self): self.calls = 0
            def submit(self, fn, payload): self.calls += 1; return Future({"state": "completed", "valuation": 0.5})
        executor = Executor(); pending = [{"id": "a"}, {"id": "b"}]
        with patch.object(d, "wait", side_effect=lambda active, return_when: ({next(iter(active))}, set())):
            result = d.coordinate_assignments(pending, lambda c: c, executor, 1, 9.5, 10.0)
        self.assertEqual(executor.calls, 1)
        self.assertEqual(result["known"], 10.0)
        self.assertEqual(len(result["pending"]), 1)

    def test_empty_completed_answer_is_exportable_failure(self):
        code, ok = bridge._extract_fenced_block("", "bigcodebench")
        self.assertEqual((code, ok), ("", False))


if __name__ == "__main__": unittest.main()
