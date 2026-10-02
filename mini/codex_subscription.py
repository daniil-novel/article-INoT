from __future__ import annotations
import json
from pathlib import Path

ARMS = ('single_neutral', 'single_roles', 'multi_neutral', 'multi_roles', 'direct')

def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n'
    path.write_text(payload, encoding='utf-8', newline='\n')
