"""The offline continuation must not act on missing or failed native stages."""
import json
import os

import pytest

from reproducibility.revision_20260911 import finalize_primary_offline as finalizer


@pytest.fixture
def terminal_stage_tree(tmp_path):
    (tmp_path / 'generation').mkdir()
    (tmp_path / 'generation/status.json').write_text(json.dumps({'state': 'generation_finished'}))
    (tmp_path / 'pipeline').mkdir()
    for name in finalizer.STAGES:
        (tmp_path / 'pipeline' / (name + '.exit.json')).write_text(json.dumps({'returncode': 0}))
    return tmp_path


def test_full_stage_gate_preserves_all_fifteen_native_groups(terminal_stage_tree):
    exits = finalizer.complete_stage_gate(terminal_stage_tree)
    assert len(exits) == 18
    assert len([name for name in exits if name.startswith('native-')]) == 15


def test_missing_native_stage_blocks_the_continuation(terminal_stage_tree):
    (terminal_stage_tree / 'pipeline/native-direct-r103.exit.json').unlink()
    with pytest.raises(ValueError, match='Missing completed stage'):
        finalizer.complete_stage_gate(terminal_stage_tree)


@pytest.mark.parametrize('invalid_returncode', [1, None, False, '0'])
def test_failed_or_ambiguous_analysis_is_not_success(terminal_stage_tree, invalid_returncode):
    (terminal_stage_tree / 'pipeline/analyze.exit.json').write_text(json.dumps({'returncode': invalid_returncode}))
    with pytest.raises(ValueError, match='Unsuccessful completed stage'):
        finalizer.complete_stage_gate(terminal_stage_tree)


def test_dispatch_lock_blocks_even_with_terminal_status(terminal_stage_tree):
    (terminal_stage_tree / 'generation/DISPATCH.lock').write_text('retained-lock')
    with pytest.raises(ValueError, match='not terminal'):
        finalizer.complete_stage_gate(terminal_stage_tree)


def test_unrelated_process_is_not_accepted_as_the_finisher():
    with pytest.raises(ValueError, match='not the existing primary finisher'):
        finalizer.confirm_finisher(os.getpid())
