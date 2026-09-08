from pathlib import Path
import tempfile
import unittest

from reproducibility.heldout200.inot import INOT_DESCRIPTION, TREATMENT, ordered_tasks, plan, prompt_for


class InotTests(unittest.TestCase):
    def test_description_is_bounded_and_contains_required_phases(self):
        self.assertLessEqual(len(INOT_DESCRIPTION.split()), 140)
        for term in ('virtual', 'argument', 'critique', 'rebuttal', 'update', 'agreement', '1..10', 'A fallback'):
            self.assertIn(term, INOT_DESCRIPTION)

    def test_plan_has_200_cells_and_separate_treatment(self):
        tasks = [{'task_id': f'BigCodeBench/{i}', 'prompt': 'p', 'context': 'c'} for i in range(200)]
        with tempfile.TemporaryDirectory() as d:
            protocol = Path(d) / 'protocol.md'
            protocol.write_text('protocol')
            selection = Path(d) / 'selection.json'
            selection.write_text(__import__('json').dumps({'count': 200, 'assigned_task_ids': [t['task_id'] for t in tasks]}))
            gate = Path(d) / 'gate.json'
            gate.write_text(__import__('json').dumps({'controls_complete': True, 'assigned_task_ids': [t['task_id'] for t in tasks], 'evaluable_task_ids': [t['task_id'] for t in tasks]}))
            manifest = plan(tasks, protocol, selection, gate)
        self.assertEqual(manifest['planned_generations'], 200)
        self.assertEqual(manifest['planned_cli_turns'], 200)
        self.assertTrue(all(c['arm'] == TREATMENT for c in manifest['cells']))
        self.assertEqual(manifest['order_seed'], 20260908)

    def test_plan_rejects_wrong_selection_or_gate(self):
        tasks = [{'task_id': f'BigCodeBench/{i}', 'prompt': 'p', 'context': 'c'} for i in range(200)]
        with tempfile.TemporaryDirectory() as d:
            protocol = Path(d) / 'protocol.md'; protocol.write_text('protocol')
            selection = Path(d) / 'selection.json'; selection.write_text(__import__('json').dumps({'count': 200, 'assigned_task_ids': ['wrong'] * 200}))
            gate = Path(d) / 'gate.json'; gate.write_text(__import__('json').dumps({'controls_complete': True, 'assigned_task_ids': [t['task_id'] for t in tasks], 'evaluable_task_ids': [t['task_id'] for t in tasks]}))
            with self.assertRaises(ValueError): plan(tasks, protocol, selection, gate)

    def test_plan_rejects_incomplete_control_gate(self):
        tasks = [{'task_id': f'BigCodeBench/{i}', 'prompt': 'p', 'context': 'c'} for i in range(200)]
        with tempfile.TemporaryDirectory() as d:
            protocol = Path(d) / 'protocol.md'; protocol.write_text('protocol')
            ids = [t['task_id'] for t in tasks]
            selection = Path(d) / 'selection.json'; selection.write_text(__import__('json').dumps({'count': 200, 'assigned_task_ids': ids}))
            gate = Path(d) / 'gate.json'; gate.write_text(__import__('json').dumps({'controls_complete': False, 'assigned_task_ids': ids, 'evaluable_task_ids': ids}))
            with self.assertRaises(ValueError): plan(tasks, protocol, selection, gate)

    def test_real_prepared_v2_task_file_matches_selection_and_final_gate(self):
        tasks_path = Path('reproducibility/runs/heldout200-controls-v2/input/prepared.jsonl')
        selection = Path('reproducibility/revision/heldout200_selection.json')
        gate = Path('reproducibility/results/20260908_codex_mini_heldout200/controls/attempt3/heldout200_control_gate.json')
        protocol = Path('reproducibility/revision/INOT_PROTOCOL.md')
        tasks = ordered_tasks(tasks_path)
        manifest = plan(tasks, protocol, selection, gate, tasks_path)
        self.assertEqual(manifest['task_count'], 200)
        self.assertEqual(manifest['planned_generations'], 200)
        self.assertEqual(manifest['task_file_sha256'], manifest['control_gate_prepared_split_sha256'])
        self.assertEqual(manifest['task_ids'], __import__('json').loads(selection.read_text())['assigned_task_ids'])
        self.assertEqual(len(manifest['evaluable_task_ids']), 193)

    def test_prompt_keeps_full_task_context_and_final_output(self):
        prompt = prompt_for({'prompt': 'solve this', 'context': 'all context'})
        self.assertIn('TASK\nsolve this', prompt)
        self.assertIn('FULL SUPPLIED CONTEXT\nall context', prompt)
        self.assertIn('final', prompt.lower())


if __name__ == '__main__':
    unittest.main()
