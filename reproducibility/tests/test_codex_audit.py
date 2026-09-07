import json
from pathlib import Path
import tempfile
import unittest
from reproducibility.audit_codex_pilot import inventory_attempt, audit, sha
from reproducibility import codex_subscription as c


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

    def make_archive(self, archive):
        tasks=[{'task_id':'test','prompt':'write code','context':'full context'}]
        manifest=c.make_manifest(tasks,[1],['direct']);cell=manifest['cells'][0]
        c.save(archive/'manifest.json',manifest);c.save(archive/'tasks.json',tasks)
        c.save(archive/'status.json',{'state':'completed'})
        (archive/'instructions.txt').write_bytes(c.BASE.encode())
        (archive/'runner_source.py').write_bytes(Path(c.__file__).read_bytes().replace(b'\r\n',b'\n'))
        (archive/'npm-package-lock.json').write_text('{}')
        runtime={'version':c.CLI_VERSION,'authentication':'chatgpt','workers':2,'timeout_seconds':180,'prefix':['codex']}
        c.save(archive/'runtime.json',runtime)
        c.save(archive/'runtime_provenance.json',{'cli_version':c.CLI_VERSION,'prefix':['codex'],'package_version':'0.153.4','native_executable_sha256':'fixture',
              'npm_lock_sha256':sha(archive/'npm-package-lock.json'),'empty_working_directory':str(archive/'empty'),
              'instructions_path':str(archive/'instructions.txt'),'instructions_sha256':sha(archive/'instructions.txt')})
        folder=archive/'turns'/(cell['id']+'-0');folder.mkdir(parents=True)
        (folder/'prompt.txt').write_bytes(c.prompt_for(tasks[0],cell,0,[]).encode())
        c.save(folder/'argv.json',c.cli_command(['codex'],archive/'empty',archive/'instructions.txt'))
        (folder/'stderr.txt').write_text('')
        events=[{'type':'thread.started'},{'type':'turn.started'},
                {'type':'item.completed','item':{'type':'agent_message','text':'answer'}},
                {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':0,'output_tokens':10,'reasoning_output_tokens':2}}]
        (folder/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
        result=c.parse_events((folder/'events.jsonl').read_bytes())
        result['files_sha256']={name:sha(folder/name) for name in ('prompt.txt','argv.json','stderr.txt','events.jsonl')}
        c.save(folder/'result.json',result);c.save(folder/'status.json',{'state':'completed'})
        row={**cell,**result,'total_tokens':110,'wall_seconds':1}
        (archive/'results.jsonl').write_bytes(c.canonical(row)+b'\n')
        return folder

    def test_changed_cli_flags_fail_even_with_consistent_file_hashes(self):
        with tempfile.TemporaryDirectory() as root:
            archive=Path(root);folder=self.make_archive(archive)
            self.assertEqual(audit(archive)['audit'],'passed')
            argv=c.read(folder/'argv.json');argv[argv.index('--sandbox')+1]='workspace-write'
            c.save(folder/'argv.json',argv)
            result=c.read(folder/'result.json');result['files_sha256']['argv.json']=sha(folder/'argv.json');c.save(folder/'result.json',result)
            with self.assertRaisesRegex(ValueError,'Exact CLI'):audit(archive)

    def test_wrong_runtime_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            archive=Path(root);self.make_archive(archive)
            runtime=c.read(archive/'runtime.json');runtime['version']='codex-cli 0.144.1';c.save(archive/'runtime.json',runtime)
            with self.assertRaisesRegex(ValueError,'Runtime version'):audit(archive)


if __name__=='__main__': unittest.main()
