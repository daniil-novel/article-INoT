"""Export and reconcile the full development matrix using archived native evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from . import codex_subscription as c
from .audit_codex_pilot import audit
from .benchmark_bridge import _extract_fenced_block
from .scale_env.validate_native import environment_from_gate, validate_native
from .analyze_scale import summarize


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidates(archive):
    manifest = c.read(archive / 'manifest.json')
    if c.read(archive / 'status.json')['state'] != 'completed':
        raise ValueError('A partial generation matrix must be reported as partial, not silently completed')
    if sha(archive / 'control-gate.json') != manifest['control_gate_sha256']:
        raise ValueError('Archived pre-generation gate changed')
    rows = []
    for shard in manifest['shards']:
        path = archive / 'shards' / shard['name']
        checked = audit(path)
        if checked['manifest_sha256'] != shard['manifest']['manifest_sha256']:
            raise ValueError('A shard differs from its pre-generation assignment')
        rows.extend(json.loads(line) for line in (path / 'results.jsonl').read_text(encoding='utf-8').splitlines())
    expected = {(t, a, r) for t in manifest['assigned_task_ids'] for a in c.ARMS for r in manifest['replicate_ids']}
    keys = [(r['task_id'], r['arm'], r['replicate_id']) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('The combined matrix contains missing or duplicate candidates')
    return manifest, rows


def export(archive, out):
    manifest, rows = candidates(archive)
    out.mkdir(parents=True, exist_ok=False)
    indexed = {(r['task_id'], r['arm'], r['replicate_id']): r for r in rows}
    groups = []
    for arm in c.ARMS:
        for rep in manifest['replicate_ids']:
            samples = []
            formats = {}
            for task in manifest['assigned_task_ids']:
                solution, extracted = _extract_fenced_block(indexed[task, arm, rep]['final_text'], 'bigcodebench')
                samples.append({'task_id': task, 'solution': solution})
                formats[task] = extracted
            name = f'{arm}--r{rep}'
            path = out / (name + '.jsonl')
            path.write_bytes(b''.join(c.canonical(s) + b'\n' for s in samples))
            groups.append({'name': name, 'arm': arm, 'replicate_id': rep,
                           'file': path.name, 'sha256': sha(path), 'format_extracted': formats})
    c.save(out / 'export_manifest.json', {'source_manifest_sha256': manifest['manifest_sha256'], 'groups': groups})
    return groups


def collect(archive, predictions, native, controls, output):
    manifest, rows = candidates(archive)
    if sha(controls / 'dev40_control_gate.json') != manifest['control_gate_sha256']:
        raise ValueError('Controls differ from the generation plan')
    gate = c.read(controls / 'dev40_control_gate.json')
    environment = environment_from_gate(controls)
    for kind in ('gold', 'incorrect'):
        samples = [json.loads(line) for line in (controls / kind / 'input/samples.jsonl').read_text().splitlines()]
        checked = validate_native(controls / kind, {r['task_id']: r['solution'] for r in samples}, environment)
        if not checked['ok'] or any(checked['statuses'][t] != gate['status_by_task'][t][kind] for t in gate['assigned_task_ids']):
            raise ValueError('Control reports do not support the frozen eligibility map')
    export_manifest = c.read(predictions / 'export_manifest.json')
    if export_manifest['source_manifest_sha256'] != manifest['manifest_sha256']:
        raise ValueError('Predictions originate from another plan')
    expected_groups = {(arm, rep) for arm in c.ARMS for rep in manifest['replicate_ids']}
    groups = [(g['arm'], g['replicate_id']) for g in export_manifest['groups']]
    if len(groups) != len(expected_groups) or set(groups) != expected_groups:
        raise ValueError('Export group matrix is incomplete or duplicated')
    indexed = {(r['task_id'], r['arm'], r['replicate_id']): r for r in rows}
    enriched = []
    native_audits = {}
    for group in export_manifest['groups']:
        path = predictions / group['file']
        if sha(path) != group['sha256']:
            raise ValueError('Exported samples changed')
        expected = {}
        formats = {}
        for task in manifest['assigned_task_ids']:
            row = indexed[task, group['arm'], group['replicate_id']]
            expected[task], formats[task] = _extract_fenced_block(row['final_text'], 'bigcodebench')
        if formats != group['format_extracted']:
            raise ValueError('Extraction metadata changed')
        checked = validate_native(native / group['name'], expected, environment)
        native_audits[group['name']] = checked
        if not checked['ok']:
            raise ValueError('Native evaluation failed provenance/coverage audit: ' + group['name'] + ': ' + str(checked['errors']))
        for task in manifest['assigned_task_ids']:
            row = indexed[task, group['arm'], group['replicate_id']]
            status = checked['statuses'][task]
            enriched.append({**row, 'raw_test_status': status,
                             'analysis_status': status if task in gate['evaluable_task_ids'] else None,
                             'format_extracted': formats[task],
                             'native_report_sha256': checked['report_sha256']})
    summary = summarize(enriched, manifest['assigned_task_ids'])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'candidate_records.jsonl').write_bytes(b''.join(c.canonical(r) + b'\n' for r in enriched))
    c.save(output / 'summary.json', summary)
    c.save(output / 'native_audit.json', native_audits)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('export', 'collect'))
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--predictions', required=True, type=Path)
    p.add_argument('--native', type=Path)
    p.add_argument('--controls', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if a.command == 'export':
        print(json.dumps({'groups': len(export(a.archive, a.predictions))}))
    else:
        if any(v is None for v in (a.native, a.controls, a.output)):
            p.error('--native, --controls and --output are required to collect')
        result = collect(a.archive, a.predictions, a.native, a.controls, a.output)
        print(json.dumps({'recorded_attempts': result['recorded_attempts'], 'by_arm': result['by_arm']}))
