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


if __name__=='__main__':unittest.main()
