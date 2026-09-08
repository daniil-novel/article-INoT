import json
from pathlib import Path
import tempfile
import unittest
from reproducibility.tests.test_codex_audit import FailedAttemptAccountingTests
from reproducibility import codex_subscription as c
from reproducibility.heldout200.partial_audit import audit_shard, observed_usage


class PartialAuditTests(unittest.TestCase):
    def fixture(self,root):
        folder=FailedAttemptAccountingTests().make_archive(root)
        row=json.loads((root/'results.jsonl').read_text());row.update(model=c.MODEL,seed=1)
        c.save(root/'cells'/f"{row['id']}.json",row)
        (root/'results.jsonl').write_bytes(c.canonical(row)+b'\n')
        return folder,c.read(root/'manifest.json'),c.read(root/'tasks.json'),row

    def test_valid_archive_then_tampered_prompt_and_row_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder,m,t,row=self.fixture(root)
            self.assertEqual(audit_shard(root,m,t)['completed_cells'],1)
            row['usage']['input_tokens']=999
            c.save(root/'cells'/f"{row['id']}.json",row);(root/'results.jsonl').write_bytes(c.canonical(row)+b'\n')
            with self.assertRaisesRegex(ValueError,'token totals'):audit_shard(root,m,t)
            (folder/'prompt.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Prompt bytes'):audit_shard(root,m,t)

    def test_missing_stage_and_orphan_turn_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder,m,t,row=self.fixture(root)
            (root/'turns/orphan').mkdir()
            with self.assertRaisesRegex(ValueError,'orphan'):audit_shard(root,m,t)
            (root/'turns/orphan').rmdir()
            # A stage 1 without stage 0 cannot be a valid interrupted prefix.
            m=c.make_manifest(t,[1],['multi_neutral']);cell=m['cells'][0]
            c.save(root/'manifest.json',m)
            folder.rename(root/'turns'/f"{cell['id']}-1")
            (root/'cells'/f"{row['id']}.json").unlink();(root/'results.jsonl').write_bytes(b'')
            c.save(root/'status.json',{'state':'blocked'})
            with self.assertRaisesRegex(ValueError,'missing predecessor'):audit_shard(root,m,t)

    def test_truncated_turn_remains_unknown_and_has_no_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder,m,t,row=self.fixture(root)
            (root/'cells'/f"{row['id']}.json").unlink();(root/'results.jsonl').write_bytes(b'')
            (folder/'result.json').unlink();(folder/'events.jsonl').write_bytes(b'{"type":"turn.completed","usage":')
            c.save(folder/'status.json',{'state':'blocked'});c.save(root/'status.json',{'state':'blocked'})
            result=audit_shard(root,m,t)
            self.assertEqual((result['completed_cells'],result['submitted_cells'],result['unknown_usage_turns']),(0,1,1))
            self.assertEqual(result['known_total_tokens'],0)

    def test_cost_is_preserved_for_invalid_treatment_and_missing_provenance_rejects(self):
        raw=b'{"type":"item.completed","item":{"type":"todo_list"}}\n'+c.canonical({'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':50,'output_tokens':10}})
        self.assertEqual(observed_usage(raw)['input_tokens'],100)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder,m,t,row=self.fixture(root)
            (root/'runtime_provenance.json').unlink()
            with self.assertRaises(FileNotFoundError):audit_shard(root,m,t)


if __name__=='__main__':unittest.main()
