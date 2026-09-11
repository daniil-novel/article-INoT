"""Offline contract tests for the SCC/SR/SN task-level analyzer."""
import json
import tempfile
import unittest
from pathlib import Path

from reproducibility.revision_20260911 import scc_analyze as a
from reproducibility.revision_20260911.scc_export import _resource


def row(task, method, rep, quality, **extra):
    return {"task_id": task, "method": method, "replicate_id": rep, "quality": quality, **extra}


class SCCAnalysisTests(unittest.TestCase):
    def test_duplicate_cell_and_invalid_repeat_are_rejected(self):
        rows = [row("t1", a.METHODS[0], 101, True), row("t1", a.METHODS[0], 101, False)]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "r.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                a.analyze(path)
            rows[1]["replicate_id"] = 999
            path.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError, "replicate_id"):
                a.analyze(path)

    def test_task_pairing_prevents_repeat_pseudoreplication(self):
        rows = [row("t1", method, rep, method == a.SCC)
                for method in a.METHODS for rep in a.REPLICATES]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "r.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            result = a.analyze(path)
        contrast = result["contrasts"][f"{a.SCC}-{a.METHODS[0]}"]
        self.assertEqual(contrast["n_tasks"], 1)
        self.assertAlmostEqual(contrast["mean_difference"], 1.0)

    def test_holm_adjusts_actual_two_primary_pvalues(self):
        adjusted = a._holm({"small": 0.01, "large": 0.03})
        self.assertAlmostEqual(adjusted["small"], 0.02)
        self.assertAlmostEqual(adjusted["large"], 0.03)
        self.assertEqual(set(adjusted), {"small", "large"})

    def test_holm_keeps_fixed_two_member_family_when_one_p_is_unestimable(self):
        adjusted = a._holm({"estimable": 0.01, "unestimable": None})
        self.assertAlmostEqual(adjusted["estimable"], 0.02)
        self.assertIsNone(adjusted["unestimable"])

    def test_unknown_format_failure_enters_bounds_not_quality_failure(self):
        rows = [row("t1", method, rep, None if method == a.SCC else True,
                     outcome_type="format_failure" if method == a.SCC else "native_outcome")
                for method in a.METHODS for rep in a.REPLICATES]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "r.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            result = a.analyze(path)
        self.assertEqual(result["quality"]["unknown_quality_count"], 0)
        bounds = result["missingness_bounds"]["all_assigned"]["SCC-SR"]
        self.assertEqual((bounds["lower_difference"], bounds["upper_difference"]), (-1.0, -1.0))

    def test_finish_schema_distinguishes_format_failure_and_infrastructure(self):
        rows = []
        for method in a.METHODS:
            for rep in a.REPLICATES:
                rows.append(row("t_format", method, rep, False if method == a.SCC else True,
                                 generation_complete=True, native_status="fail",
                                 format_extracted=False if method == a.SCC else True,
                                 outcome_type="model_format_failure" if method == a.SCC else "native_outcome",
                                 resource_usage={"turns": 1, "known_turns": 1, "unknown_turns": 0,
                                                 "input_tokens": 6, "cached_input_tokens": 0,
                                                 "output_tokens": 4, "known_api_equivalent_usd": 0.1}))
                rows.append(row("t_transport", method, rep, None,
                                 generation_complete=False, native_status=None,
                                 format_extracted=False, outcome_type="transport_failure",
                                 resource_usage={"turns": 1, "known_turns": 0, "unknown_turns": 1,
                                                 "input_tokens": 0, "cached_input_tokens": 0,
                                                 "output_tokens": 0, "known_api_equivalent_usd": 0.0}))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "finish.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            result = a.analyze(path)
        self.assertEqual(result["quality"]["unknown_by_outcome_type"]["transport_failure"], 9)
        self.assertNotIn("model_format_failure", result["quality"]["unknown_by_outcome_type"])
        self.assertIn("api_equivalent_usd", result["resources"])
        self.assertEqual(result["resources"]["api_equivalent_usd"][f"{a.SCC}-{a.METHODS[0]}"]["n_complete_task_pairs"], 1)

    def test_actual_export_resource_schema_has_complete_and_known_subtotals(self):
        with tempfile.TemporaryDirectory() as td:
            assignment = Path(td); turns = assignment / "turns"
            for name, usage in (("000", {"input_tokens": 7, "cached_input_tokens": 0, "output_tokens": 3}),
                                ("001", None)):
                folder = turns / name; folder.mkdir(parents=True)
                events = [{"type": "turn.completed", "usage": usage}] if usage else []
                (folder / "events.jsonl").write_text("\n".join(json.dumps(x) for x in events) + "\n")
                (folder / "status.json").write_text(json.dumps({"state": "completed"}))
            resource = _resource(assignment)
        self.assertEqual(resource["turns"], 2)
        self.assertEqual(resource["known_turns"], 1)
        self.assertEqual(resource["unknown_turns"], 1)
        self.assertEqual(set(resource), {"turns", "known_turns", "unknown_turns", "input_tokens",
                                         "cached_input_tokens", "output_tokens", "known_api_equivalent_usd", "invalid_usage"})
        self.assertEqual(resource["invalid_usage"], [])
        self.assertIsNone(a._metric({"resource_usage": resource}, "api_equivalent_usd"))
        self.assertEqual(a._metric({"resource_usage": resource}, "known_api_equivalent_usd"), resource["known_api_equivalent_usd"])

    def test_strict_gate_rejects_quality_true_for_ineligible_task(self):
        rows = [row(str(i), method, rep, True) for i in range(1000) for method in a.METHODS for rep in a.REPLICATES]
        selection = {"prior_primary_task_ids": [str(i) for i in range(200)],
                     "new_task_ids": [str(i) for i in range(200, 1000)]}
        gate = {"assigned_task_ids": [str(i) for i in range(1000)],
                "evaluable_task_ids": [str(i) for i in range(985)]}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "strict.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError, "control-ineligible"):
                a.analyze(path, strict=True, selection=selection, control_gate=gate)

    def test_ineligible_quality_true_is_rejected(self):
        rows = [row("t1", method, rep, True, outcome_type="control_ineligible")
                for method in a.METHODS for rep in a.REPLICATES]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "invalid.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError, "quality=null"):
                a.analyze(path)

    def test_all_assignment_bounds_and_control_gate_selection(self):
        rows = []
        for task in ("old", "new"):
            for method in a.METHODS:
                for rep in a.REPLICATES:
                    rows.append(row(task, method, rep, True if method != a.SCC else None,
                                    control_eligible=(task == "old"), subgroup="old200" if task == "old" else "new800"))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "r.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            result = a.analyze(path)
        self.assertEqual(result["control_eligibility"]["eligible_task_count"], 1)
        self.assertEqual(result["subgroups"].keys(), {"old200", "new800"})
        self.assertEqual(result["missingness_bounds"]["all_assigned"]["SCC-SN"]["lower_difference"], -1.0)

    def test_strict_contract_requires_exact_1000_tasks(self):
        rows = [row("t1", method, rep, True) for method in a.METHODS for rep in a.REPLICATES]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "r.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError, "1000 tasks"):
                a.analyze(path, strict=True)


if __name__ == "__main__":
    unittest.main()
