"""Expose each audited submitted turn in a spreadsheet-readable resource ledger."""
import argparse
import csv
import json
import math
from pathlib import Path

from .resource_ledger import summarize_turns
from ..codex_subscription import value_usage


FIELDS = ('attempt', 'shard', 'cell', 'stage', 'terminal_state', 'usage_available',
          'input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_subset',
          'total_tokens', 'api_equivalent_usd', 'uncached_sensitivity_usd', 'events_sha256')


def ledger_rows(audits, summaries):
    rows = []
    seen = set()
    if set(audits) != set(summaries):
        raise ValueError('Audit/summary attempt mismatch')
    for attempt in ('original', 'continuation'):
        audit = audits[attempt]
        if 'shards' in audit:
            turns = [(shard['shard'], turn) for shard in audit['shards'] for turn in shard['turn_inventory']]
        else:
            turns = [('', turn) for turn in audit['inventory']['turns']]
        actual = summarize_turns([turn for _, turn in turns])
        for key, expected in summaries[attempt].items():
            value = actual[key]
            if isinstance(expected, float):
                if not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError('Summary accounting mismatch: ' + key)
            elif value != expected:
                raise ValueError('Summary accounting mismatch: ' + key)
        for shard, turn in turns:
            cell = turn.get('cell', turn.get('turn'))
            stage = turn.get('stage', 0)
            key = (attempt, shard, cell, stage)
            if key in seen:
                raise ValueError('Duplicate submitted turn')
            seen.add(key)
            usage = turn['observed_usage']
            row = dict.fromkeys(FIELDS, '')
            row.update(attempt=attempt, shard=shard, cell=cell, stage=stage,
                       terminal_state=turn['status']['state'], usage_available=usage is not None,
                       events_sha256=turn.get('events_sha256', turn.get('files_sha256', {}).get('events.jsonl')))
            if usage is not None:
                for name in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
                    row[name] = usage[name]
                row['reasoning_output_subset'] = usage.get('reasoning_output_tokens', '')
                row['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
                if usage.get('cache_write_input_tokens', 0) == 0:
                    value = value_usage(usage)
                    recorded = turn.get('api_equivalent_usd', turn.get('observed_api_equivalent_usd'))
                    if recorded is None or not math.isclose(value, recorded, rel_tol=1e-12, abs_tol=1e-12):
                        raise ValueError('Turn valuation mismatch')
                    row['api_equivalent_usd'] = f'{value:.10f}'
                    row['uncached_sensitivity_usd'] = f"{(usage['input_tokens']*.75+usage['output_tokens']*4.5)/1e6:.10f}"
            rows.append(row)
    return rows


def export(analysis, output):
    audits = json.loads((analysis/'generation_audit.json').read_text(encoding='utf-8'))
    summary = json.loads((analysis/'summary.json').read_text(encoding='utf-8'))
    rows = ledger_rows(audits, summary['submitted_token_components'])
    with output.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'submitted_turn_rows': export(args.analysis, args.output)}))
