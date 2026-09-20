"""Recompute primary, mini, and SCC numerical summaries from anonymous ledgers."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fse-full-replay-") as directory:
        temp = Path(directory)
        primary_out = temp / "primary-summary.json"
        run([
            sys.executable, "primary/analyze.py",
            "--records", "primary/assignment_outcomes.jsonl",
            "--selection", "primary/selection.json",
            "--out", str(primary_out),
        ])
        assert load(primary_out) == load(ROOT / "primary/summary.json"), "primary summary differs"

        mini_out = temp / "mini-summary.json"
        run([
            sys.executable, "mini/analyze.py",
            "--records", "mini/assignment_outcomes.jsonl",
            "--manifest", "mini/selection.json",
            "--out", str(mini_out),
        ])
        replayed_mini = load(mini_out)
        retained_mini = load(ROOT / "mini/summary.json")
        assert all(retained_mini.get(key) == value for key, value in replayed_mini.items()), "mini summary differs"

        scc_out = temp / "scc-analysis"
        run([
            sys.executable, "scc/analyze.py",
            "--records", "scc/assignment_outcomes.jsonl",
            "--selection", "scc/selection_manifest.json",
            "--control-gate", "scc/control_gate.json",
            "--source-audit", "scc/source_audit",
            "--out", str(scc_out),
            "--draws", "10000",
        ])
        replayed = load(scc_out / "summary.json")
        retained = load(ROOT / "scc/summary.json")
        # Sanitizing the unused source-text field intentionally changes only
        # the input-file hash recorded in provenance.
        replayed.pop("provenance", None)
        retained.pop("provenance", None)
        assert replayed == retained, "SCC numerical summary differs"

    print("Primary and SCC summaries, plus the mini numerical analysis fields, reproduced from anonymous assignment ledgers.")


if __name__ == "__main__":
    main()
