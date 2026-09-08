import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reproducibility.heldout200 import assemble as a
from reproducibility.heldout200.run_observed_native import validate_observed_ids, ids
from reproducibility import codex_subscription as c

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


    def test_native_integrity_failure_is_never_collected_as_quality(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.manifest(root)
            row={**self.cell,'model':c.MODEL,'final_text':'```python\nprint(1)\n```'}
            joined=merge_audits({'all_assignment_availability':{'c':'completed'},'rows':[row]},m)
            joined['source_archive_hashes']={'original':'fixture'}
            gate=root/'controls';gate.mkdir()
            c.save(gate/'heldout200_control_gate.json',{'assigned_task_ids':['t'],'evaluable_task_ids':['t']})
            joined['control_gate_sha256']=a.sha256(gate/'heldout200_control_gate.json')
            predictions=root/'predictions';export_bigcodebench(joined,predictions)
            native=root/'native';(native/'direct').mkdir(parents=True)
            c.save(native/'direct/run-metadata.json',{'status':'completed','exit_code':0})
            with patch.object(a,'environment_from_gate',return_value={}),patch.object(a,'validate_native',return_value={'ok':False,'errors':['changed code'],'statuses':{'t':'pass'}}):
                with self.assertRaisesRegex(ValueError,'Native integrity failed'):
                    a.collect_native(joined,predictions,native,gate,root/'analysis')
            self.assertFalse((root/'analysis').exists())

    def test_observed_native_ids_are_a_unique_ordered_subset(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'samples.jsonl'
            path.write_text('{"task_id":"a"}\n{"task_id":"c"}\n')
            self.assertEqual(ids(path),['a','c'])
        validate_observed_ids(['a','c'],['a','b','c'])
        for bad in (['c','a'],['a','a'],['z'],[]):
            with self.assertRaises(ValueError):validate_observed_ids(bad,['a','b','c'])


if __name__ == '__main__':
    unittest.main()
