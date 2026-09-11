"""Prepare a separate path-neutral primary-generation copy for offline replay.

This is not an AAMAS upload builder or an anonymity certification. It never runs
the CLI, native tests or statistical analysis. Original evidence is read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import stat
import sys

sys.dont_write_bytecode = True
from reproducibility import codex_luna_subscription as cli
from reproducibility.revision_20260911.verify_primary_metadata_copy import validate_terminal_inventory


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_inventory(root: Path) -> list[Path]:
    """Refuse links and reparse points before descending into a directory."""
    result = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Links/reparse points are outside the copy contract')
            if name in files:
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('Only regular evidence files are supported')
                result.append(path)
    return sorted(result)


class MetadataTransform:
    def __init__(self, runtime: dict, provenance: dict, sessions: list[str]):
        if len(runtime['prefix']) != 2 or runtime['version'] != cli.CLI_VERSION:
            raise ValueError('Expected the recorded two-element official CLI prefix')
        self.original_prefix = runtime['prefix']
        self.prefix = ['ANON_NODE', 'ANON_CODEX_ENTRY']
        self.sessions = {value: f'session-{index:02d}' for index, value in enumerate(sessions, 1)}
        self.paths = dict(zip(self.original_prefix, self.prefix))
        for key, replacement in [('native_executable_path', 'ANON_NATIVE_EXECUTABLE'),
                                 ('empty_working_directory', 'ANON_WORKDIR'),
                                 ('instructions_path', 'ANON_INSTRUCTIONS')]:
            if not isinstance(provenance.get(key), str):
                raise ValueError('Required recorded runtime path is absent')
            self.paths[provenance[key]] = replacement
        self.original_runtime_paths = tuple(self.paths)

    def command(self, argv: list) -> list:
        cd_index = argv.index('--cd') + 1
        matches = [i for i, item in enumerate(argv) if item.startswith('model_instructions_file=')]
        if len(matches) != 1:
            raise ValueError('Instructions configuration must occur exactly once')
        instruction_index = matches[0]
        instructions = json.loads(argv[instruction_index].split('=', 1)[1])
        if argv != cli.cli_command(self.original_prefix, Path(argv[cd_index]), Path(instructions)):
            raise ValueError('Original command differs from the frozen model/configuration')
        result = argv.copy()
        result[:2] = self.prefix
        result[cd_index] = 'ANON_WORKDIR'
        result[instruction_index] = 'model_instructions_file=' + json.dumps('ANON_INSTRUCTIONS')
        if result != cli.cli_command(self.prefix, Path('ANON_WORKDIR'), Path('ANON_INSTRUCTIONS')):
            raise ValueError('Derived command does not retain frozen configuration')
        return result

    def metadata(self, value, key=''):
        # Scientific strings and resource values are never searched or rewritten.
        if key in {'final_text', 'solution', 'prompt', 'text', 'usage', 'resource_usage'}:
            return value
        if isinstance(value, dict):
            return {name: self.metadata(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [self.metadata(item, key) for item in value]
        if not isinstance(value, str):
            return value
        if value in self.sessions:
            return self.sessions[value]
        if value in self.paths:
            return self.paths[value]
        if value.startswith('model_instructions_file='):
            original = json.loads(value.split('=', 1)[1])
            return 'model_instructions_file=' + json.dumps(self.metadata(original))
        path_field = key in {'prefix', 'cwd', 'working_directory', 'empty_working_directory', 'argv', 'command'} or key.endswith('_path')
        if path_field and (PureWindowsPath(value).is_absolute() or value.startswith('/')):
            replacement = f'ANON_PATH_{len(self.paths):03d}'
            self.paths[value] = replacement
            return replacement
        # Diagnostics may embed a recorded path rather than consist of one.
        for original, replacement in sorted(self.paths.items(), key=lambda item: -len(item[0])):
            value = value.replace(original, replacement)
            value = value.replace(json.dumps(original)[1:-1], replacement)
        return value

    def relative_path(self, relative: Path) -> Path:
        parts = list(relative.parts)
        if len(parts) > 1 and parts[0] == 'sessions':
            parts[1] = self.sessions[parts[1]]
        return Path(*parts)

    def events(self, raw: bytes, thread_label: str) -> bytes:
        lines = []
        for line in raw.splitlines(keepends=True):
            try:
                event = json.loads(line.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                lines.append(line)  # Preserve any malformed transport fragment.
                continue
            if isinstance(event, dict) and 'thread_id' in event:
                if not isinstance(event['thread_id'], str):
                    raise ValueError('Unexpected thread identifier type')
                event['thread_id'] = thread_label
                newline = b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
                lines.append(encoded(event).rstrip(b'\n') + newline)
            else:
                lines.append(line)
        return b''.join(lines)


def prepare(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Source and destination must not overlap')
    if output.exists():
        raise FileExistsError('Refusing to overwrite a derivative')
    status_bytes = (source / 'status.json').read_bytes()
    if json.loads(status_bytes)['state'] != 'generation_finished' or (source / 'DISPATCH.lock').exists():
        raise ValueError('A terminal generation without a dispatch lock is required')
    runtime = json.loads((source / 'runtime.json').read_bytes())
    provenance = json.loads((source / 'runtime_provenance.json').read_bytes())
    manifest = json.loads((source / 'manifest.json').read_bytes())
    if manifest.get('planned_candidates') != 15000 or manifest.get('planned_cli_turns') != 27000:
        raise ValueError('Expected the frozen full primary allocation')
    terminal_inventory = validate_terminal_inventory(source, manifest)
    recorded_builder = (source / 'sources/codex_luna_subscription.py').read_bytes().replace(b'\r\n', b'\n')
    if recorded_builder != Path(cli.__file__).read_bytes().replace(b'\r\n', b'\n') or digest(recorded_builder) != manifest['source_sha256_lf']['codex_luna_subscription.py']:
        raise ValueError('Command builder differs from recorded frozen source')
    sessions = sorted(p.name for p in (source / 'sessions').iterdir() if p.is_dir())
    transform = MetadataTransform(runtime, provenance, sessions)
    paths = file_inventory(source)
    output.mkdir(parents=True)
    incomplete = output / 'INCOMPLETE'
    incomplete.write_text('Not a verified copy. Do not publish.\n', encoding='utf-8')
    generation = output / 'generation'
    generation.mkdir()
    (generation / 'empty').mkdir()
    originals, derivative_paths, changed = {}, set(), Counter()
    source_inventory = hashlib.sha256()
    thread_labels = {p.name: f'thread-{index:05d}' for index, p in enumerate(sorted((source / 'turns').iterdir()), 1) if p.is_dir()}

    for index, path in enumerate(paths, 1):
        relative = path.relative_to(source)
        destination_relative = transform.relative_path(relative)
        if destination_relative.as_posix() in derivative_paths:
            raise ValueError('Transformation creates a path collision')
        derivative_paths.add(destination_relative.as_posix())
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Source changed during copy')
        originals[relative.as_posix()] = (len(raw), digest(raw), after.st_mtime_ns)
        source_inventory.update(encoded({'path': relative.as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}))
        data = raw
        if relative.parts[0] == 'turns' and path.name == 'argv.json':
            data = encoded(transform.command(json.loads(raw)))
        elif relative.parts[0] == 'turns' and path.name == 'events.jsonl':
            data = transform.events(raw, thread_labels[relative.parts[1]])
        elif relative.parts[0] == 'sessions' and path.name == 'command.json':
            data = encoded(transform.command(json.loads(raw)))
        elif relative.parts[0] in {'cells', 'failures', 'sessions'} or relative.as_posix() in {'runtime.json', 'runtime_provenance.json', 'status.json'}:
            data = encoded(transform.metadata(json.loads(raw)))
        elif relative.as_posix() == 'results.jsonl':
            data = b''.join(encoded(transform.metadata(json.loads(line))) for line in raw.splitlines() if line.strip())
        destination = generation / destination_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if data != raw:
            category = relative.parts[0] + '/*.json' if relative.parts[0] in {'cells', 'failures'} else path.name
            changed[category] += 1
        if index % 50000 == 0:
            print(json.dumps({'stage': 'copy', 'files': index}), flush=True)

    # Rebuild the precise references changed by argv and event metadata; never
    # change accepted response/usage fields or create a result for a failed turn.
    rebuilt = 0
    for folder in sorted((generation / 'turns').iterdir()):
        for name in ('result.json', 'empty_response_classification.json'):
            path = folder / name
            if not path.is_file():
                continue
            before = path.read_bytes()
            record = json.loads(before)
            if set(record['files_sha256']) != {'prompt.txt', 'argv.json', 'events.jsonl', 'stderr.txt'}:
                raise ValueError('Unexpected per-turn hash contract')
            record['files_sha256'] = {item: digest((folder / item).read_bytes()) for item in record['files_sha256']}
            after = encoded(record)
            path.write_bytes(after)
            if before != after:
                changed[name] += 1
            rebuilt += 1

    source_after = hashlib.sha256()
    residual = []
    private_patterns = {pattern for token in transform.paths for pattern in
                        (token.encode(), json.dumps(token)[1:-1].encode(),
                         json.dumps(token, ensure_ascii=False)[1:-1].encode())}
    if [p.relative_to(source).as_posix() for p in file_inventory(source)] != list(originals):
        raise ValueError('Source inventory changed during preparation')
    for relative, (size, content_hash, mtime) in originals.items():
        path = source / relative
        raw = path.read_bytes()
        if (len(raw), digest(raw), path.stat().st_mtime_ns) != (size, content_hash, mtime):
            raise ValueError('Original evidence changed during preparation')
        source_after.update(encoded({'path': relative, 'bytes': size, 'sha256': content_hash}))
        derived = generation / transform.relative_path(Path(relative))
        data = derived.read_bytes()
        if any(pattern in data for pattern in private_patterns):
            residual.append(derived.relative_to(generation).as_posix())
    if source_inventory.digest() != source_after.digest() or (source / 'status.json').read_bytes() != status_bytes or (source / 'DISPATCH.lock').exists():
        raise ValueError('Original generation changed or resumed')

    files = [{'path': p.relative_to(generation).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())} for p in file_inventory(generation)]
    if len(files) != len(paths):
        raise ValueError('The copy omitted or introduced evidence files')
    (output / 'DERIVATIVE_MANIFEST.json').write_bytes(encoded({'scope': 'generation copy only', 'files': files}))
    result = {
        'schema': 'primary-metadata-copy-v2', 'original_files': len(paths), 'copied_files': len(files),
        'original_inventory_sha256': source_inventory.hexdigest(),
        'derivative_manifest_sha256': digest((output / 'DERIVATIVE_MANIFEST.json').read_bytes()),
        'changed_metadata_by_filename': dict(changed), 'rebuilt_per_turn_hash_records': rebuilt,
        'sessions_relabelled': len(sessions), 'thread_labels_available': len(thread_labels),
        'source_files_unchanged': True, 'terminal_inventory': terminal_inventory,
        'residual_discovered_metadata_paths': residual,
        'scientific_replay_completed': False, 'replay_validation_required': True, 'not_a_submission_artifact': True,
        'limits': ['Generation copy only. SCC, native outputs, source-group and pricing sidecars are outside this transform.',
                   'No whole-package anonymity certification. The residual scan covers runtime and discovered metadata paths only.',
                   'Prompts, responses and resources require full frozen-code reconstruction before this copy is accepted.',
                   'New hashes identify the derivative; they do not replace original evidence identity.']}
    (output / 'PREPARATION_REPORT.json').write_bytes(encoded(result))
    incomplete.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output)), flush=True)


if __name__ == '__main__':
    main()
