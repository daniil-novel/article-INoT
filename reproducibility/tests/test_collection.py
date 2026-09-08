import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reproducibility.collect_outcomes import collect, sha


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.archive=self.root/'archive';self.archive.mkdir()
        self.reports=self.root/'reports';self.reports.mkdir()
        self.code='def task_func(): return 1'
        self.g={'task_id':'BigCodeBench/0','arm':'single_neutral','seed':17,'model':'mock/model','cost_usd':.01,'total_tokens':100,'truncated':False}
        (self.archive/'results.jsonl').write_text(json.dumps(self.g)+'\n')
        (self.archive/'config.json').write_text(json.dumps({'model':'mock/model'}))
        (self.archive/'manifest.json').write_text(json.dumps({'cells':[self.g]}))
        self.pred=self.root/'predictions.jsonl';self.pred.write_text(json.dumps({'task_id':self.g['task_id'],'solution':self.code})+'\n')
        self.em=self.root/'export_manifest.json'
        self.em.write_text(json.dumps({'benchmark':'bigcodebench','source_sha256':sha(self.archive/'results.jsonl'),
                                      'groups':[{'model':'mock/model','arm':'single_neutral','seed':17,'path':str(self.pred),'sha256':sha(self.pred)}]}))
        self.check=patch('reproducibility.collect_outcomes.audit',return_value={'ok':True})
        self.check.start();self.addCleanup(self.check.stop)

    def report(self,code,status):
        p=self.reports/'predictions_eval_results.json'
        p.write_text(json.dumps({'eval':{self.g['task_id']:[{'solution':code,'status':status,'details':{}}]}}))

    def test_official_pass_is_joined_and_hashed(self):
        self.report(self.code,'pass')
        rows=collect(self.archive,self.em,self.reports)
        self.assertTrue(rows[0]['resolved'])
        self.assertEqual(len(rows[0]['report_sha256']),64)

    def test_report_absence_remains_missing(self):
        row=collect(self.archive,self.em,self.reports)[0]
        self.assertIsNone(row['resolved'])
        self.assertEqual(row['missing_reason'],'official_report_missing')

    def test_another_evaluated_program_is_rejected(self):
        self.report('def task_func(): return 2','pass')
        with self.assertRaisesRegex(ValueError,'different code'):collect(self.archive,self.em,self.reports)

    def test_unknown_status_is_not_scored(self):
        self.report(self.code,'infrastructure_error')
        self.assertIsNone(collect(self.archive,self.em,self.reports)[0]['resolved'])

    def test_swe_empty_patch_without_report_is_explicit_candidate_failure(self):
        archive = self.root / 'swe-archive'; archive.mkdir()
        task = 'pvlib__pvlib-python-1606'
        cell = {'task_id': task, 'arm': 'direct', 'seed': 2, 'model': 'mock/model',
                'cost_usd': .01, 'total_tokens': 100, 'truncated': False, 'final_text': 'No usable patch.'}
        (archive / 'results.jsonl').write_text(json.dumps(cell) + '\n')
        (archive / 'config.json').write_text(json.dumps({'model': 'mock/model'}))
        (archive / 'manifest.json').write_text(json.dumps({'cells': [cell]}))
        pred = self.root / 'swe-predictions.jsonl'
        pred.write_text(json.dumps({'instance_id': task, 'model_name_or_path': 'mock/model', 'model_patch': ''}) + '\n')
        run_id = 'swe-run'
        em = self.root / 'swe-export.json'
        em.write_text(json.dumps({'benchmark': 'swebench', 'source_sha256': sha(archive / 'results.jsonl'),
                                  'groups': [{'model': 'mock/model', 'arm': 'direct', 'seed': 2,
                                              'path': str(pred), 'sha256': sha(pred), 'run_id': run_id}]}))
        rows = collect(archive, em, self.reports)
        self.assertFalse(rows[0]['resolved'])
        self.assertEqual(rows[0]['outcome_type'], 'candidate_invalid_patch')
        self.assertIsNone(rows[0]['report_sha256'])
        self.assertEqual(len(rows[0]['prediction_sha256']), 64)

    def test_swe_missing_report_with_nonempty_patch_is_unknown(self):
        archive = self.root / 'swe-archive'; archive.mkdir()
        task = 'pvlib__pvlib-python-1606'
        cell = {'task_id': task, 'arm': 'direct', 'seed': 2, 'model': 'mock/model',
                'cost_usd': .01, 'total_tokens': 100, 'truncated': False, 'final_text': '```diff\ndiff --git a/a b/a\n```'}
        (archive / 'results.jsonl').write_text(json.dumps(cell) + '\n')
        (archive / 'config.json').write_text(json.dumps({'model': 'mock/model'}))
        (archive / 'manifest.json').write_text(json.dumps({'cells': [cell]}))
        pred = self.root / 'swe-predictions.jsonl'
        pred.write_text(json.dumps({'instance_id': task, 'model_name_or_path': 'mock/model', 'model_patch': 'diff --git a/a b/a'}) + '\n')
        run_id = 'swe-run'
        (self.reports / run_id).mkdir()
        (self.reports / run_id / 'results.json').write_text(json.dumps({'error_ids': [task], 'infra_failure_ids': []}))
        em = self.root / 'swe-export.json'
        em.write_text(json.dumps({'benchmark': 'swebench', 'source_sha256': sha(archive / 'results.jsonl'),
                                  'groups': [{'model': 'mock/model', 'arm': 'direct', 'seed': 2,
                                              'path': str(pred), 'sha256': sha(pred), 'run_id': run_id}]}))
        rows = collect(archive, em, self.reports)
        self.assertIsNone(rows[0]['resolved'])
        self.assertEqual(rows[0]['outcome_type'], 'evaluator_error')

    def test_swe_infrastructure_report_does_not_become_candidate_failure(self):
        archive = self.root / 'swe-archive'; archive.mkdir()
        task = 'pvlib__pvlib-python-1606'
        cell = {'task_id': task, 'arm': 'direct', 'seed': 2, 'model': 'mock/model',
                'cost_usd': .01, 'total_tokens': 100, 'truncated': False, 'final_text': 'No usable patch.'}
        (archive / 'results.jsonl').write_text(json.dumps(cell) + '\n')
        (archive / 'config.json').write_text(json.dumps({'model': 'mock/model'}))
        (archive / 'manifest.json').write_text(json.dumps({'cells': [cell]}))
        pred = self.root / 'swe-predictions.jsonl'
        pred.write_text(json.dumps({'instance_id': task, 'model_name_or_path': 'mock/model', 'model_patch': ''}) + '\n')
        run_id = 'swe-run'
        task_dir = self.reports / run_id / 'mock__model' / task
        task_dir.mkdir(parents=True)
        (task_dir / 'patch.diff').write_text('')
        (task_dir / 'report.json').write_text(json.dumps({task: {
            'resolved': False, 'infra_failure': True,
        }}))
        em = self.root / 'swe-export.json'
        em.write_text(json.dumps({'benchmark': 'swebench', 'source_sha256': sha(archive / 'results.jsonl'),
                                  'groups': [{'model': 'mock/model', 'arm': 'direct', 'seed': 2,
                                              'path': str(pred), 'sha256': sha(pred), 'run_id': run_id}]}))
        rows = collect(archive, em, self.reports)
        self.assertIsNone(rows[0]['resolved'])
        self.assertEqual(rows[0]['outcome_type'], 'infrastructure_unknown')

    def test_swe_native_application_rejection_is_explicit_failure(self):
        archive = self.root / 'swe-archive'; archive.mkdir()
        task = 'pvlib__pvlib-python-1606'
        cell = {'task_id': task, 'arm': 'direct', 'seed': 2, 'model': 'mock/model',
                'cost_usd': .01, 'total_tokens': 100, 'truncated': False, 'final_text': '```diff\ndiff --git a/a b/a\n```'}
        (archive / 'results.jsonl').write_text(json.dumps(cell) + '\n')
        (archive / 'config.json').write_text(json.dumps({'model': 'mock/model'}))
        (archive / 'manifest.json').write_text(json.dumps({'cells': [cell]}))
        pred = self.root / 'swe-predictions.jsonl'
        patch_text = 'diff --git a/a b/a'
        pred.write_text(json.dumps({'instance_id': task, 'model_name_or_path': 'mock/model', 'model_patch': patch_text}) + '\n')
        run_id = 'swe-run'
        task_dir = self.reports / run_id / 'mock__model' / task
        task_dir.mkdir(parents=True)
        (task_dir / 'patch.diff').write_text(patch_text)
        (task_dir / 'run_instance.log').write_text('>>>>> Patch Apply Failed')
        (self.reports / run_id / 'results.json').write_text(json.dumps({'error_ids': [task], 'infra_failure_ids': []}))
        em = self.root / 'swe-export.json'
        em.write_text(json.dumps({'benchmark': 'swebench', 'source_sha256': sha(archive / 'results.jsonl'),
                                  'groups': [{'model': 'mock/model', 'arm': 'direct', 'seed': 2,
                                              'path': str(pred), 'sha256': sha(pred), 'run_id': run_id}]}))
        rows = collect(archive, em, self.reports)
        self.assertFalse(rows[0]['resolved'])
        self.assertEqual(rows[0]['outcome_type'], 'native_application_rejection')
        self.assertEqual(len(rows[0]['application_log_sha256']), 64)


if __name__=='__main__':unittest.main()
