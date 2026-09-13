"""Reconcile partial programs without imputing primary SCC outcomes."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from .partial_runner import validate_setup
from reproducibility.scale_env.validate_native import validate_native


def report(setup_path: Path) -> dict:
    setup = json.loads(setup_path.read_text(encoding='utf-8'))
    validate_setup(setup)
    gate = json.loads(Path(setup['control_gate']).read_text(encoding='utf-8'))
    eligible = set(gate['evaluable_task_ids'])
    groups, records = [], []
    hashes = setup['candidate_source_hashes']
    for group in setup['groups']:
        rep = group['replicate_id']
        samples = [json.loads(line) for line in Path(group['samples']).read_text(encoding='utf-8').splitlines() if line.strip()]
        expected = {row['task_id']: row['solution'] for row in samples}
        folder = setup_path.parent / 'native' / f'replicate-{rep}'
        checked = validate_native(folder, expected, setup['control_environment'])
        counts: Counter = Counter()
        for task in expected:
            raw_status = checked['statuses'][task]
            # Rows in an invalid native evidence group have no quality standing.
            status = raw_status if checked['ok'] else None
            code = status if status in ('pass', 'fail', 'timeout') else 'unknown'
            counts[code] += 1
            key = next(key for key in hashes if key.startswith(f'{rep}:{task}:'))
            records.append({'assignment_id': key.split(':', 2)[2], 'task_id': task,
                'replicate_id': rep, 'program_sha256': hashes[key],
                'control_eligible': task in eligible, 'raw_native_status': raw_status,
                'native_status': status, 'diagnostic_quality': (status == 'pass')
                if status is not None and task in eligible else None,
                'primary_scc_quality': None})
        groups.append({'replicate_id': rep, 'candidate_count': len(expected),
            'validation_ok': checked['ok'], 'validation_errors': checked['errors'],
            'report_sha256': checked['report_sha256'],
            'status_counts': {name: counts[name] for name in ('pass', 'fail', 'timeout', 'unknown')}})
    if len(records) != 396 or len({r['assignment_id'] for r in records}) != 396:
        raise ValueError('diagnostic records do not cover the fixed 396 assignments')
    return {'schema': 'scc-partial-diagnostic-report-v2', 'groups': groups,
        'records': records, 'primary_scc_method_score': None, 'primary_imputation': None,
        'interpretation': 'Separate retained-program diagnostic; incomplete SCC workflows remain unknown.'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = report(args.setup.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
