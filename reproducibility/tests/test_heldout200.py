import json
from pathlib import Path
import tempfile
import unittest

from reproducibility import codex_subscription as c
from reproducibility.heldout200.generate import plan, ordered_tasks
from reproducibility.heldout200.analyze import summarize
from reproducibility.heldout200.prepare_inputs import selected_ids


class HeldoutTests(unittest.TestCase):
    def test_real_selection_has_no_development_or_incidentally_exposed_tasks(self):
        split = c.read(Path('reproducibility/revision/task_split_manifest.json'))
        selection = c.read(Path('reproducibility/revision/heldout200_selection.json'))
        self.assertEqual(selection['assigned_task_ids'], selected_ids(split))
        self.assertFalse(set(selection['assigned_task_ids']) & set(split['dev_task_ids']))
        self.assertFalse(set(selection['assigned_task_ids']) & {f'BigCodeBench/{i}' for i in range(8)})

    def test_full_allocation_and_real_child_loader_agree(self):
        tasks = [dict(task_id=f't/{i}', prompt='Implement a function.', context='', benchmark='bigcodebench', metadata={}) for i in range(200)]
        gate = dict(assigned_task_ids=[t['task_id'] for t in tasks], controls_complete=True,
                    evaluable_task_ids=[t['task_id'] for t in tasks[:-1]])
        manifest = plan(tasks, gate, 'a' * 64)
        self.assertEqual((manifest['planned_generations'], manifest['planned_cli_turns']), (1000, 1800))
        keys = []
        mapping = {t['task_id']: t for t in tasks}
        with tempfile.TemporaryDirectory() as folder:
            for shard in manifest['shards']:
                p = Path(folder) / (shard['name'] + '.jsonl')
                p.write_bytes(b''.join(c.canonical(mapping[t]) + b'\n' for t in shard['task_ids']))
                child = c.make_manifest(c.tasks_from(p), [4], list(c.ARMS))
                self.assertEqual(child, shard['manifest'])
                keys.extend((x['task_id'], x['arm'], x['replicate_id']) for x in child['cells'])
        expected = {(t['task_id'], a, 4) for t in tasks for a in c.ARMS}
        self.assertEqual(set(keys), expected)
        self.assertEqual(len(keys), len(expected))

    def test_exact_discordance_and_holm_family(self):
        ids = [f't/{i}' for i in range(8)]
        rows = [dict(task_id=t, arm=a, replicate_id=4, analysis_status='pass' if a == 'single_roles' else 'fail',
                     total_tokens=100, api_equivalent_usd=.001, uncached_sensitivity_usd=.002)
                for t in ids for a in c.ARMS]
        result = summarize(rows, ids)
        tests = {t['contrast']: t for t in result['four_predeclared_quality_tests']}
        r = tests['roles_minus_neutral_single']
        self.assertEqual((r['a_only_passes'], r['b_only_passes']), (8, 0))
        self.assertEqual(r['exact_two_sided_mcnemar_p'], 2 / 256)
        self.assertEqual(r['holm_adjusted_p'], 4 * 2 / 256)
        self.assertEqual(tests['roles_minus_neutral_multi']['holm_adjusted_p'], 1)
        # A missing outcome is not silently converted into a discordant failure.
        rows[1]['analysis_status'] = None
        reduced = summarize(rows, ids)['four_predeclared_quality_tests'][0]
        self.assertEqual(reduced['complete_task_pairs'], 7)


if __name__ == '__main__':
    unittest.main()
