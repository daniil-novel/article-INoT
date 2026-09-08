import unittest
import tempfile
from pathlib import Path

from reproducibility import scale_codex as s


class ScalePlanTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [{'task_id': f'task/{i}'} for i in range(40)]
        self.gate = {'assigned_task_ids': [t['task_id'] for t in self.tasks],
                     'evaluable_task_ids': ['task/0'], 'controls_complete': True}

    def test_complete_paired_assignment_keeps_unavailable_tasks(self):
        plan = s.plan(self.tasks, self.gate, 'hash')
        cells = [c for shard in plan['shards'] for c in shard['manifest']['cells']]
        self.assertEqual(len(cells), 400)
        self.assertEqual(len({c['id'] for c in cells}), 400)
        self.assertEqual(sum(c['cli_turns'] for c in cells), 720)
        self.assertEqual({c['task_id'] for c in cells}, set(self.gate['assigned_task_ids']))
        for task in self.tasks:
            self.assertEqual(sum(c['task_id'] == task['task_id'] for c in cells), 10)

    def test_missing_or_misordered_controls_reject_before_launch(self):
        for mutation in ({'controls_complete': False}, {'evaluable_task_ids': []},
                         {'assigned_task_ids': list(reversed(self.gate['assigned_task_ids']))}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                s.plan(self.tasks, {**self.gate, **mutation}, 'hash')

    def test_model_and_runner_remain_identical_to_published_pilot(self):
        p = s.plan(self.tasks, self.gate, 'hash')
        for shard in p['shards']:
            self.assertEqual(shard['manifest']['model_requested'], 'gpt-5.4-mini')
            self.assertEqual(shard['manifest']['reasoning_effort'], 'medium')
            self.assertEqual(shard['manifest']['source_sha256_lf'], s.c.source_hash())

    def test_real_shard_files_match_v2_canonicalizing_loader(self):
        tasks = [{'task_id': f'task/{i}', 'prompt': 'implement f', 'context': '',
                  'benchmark': 'bigcodebench', 'metadata': {}} for i in range(40)]
        p = s.plan(tasks, self.gate, 'hash')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'tasks.jsonl'
            for shard in p['shards']:
                selected = [t for tid in shard['task_ids'] for t in tasks if t['task_id'] == tid]
                path.write_bytes(b''.join(s.c.canonical(t) + b'\n' for t in selected))
                self.assertEqual(s.ordered_tasks(path), selected)
                self.assertEqual(shard['manifest'], s.c.make_manifest(s.c.tasks_from(path), [shard['replicate']], list(s.c.ARMS)))


if __name__ == '__main__':
    unittest.main()
