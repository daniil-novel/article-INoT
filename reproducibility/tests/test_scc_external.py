"""Contract checks execute upstream Session, not a rewritten SCC state machine."""
import copy
import unittest
from reproducibility.external_baselines import scc


class SCCContracts(unittest.TestCase):
    def drive(self, feedback, replies=None):
        replies = iter(replies or ['{"plan":"implement"}',
            '```python\ndef task_func(x):\n    return 0\n```',
            '```python\ndef check(candidate):\n    print(candidate(1))\n```',
            '```python\ndef task_func(x):\n    return x + 1\n```'])
        requests, executed = [], []
        def model(messages, **kwargs):
            requests.append(copy.deepcopy(messages))
            return [next(replies)]
        def execute(code, report):
            executed.append((code, report))
            return feedback
        code, history = scc.run_session('Return x plus one.', model, execute)
        return code, history, requests, executed

    def test_success_stops_after_tester_even_when_program_is_wrong(self):
        code, history, requests, executed = self.drive('Code Test Passed.')
        self.assertEqual(len(requests), 3)
        self.assertIn('return 0', code)
        self.assertIn('check(task_func)', executed[0][0])
        self.assertEqual(len(executed), 1)

    def test_failed_generated_test_reaches_original_repair_transition(self):
        code, history, requests, executed = self.drive('failed with AssertionError. wrong')
        self.assertEqual(len(requests), 4)
        self.assertIn('return x + 1', code)
        self.assertTrue(any('failed with AssertionError. wrong' in m['content'] for m in requests[3]))
        self.assertEqual(len(executed), 1)  # Upstream skips the final-round tester.

    def test_transport_abort_is_not_swallowed_as_model_error(self):
        def abort(*args, **kwargs):
            raise scc.TransportAbort('quota')
        with self.assertRaises(scc.TransportAbort):
            scc.run_session('Task', abort, lambda *args: self.fail('No execution expected'))

    def test_invalid_first_program_remains_upstream_error(self):
        code, history, requests, executed = self.drive('', ['plan', 'No implementation'])
        self.assertEqual(code, 'error')
        self.assertEqual(len(requests), 2)
        self.assertEqual(executed, [])

    def test_invalid_repair_retains_previous_valid_code(self):
        code, history, requests, executed = self.drive('example failure', ['plan',
            '```python\ndef task_func(x):\n    return 0\n```',
            '```python\ndef check(candidate):\n    print(candidate(1))\n```',
            'No valid repair'])
        self.assertIn('return 0', code)
        self.assertEqual(len(requests), 4)

    def test_original_extractor_uses_first_fence_and_last_function(self):
        scc.load_upstream()
        import utils
        code = utils.code_truncate('```python\ndef a(): pass\ndef b(): pass\n```\n```python\ndef c(): pass\n```')
        self.assertNotIn('def c', code)
        self.assertEqual(utils.find_method_name(code), 'b')

    def test_messages_round_trip_without_shortening_or_role_loss(self):
        import json
        messages = [{'role': 'user', 'content': 'a\n\"б\"'},
                    {'role': 'assistant', 'content': '```python\npass\n```'}]
        text = scc.serialize_messages(messages)
        self.assertEqual(json.loads(text.split('\n', 1)[1].rsplit('\n', 2)[0]), messages)

    def test_input_guard_never_truncates(self):
        with self.assertRaises(scc.TransportAbort):
            scc.serialize_messages([{'role': 'user', 'content': 'x'*65536}])

    def test_exact_upstream_source_integrity(self):
        self.assertEqual(scc.verify_vendor()['commit'], 'b471e12051190dbae2c71b429a3c87466df4b336')


if __name__ == '__main__':
    unittest.main()
