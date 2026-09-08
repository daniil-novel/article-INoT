import json
from pathlib import Path

from reproducibility.swe_smoke.complete_dev1 import inventory


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_inventory_distinguishes_started_failure_from_unsubmitted(tmp_path):
    cells = [{'id': str(i), 'arm': 'direct'} for i in range(3)]
    write(tmp_path / 'manifest.json', {'cells': cells})
    write(tmp_path / 'status.json', {'state': 'blocked'})
    write(tmp_path / 'cells/0.json', {'final_text': 'answer'})
    (tmp_path / 'turns/0-0').mkdir(parents=True)
    (tmp_path / 'turns/1-0').mkdir()
    assert [r['original_status'] for r in inventory(tmp_path)] == ['completed', 'started_incomplete', 'never_submitted']
    assert inventory(tmp_path)[1]['original_turns'] == ['1-0']


def test_inventory_rejects_running_original(tmp_path):
    import pytest
    write(tmp_path / 'manifest.json', {'cells': []})
    write(tmp_path / 'status.json', {'state': 'started'})
    with pytest.raises(ValueError, match='terminal'):
        inventory(tmp_path)
