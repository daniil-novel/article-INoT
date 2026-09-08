"""Single-shot native BigCodeBench held-out control runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

EXPECTED_COMMIT = "09dd993f46c3fbf3a799465bb96d524edcb0b199"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def capture(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout.strip()

def ids(path: Path) -> list[str]:
    out = [str(json.loads(line)["task_id"]) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(out) != 200 or len(set(out)) != 200:
        raise ValueError("input must contain exactly 200 unique task IDs")
    return out

def main() -> int:
    p = argparse.ArgumentParser()
    for name in ("dataset", "prepared", "samples", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--selection", type=Path, default=Path('reproducibility/revision/heldout200_selection.json'))
    p.add_argument("--deadline-seconds", type=int, default=7200)
    a = p.parse_args()
    for path in (a.dataset, a.prepared, a.samples):
        if not path.is_file(): raise FileNotFoundError(path)
    task_ids = ids(a.samples)
    if ids(a.prepared) != task_ids: raise ValueError("prepared and samples IDs differ")
    selection = json.loads(a.selection.read_text(encoding='utf-8'))
    if task_ids != selection['assigned_task_ids'] or ids(a.dataset) != task_ids:
        raise ValueError('Native task order differs from the frozen allocation')
    if sha256(a.prepared) != selection['model_input_sha256'] or sha256(a.dataset) != selection['evaluator_dataset_sha256']:
        raise ValueError('Native task data differ from the frozen selection hashes')
    if a.deadline_seconds <= 0:
        raise ValueError('A positive external deadline is required')
    a.output.mkdir(parents=True, exist_ok=True)
    if any(a.output.iterdir()): raise ValueError("output directory must be empty")
    stage = a.output / "input"; stage.mkdir(); staged = stage / "samples.jsonl"; shutil.copyfile(a.samples, staged)
    repo = Path(__file__).resolve().parents[2]; upstream = repo / "reproducibility/vendor/bigcodebench"; req = repo / "reproducibility/scale_env/requirements.txt"; dockerfile = repo / "reproducibility/scale_env/Dockerfile"
    commit = capture(["git", "-C", str(upstream), "rev-parse", "HEAD"])
    if commit != EXPECTED_COMMIT: raise ValueError("pinned upstream HEAD mismatch")
    subprocess.run(["git", "-C", str(upstream), "diff", "--quiet", "--exit-code", "HEAD", "--"], check=True)
    image_id = capture(["docker", "--context", "default", "image", "inspect", a.image, "--format", "{{.Id}}"])
    base_image_id = capture(["docker", "--context", "default", "image", "inspect", "bcb-official-cli:dev", "--format", "{{.Id}}"])
    provenance = json.loads(capture([sys.executable, str(repo / "reproducibility/scale_env/provenance.py"), "--vendor", str(upstream), "--dataset", str(a.dataset), "--prepared", str(a.prepared), "--requirements", str(req), "--dockerfile", str(dockerfile)]))
    container = "heldout200-" + uuid.uuid4().hex[:16]
    argv = ["docker", "--context", "default", "run", "--name", container, "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--memory", "3g", "--pids-limit", "256", "--cpus", "2", "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m", "--mount", f"type=bind,source={upstream},target=/workspace/reproducibility/vendor/bigcodebench,readonly", "--mount", f"type=bind,source={a.dataset.resolve()},target=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl,readonly", "--mount", f"type=bind,source={a.output.resolve()},target=/run", "--mount", f"type=bind,source={staged.resolve()},target=/run/input/samples.jsonl,readonly", "--env", "BIGCODEBENCH_OVERRIDE_PATH=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl", "--env", "NLTK_DATA=/opt/nltk_data", "--entrypoint", "python", image_id, "-m", "bigcodebench.evaluate", "instruct", "full", "--samples", "/run/input/samples.jsonl", "--execution", "local", "--selective_evaluate", ",".join(task_ids), "--calibrated", "False", "--parallel", "2", "--no_gt", "True", "--save_pass_rate", "False", "--min_time_limit", "0.1", "--max_as_limit", "30720", "--max_data_limit", "30720", "--max_stack_limit", "10"]
    meta: dict[str, Any] = {"schema": "heldout200-native-run-v2", "image_id": image_id, "base_image_id": base_image_id, "upstream_commit_expected": EXPECTED_COMMIT, "upstream_commit_verified": commit, "selected_ids": task_ids, "assigned_task_ids": task_ids, "cli_split": "instruct", "dataset_sha256": sha256(a.dataset), "prepared_split_sha256": sha256(a.prepared), "samples_source_sha256": sha256(a.samples), "staged_samples_sha256": sha256(staged), "network": "none", "argv": argv, "process_limits": {"memory": "3g", "pids": 256, "cpus": 2}, "provenance": provenance, "no_retry": True, "deadline_seconds": a.deadline_seconds}
    (a.output / "run-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    meta['selection_sha256'] = sha256(a.selection)
    meta['launcher_sha256'] = sha256(Path(__file__))
    meta['started_unix'] = time.time()
    freeze = ["docker", "--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--entrypoint", "python", image_id, "-m", "pip", "freeze"]
    with (a.output / "pip-freeze.txt").open("w", encoding="utf-8") as f: subprocess.run(freeze, check=True, stdout=f)
    meta["package_freeze_sha256"] = sha256(a.output / "pip-freeze.txt")
    resources = ["docker", "--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--entrypoint", "sh", image_id, "-c", "find /opt/nltk_data -type f -print0 | sort -z | xargs -0 sha256sum"]
    with (a.output / "nltk-resources-sha256.txt").open("w", encoding="utf-8") as f: subprocess.run(resources, check=True, stdout=f)
    meta["nltk_resources_sha256"] = sha256(a.output / "nltk-resources-sha256.txt")
    (a.output / "run-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    try:
        with (a.output / "stdout.log").open("w", encoding="utf-8") as out, (a.output / "stderr.log").open("w", encoding="utf-8") as err: result = subprocess.run(argv, stdout=out, stderr=err, timeout=a.deadline_seconds)
        meta["status"] = "completed" if result.returncode == 0 else "failed"; meta["exit_code"] = result.returncode
        if result.returncode: raise RuntimeError(f"evaluator exited with {result.returncode}")
        if sha256(staged) != meta["samples_source_sha256"]: raise ValueError("staged samples changed")
        meta["post_evaluator_staged_samples_sha256"] = sha256(staged)
    except subprocess.TimeoutExpired:
        meta["status"] = "deadline"; meta["exit_code"] = None; raise
    finally:
        subprocess.run(["docker", "--context", "default", "rm", "-f", container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        meta["finished_at_unix"] = time.time(); report = a.output / "input/samples_eval_results.json"; meta["report_sha256"] = sha256(report) if report.exists() else None
        (a.output / "run-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        hashes = {str(x.relative_to(a.output)): sha256(x) for x in a.output.rglob("*") if x.is_file()}; hashes.pop("report_hashes.json", None)
        (a.output / "report_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__": raise SystemExit(main())
