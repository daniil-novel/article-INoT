import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from reproducibility.swe_smoke.prepare_task import FORBIDDEN_FIELDS, verify_checkout


ROOT = Path(__file__).parents[1]
PACKET = ROOT / "results" / "20260908_codex_mini_swe_dev1" / "retrieval"


class SweSmokePreparationTests(unittest.TestCase):
    def test_runner_context_preserves_every_selected_file_byte(self):
        runner = PACKET / "runner-v2"
        task = json.loads((runner / "tasks.jsonl").read_text(encoding="utf-8"))
        verification = json.loads((runner / "checkout_verification.json").read_text(encoding="utf-8"))
        parts = []
        for record in verification["files"]:
            path = record["path"]
            content = (PACKET / "files" / path).read_bytes().decode("utf-8")
            parts.append(f"===== BEGIN RETRIEVED FILE: {path} =====\n{content}\n===== END RETRIEVED FILE: {path} =====")
        self.assertEqual(task["context"].encode("utf-8"), "\n\n".join(parts).encode("utf-8"))
        self.assertEqual(sum(record["bytes"] for record in verification["files"]), 23863)

    def test_runner_schema_excludes_forbidden_fields_and_renames_manifest_field(self):
        task = json.loads((PACKET / "runner-v2" / "tasks.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(set(task), {"task_id", "prompt", "context", "benchmark", "metadata"})
        self.assertEqual(task["benchmark"], "swebench")
        serialized_keys = json.dumps({"task": sorted(task), "metadata": sorted(task["metadata"])}, ensure_ascii=False).lower()
        for field in FORBIDDEN_FIELDS:
            self.assertNotIn(field, serialized_keys)
        manifest = json.loads((PACKET / "runner-v2" / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("forbidden_columns_not_read", manifest)
        self.assertNotIn("forbidden_columns_read", manifest)

    def test_tampered_retrieval_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_copy = root / "packet"
            shutil.copytree(PACKET, packet_copy)
            selected = json.loads((packet_copy / "manifest.json").read_text(encoding="utf-8"))["selected_file_records"]
            repo = root / "checkout"
            shutil.copytree(PACKET / "files", repo)
            def git(*args):
                return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout
            git("init", "-q")
            git("config", "core.autocrlf", "false")
            git("add", ".")
            git("-c", "user.name=Evidence test", "-c", "user.email=evidence@example.invalid", "commit", "-qm", "Frozen public source fixture")
            commit = git("rev-parse", "HEAD").decode("ascii").strip()
            verified = verify_checkout(repo, commit, selected, packet_copy / "files", root / "verified")
            self.assertEqual(len(verified["files"]), len(selected))
            target = packet_copy / "files" / selected[0]["path"]
            data = bytearray(target.read_bytes())
            data[0] ^= 1
            target.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "Tampered retrieval file hash"):
                verify_checkout(repo, commit, selected, packet_copy / "files", root / "rejected")


if __name__ == "__main__":
    unittest.main()
