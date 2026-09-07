import json
from pathlib import Path
import tempfile
import unittest
from reproducibility.audit_codex_pilot import inventory_attempt


class FailedAttemptAccountingTests(unittest.TestCase):
    def test_tool_failure_usage_is_included_and_missing_is_not_zero(self):
        with tempfile.TemporaryDirectory() as root:
            archive=Path(root)
            (archive/'status.json').write_text('{"state":"blocked"}')
            for name,events in [('tool',[{'type':'item.completed','item':{'type':'todo_list'}},
                                         {'type':'turn.completed','usage':{'input_tokens':1000,'cached_input_tokens':400,'output_tokens':200}}]),
                                ('timeout',[])]:
                folder=archive/'turns'/name;folder.mkdir(parents=True)
                (folder/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
                (folder/'status.json').write_text('{"state":"blocked"}')
            result=inventory_attempt(archive)
            self.assertEqual(result['submitted_turns'],2)
            self.assertEqual(result['turns_with_complete_usage'],1)
            self.assertEqual(result['turns_with_unavailable_usage'],1)
            self.assertEqual(result['known_total_tokens'],1200)
            self.assertAlmostEqual(result['known_api_equivalent_usd'],.00138)
            self.assertTrue(all(not t['text_only_trace'] for t in result['turns']))


if __name__=='__main__': unittest.main()
