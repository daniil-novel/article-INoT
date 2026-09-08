import json
from pathlib import Path
import shutil
import tempfile
import unittest
from reproducibility.audit_official_cli import check_run, read, jsonl

EVIDENCE=Path(__file__).resolve().parents[1]/'results/20260908_codex_mini_dev8/official-cli/direct'


class NativeAuditTests(unittest.TestCase):
    def setup_copy(self, root):
        folder=Path(root)/'native';shutil.copytree(EVIDENCE,folder)
        expected={r['task_id']:r['solution'] for r in jsonl(folder/'input/samples.jsonl')}
        dataset=read(folder/'run-metadata.json')['official_dataset_sha256']
        return folder,expected,dataset

    def test_actual_native_report_matches_preserved_samples(self):
        expected={r['task_id']:r['solution'] for r in jsonl(EVIDENCE/'input/samples.jsonl')}
        r=check_run(EVIDENCE,expected,read(EVIDENCE/'run-metadata.json')['official_dataset_sha256'])
        self.assertEqual(len(r['raw_status_by_task']),8)

    def test_report_cannot_substitute_a_different_solution(self):
        with tempfile.TemporaryDirectory() as root:
            folder,expected,dataset=self.setup_copy(root)
            file=folder/'input/samples_eval_results.json';r=read(file)
            next(iter(r['eval'].values()))[0]['solution']='replacement'
            file.write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'different code'):check_run(folder,expected,dataset)

    def test_wrong_benchmark_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            folder,expected,dataset=self.setup_copy(root)
            file=folder/'run-metadata.json';r=read(file);argv=r['arguments']
            argv[argv.index('bigcodebench.evaluate')+1]='dev'
            file.write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Wrong benchmark mode'):check_run(folder,expected,dataset)


if __name__=='__main__':unittest.main()
