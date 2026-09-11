import json
import subprocess
import sys

import pytest

from reproducibility.revision_20260911 import publish_scale
from reproducibility.revision_20260911.publish_scale import publish


def test_publisher_refuses_active_generation_before_copying(tmp_path):
    root = tmp_path / "run"
    (root / "generation").mkdir(parents=True)
    (root / "generation" / "status.json").write_text(json.dumps({"state": "running"}))
    output = tmp_path / "published"
    with pytest.raises(ValueError, match="not generation_finished"):
        publish(root, output, tmp_path / "inputs", tmp_path / "gate", tmp_path / "manifest.json")
    assert not output.exists()


def test_publisher_never_overwrites_existing_output(tmp_path):
    root = tmp_path / "run"
    output = tmp_path / "published"
    output.mkdir()
    (output / "sentinel.txt").write_text("keep")
    with pytest.raises(ValueError, match="refuse to overwrite"):
        publish(root, output, tmp_path / "inputs", tmp_path / "gate", tmp_path / "manifest.json")
    assert (output / "sentinel.txt").read_text() == "keep"


def test_publisher_stages_complete_archive_and_offline_byte_check(tmp_path, monkeypatch):
    root = tmp_path / "run"
    generation = root / "generation"
    for name in ("cells", "failures", "sessions", "sources", "empty", "turns"):
        (generation / name).mkdir(parents=True)
    for name in ("manifest.json", "tasks.json", "instructions.txt", "results.jsonl", "status.json", "runtime.json", "runtime_provenance.json"):
        (generation / name).write_text("{}\n")
    (root / "pipeline").mkdir()
    (root / "predictions").mkdir()
    (root / "native").mkdir()
    (root / "analysis").mkdir()
    for name in ("candidate_records.jsonl", "turn_usage.json", "native_audit.json", "summary.json"):
        (root / "analysis" / name).write_text("[]\n")
    inputs = tmp_path / "inputs"
    gate = tmp_path / "gate"
    inputs.mkdir(); gate.mkdir()
    (inputs / "selection.json").write_text("{}\n")
    (gate / "heldout200_control_gate.json").write_text("{}\n")
    frozen = tmp_path / "manifest.json"
    frozen.write_text("{}\n")
    monkeypatch.setattr(publish_scale, "validate_terminal_generation", lambda *a: {})
    monkeypatch.setattr(publish_scale, "validate_hash_bindings", lambda *a: {"runtime_sha256": "fixture"})
    monkeypatch.setattr(publish_scale, "validate_finish", lambda *a: {"records": 15000})
    monkeypatch.setattr(publish_scale, "validate_full_replay", lambda *a: None)
    # This packaging fixture must not depend on a local, ignored benchmark checkout.
    vendor = tmp_path / "vendor-fixture"
    vendor.mkdir()
    (vendor / "fixture.py").write_bytes(b"# retained source bytes\n")
    copy_tree = publish_scale.copy_tree
    benchmark = publish_scale.REPO_ROOT / "reproducibility/vendor/bigcodebench"
    monkeypatch.setattr(publish_scale, "copy_tree",
                        lambda source, target: copy_tree(vendor if source == benchmark else source, target))
    output = tmp_path / "published"
    publish(root, output, inputs, gate, frozen)
    assert (output / "analysis" / "candidate_records.jsonl").is_file()
    assert (output / "pipeline").is_dir()
    assert (output / "sources/bigcodebench/fixture.py").read_bytes() == b"# retained source bytes\n"
    assert (output / "verify_bytes.py").is_file()
    subprocess.run([sys.executable, str(output / "verify_bytes.py")], check=True, capture_output=True, text=True)
    assert (output / "EVIDENCE_MANIFEST.json").is_file()


def test_offline_replay_recomputes_primary_means(tmp_path):
    records = []
    arms = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
    for task_no in range(1000):
        task = f"BigCodeBench/{task_no}"
        for arm in arms:
            for repeat in (101, 102, 103):
                records.append({"task_id": task, "arm": arm, "replicate_id": repeat, "quality": False, "generation_complete": True})
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "candidate_records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))
    contrasts = {
        name: {"eligible_tasks": 1000, "mean_difference": 0.0}
        for name in ("single_roles_minus_single_neutral", "multi_roles_minus_multi_neutral", "multi_neutral_minus_single_neutral", "multi_roles_minus_single_roles")
    }
    (analysis / "summary.json").write_text(json.dumps({"contrasts": contrasts}))
    verifier = tmp_path / "replay_verify.py"
    publish_scale.write_replay_verifier(verifier)
    subprocess.run([sys.executable, str(verifier)], check=True, capture_output=True, text=True)


def test_publication_rejects_native_reconstruction_mismatch(tmp_path, monkeypatch):
    from reproducibility.scale1000_luna import collect

    root = tmp_path / "run"
    (root / "analysis").mkdir(parents=True)
    (root / "analysis/candidate_records.jsonl").write_text('{"quality":true}\n')

    def changed_native_replay(*args):
        out = args[-1]
        out.mkdir()
        (out / "candidate_records.jsonl").write_text('{"quality":false}\n')

    monkeypatch.setattr(collect, "collect", changed_native_replay)
    with pytest.raises(ValueError, match="raw/native reconstruction differs"):
        publish_scale.validate_full_replay(root, tmp_path, tmp_path, tmp_path)


def test_publication_rejects_changed_statistical_summary(tmp_path, monkeypatch):
    from reproducibility.scale1000_luna import collect
    from reproducibility.scale1000 import analyze

    root = tmp_path / "run"
    (root / "analysis").mkdir(parents=True)
    payloads = {"candidate_records.jsonl": "{}\n", "turn_usage.json": "[]\n", "native_audit.json": "{}\n"}
    for name, data in payloads.items():
        (root / "analysis" / name).write_text(data)
    (root / "analysis/summary.json").write_text('{"holm_p":0.001}')
    (tmp_path / "selection.json").write_text('{}')

    def identical_native_replay(*args):
        out = args[-1]
        out.mkdir()
        for name, data in payloads.items():
            (out / name).write_text(data)

    monkeypatch.setattr(collect, "collect", identical_native_replay)
    monkeypatch.setattr(analyze, "summarize", lambda *args: {"holm_p": 1.0})
    with pytest.raises(ValueError, match="full statistical replay differs"):
        publish_scale.validate_full_replay(root, tmp_path, tmp_path, tmp_path)
