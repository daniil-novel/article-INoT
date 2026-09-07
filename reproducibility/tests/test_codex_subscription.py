import json
import unittest
from reproducibility import codex_subscription as c


class SubscriptionTests(unittest.TestCase):
    def stream(self, usage=None, extra=None):
        events=[{'type':'thread.started','thread_id':'fixture'}, {'type':'turn.started'}]
        if extra:events.append(extra)
        events += [{'type':'item.completed','item':{'type':'agent_message','text':'```python\ndef f(): return 1\n```'}},
                   {'type':'turn.completed','usage':usage or {'input_tokens':1000,'cached_input_tokens':400,'output_tokens':200,'reasoning_output_tokens':150}}]
        return '\n'.join(json.dumps(e) for e in events).encode()

    def test_cost_counts_subsets_once(self):
        r=c.parse_events(self.stream())
        self.assertAlmostEqual(r['api_equivalent_usd'],(.75*600+.075*400+4.5*200)/1e6)
        self.assertAlmostEqual(r['uncached_sensitivity_usd'],(.75*1000+4.5*200)/1e6)

    def test_usage_is_required(self):
        with self.assertRaises(ValueError):c.parse_events(self.stream({'input_tokens':1000}))

    def test_cached_tokens_cannot_exceed_input(self):
        with self.assertRaises(ValueError):c.parse_events(self.stream({'input_tokens':10,'cached_input_tokens':20,'output_tokens':3}))

    def test_tool_and_reconnect_events_fail_closed(self):
        for extra in [{'type':'error','message':'Reconnecting'}, {'type':'item.completed','item':{'type':'command_execution','command':'pytest'}}, {'type':'context.compacted'}]:
            with self.subTest(extra=extra),self.assertRaises(ValueError):c.parse_events(self.stream(extra=extra))

    def test_full_context_and_history_no_metadata_leak(self):
        task={'task_id':'a','prompt':'instructions','context':'完整\ncontext','metadata':{'test':'DO NOT FORWARD'}}
        cell={'arm':'multi_roles','cli_turns':3}
        first='complete output\n'*300
        text=c.prompt_for(task,cell,1,[first])
        self.assertIn(task['context'],text);self.assertIn(first,text);self.assertNotIn('DO NOT FORWARD',text)
        with self.assertRaises(ValueError):c.prompt_for(task,cell,1,[])

    def test_manifest_has_full_matrix_and_no_fake_seed_claim(self):
        tasks=[{'task_id':'a'},{'task_id':'b'}]
        m=c.make_manifest(tasks,[1,2],list(c.ARMS))
        self.assertEqual(m['planned_generations'],20);self.assertEqual(m['planned_cli_turns'],36)
        self.assertFalse(m['model_seed_supported']);self.assertFalse(m['completion_allowance_matched'])
        self.assertEqual(m,c.make_manifest(tasks,[1,2],list(c.ARMS)))

    def test_subscription_transport_and_tools_are_explicit(self):
        argv=c.cli_command(['codex'],'empty','instructions.txt')
        self.assertIn('forced_login_method="chatgpt"',argv)
        self.assertIn('model_providers.study-openai.request_max_retries=0',argv)
        self.assertIn('model_providers.study-openai.supports_websockets=false',argv)
        self.assertIn('features.shell_tool=false',argv)
        self.assertEqual(argv[-1],'-')


if __name__=='__main__':unittest.main()
