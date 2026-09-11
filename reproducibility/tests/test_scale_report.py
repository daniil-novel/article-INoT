"""Offline tests for the separate post-finish scale1000 descriptive report."""
import json
import tempfile
import unittest
from pathlib import Path

from reproducibility.revision_20260911.scale_report import build_report, render_tex


class ScaleReportTests(unittest.TestCase):
    def _fixture(self, folder: Path, finished: bool = True):
        tasks = [f"t{i:04d}" for i in range(1000)]
        arms = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
        rows = []
        for task_i, task in enumerate(tasks):
            for arm_i, arm in enumerate(arms):
                for rep in (101, 102, 103):
                    is_unavailable = task_i == 983 and arm == "direct" and rep == 101
                    is_format = task_i == 984 and arm == "single_roles" and rep == 101
                    q = None if is_unavailable else False if is_format else bool((task_i + arm_i + rep) % 2)
                    rows.append({
                        "task_id": task, "arm": arm, "replicate_id": rep,
                        "quality": q, "generation_complete": not is_unavailable,
                        "outcome_type": "generation_unavailable" if is_unavailable else "model_format_failure" if is_format else "native_outcome",
                        "format_extracted": not is_format,
                        "native_status": "fail" if is_format else "pass",
                        "resource_usage": {"total_tokens": 100 + arm_i, "api_equivalent_usd": 0.01 + arm_i / 1000},
                        "assignment_session": "resume" if task_i >= 800 else "original",
                    })
        records = folder / "candidate_records.jsonl"
        records.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        summary = folder / "summary.json"
        summary.write_text(json.dumps({"schema": "scale1000-task-cluster-analysis-v1", "tasks": 1000,
                                       "planned_candidates": 15000, "generation_state": "generation_finished" if finished else "running"}), encoding="utf-8")
        gate = folder / "gate.json"
        gate.write_text(json.dumps({"assigned_task_ids": tasks, "evaluable_task_ids": tasks[:985]}), encoding="utf-8")
        status = folder / "status.json"
        status.write_text(json.dumps({"state": "generation_finished" if finished else "running"}), encoding="utf-8")
        return records, summary, gate, status

    def test_finished_report_bounds_breakdowns_and_tex(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); records, summary, gate, status = self._fixture(folder)
            out = folder / "report"
            report = build_report(records, summary, gate, out, status)
            self.assertEqual(report["analysis_status"], "generation_finished")
            self.assertEqual(report["gate_eligible_count"], 985)
            self.assertEqual(report["assignment_breakdown"]["submitted_unavailable"], 1)
            self.assertEqual(report["assignment_breakdown"]["format_failure"], 1)
            self.assertEqual(report["assignment_breakdown"]["native_ineligible"], 225)
            self.assertEqual(report["session_breakdown"]["resume"], 3000)
            self.assertIn("missingness_bounds", report)
            self.assertEqual(report["missingness_bounds"]["control_eligible"]["single_roles_minus_single_neutral"]["task_count"], 985)
            self.assertIn("\\textwidth", (out / "scale_report_en.tex").read_text(encoding="utf-8"))
            ru = (out / "scale_report_ru.tex").read_text(encoding="utf-8")
            self.assertIn("сохранённый реестр", ru)
            self.assertIn("Роли--нейтральный", ru)
            self.assertNotIn("ledger", ru.lower())
            self.assertNotIn("frozen", ru.lower())

    def test_not_finished_report_makes_no_outcome_claim(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); records, summary, gate, status = self._fixture(folder, finished=False)
            report = build_report(records, summary, gate, folder / "report", status)
            self.assertEqual(report["readiness"], "not_ready_for_outcome_claims")
            self.assertNotIn("missingness_bounds", report)
            self.assertNotIn("bounds", render_tex(report, "en"))

    def test_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); records, summary, gate, status = self._fixture(folder)
            out = folder / "report"; out.mkdir()
            with self.assertRaises(FileExistsError):
                build_report(records, summary, gate, out, status)


if __name__ == "__main__":
    unittest.main()
