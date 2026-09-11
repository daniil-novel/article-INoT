# SCC Luna development comparison (2026-09-11)

This is a development feasibility gate with fresh executions of three previously exposed BigCodeBench tasks, one repeat, and three same-Luna arms: SR, SN, and the SCC author implementation with its disclosed CLI transport. All 9/9 assignments completed, using 18 model calls and known API-equivalent valuation of $0.02301176. Native outcomes are SR 0/3 pass, SN 1/3 pass, and SCC 1/3 pass. These development-only outcomes support no inferential or main-study performance claim; none of these tasks is in the 1,000-task main allocation.

The archive retains raw generation, native reports, pipeline logs, predictions, the original three-task native preparation and gold/negative controls, licenses, and relevant source copies. Authentication data, virtual environments, binaries, and `.git` metadata are excluded.

Offline verification (no model or native rerun):

```text
python -m pip install -r requirements-replay.txt
python replay/scc_dev_replay.py --root .
python provenance/evidence_manifest.py verify .
```

The replay command checks every generation row against `summary.json`, validates all three retained native groups, and validates the three gold and three negative controls with the recorded environment metadata.
