import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("factorial_runner", Path(__file__).parents[1]/"factorial_runner.py")
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = {"model":"mock/model","provider":"mock","seeds":[17,43,101],"arms":list(f.ARMS),
                  "temperature":.2,"max_completion_tokens_total":300,"max_cost_usd":300,
                  "input_usd_per_million":1,"output_usd_per_million":1,
                  "max_context_tokens":100000,"prompt_tokens_upper_bound":90000}
        self.tasks = [{"task_id":str(i),"prompt":"Implement statistical tests; preserve requirements.",
                       "context":"Контекст\n"+str(i),"benchmark":"mock","metadata":{"test":"NEVER SEND"}} for i in range(2)]
        self.cp,self.tp,self.mp = (self.root/x for x in ("c.json","t.jsonl","m.json"))
        self.prepare()
        self.ledger,self.archive = self.root/"ledger.json",self.root/"archive"
        self.env = patch.dict(os.environ,{"OPENROUTER_API_KEY":"secret-test-value"})
        self.env.start();self.addCleanup(self.env.stop)

    def prepare(self):
        f.save(self.cp,self.c)
        self.tp.write_text("".join(json.dumps(t)+"\n" for t in self.tasks),encoding="utf-8")
        self.m = f.build_manifest(self.c,self.tasks)
        f.save(self.mp,self.m)

    def response(self,request,key):
        self.assertNotIn(key,json.dumps(request))
        self.assertEqual(len(f.read(self.ledger)["pending"]),1)
        body = {"id":"mock-response","model":"mock/model","provider":"mock","usage":{
                "cost":.0001,"prompt_tokens":10,"completion_tokens":10,"total_tokens":20},
                "choices":[{"finish_reason":"stop","message":{"content":"```python\ndef task_func(): return 1\n```"}}]}
        return {"body":json.dumps(body),"status":200,"started_unix":1,"latency_seconds":.01}

    def run_it(self,send=None,budget=1):
        return f.run(self.cp,self.tp,self.mp,self.archive,self.ledger,budget,send=send or self.response)

    def test_full_grid_all_seeds(self):
        self.assertEqual(self.m["call_count"],48)
        self.assertEqual(self.m["generation_count"],24)
        self.assertEqual(len({(x['task_id'],x['seed'],x['arm']) for x in self.m['cells']}),24)
        self.assertEqual(self.m,f.build_manifest(self.c,self.tasks))

    def test_identical_context_role_only_intervention(self):
        cell={"calls":1,"seed":17,"arm":"single_neutral"}
        a=f.payload(self.c,self.tasks[0],cell,0,[])
        b=f.payload(self.c,self.tasks[0],{**cell,"arm":"single_roles"},0,[])
        self.assertEqual(a['messages'][1],b['messages'][1])
        self.assertNotIn('NEVER SEND',json.dumps(a))
        self.assertIn(self.tasks[0]['context'],a['messages'][1]['content'])
        self.assertEqual(a['seed'],17)
        self.assertNotIn('truncation',a)
        self.assertEqual(a['messages'][0]['content'].replace('stage 1:','planner:').replace('stage 2:','implementer:').replace('stage 3:','reviewer:'),b['messages'][0]['content'])

    def test_archive_integrity_resume_and_seed_isolation(self):
        self.assertEqual(self.run_it()['status'],'completed')
        self.assertTrue(f.audit(self.archive)['ok'])
        self.assertEqual(len((self.archive/'results.jsonl').read_text().splitlines()),24)
        self.run_it(send=lambda *_:self.fail('Completed resume called API'))
        for cell in self.m['cells']:
            p=f.read(self.archive/'calls'/f"{cell['id']}-0.request.json")
            self.assertNotIn('PREVIOUS STAGE',p['messages'][1]['content'])
        response=next((self.archive/'calls').glob('*.response.json'))
        response.write_text('{}')
        self.assertFalse(f.audit(self.archive)['ok'])

    def test_budget_and_context_block_before_http(self):
        result=self.run_it(send=lambda *_:self.fail('budget exceeded'),budget=.0000001)
        self.assertEqual(result['status'],'blocked_budget')
        self.c['prompt_tokens_upper_bound']=1;self.prepare()
        self.archive=self.root/'small'
        with self.assertRaisesRegex(ValueError,'not shortened'):
            self.run_it(send=lambda *_:self.fail('context exceeded'))

    def test_unknown_charge_keeps_raw_and_blocks_resume(self):
        def missing_cost(request,key):
            raw=self.response(request,key);d=json.loads(raw['body']);del d['usage']['cost'];raw['body']=json.dumps(d);return raw
        self.assertEqual(self.run_it(send=missing_cost)['status'],'blocked_unknown_charge')
        self.assertTrue(list((self.archive/'calls').glob('*.transport.json')))
        self.assertGreater(sum(f.read(self.ledger)['pending'].values()),0)
        with self.assertRaisesRegex(ValueError,'reconciliation'):
            self.run_it(send=lambda *_:self.fail('ambiguous retry'))

    def test_http_error_and_key_redaction(self):
        result=self.run_it(send=lambda r,k:{'body':'{"error":"'+k+'"}','status':503})
        self.assertEqual(result['status'],'blocked_unknown_charge')
        for p in self.archive.rglob('*.json'):
            self.assertNotIn('secret-test-value',p.read_text())
        raw=f.read(next((self.archive/'calls').glob('*.transport.json')))
        self.assertEqual(raw['status'],503)

    def test_global_budget_across_attempts(self):
        self.run_it()
        ledger=f.read(self.ledger);ledger['spent_usd']=299.999999;f.save(self.ledger,ledger)
        self.archive=self.root/'second'
        self.assertEqual(self.run_it(send=lambda *_:self.fail('global budget ignored'))['status'],'blocked_budget')

    def test_nonfinite_values_and_duplicate_grid_rejected(self):
        for value in [float('nan'),float('inf'),-1,True]:
            with self.assertRaises(ValueError):f.finite(value,'cost')
        self.c['seeds']=[17,17];f.save(self.cp,self.c)
        with self.assertRaisesRegex(ValueError,'duplicate'):f.config_from(self.cp)

    def test_changed_source_or_manifest_rejected(self):
        m=f.read(self.mp);m['cells']=m['cells'][:-1];f.save(self.mp,m)
        with self.assertRaisesRegex(ValueError,'Frozen manifest'):
            self.run_it(send=lambda *_:self.fail('changed manifest'))

    def test_lock_prevents_concurrent_campaign(self):
        with f.ledger_lock(self.ledger):
            with self.assertRaises(FileExistsError):
                self.run_it(send=lambda *_:self.fail('lock ignored'))

    def test_derived_results_tampering_is_detected(self):
        self.run_it()
        p=self.archive/'results.jsonl'
        rows=[json.loads(line) for line in p.read_text().splitlines()]
        rows[0]['cost_usd']=0
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        self.assertFalse(f.audit(self.archive)['ok'])


if __name__=='__main__':unittest.main()
