"""Run the separately frozen developer-only diagnostic after the main queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(setup_path: Path, job: Path, pid: int, created: float) -> None:
    from .developer_diagnostic import validate_setup
    from reproducibility.scale_env.validate_native import validate_native

    process = psutil.Process(pid)
    if abs(process.create_time() - created) > .01 or Path(process.cwd()).resolve() != ROOT:
        raise ValueError("Main queue process identity differs")
    if "reproducibility.scc2000.queue_finish_parallel" not in process.cmdline():
        raise ValueError("Waiting process is not the authorized main queue")
    setup = read(setup_path)
    validate_setup(setup)
    job.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), ROOT / "reproducibility/scc2000/developer_diagnostic.py",
               ROOT / "reproducibility/heldout200/run_observed_native.py",
               ROOT / "reproducibility/scale_env/validate_native.py"]
    frozen = {str(p): sha(p) for p in sources + [setup_path]}
    save(job / "provenance.json", {"main_pid": pid, "main_created": created,
        "frozen_files": frozen, "no_model_calls": True, "no_candidate_retries": True})
    save(job / "status.json", {"state": "waiting_for_main_queue", "started_unix": time.time()})
    try:
        while process.is_running():
            try:
                process.wait(timeout=30)
            except psutil.TimeoutExpired:
                continue
        previous = ROOT / "reproducibility/runs/scc1000-luna-v1/finish-queue-parallel-20260913/status.json"
        if read(previous).get("state") != "completed":
            raise ValueError("Main native queue did not complete successfully")
        for name, expected in frozen.items():
            if sha(Path(name)) != expected:
                raise ValueError("Diagnostic source changed after queue binding: " + name)
        validate_setup(setup)
        requirements = ROOT / "reproducibility/scale1000/environment-v2/requirements.txt"
        dockerfile = ROOT / "reproducibility/scale1000/environment-v2/Dockerfile"
        env = setup["control_environment"]
        for path, key in ((requirements, "requirements_sha256"), (dockerfile, "dockerfile_sha256")):
            if sha(path) != env[key]:
                raise ValueError("Native environment source mismatch")
        image = "bcb-scale1000:v2"
        actual = subprocess.check_output(["docker", "--context", "default", "image", "inspect",
            image, "--format", "{{.Id}}"], text=True).strip()
        if actual != setup["frozen_image_id"]:
            raise ValueError("Native image differs from frozen controls")
        python = ROOT / "tmp/revision/replay-venv/Scripts/python.exe"
        eligible = set(read(Path(setup["control_gate"]))["evaluable_task_ids"])
        records, groups = [], []
        save(job / "status.json", {"state": "native_developer_diagnostic", "started_unix": time.time()})
        for group in setup["groups"]:
            rep = group["replicate_id"]
            target = setup_path.parent / "native" / f"replicate-{rep}"
            if target.exists():
                raise ValueError("Refusing a diagnostic rerun: " + str(target))
            command = [str(python), "-X", "utf8", "-m", "reproducibility.heldout200.run_observed_native",
                "--dataset", setup["dataset"], "--prepared", setup["prepared"],
                "--samples", group["samples"], "--output", str(target), "--selection", setup["selection"],
                "--image", image, "--requirements", str(requirements), "--dockerfile", str(dockerfile),
                "--deadline-seconds", "7200"]
            save(job / f"replicate-{rep}.command.json", command)
            with (job / f"replicate-{rep}.stdout.log").open("xb") as stdout, (job / f"replicate-{rep}.stderr.log").open("xb") as stderr:
                completed = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            save(job / f"replicate-{rep}.exit.json", {"returncode": completed.returncode, "finished_unix": time.time()})
            samples = [json.loads(line) for line in Path(group["samples"]).read_text(encoding="utf-8").splitlines() if line.strip()]
            expected = {r["task_id"]: r["solution"] for r in samples}
            audit = validate_native(target, expected, env)
            groups.append({"replicate_id": rep, "audit": audit})
            for task in expected:
                raw = audit["statuses"].get(task)
                status = raw if audit["ok"] and completed.returncode == 0 else None
                identities = [k for k in setup["candidate_source_hashes"] if k.startswith(f"{rep}:{task}:")]
                if len(identities) != 1:
                    raise ValueError("Diagnostic assignment identity mismatch")
                records.append({"assignment_id": identities[0].split(":", 2)[2],
                    "task_id": task, "replicate_id": rep, "raw_native_status": raw,
                    "native_status": status, "control_eligible": task in eligible,
                    "diagnostic_quality": status == "pass" if task in eligible and status in ("pass", "fail", "timeout") else None,
                    "primary_scc_quality": None})
            save(job / "partial-report.json", {"groups": groups, "records": records, "primary_imputation": None})
            if completed.returncode or not audit["ok"]:
                raise ValueError("Diagnostic group failed validation; raw outcomes retained")
        if len(records) != 399 or len({r["assignment_id"] for r in records}) != 399:
            raise ValueError("Diagnostic coverage differs from 399 frozen programs")
        save(setup_path.parent / "diagnostic-report.json", {"schema": "scc-developer-only-diagnostic-v1",
            "groups": groups, "records": records, "primary_imputation": None})
        save(job / "status.json", {"state": "completed", "programs": 399, "finished_unix": time.time()})
    except BaseException as exc:
        save(job / "status.json", {"state": "stopped", "reason": str(exc), "finished_unix": time.time()})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--created", type=float, required=True)
    args = parser.parse_args()
    run(args.setup.resolve(), args.job.resolve(), args.pid, args.created)
