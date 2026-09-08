import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reproducibility.heldout200 import inot_audit as a
from reproducibility import codex_subscription as c


class InotAuditTests(unittest.TestCase):
    def fixture(self, root):
        task = {'task_id': 'BigCodeBench/1', 'prompt': 'Implement task_func.', 'context': 'complete context'}
        cell = {'id': 'cell1', 'task_id': task['task_id'], 'arm': a.TREATMENT, 'replicate_id': 5, 'cli_turns': 1}
        tasks = [task]
        expected = {'cells': [cell], 'task_ids': [task['task_id']]}
        names = {'protocol.md': 'protocol_sha256', 'inot_source.py': 'source_sha256_lf',
                 'factorial_runner.py': 'shared_factorial_runner_sha256_lf',
                 'record_codex_runtime.py': 'shared_runtime_capture_sha256_lf',
                 'audit_codex_pilot.py': 'shared_archive_inventory_sha256_lf',
                 'runner_source.py': 'shared_runner_source_sha256_lf',
                 'selection.json': 'selection_sha256', 'control-gate.json': 'control_gate_sha256'}
        for name,key in names.items():
            (root/name).write_bytes(name.encode());expected[key]=a.sha256(root/name)
        (root/'instructions.txt').write_bytes(c.BASE.encode())
        (root/'npm-package-lock.json').write_bytes(b'{}')
        c.save(root/'manifest.json',expected);c.save(root/'tasks.json',tasks)
        runtime={'version':c.CLI_VERSION,'authentication':'chatgpt','workers':2,'timeout_seconds':180,'prefix':['node','codex.js']}
        c.save(root/'runtime.json',runtime)
        provenance={'cli_version':c.CLI_VERSION,'prefix':runtime['prefix'],'package_version':'0.153.4','native_executable_sha256':'fixture-binary',
                    'instructions_sha256':a.sha256(root/'instructions.txt'),'npm_lock_sha256':a.sha256(root/'npm-package-lock.json'),
                    'empty_working_directory':str(root/'empty'),'instructions_path':str(root/'instructions.txt')}
        c.save(root/'runtime_provenance.json',provenance)
        folder=root/'turns'/'cell1';folder.mkdir(parents=True)
        (folder/'prompt.txt').write_bytes(a.prompt_for(task).encode())
        c.save(folder/'argv.json',c.cli_command(runtime['prefix'],provenance['empty_working_directory'],provenance['instructions_path']))
        usage={'input_tokens':10,'cached_input_tokens':4,'output_tokens':3}
        events=[{'type':'thread.started'},{'type':'turn.started'},
                {'type':'item.completed','item':{'type':'agent_message','text':'FINAL_OUTPUT_BEGIN\n```python\ndef task_func(): return 1\n```\nFINAL_OUTPUT_END'}},
                {'type':'turn.completed','usage':usage}]
        (folder/'events.jsonl').write_bytes(b''.join(c.canonical(e)+b'\n' for e in events));(folder/'stderr.txt').write_bytes(b'')
        parsed=c.parse_events((folder/'events.jsonl').read_bytes())
        c.save(folder/'result.json',{**parsed,'wall_seconds':1,'files_sha256':{n:a.sha256(folder/n) for n in ['prompt.txt','argv.json','events.jsonl','stderr.txt']}})
        c.save(folder/'status.json',{'state':'completed'})
        row={**cell,**parsed,'model':c.MODEL,'seed':5,'treatment':a.TREATMENT,'total_tokens':13}
        c.save(root/'cells'/'cell1.json',row)
        (root/'results.jsonl').write_bytes(c.canonical(row)+b'\n')
        c.save(root/'status.json',{'state':'completed','failures':[]})
        return tasks,expected,row

    def check(self,root,tasks,expected):
        with patch.object(a,'ordered_tasks',return_value=tasks),patch.object(a,'plan',return_value=expected):
            return a.audit(root,root/'tasks.json',root/'selection.json',root/'control-gate.json',root/'protocol.md')

    def test_valid_archive_then_changed_prompt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tasks,m,row=self.fixture(root)
            self.assertEqual(self.check(root,tasks,m)['observed_cells'],1)
            (root/'turns/cell1/prompt.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'prompt bytes'):self.check(root,tasks,m)

    def test_orphan_and_exact_cli_override_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tasks,m,row=self.fixture(root)
            orphan=root/'turns/unauthorized';orphan.mkdir()
            with self.assertRaisesRegex(ValueError,'orphan'):self.check(root,tasks,m)
            orphan.rmdir();f=root/'turns/cell1/argv.json'
            c.save(f,c.read(f)+['-c','model_reasoning_effort="high"'])
            with self.assertRaisesRegex(ValueError,'Exact CLI'):self.check(root,tasks,m)

    def test_tampered_row_usage_final_and_total_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tasks,m,row=self.fixture(root)
            parsed=c.parse_events((root/'turns/cell1/events.jsonl').read_bytes())
            a.validate_row_against_turn(row,parsed)
            for key,value in [('final_text','changed'),('usage',{'input_tokens':99}),('total_tokens',999)]:
                with self.assertRaises(ValueError):a.validate_row_against_turn({**row,key:value},parsed)

    def test_partial_export_and_real_jsonl_order(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tasks,m,row=self.fixture(root)
            m['cells'].append({**m['cells'][0],'id':'cell2','task_id':'BigCodeBench/2'});m['task_ids'].append('BigCodeBench/2')
            c.save(root/'manifest.json',m)
            with self.assertRaises(ValueError):a.export_bigcodebench_code(root/'results.jsonl',root/'manifest.json',root/'strict')
            result=a.export_bigcodebench_code(root/'results.jsonl',root/'manifest.json',root/'partial',partial_status=True)
            self.assertEqual(result['status'],'partial_explicit')
            rows=[json.loads(x) for x in (root/'partial/samples.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),1);self.assertTrue(rows[0]['format_extracted'])


if __name__=='__main__':unittest.main()
