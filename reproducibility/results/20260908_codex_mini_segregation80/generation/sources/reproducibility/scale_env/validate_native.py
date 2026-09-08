"""Reusable validation for native BigCodeBench CLI report folders."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _expected_tail(task_ids: list[str]) -> list[str]:
    return [
        "bigcodebench.evaluate", "instruct", "full", "--samples", "/run/input/samples.jsonl",
        "--execution", "local", "--selective_evaluate", ",".join(task_ids),
        "--calibrated", "False", "--parallel", "2", "--no_gt", "True",
        "--save_pass_rate", "False", "--min_time_limit", "0.1", "--max_as_limit", "30720",
        "--max_data_limit", "30720", "--max_stack_limit", "10",
    ]


def environment_from_gate(folder: Path) -> dict[str, Any]:
    """Resolve environment values through the pre-generation gate's exact file hashes."""
    gate = json.loads((folder / 'dev40_control_gate.json').read_text(encoding='utf-8'))
    environments = []
    for kind in ('gold', 'incorrect'):
        root = folder / kind
        for suffix, relative in (('metadata', 'run-metadata.json'), ('report', 'input/samples_eval_results.json'), ('samples', 'input/samples.jsonl')):
            if sha256(root / relative) != gate[f'{kind}_{suffix}_sha256']:
                raise ValueError('Control evidence changed after gate: ' + kind + '/' + relative)
        meta = json.loads((root / 'run-metadata.json').read_text(encoding='utf-8'))
        fields = ('image_id', 'base_image_id', 'upstream_commit_verified', 'network', 'cli_split',
                  'package_freeze_sha256', 'nltk_resources_sha256')
        environments.append({**{k: meta[k] for k in fields}, **meta['provenance']})
    if environments[0] != environments[1]:
        raise ValueError('Gold and negative environments differ')
    if environments[0]['image_id'] != gate['image_id'] or environments[0]['vendor_tree_sha256'] != gate['source_tree_sha256']:
        raise ValueError('Gate environment differs from its referenced control files')
    return environments[0]


def validate_native(
    folder: Path,
    expected_task_solution: dict[str, str],
    expected_control_environment: dict[str, Any],
) -> dict[str, Any]:
    """Validate one native report; missing reports remain explicit missing data."""
    metadata_path = folder / "run-metadata.json"
    report_path = folder / "input" / "samples_eval_results.json"
    errors: list[str] = []
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    ids = list(expected_task_solution)
    for key in ("image_id", "base_image_id", "upstream_commit_verified", "network", "cli_split"):
        expected_key = "upstream_commit" if key == "upstream_commit_verified" else key
        if metadata.get(key) != expected_control_environment.get(expected_key, expected_control_environment.get(key)):
            errors.append(f"environment mismatch: {key}")
    for key in ("vendor_tree_sha256", "dataset_sha256", "prepared_split_sha256", "requirements_sha256", "dockerfile_sha256"):
        if metadata.get("provenance", {}).get(key) != expected_control_environment.get(key):
            errors.append(f"provenance mismatch: {key}")
    for key in ("package_freeze_sha256", "nltk_resources_sha256"):
        if metadata.get(key) != expected_control_environment.get(key):
            errors.append(f"runtime hash mismatch: {key}")
    staged = folder / "input" / "samples.jsonl"
    if not staged.exists() or metadata.get("samples_source_sha256") != sha256(staged):
        errors.append("sample source hash mismatch")
    if metadata.get("staged_samples_sha256") != metadata.get("post_evaluator_staged_samples_sha256") or metadata.get("staged_samples_sha256") != metadata.get("samples_source_sha256"):
        errors.append("pre/post staged sample hash mismatch")
    if staged.exists():
        samples = [json.loads(line) for line in staged.read_text(encoding='utf-8').splitlines() if line.strip()]
        if len(samples) != len(ids) or {r.get('task_id'): r.get('solution') for r in samples} != expected_task_solution:
            errors.append("staged input differs from exact expected solutions")
    freeze = folder / "pip-freeze.txt"
    resources = folder / "nltk-resources-sha256.txt"
    if not freeze.exists() or metadata.get("package_freeze_sha256") != sha256(freeze):
        errors.append("pip-freeze hash mismatch")
    if not resources.exists() or metadata.get("nltk_resources_sha256") != sha256(resources):
        errors.append("NLTK resource hash mismatch")
    argv = metadata.get("argv", [])
    for key, value in {'--network': 'none', '--cap-drop': 'ALL', '--user': '65532:65532',
                       '--security-opt': 'no-new-privileges', '--memory': '3g', '--pids-limit': '256', '--cpus': '2'}.items():
        if key not in argv or argv[argv.index(key) + 1] != value:
            errors.append('container option mismatch: ' + key)
    if '--read-only' not in argv or not any('target=/run/input/samples.jsonl,readonly' in v for v in argv):
        errors.append('read-only isolation mismatch')
    if metadata.get('image_id') not in argv:
        errors.append('recorded image was not invoked')
    try:
        module = argv.index("-m")
        if argv[module + 1:] != _expected_tail(ids):
            errors.append("CLI argv mismatch")
    except ValueError:
        errors.append("CLI module invocation missing")

    statuses: dict[str, str | None] = {task_id: None for task_id in ids}
    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        actual = data.get("eval", {})
        if set(actual) != set(ids):
            errors.append("report task set mismatch")
        for task_id in ids:
            rows = actual.get(task_id, [])
            if len(rows) != 1:
                errors.append(f"missing or duplicate report row: {task_id}")
                continue
            row = rows[0]
            if row.get("task_id") != task_id or row.get("solution") != expected_task_solution[task_id]:
                errors.append(f"evaluated solution mismatch: {task_id}")
            status = row.get("status")
            if status not in ('pass', 'fail', 'timeout'):
                errors.append(f'unknown test status: {task_id}')
            else:
                statuses[task_id] = status
    else:
        errors.append("report missing; all task statuses remain missing")
    return {"ok": not errors, "errors": errors, "statuses": statuses,
            "report_sha256": sha256(report_path) if report_path.exists() else None}
