"""Artificial raw/native fixtures exercise full replay; no study outcomes are read."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from reproducibility import codex_luna_subscription as cli
from reproducibility.evidence_manifest import write
from reproducibility.scale1000_luna import collect, dispatch
from reproducibility.scale1000 import analyze
from reproducibility.scale_env.validate_native import _expected_tail
from reproducibility.revision_20260911 import scale_replay

ROOT = Path(__file__).resolve().parents[2]


def fixture(tmp_path):
    archive = tmp_path / "artificial-study"
    generation = archive / "generation"; generation.mkdir(parents=True)
    inputs = archive / "inputs/scale1000-v1"
    (inputs / "input").mkdir(parents=True)
    original = ROOT / "reproducibility/scale1000/inputs-v1"
    for name in ("selection.json", "input/prepared.jsonl"):
        shutil.copyfile(original / name, inputs / name)
    gate = archive / "controls/controls-v3"
    shutil.copytree(ROOT / "reproducibility/results/20260908_scale1000_preflight/controls-v3", gate)
    frozen = dispatch.plan(inputs, gate)
    cli.save(generation / "manifest.json", frozen)
    cli.save(generation / "status.json", {"state": "generation_finished", "synthetic_fixture": True})
    tasks = cli.tasks_from(inputs / "input/prepared.jsonl")
    cli.save(generation / "tasks.json", tasks)
    (generation / "instructions.txt").write_bytes(cli.BASE.encode())
    prefix = ["synthetic-codex-no-execution"]
    cli.save(generation / "runtime.json", {"prefix": prefix, "version": cli.CLI_VERSION})
    for name in dispatch.DEPENDENCIES:
        target = generation / "sources" / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / "reproducibility" / name).read_bytes().replace(b"\r\n", b"\n"))
    (archive / "protocols").mkdir()
    shutil.copyfile(ROOT / "reproducibility/scale1000_luna/PROTOCOL.md", archive / "protocols/PROTOCOL.md")
    eligible = cli.read(gate / "heldout200_control_gate.json")["evaluable_task_ids"][:2]
    task_index = {task["task_id"]: task for task in tasks}
    # Two tasks, all five arms and all three repeats: 30 artificial completed cells.
    for cell in frozen["inner_manifest"]["cells"]:
        if cell["task_id"] not in eligible: continue
        history = []; turns = []
        for stage in range(cell["cli_turns"]):
            folder = generation / "turns" / f"{cell['id']}-{stage}"; folder.mkdir(parents=True)
            answer = "```python\ndef task_func():\n    return 1\n```"
            events = [{"type": "thread.started", "thread_id": "artificial-test-fixture"},
                {"type": "turn.started"}, {"type": "item.completed", "item": {"type": "agent_message", "text": answer}},
                {"type": "turn.completed", "usage": {"input_tokens": 100 + stage, "cached_input_tokens": 20, "output_tokens": 10}}]
            (folder / "events.jsonl").write_bytes(b"".join(cli.canonical(e) + b"\n" for e in events))
            (folder / "prompt.txt").write_bytes(cli.prompt_for(task_index[cell["task_id"]], cell, stage, history).encode())
            cli.save(folder / "argv.json", cli.cli_command(prefix, Path(r"E:\artificial\empty"), Path(r"E:\artificial\instructions.txt")))
            (folder / "stderr.txt").write_bytes(b"")
            result = cli.parse_events((folder / "events.jsonl").read_bytes())
            result["files_sha256"] = {name: dispatch.sha(folder / name) for name in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt")}
            cli.save(folder / "result.json", result)
            cli.save(folder / "status.json", {"state": "completed", "synthetic_fixture": True})
            history.append(answer); turns.append(result)
        usage = {name: sum(turn["usage"][name] for turn in turns) for name in ("input_tokens", "cached_input_tokens", "output_tokens")}
        cli.save(generation / "cells" / (cell["id"] + ".json"), {**cell, "final_text": history[-1], "usage": usage,
            "total_tokens": usage["input_tokens"] + usage["output_tokens"],
            "api_equivalent_usd": sum(turn["api_equivalent_usd"] for turn in turns),
            "uncached_sensitivity_usd": sum(turn["uncached_sensitivity_usd"] for turn in turns)})
    predictions = archive / "predictions"
    collect.export(generation, inputs, gate, generation / "manifest.json", predictions)
    reference_meta = cli.read(gate / "gold/run-metadata.json")
    for rep in dispatch.REPEATS:
        for arm_no, arm in enumerate(cli.ARMS):
            key = f"{arm}-r{rep}"
            folder = archive / "native" / key; (folder / "input").mkdir(parents=True)
            shutil.copyfile(predictions / (key + ".jsonl"), folder / "input/samples.jsonl")
            samples = [json.loads(line) for line in (folder / "input/samples.jsonl").read_text().splitlines()]
            ids = [row["task_id"] for row in samples]
            metadata = copy.deepcopy(reference_meta); metadata["synthetic_fixture"] = True
            metadata["argv"] = metadata["argv"][:metadata["argv"].index("-m") + 1] + _expected_tail(ids)
            for name in ("samples_source_sha256", "staged_samples_sha256", "post_evaluator_staged_samples_sha256"):
                metadata[name] = dispatch.sha(folder / "input/samples.jsonl")
            cli.save(folder / "run-metadata.json", metadata)
            for name in ("pip-freeze.txt", "nltk-resources-sha256.txt"):
                shutil.copyfile(gate / "gold" / name, folder / name)
            rows = {row["task_id"]: [{**row, "status": "pass" if (number + arm_no + rep) % 3 else "fail"}]
                for number, row in enumerate(samples)}
            cli.save(folder / "input/samples_eval_results.json", {"eval": rows, "synthetic_fixture": True})
    collect.collect(generation, inputs, gate, generation / "manifest.json", predictions, archive / "native", archive / "analysis")
    records = [json.loads(line) for line in (archive / "analysis/candidate_records.jsonl").read_text().splitlines()]
    cli.save(archive / "analysis/summary.json", analyze.summarize(records, cli.read(inputs / "selection.json")))
    scale_replay.install(archive, ROOT)
    write(archive)
    return archive


def test_full_frozen_replay_outside_checkout_and_tamper_detection(tmp_path):
    archive = fixture(tmp_path)
    outside = tmp_path / "unrelated-directory"; outside.mkdir()
    env = dict(os.environ); env.pop("PYTHONPATH", None)
    command = [sys.executable, str(archive / "provenance/scale_replay.py"), "--archive", str(archive)]
    def replay():
        return subprocess.run(command, cwd=outside, env=env, capture_output=True, text=True, timeout=120)
    result = replay()
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["assigned_rows"] == 15000
    # Refreshing the byte inventory must not hide a false inferential result.
    summary = archive / "analysis/summary.json"; original = summary.read_bytes()
    altered = cli.read(summary)
    contrast = altered["contrasts"]["single_roles_minus_single_neutral"]
    assert contrast["holm_p"] == 1.0
    contrast["holm_p"] = 0.000001  # false significance; original mean/count stay unchanged
    cli.save(summary, altered); write(archive)
    result = replay()
    assert result.returncode != 0 and "statistical summary differs" in result.stderr
    summary.write_bytes(original)
    # The raw request must match the frozen task and complete prior-stage history.
    prompt = next((archive / "generation/turns").glob("*/prompt.txt")); original = prompt.read_bytes()
    prompt.write_bytes(b"substituted synthetic request"); write(archive)
    result = replay()
    assert result.returncode != 0 and "Prompt or forwarded response differs" in result.stderr
    prompt.write_bytes(original)
    # A report with the right ID but another program cannot justify the saved outcome.
    report = next((archive / "native").glob("*/input/samples_eval_results.json"))
    altered = cli.read(report); first = next(iter(altered["eval"].values()))
    first[0]["solution"] = "def task_func(): return 123"
    cli.save(report, altered); write(archive)
    result = replay()
    assert result.returncode != 0 and "evaluated solution mismatch" in result.stderr
