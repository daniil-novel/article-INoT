"""Run the bounded SCC software/evidence gate without model calls.

The gate uses the declared isolated dependency directory when present and
writes only the requested report path. It is suitable before any main-series
dispatch and does not consume subscription quota.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--deps", type=Path, default=Path("tmp/external-baseline-deps"))
    a = p.parse_args()
    env = dict(__import__("os").environ)
    if a.deps.exists():
        env["PYTHONPATH"] = str(a.deps.resolve()) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    cmd = [a.python, "-m", "unittest", "reproducibility.revision_20260911.scc_revision_tests"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    report = {"schema": "scc-dev-gate-v1", "command": cmd,
              "returncode": result.returncode, "stdout": result.stdout,
              "stderr": result.stderr, "model_calls": 0,
              "finished_unix": time.time()}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result.returncode == 0, "report": str(a.report), "model_calls": 0}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
