from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
from reproducibility.segregation80 import prepare as module


def synthetic_task(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "instruct_prompt": "Implement task_func. Return one Python program.",
        "code_prompt": "def task_func(x):\n",
        "canonical_solution": "    return x\n",
        "test": "assert task_func(1) == 1",
    }


def synthetic_files(tmp_path: Path) -> SimpleNamespace:
    ids = [f"BigCodeBench/{i}" for i in range(90)]
    rows = [synthetic_task(task_id) for task_id in ids]
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    confirm_ids = ids[1:]
    confirmatory = tmp_path / "confirmatory.jsonl"
    confirmatory.write_text("".join(json.dumps({"task_id": task_id}) + "\n" for task_id in confirm_ids), encoding="utf-8", newline="\n")
    split = {
        "source_sha256": module.sha256_file(dataset),
        "confirmatory_sha256": module.sha256_file(confirmatory),
        "dev_task_ids": [ids[0]],
        "confirmatory_task_ids": confirm_ids,
    }
    split_path = tmp_path / "split.json"
    split_path.write_text(json.dumps(split), encoding="utf-8")
    heldout_path = tmp_path / "heldout.json"
    heldout_path.write_text(json.dumps({"assigned_task_ids": [ids[1]]}), encoding="utf-8")
    return SimpleNamespace(dataset=dataset, confirmatory=confirmatory, split=split_path, heldout=heldout_path)


def test_selection_is_next_80_in_frozen_order_and_disjoint():
    split = {"confirmatory_task_ids": ["BigCodeBench/9", "BigCodeBench/8", "BigCodeBench/10", "BigCodeBench/11"], "dev_task_ids": ["BigCodeBench/9"]}
    heldout = {"assigned_task_ids": ["BigCodeBench/8"]}
    selected, candidates = module.choose_ids(split, heldout, count=2)
    assert selected == ["BigCodeBench/10", "BigCodeBench/11"]
    assert selected == candidates[:2]
    assert len(selected) == 2 and len(set(selected)) == 2
    assert not set(selected) & set(heldout["assigned_task_ids"])
    assert not set(selected) & set(split["dev_task_ids"])
    assert not any(task_id.rsplit("/", 1)[-1] in module.EXPOSED_NUMBERS for task_id in selected)


def test_prompt_factors_and_model_schema_are_explicit():
    task = synthetic_task("BigCodeBench/101")
    raw = json.dumps(task).encode("utf-8")
    built = {arm: module.build_model_row(task, arm, module.sha256_bytes(raw)) for arm in module.ARM_NAMES}
    assert {row["context"] for row in built.values()} == {task["code_prompt"]}
    assert "planner" in built["role_boundary"]["prompt"].lower()
    assert "stage 1" in built["neutral_boundary"]["prompt"].lower()
    assert "[PLANNER]" in built["role_boundary"]["prompt"]
    assert "[PLANNER]" not in built["role_prose"]["prompt"]
    assert "[STAGE 1]" in built["neutral_boundary"]["prompt"]
    assert "[STAGE 1]" not in built["neutral_prose"]["prompt"]
    for operation in module.OPERATIONS:
        assert all(operation in row["prompt"] for row in built.values())
    assert module.COMMON_LEAD in module.TEMPLATES["role_boundary"]
    assert module.COMMON_TAIL in module.TEMPLATES["neutral_prose"]
    for row in built.values():
        assert not set(row) & set(module.FORBIDDEN_MODEL_FIELDS)
        assert set(row) == {"task_id", "prompt", "context", "benchmark", "metadata"}
        assert row["metadata"]["source_row_sha256"] == module.sha256_bytes(raw)


def test_evaluator_artifacts_are_separate_from_model_inputs(tmp_path):
    frozen = synthetic_files(tmp_path)
    args = type("Args", (), {
        "dataset": frozen.dataset,
        "split_manifest": frozen.split,
        "confirmatory": frozen.confirmatory,
        "heldout_selection": frozen.heldout,
        "output_dir": tmp_path / "segregation80",
    })()
    selection = module.prepare(args)
    assert len(selection["assigned_task_ids"]) == 80
    model_path = args.output_dir / "input/role_boundary.jsonl"
    for line in model_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        assert "test" not in row and "canonical_solution" not in row
    evaluator = [json.loads(line) for line in (args.output_dir / "evaluator/evaluator_dataset.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(evaluator) == 80
    assert all("test" in row and "canonical_solution" in row for row in evaluator)
    manifest = json.loads((args.output_dir / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["no_generation"] is True
    assert manifest["model_rows_per_arm"] == 80
    assert manifest["base_prepared_sha256"] == selection["model_input_sha256"]
