import json
import shutil
from pathlib import Path

import pytest

from reproducibility import codex_luna_subscription as cli
from reproducibility.revision_20260911 import publish_scc


def _args(tmp_path):
    root = tmp_path / "run"; generation = root / "generation"; generation.mkdir(parents=True)
    cli.save(generation / "status.json", {"state": "paused"})
    inputs = tmp_path / "inputs"; inputs.mkdir()
    gate = tmp_path / "gate"; gate.mkdir()
    manifest = tmp_path / "manifest.json"; cli.save(manifest, {"methods": [], "replicate_ids": []})
    return root, inputs, gate, manifest


def test_publish_refuses_unfinished_generation_before_output(tmp_path):
    root, inputs, gate, manifest = _args(tmp_path); output = tmp_path / "published"
    with pytest.raises(ValueError, match="generation_finished"):
        publish_scc.publish(root, inputs, gate, manifest, output)
    assert not output.exists()


def test_publish_refuses_existing_output(tmp_path):
    root, inputs, gate, manifest = _args(tmp_path); output = tmp_path / "published"; output.mkdir()
    with pytest.raises(FileExistsError, match="overwrite"):
        publish_scc.publish(root, inputs, gate, manifest, output)


def test_publish_refuses_missing_ledger_after_terminal_generation(tmp_path):
    root, inputs, gate, manifest = _args(tmp_path)
    cli.save(root / "generation/status.json", {"state": "generation_finished"})
    with pytest.raises(ValueError, match="ledger"):
        publish_scc.publish(root, inputs, gate, manifest, tmp_path / "published")


def test_publish_rejects_tampered_candidate_ledger(tmp_path, monkeypatch):
    root = tmp_path / "run"; root.mkdir(); (root / "candidate_records.jsonl").write_text('{"id":"tampered"}\n', encoding="utf-8")
    monkeypatch.setattr(publish_scc.scc_finish, "_records", lambda *args: [{"id": "derived"}])
    with pytest.raises(ValueError, match="ledger differs"):
        publish_scc._validate_join(root, tmp_path / "predictions", {"audits": {}, "eligible": set()})


def test_copied_source_tree_reconstructs_actual_frozen_plan(tmp_path):
    from reproducibility.revision_20260911 import scc_controls
    repository = publish_scc.ROOT
    manifest = cli.read(repository / "reproducibility/revision_20260911/scc_manifest.json")
    files = list(manifest["source_files_sha256"]) + [
        "reproducibility/results/20260911_scc_comparison_dev9/summary.json"]
    for name in files:
        target = tmp_path / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / name, target)
    before = scc_controls.ROOT, scc_controls.REV
    with publish_scc._archive_source_context(tmp_path):
        actual = scc_controls.plan(repository / "reproducibility/scale1000/inputs-v1",
            repository / "reproducibility/results/20260908_scale1000_preflight/controls-v3")
        assert actual == manifest
    assert (scc_controls.ROOT, scc_controls.REV) == before


def test_separate_resource_ledger_cannot_be_changed(tmp_path, monkeypatch):
    derived = [{"id": "a", "task_id": "t", "method": "single_roles", "replicate_id": 101,
                "resource_usage": {"turns": 1}, "availability": "completed"}]
    (tmp_path / "candidate_records.jsonl").write_text(json.dumps(derived[0]) + "\n", encoding="utf-8")
    (tmp_path / "resource_usage.jsonl").write_text('{"invented":true}\n', encoding="utf-8")
    monkeypatch.setattr(publish_scc.scc_finish, "_records", lambda *args: derived)
    with pytest.raises(ValueError, match="resource ledger differs"):
        publish_scc._validate_join(tmp_path, tmp_path, {"audits": {}, "eligible": set()})


def test_archive_pricing_scope_is_recomputed_even_after_refreshing_hashes(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from reproducibility.evidence_manifest import write
    from reproducibility.revision_20260911 import pricing_scope
    from reproducibility.task_dependence import package
    # Other scientific gates have dedicated tests; this fixture exercises the
    # publication verifier's required pricing replay, not SCC quality evidence.
    archive = tmp_path / 'archive'; turn = archive / 'generation/assignments/fixture/turns/000'
    turn.mkdir(parents=True)
    cli.save(turn / 'events.jsonl', {'type': 'turn.completed', 'usage':
        {'input_tokens': 100, 'cached_input_tokens': 0, 'output_tokens': 10, 'cache_write_input_tokens': 0}})
    cli.save(archive / 'generation/manifest.json', {})
    (archive / 'analysis').mkdir(); cli.save(archive / 'analysis/summary.json', {})
    (archive / 'README.md').write_text('Software fixture only')
    (archive / 'provenance').mkdir()
    shutil.copyfile(pricing_scope.__file__, archive / 'provenance/pricing_scope.py')
    pricing_scope.write_sidecar(archive / 'generation', archive / 'pricing_scope.json')
    monkeypatch.setattr(publish_scc, '_archive_source_context', lambda *args: nullcontext())
    monkeypatch.setattr(publish_scc.scc_export, 'validate_export', lambda *args: None)
    monkeypatch.setattr(publish_scc, '_native_gate', lambda *args: {})
    monkeypatch.setattr(publish_scc, '_validate_join', lambda *args: None)
    monkeypatch.setattr(publish_scc, '_recompute', lambda *args: None)
    monkeypatch.setattr(package, 'verify_archive', lambda *args: None)
    write(archive)
    assert publish_scc.verify_archive(archive)['ok']
    sidecar = cli.read(archive / 'pricing_scope.json')
    sidecar['summary']['max_input_tokens'] = 99
    cli.save(archive / 'pricing_scope.json', sidecar); write(archive)
    with pytest.raises(ValueError, match='pricing-scope sidecar differs'):
        publish_scc.verify_archive(archive)
