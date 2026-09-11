"""Scientific-content and failure-preservation checks for a metadata derivative."""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from reproducibility import codex_luna_subscription as cli
from reproducibility.revision_20260911.prepare_primary_metadata_copy import MetadataTransform, prepare
from reproducibility.revision_20260911.verify_primary_metadata_copy import validate_terminal_inventory


@pytest.fixture
def transform():
    return MetadataTransform(
        {'prefix': ['node-original', 'entry-original'], 'version': cli.CLI_VERSION},
        {'native_executable_path': 'native-original', 'empty_working_directory': 'workspace-original',
         'instructions_path': 'instructions-original'}, ['old-session'])


def test_scientific_strings_and_counters_are_not_redacted(transform):
    scientific = {'final_text': 'Use workspace-original, old-session and C:\\data\\x.',
                  'solution': '/absolute/example', 'usage': {'input_tokens': 12, 'output_tokens': 9},
                  'session': 'old-session'}
    changed = transform.metadata(scientific)
    assert changed['session'] == 'session-01'
    for key in ('final_text', 'solution', 'usage'):
        assert changed[key] == scientific[key]


def test_diagnostic_keeps_failure_reason(transform):
    value = {'failure_reason': 'Failed to read workspace-original: permission denied.'}
    assert transform.metadata(value)['failure_reason'] == 'Failed to read ANON_WORKDIR: permission denied.'
    # A diagnostic beginning with an unknown absolute path is not wholly erased.
    value = {'failure_reason': 'C:\\unknown\\file: syntax error at line 3'}
    assert transform.metadata(value) == value


def test_event_transform_preserves_response_bytes_and_malformed_fragments(transform):
    response = b'{ "type": "item.completed", "item": {"type":"agent_message","text":"workspace-original old-session"}}\r\n'
    malformed = b'\xffnot-json\n'
    raw = b'{"type":"thread.started","thread_id":"private-id"}\n' + response + malformed
    result = transform.events(raw, 'thread-00001')
    assert result.endswith(response + malformed)
    assert json.loads(result.splitlines()[0])['thread_id'] == 'thread-00001'


def test_bom_fragment_is_not_silently_repaired(transform):
    raw = b'\xef\xbb\xbf{"type":"thread.started","thread_id":"private-id"}\n'
    assert transform.events(raw, 'thread-00001') == raw


def test_event_thread_change_preserves_unicode_scientific_values(transform):
    before = {'thread_id': 'private-id', 'text': 'Путь C:\\данные\\файл, workspace-original',
              'usage': {'input_tokens': 10}, 'nested': {'thread_id': 'scientific-example'}}
    raw = json.dumps(before, ensure_ascii=True).encode() + b'\r\n'
    after = json.loads(transform.events(raw, 'thread-00001'))
    assert after == {**before, 'thread_id': 'thread-00001'}


@pytest.fixture
def terminal_archive(tmp_path):
    root = tmp_path / 'archive'
    for directory in ('cells', 'failures', 'turns/a-0', 'turns/b-0', 'sessions/session-1'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    cells = [{'id': name, 'task_id': name, 'cli_turns': 1} for name in ('a', 'b')]
    manifest = {'inner_manifest': {'cells': cells}, 'planned_candidates': 2, 'planned_cli_turns': 2}
    row = {**cells[0], 'generation_complete': True, 'session': 'session-1', 'final_text': 'answer',
           'usage': {'input_tokens': 3, 'output_tokens': 2}}
    status = {'state': 'generation_finished', 'completed_candidates': 1,
              'submitted_incomplete_candidates': 1, 'untouched_candidates': 0, 'session': 'session-1'}
    for name, value in [('cells/a.json', row), ('turns/a-0/result.json', {'accepted': True}),
                        ('status.json', status), ('sessions/session-1/completion.json', status)]:
        (root / name).write_text(json.dumps(value), encoding='utf-8')
    (root / 'results.jsonl').write_text(json.dumps(row) + '\n', encoding='utf-8')
    return root, manifest


def test_terminal_inventory_preserves_interruption_without_failure_json(terminal_archive):
    root, manifest = terminal_archive
    assert validate_terminal_inventory(root, manifest) == {
        'completed_candidates': 1, 'submitted_incomplete_candidates': 1, 'untouched_candidates': 0,
        'assigned_candidates': 2, 'submitted_turns': 2, 'retained_failure_records': 0}


@pytest.mark.parametrize('damage', ['cell', 'accepted_turn', 'interrupted_turn', 'result_index', 'unknown_failure'])
def test_terminal_inventory_rejects_missing_or_contradictory_evidence(terminal_archive, damage):
    root, manifest = terminal_archive
    if damage == 'cell':
        (root / 'cells/a.json').unlink()
    elif damage == 'accepted_turn':
        (root / 'turns/a-0/result.json').unlink()
    elif damage == 'interrupted_turn':
        (root / 'turns/b-0').rmdir()
    elif damage == 'result_index':
        (root / 'results.jsonl').write_text('')
    else:
        (root / 'failures/unknown.json').write_text('{}')
    with pytest.raises(ValueError):
        validate_terminal_inventory(root, manifest)


def test_terminal_inventory_retains_failure_identity(terminal_archive):
    root, manifest = terminal_archive
    failure = {**manifest['inner_manifest']['cells'][1], 'generation_complete': False,
               'session': 'session-1', 'failure_reason': 'transport interrupted'}
    (root / 'failures/b.json').write_text(json.dumps(failure))
    assert validate_terminal_inventory(root, manifest)['retained_failure_records'] == 1
    failure['task_id'] = 'different-task'
    (root / 'failures/b.json').write_text(json.dumps(failure))
    with pytest.raises(ValueError, match='identity'):
        validate_terminal_inventory(root, manifest)


def test_neutral_command_is_cross_platform_and_keeps_scientific_configuration(transform):
    before = cli.cli_command(transform.original_prefix, Path('workspace-original'), Path('instructions-original'))
    after = transform.command(before)
    for cls in (PureWindowsPath, PurePosixPath):
        assert after == cli.cli_command(transform.prefix, cls('ANON_WORKDIR'), cls('ANON_INSTRUCTIONS'))
    assert before[before.index('--model') + 1] == after[after.index('--model') + 1]


@pytest.mark.parametrize('change', ['model', 'reasoning', 'tools', 'prefix'])
def test_transform_does_not_accept_unplanned_commands(transform, change):
    argv = cli.cli_command(transform.original_prefix, Path('workspace-original'), Path('instructions-original'))
    if change == 'model':
        argv[argv.index('--model') + 1] = 'other-model'
    elif change == 'reasoning':
        index = next(i for i, value in enumerate(argv) if value.startswith('model_reasoning_effort='))
        argv[index] = 'model_reasoning_effort="high"'
    elif change == 'tools':
        index = next(i for i, value in enumerate(argv) if value.startswith('features.shell_tool='))
        argv[index] = 'features.shell_tool=true'
    else:
        argv[0] = 'different-executable'
    with pytest.raises(ValueError, match='frozen model/configuration'):
        transform.command(argv)


def test_refuses_output_overlap_or_overwrite_before_writing(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    with pytest.raises(ValueError, match='overlap'):
        prepare(source, source / 'nested')
    with pytest.raises(ValueError, match='overlap'):
        prepare(source, tmp_path)
    existing = tmp_path / 'existing'
    existing.mkdir()
    sentinel = existing / 'keep.txt'
    sentinel.write_text('keep')
    with pytest.raises(FileExistsError):
        prepare(source, existing)
    assert sentinel.read_text() == 'keep'
