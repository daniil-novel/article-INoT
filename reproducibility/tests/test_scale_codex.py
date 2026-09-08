import unittest

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


if __name__ == '__main__':
    unittest.main()
