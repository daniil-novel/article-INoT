"""Artificial quality ledgers test packaging; no generated study outcomes are read."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from reproducibility.task_dependence import audit, package, sensitivity


@pytest.mark.parametrize("study", ["factorial", "scc"])
def test_all_source_groups_and_draws_replay_outside_checkout(tmp_path, study):
    inputs = audit.ROOT / "reproducibility/scale1000/inputs-v1"
    gate = audit.ROOT / "reproducibility/results/20260908_scale1000_preflight/controls-v3"
    source = audit.ROOT / "reproducibility/task_dependence/source-audit-v2"
    assigned = json.loads((inputs / "selection.json").read_text())["assigned_task_ids"]
    eligible = set(json.loads((gate / "heldout200_control_gate.json").read_text())["evaluable_task_ids"])
    root = tmp_path / "artificial-fixture"
    (root / "generation").mkdir(parents=True)
    (root / "analysis").mkdir()
    (root / "generation/status.json").write_bytes(audit.encoded({"state": "generation_finished", "synthetic_fixture": True}))
    (root / "analysis/summary.json").write_bytes(audit.encoded({"synthetic_fixture": True}))
    methods = sorted({m for pair in sensitivity.CONTRASTS[study] for m in pair})
    if study == "factorial": methods.append("direct")
    rows = []
    for number, task in enumerate(assigned):
        for index, method in enumerate(methods):
            for repeat in sensitivity.REPEATS:
                rows.append({"task_id": task, "arm" if study == "factorial" else "method": method,
                    "replicate_id": repeat, "quality": (number + index + repeat) % 3 == 0 if task in eligible else None})
    records = "analysis/candidate_records.jsonl" if study == "factorial" else "candidate_records.jsonl"
    (root / records).write_bytes(b"".join(audit.encoded(row) for row in rows))
    saved = root / "source-family-sensitivity"
    sensitivity.run(root, study, source, saved, selection_path=inputs / "selection.json",
        gate_path=gate / "heldout200_control_gate.json")
    archive = tmp_path / "downloaded-evidence"; archive.mkdir()
    shutil.copytree(root / "generation", archive / "generation")
    shutil.copytree(root / "analysis", archive / "analysis")
    if study == "scc": shutil.copyfile(root / records, archive / records)
    archive_inputs, archive_gate = [archive / part for part in package.LAYOUT[study]]
    (archive_inputs / "input").mkdir(parents=True)
    archive_gate.mkdir(parents=True)
    shutil.copyfile(inputs / "selection.json", archive_inputs / "selection.json")
    shutil.copyfile(inputs / "input/prepared.jsonl", archive_inputs / "input/prepared.jsonl")
    shutil.copyfile(gate / "heldout200_control_gate.json", archive_gate / "heldout200_control_gate.json")
    package.attach(root, archive, study, inputs, gate, audit.ROOT)
    outside = tmp_path / "unrelated-working-directory"; outside.mkdir()
    env = dict(os.environ); env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, str(archive / "source_family_replay.py")],
        cwd=outside, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    replay = json.loads(result.stdout)
    assert replay["ok"] and replay["rows"] == len(rows)
    assert replay["replayed_files"] == 1 + 4 * len(sensitivity.CONTRASTS[study])
    # A tampered retained draw is detected even without changing the point estimate.
    draw = next((archive / "source-family-sensitivity").glob("prompt_050--*.json"))
    original = draw.read_bytes(); draw.write_bytes(b"[]\n")
    with pytest.raises(ValueError, match="draw vectors differ"):
        sensitivity.verify_saved(archive, study, archive / "source-task-audit", archive / "source-family-sensitivity",
            selection_path=archive_inputs / "selection.json", gate_path=archive_gate / "heldout200_control_gate.json")
    draw.write_bytes(original)
    # The original assigned source graph is also replayed, not only inventoried.
    altered_source = archive / "supplementary-sources/reproducibility/task_dependence/PROTOCOL.md"
    altered_source.write_bytes(altered_source.read_bytes() + b"changed\n")
    with pytest.raises(ValueError, match="source or dependency"):
        package.verify_archive(archive)


def test_supplementary_publication_cannot_silently_omit_analysis(tmp_path):
    with pytest.raises(ValueError, match="required before publication"):
        package.attach(tmp_path, tmp_path / "archive", "scc", tmp_path, tmp_path, audit.ROOT)
    assert not (tmp_path / "archive").exists()
