# SCC publisher final audit (preparatory)

The future-facing `publish_scc.py` was tightened without changing frozen SCC
sources. It now regenerates the export in a temporary directory, compares
retained prediction bytes, validates all nine native groups, joins the native
audits through `scc_finish._records`, compares both candidate and resource
ledgers, and recomputes strict `scc_analyze` before copying any output. Its
portable verifier performs the same checks using the archive-local source tree
and restores `scc_controls.ROOT`, `scc_controls.REV`, and exporter globals after
verification. Bytecode writing is disabled before source imports.

The publisher retains safe runtime metadata including token counters, copies
requirements/Dockerfile and the development-gate summary required by the
frozen control source closure, and removes only explicit secret/auth fields.
It still refuses active or unfinished generation, incomplete native/ledger
evidence, and existing output directories.

Validation performed without model/native calls:

- `test_publish_scc.py`: **4 passed**;
- `py_compile`: passed;
- real frozen-plan source-closure check in a temporary copied source tree:
  `scc_controls.plan` returned `planned_assignments=9000` and the computed
  `manifest_sha256` matched the frozen SCC manifest (`True`);
- the closure check required copying the development summary to
  `reproducibility/results/20260911_scc_comparison_dev9/summary.json`, which
  is now part of the publisher's source copy contract.

No end-to-end main-study publication was run. The publisher remains future
facing until root completes the generation/native/analysis gates.
