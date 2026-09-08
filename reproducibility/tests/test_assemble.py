import json
from pathlib import Path
import tempfile
import unittest

from reproducibility.heldout200.assemble import export_bigcodebench, merge_audits


class AssembleTests(unittest.TestCase):
    def setUp(self):
        self.cell = {'id': 'c', 'task_id': 't', 'arm': 'direct', 'replicate_id': 4, 'cli_turns': 1}

    def manifest(self, root):
        path = root / 'manifest.json'
        path.write_text(json.dumps({'assigned_task_ids': ['t'], 'planned_generations': 1, 'manifest_sha256':'fixture',
                                    'shards': [{'manifest': {'cells': [self.cell]}}]}))
        return path

    def test_missing_is_preserved_and_exported_as_no_eval(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.manifest(root)
            assembled = merge_audits({'all_assignment_availability': {'c': 'never_started'}, 'rows': []}, manifest)
            result = export_bigcodebench(assembled, root / 'out')
            self.assertEqual(result['arms']['direct']['missing_task_ids'], ['t'])
            self.assertEqual(result['arms']['direct']['analysis_status'], 'no_eval')

    def test_parent_continuation_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.manifest(root)
            row = {**self.cell, 'model': 'gpt-5.4-mini', 'final_text': '```python\nx\n```'}
            parent = {'all_assignment_availability': {'c': 'completed'}, 'rows': [row]}
            with self.assertRaisesRegex(ValueError,'already started'):
                merge_audits(parent, manifest, {'rows': [row], 'all_assignment_availability': {'c': 'completed'}})

    def test_unexpected_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.manifest(root)
            with self.assertRaises(ValueError):
                merge_audits({'all_assignment_availability': {'c': 'completed'},
                              'rows': [{'id': 'other', 'task_id': 't'}]}, manifest)


if __name__ == '__main__':
    unittest.main()
