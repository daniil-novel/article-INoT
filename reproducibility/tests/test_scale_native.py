import json
from pathlib import Path
import shutil
import tempfile
import unittest

from reproducibility.scale_env.validate_native import validate_native, sha256, environment_from_gate

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / 'results/20260908_codex_mini_dev40/controls/attempt3'
if not CONTROLS.exists():
    CONTROLS = ROOT / 'runs/dev40-controls-v3'


@unittest.skipUnless(CONTROLS.exists(), 'saved real control evidence is required')
class NativeScaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'gold'
        shutil.copytree(CONTROLS / 'gold', self.folder)
        self.gate = environment_from_gate(CONTROLS)
        self.expected = {r['task_id']: r['solution'] for r in map(json.loads, (self.folder / 'input/samples.jsonl').read_text().splitlines())}

    def tearDown(self):
        self.temp.cleanup()

    def test_saved_real_control_passes_exact_validation(self):
        result = validate_native(self.folder, self.expected, self.gate)
        self.assertTrue(result['ok'], result['errors'])
        self.assertEqual(sum(v == 'pass' for v in result['statuses'].values()), 39)

    def test_updated_hash_does_not_hide_a_substituted_solution(self):
        staged = self.folder / 'input/samples.jsonl'
        rows = [json.loads(line) for line in staged.read_text().splitlines()]
        rows[0]['solution'] = 'def task_func(): return 123'
        staged.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
        meta_path = self.folder / 'run-metadata.json'
        meta = json.loads(meta_path.read_text())
        for key in ('samples_source_sha256', 'staged_samples_sha256', 'post_evaluator_staged_samples_sha256'):
            meta[key] = sha256(staged)
        meta_path.write_text(json.dumps(meta))
        result = validate_native(self.folder, self.expected, self.gate)
        self.assertFalse(result['ok'])
        self.assertIn('staged input differs from exact expected solutions', result['errors'])

    def test_actual_network_argument_is_checked(self):
        meta_path = self.folder / 'run-metadata.json'
        meta = json.loads(meta_path.read_text())
        meta['argv'][meta['argv'].index('--network') + 1] = 'bridge'
        meta_path.write_text(json.dumps(meta))
        self.assertFalse(validate_native(self.folder, self.expected, self.gate)['ok'])


if __name__ == '__main__':
    unittest.main()
