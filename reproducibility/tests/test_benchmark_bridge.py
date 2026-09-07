import json
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from reproducibility import benchmark_bridge as bridge


def _write_jsonl(path: Path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _read_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _task(task_id, prompt="Prompt", context="Context"):
    return {
        "task_id": task_id,
        "instruct_prompt": prompt,
        "code_prompt": context,
        "complete_prompt": "DOCSTRING",
        "test": "def test_x(): ...",
        "canonical_solution": "pass",
    }


class BenchmarkBridgePrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.dataset = self.tmpdir / "dataset.jsonl"
        self.out = self.tmpdir / "out"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prepared_rows(self):
        return _read_jsonl(self.out / "prepared.jsonl")

    def test_prepare_deterministic_split(self):
        rows = [_task("t03"), _task("t01"), _task("t02"), _task("t00")]
        _write_jsonl(self.dataset, rows)
        manifest = bridge.prepare_dataset(self.dataset, self.out, dev_size=2)
        got = [r["task_id"] for r in self._prepared_rows()]
        ids = sorted(["t03", "t01", "t02", "t00"])
        rng = random.Random(bridge.SEED)
        rng.shuffle(ids)
        expected = ids[:2]
        self.assertEqual(got, expected)
        self.assertEqual(manifest["dev_size"], 2)
        confirm = _read_jsonl(self.out / "confirmatory.jsonl")
        confirm_ids = {r["task_id"] for r in confirm}
        self.assertFalse(confirm_ids.intersection(got))
        self.assertEqual(confirm_ids.union(got), set(ids))
        self.assertEqual(len(confirm), 2)

    def test_prepare_no_solution_or_test_leakage(self):
        rows = [_task("alpha")]
        _write_jsonl(self.dataset, rows)
        bridge.prepare_dataset(self.dataset, self.out, dev_size=1)
        row = self._prepared_rows()[0]
        self.assertEqual(set(row), {"task_id", "prompt", "context", "benchmark", "metadata"})
        self.assertNotIn("test", row)
        self.assertNotIn("complete_prompt", row)
        self.assertNotIn("canonical_solution", row)

    def test_prepare_preserves_unicode_context(self):
        rows = [_task("u1", "Задание:", "Контекст: π≈3.14159, emoji 😀")]
        _write_jsonl(self.dataset, rows)
        bridge.prepare_dataset(self.dataset, self.out, dev_size=1)
        row = self._prepared_rows()[0]
        self.assertEqual(row["context"], "Контекст: π≈3.14159, emoji 😀")
        self.assertEqual(row["prompt"], "Задание:")

    def test_prepare_rejects_duplicate_task_ids(self):
        rows = [_task("dup"), _task("dup")]
        _write_jsonl(self.dataset, rows)
        with self.assertRaises(ValueError):
            bridge.prepare_dataset(self.dataset, self.out, dev_size=1)

    def test_prepare_rejects_missing_prompt(self):
        bad = [{"task_id": "bad", "code_prompt": "ctx"}]
        _write_jsonl(self.dataset, bad)
        with self.assertRaises(ValueError):
            bridge.prepare_dataset(self.dataset, self.out, dev_size=1)


class BenchmarkBridgeExportTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.results = self.tmpdir / "results.jsonl"
        self.out = self.tmpdir / "out"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_distinct_grouped_files(self):
        rows = [
            {
                "task_id": "a",
                "arm": "base",
                "seed": 1,
                "model": "org/model-A",
                "final_text": "```python\nprint(1)\n```",
            },
            {
                "task_id": "b",
                "arm": "base",
                "seed": 1,
                "model": "org/model-A",
                "final_text": "```python\nprint(2)\n```",
            },
            {
                "task_id": "c",
                "arm": "alt",
                "seed": 1,
                "model": "org/model-A",
                "final_text": "```python\nprint(3)\n```",
            },
            {
                "task_id": "d",
                "arm": "base",
                "seed": 2,
                "model": "org/model-B",
                "final_text": "```python\nprint(4)\n```",
            },
        ]
        _write_jsonl(self.results, rows)
        manifest = bridge.export_results(self.results, "bigcodebench", self.out)
        paths = [g["path"] for g in manifest["groups"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(len(manifest["groups"]), 3)
        self.assertEqual(manifest["ambiguous_or_missing_extractions"], 0)

    def test_export_ambiguous_fences_are_empty_and_counted(self):
        rows = [
            {
                "task_id": "x",
                "arm": "base",
                "seed": 7,
                "model": "org/amb",
                "final_text": "```python\nprint(1)\n```\nmiddle\n```python\nprint(2)\n```",
            }
        ]
        _write_jsonl(self.results, rows)
        manifest = bridge.export_results(self.results, "bigcodebench", self.out)
        std = _read_jsonl(self.out / "standardized_results.jsonl")
        self.assertEqual(std[0]["final_text"], "")
        self.assertEqual(manifest["ambiguous_or_missing_extractions"], 1)
        group_path = Path(manifest["groups"][0]["path"])
        pred_rows = _read_jsonl(group_path)
        self.assertEqual(pred_rows[0]["solution"], "")
        self.assertIn("extract_failed", manifest["logs"][0])


if __name__ == "__main__":
    unittest.main()
