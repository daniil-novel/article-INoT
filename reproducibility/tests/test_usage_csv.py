import copy
import csv
import json
from pathlib import Path

import pytest

from reproducibility.heldout200.export_usage_csv import export, ledger_rows


ANALYSIS = Path('reproducibility/results/20260908_codex_mini_inot200/analysis')


def test_public_inot_ledger_preserves_missing_turn_and_reconciles_cost(tmp_path):
    target = tmp_path/'usage.csv'
    assert export(ANALYSIS, target) == 200
    with target.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    missing = [row for row in rows if row['usage_available'] == 'False']
    assert len(missing) == 1
    assert missing[0]['input_tokens'] == missing[0]['api_equivalent_usd'] == ''
    assert sum(int(row['total_tokens']) for row in rows if row['total_tokens']) == 767679
    assert sum(float(row['api_equivalent_usd']) for row in rows if row['api_equivalent_usd']) == pytest.approx(1.05886035)


def test_ledger_rejects_changed_turn_valuation():
    audit = json.loads((ANALYSIS/'generation_audit.json').read_text(encoding='utf-8'))
    summary = json.loads((ANALYSIS/'summary.json').read_text(encoding='utf-8'))
    bad = copy.deepcopy(audit)
    bad['original']['inventory']['turns'][0]['observed_api_equivalent_usd'] += 1
    with pytest.raises(ValueError, match='Turn valuation mismatch'):
        ledger_rows(bad, summary['submitted_token_components'])
