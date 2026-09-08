"""Offline safety tests for the fixed-task SWE launcher."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import evaluate_predictions as launcher
except ImportError:
    import evaluate_predictions as launcher


class LauncherTests(unittest.TestCase):
    def test_rejects_path_traversal_report_label(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "prediction.jsonl"
            p.write_text(json.dumps({"instance_id": launcher.TASK_ID, "model_patch": "", "model_name_or_path": "../escape"}) + "\n")
            with self.assertRaises(ValueError):
                launcher.load_prediction(p)

    def test_native_application_error_requires_exact_patch_and_error_membership(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            task = root / 'label' / launcher.TASK_ID
            task.mkdir(parents=True)
            (root / 'results.json').write_text(json.dumps({'error_ids': [launcher.TASK_ID]}))
            (task / 'patch.diff').write_text('broken patch')
            (task / 'run_instance.log').write_text('>>>>> Patch Apply Failed')
            result = launcher.validate_join(root, launcher.TASK_ID, 'label', 'broken patch', False)
            self.assertEqual(result['classification'], 'native_application_rejection')
            self.assertEqual(result['status'], 'complete')
            result = launcher.validate_join(root, launcher.TASK_ID, 'label', 'different patch', False)
            self.assertEqual(result['status'], 'missing')

    def test_infrastructure_failure_cannot_be_accepted_as_model_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            task = root / 'label' / launcher.TASK_ID
            task.mkdir(parents=True)
            (root / 'results.json').write_text(json.dumps({'submitted_ids': [launcher.TASK_ID]}))
            (task / 'patch.diff').write_text('patch')
            flags = dict(patch_is_None=False, patch_exists=True, patch_successfully_applied=True, resolved=False, infra_failure=True)
            (task / 'report.json').write_text(json.dumps({launcher.TASK_ID: flags}))
            result = launcher.validate_join(root, launcher.TASK_ID, 'label', 'patch', False)
            self.assertEqual(result['classification'], 'infrastructure_or_invalid_join')
            self.assertEqual(result['status'], 'missing')

    def test_report_join_rejects_wrong_task_and_records_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "run"
            task = root / "label" / launcher.TASK_ID
            task.mkdir(parents=True)
            (root / "results.json").write_text(json.dumps({"submitted_ids": [launcher.TASK_ID]}))
            (task / "report.json").write_text(json.dumps({"other": {"resolved": True}}))
            (task / "patch.diff").write_bytes(b"diff")
            result = launcher.validate_join(root, launcher.TASK_ID, "label", "diff", False)
            self.assertEqual(result["status"], "missing")
            self.assertFalse(result["report_task_id_exact"])
            self.assertIsNotNone(result["artifact_hashes"]["patch.diff"])

    def test_timeout_cleanup_removes_controller_and_task(self):
        with patch.object(launcher.subprocess, "run") as mocked:
            launcher.cleanup_owned("run-x", "sweb.controller.run-x")
            args = mocked.call_args.args[0]
            self.assertEqual(args[-2:], ["sweb.controller.run-x", "sweb.eval.pvlib__pvlib-python-1606.run-x"])

    def test_timeout_bytes_are_decoded(self):
        self.assertEqual(launcher.decode_output(b"partial\xff"), "partial�")


if __name__ == "__main__":
    unittest.main()
