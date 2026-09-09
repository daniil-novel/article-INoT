"""Published native outcomes must remain joined to the raw SCC candidates."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from reproducibility.external_baselines.audit import audit, audit_pilot

ROOT = Path(__file__).resolve().parents[1]/'results/20260909_scc_dev3'


class SCCEvidence(unittest.TestCase):
    def test_complete_raw_and_native_replay(self):
        self.assertEqual(audit_pilot(ROOT), json.loads((ROOT/'summary.json').read_text()))

    def test_edited_candidate_cannot_reuse_original_native_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'task'
            shutil.copytree(ROOT/'generation/task-0', target)
            with (target/'candidate.py').open('a',encoding='utf-8') as f:
                f.write('\n# altered after generation\n')
            with self.assertRaisesRegex(ValueError, 'Final candidate/session differs'):
                audit(target)

    def test_edited_resource_counter_rejected_against_raw_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'task'
            shutil.copytree(ROOT/'generation/task-0', target)
            p = target/'turns/000/result.json'
            data = json.loads(p.read_text()); data['usage']['input_tokens'] += 1
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Stored result differs'):
                audit(target)
