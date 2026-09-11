"""Verify a primary metadata copy by complete offline raw reconstruction.

Uses retained frozen source in a new interpreter outside the checkout. It reads
the already completed reference controls, but never reads candidate native
outcomes, calls a model, executes generated code or calculates effect statistics.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

sys.dont_write_bytecode = True


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    """Walk regular evidence files without following links or reparse points."""
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Links/reparse points are outside the replay contract')
            if name in names:
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('Only regular evidence files are supported')
                files.append(path)
    return sorted(files)


def validate_terminal_inventory(archive, manifest):
    """Check allocation membership and the dispatcher's terminal count contract.

    This does not validate prompt/response semantics; frozen reconstruction is
    still required. An interrupted assignment need not have a failure JSON.
    """
    cells = manifest['inner_manifest']['cells']
    assigned = {cell['id']: cell for cell in cells}
    if len(assigned) != len(cells) or len(cells) != manifest['planned_candidates']:
        raise ValueError('Duplicate or inconsistent planned assignment inventory')
    if sum(cell['cli_turns'] for cell in cells) != manifest['planned_cli_turns']:
        raise ValueError('Inconsistent planned turn count')
    status = json.loads((archive / 'status.json').read_bytes())
    if status['state'] != 'generation_finished' or (archive / 'DISPATCH.lock').exists():
        raise ValueError('A terminal generation without a dispatch lock is required')
    sessions = {p.name for p in (archive / 'sessions').iterdir() if p.is_dir()}
    if status.get('session') not in sessions:
        raise ValueError('Terminal session is not retained')
    completion = archive / 'sessions' / status['session'] / 'completion.json'
    if json.loads(completion.read_bytes()) != status:
        raise ValueError('Terminal session and generation status differ')
    saved, failures = {}, {}
    for directory, target, complete in [('cells', saved, True), ('failures', failures, False)]:
        for path in sorted((archive / directory).iterdir()):
            if not path.is_file() or path.suffix != '.json' or path.stem not in assigned:
                raise ValueError('Candidate/failure outside the frozen allocation')
            row = json.loads(path.read_bytes())
            if any(row.get(k) != v for k, v in assigned[path.stem].items()):
                raise ValueError('Candidate/failure identity differs from its assignment')
            if row.get('generation_complete') is not complete or row.get('session') not in sessions:
                raise ValueError('Candidate/failure terminal state or session is inconsistent')
            target[path.stem] = row
    if saved.keys() & failures.keys():
        raise ValueError('An assignment has both completion and failure records')
    expected_turns = {f"{cell['id']}-{stage}": (cell, stage) for cell in cells for stage in range(cell['cli_turns'])}
    touched = set(saved)
    submitted = set()
    for folder in (archive / 'turns').iterdir():
        if not folder.is_dir() or folder.name not in expected_turns:
            raise ValueError('Unexpected turn outside frozen allocation')
        cell, stage = expected_turns[folder.name]
        touched.add(cell['id'])
        submitted.add(folder.name)
        for previous in range(stage):
            prior = archive / 'turns' / f"{cell['id']}-{previous}"
            if not (prior / 'result.json').is_file() and not (prior / 'empty_response_classification.json').is_file():
                raise ValueError('Later turn follows absent or unaccepted prior stage')
    for cell_id in saved:
        for stage in range(assigned[cell_id]['cli_turns']):
            folder = archive / 'turns' / f'{cell_id}-{stage}'
            if not (folder / 'result.json').is_file() and not (folder / 'empty_response_classification.json').is_file():
                raise ValueError('Completed candidate is missing an accepted turn')
    counts = {'completed_candidates': len(saved),
              'submitted_incomplete_candidates': len(touched) - len(saved),
              'untouched_candidates': len(cells) - len(touched)}
    if any(type(status.get(k)) is not int or status[k] != v for k, v in counts.items()):
        raise ValueError('Terminal counts differ from the retained assignment inventory')
    if counts['untouched_candidates']:
        raise ValueError('Terminal generation still contains untouched assignments')
    retained_rows = [json.loads(line) for line in (archive / 'results.jsonl').read_bytes().splitlines() if line.strip()]
    if retained_rows != [saved[key] for key in sorted(saved)]:
        raise ValueError('Saved result index differs from completed candidate files')
    return {**counts, 'assigned_candidates': len(cells), 'submitted_turns': len(submitted),
            'retained_failure_records': len(failures)}


def worker(args):
    sys.path.insert(0, str(args.source_code))
    names = ['reproducibility.codex_luna_subscription', 'reproducibility.scale1000_luna.collect',
             'reproducibility.scale1000_luna.dispatch', 'reproducibility.heldout200.evidence',
             'reproducibility.scale_env.validate_native']
    modules = {name: importlib.import_module(name) for name in names}
    if any(not Path(module.__file__).resolve().is_relative_to(args.source_code.resolve()) for module in modules.values()):
        raise ValueError('Imported implementation outside retained frozen source')
    generation = args.copy / 'generation'
    manifest = json.loads((args.original / 'manifest.json').read_bytes())
    original_counts = validate_terminal_inventory(args.original, manifest)
    copied_counts = validate_terminal_inventory(generation, manifest)
    if original_counts != copied_counts:
        raise ValueError('Terminal inventories changed in the derivative')
    preparation = json.loads((args.copy / 'PREPARATION_REPORT.json').read_bytes())
    derivative_path = args.copy / 'DERIVATIVE_MANIFEST.json'
    if sha(derivative_path.read_bytes()) != preparation['derivative_manifest_sha256']:
        raise ValueError('Derivative manifest changed since preparation')
    expected = json.loads(derivative_path.read_bytes())['files']
    actual = [{'path': p.relative_to(generation).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
              for p in inventory(generation)]
    if expected != actual:
        raise ValueError('Missing, additional or altered derivative file')
    original_inventory = hashlib.sha256()
    for path in inventory(args.original):
        raw = path.read_bytes()
        original_inventory.update(encoded({'path': path.relative_to(args.original).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}))
    if original_inventory.hexdigest() != preparation['original_inventory_sha256']:
        raise ValueError('Original evidence differs from the prepared snapshot')
    collector = modules['reproducibility.scale1000_luna.collect']
    print(json.dumps({'stage': 'reconstruct_original'}), flush=True)
    original_rows, original_usage = collector.reconstruct(args.original, args.inputs, args.gate, args.original / 'manifest.json')
    print(json.dumps({'stage': 'reconstruct_metadata_copy'}), flush=True)
    copied_rows, copied_usage = collector.reconstruct(generation, args.inputs, args.gate, generation / 'manifest.json')
    if original_rows != copied_rows or original_usage != copied_usage:
        raise ValueError('Scientific raw reconstruction changed after metadata transformation')
    if len(original_rows) != 15000 or len({row['id'] for row in original_rows}) != 15000:
        raise ValueError('Not the full unique primary allocation')
    if any(row['quality'] is not None for row in original_rows):
        raise ValueError('Unexpected native-quality values in raw-only reconstruction')
    # The collector does not use transport-failure diagnostic JSONs. Check those
    # separately. Only the session identifier may differ in this accepted copy;
    # a changed diagnostic requires a documented follow-up, not silent approval.
    for path in sorted((args.original / 'failures').glob('*.json')):
        before = json.loads(path.read_bytes())
        after = json.loads((generation / 'failures' / path.name).read_bytes())
        before.pop('session', None)
        after.pop('session', None)
        if before != after:
            raise ValueError('Failure details changed beyond their session identifier')
    result = {
        'schema': 'primary-metadata-raw-replay-v1',
        'complete_raw_reconstruction_matches': True, 'assigned_rows': len(original_rows),
        'completed_candidates': sum(row['generation_complete'] for row in original_rows),
        'submitted_turn_usage_rows': len(original_usage),
        'raw_candidate_records_sha256': sha(encoded(original_rows)),
        'raw_turn_usage_sha256': sha(encoded(original_usage)),
        'derivative_files_verified': len(actual), 'original_snapshot_verified': True,
        'terminal_inventory': original_counts, 'failure_details_verified': True,
        'replay_worker_sha256': sha(Path(__file__).read_bytes()),
        'frozen_source_loaded_outside_checkout': True,
        'candidate_native_outcomes_inspected': False,
        'model_or_generated_code_executed': False, 'statistical_analysis_performed': False,
        'not_a_submission_artifact': True,
        'limits': ['Complete generation reconstruction only, not candidate native evaluation or the full scientific analysis.',
                   'Inputs and pre-generation reference controls are read from their original retained locations.',
                   'SCC, native metadata, pricing/source-family sidecars and whole-package anonymity remain unverified.']}
    (args.output / 'RAW_RECONSTRUCTION_REPORT.json').write_bytes(encoded(result))
    print(json.dumps(result), flush=True)


def verify(original: Path, copy: Path, inputs: Path, gate: Path, output: Path, protocol: Path):
    original, copy, inputs, gate, output, protocol = [p.resolve() for p in (original, copy, inputs, gate, output, protocol)]
    for protected in (original, copy, inputs, gate):
        if output == protected or protected in output.parents or output in protected.parents:
            raise ValueError('Replay output must not overlap retained inputs or derivative')
    if output.exists():
        raise FileExistsError('Refusing to overwrite replay evidence')
    if (copy / 'INCOMPLETE').exists():
        raise ValueError('Metadata copy has not finished')
    manifest = json.loads((original / 'manifest.json').read_bytes())
    source_code = output / 'replay-sources'
    output.mkdir(parents=True)
    for relative, expected in manifest['source_sha256_lf'].items():
        source = original / 'sources' / relative
        if not source.resolve().is_relative_to((original / 'sources').resolve()):
            raise ValueError('Frozen source path escapes its archive')
        raw = source.read_bytes()
        if sha(raw.replace(b'\r\n', b'\n')) != expected:
            raise ValueError('Recorded frozen source differs: ' + relative)
        destination = source_code / 'reproducibility' / relative
        if not destination.resolve().is_relative_to(source_code.resolve()):
            raise ValueError('Frozen source path escapes replay output')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    raw = protocol.read_bytes()
    if sha(raw.replace(b'\r\n', b'\n')) != manifest['protocol_sha256_lf']:
        raise ValueError('Primary protocol differs from frozen manifest')
    (source_code / 'reproducibility/scale1000_luna/PROTOCOL.md').write_bytes(raw)
    runner = output / 'raw_reconstruction_worker.py'
    shutil.copyfile(Path(__file__).resolve(), runner)
    directory = output / 'separate-cwd'
    directory.mkdir()
    command = [sys.executable, '-X', 'utf8', str(runner), '--worker', '--original', str(original),
               '--copy', str(copy), '--inputs', str(inputs), '--gate', str(gate),
               '--output', str(output), '--source-code', str(source_code)]
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    with (output / 'stdout.log').open('w', encoding='utf-8') as stdout, (output / 'stderr.log').open('w', encoding='utf-8') as stderr:
        completed = subprocess.run(command, cwd=directory, env=environment, stdout=stdout, stderr=stderr)
    (output / 'exit.json').write_bytes(encoded({'returncode': completed.returncode}))
    if completed.returncode:
        raise ValueError('Raw reconstruction failed; retained replay stderr contains the diagnostic')
    result = json.loads((output / 'RAW_RECONSTRUCTION_REPORT.json').read_bytes())
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'copy', 'inputs', 'gate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--source-code', type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args)
    else:
        if args.protocol is None:
            parser.error('--protocol is required')
        verify(args.original, args.copy, args.inputs, args.gate, args.output, args.protocol)


if __name__ == '__main__':
    main()
