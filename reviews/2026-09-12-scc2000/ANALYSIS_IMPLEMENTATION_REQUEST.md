# Amended SCC analysis implementation request

Implement only `reproducibility/scc2000/analyze.py` and focused tests in
`reproducibility/tests/test_scc2000_analysis.py`. Read
`reproducibility/scc2000/AMENDMENT.md` as the authoritative statistical contract.
Do not read actual SCC candidate responses or benchmark quality outcomes, run
model/native calls, edit frozen files, write live results or start subagents.

Input is the original unique9000-row ledger from frozen scc_export/scc_finish;
the continuation selection manifest has6000 selected_ids, a selected-cell
digest and counts_by_task, plus an old_inventory snapshot identifying touched
cells at restart. Require the existing control gate and source-audit-v2 (verify
its manifest and source selection identity). Reject duplicate/foreign/missing
record IDs, nonboolean qualities, observed control-ineligible quality, invalid
resource counters, and an incomplete/altered prefix identity. Selected cells
must form whole three-method task-repeat blocks. Do not import the continuation
worker at module top (host Python lacks openai); use supplied validated selection
plus ledger/source metadata and the original analysis validation as appropriate.

Implement the exact matched-repeat, equal-task two-contrast inference and bounds
in AMENDMENT.md, preserving full draw vectors, task IDs, contributing repeats,
two-test Holm adjustment, undefined constant-nonzero t-tests and honest missingness.
Use quality seed20260911, resource differences20260912, task ratios20260913,
ratio-of-means20260914; all10000 draws. State RNG implementation and percentile
method. Use original source component partitions/family_bootstrap for dependence
sensitivity. Keep per-method marginal quality and pre/post/spanning-restart effects
descriptive. Outside-prefix3000 are administratively nonselected assignments,
not failures/unknowns in the amended denominator. There are2000 blocks and956
selected tasks (941 eligible), not2000 distinct tasks.

Resource completeness must not treat a prefix of an interrupted workflow as a
whole workflow just because its recorded turns have known usage. Pair whole
terminal completed workflows with complete known turn counters on the same
replicate IDs; preserve all submitted known subtotals/unknown counters separately.
Resource task eligibility is separate from quality eligibility. Only use positive
denominators for ratios and explicitly report exclusions; never zero-impute
unpriced/missing turns. Mean-of-task-ratios and ratio-of-paired-means are distinct.

Expose a pure analyze function for synthetic tests and a CLI that refuses
existing output directories, records input/source hashes and software versions,
and writes summary.json, selected assignment rows, per-task contrasts and saved
draws. The original three-complete-repeat analysis is run separately by root
through the unchanged original analyzer; do not replace or silently relabel it.

Test meaningful counterexamples: task-weighting differs from repeat-weighting;
different observed repeats cannot be paired; outside-prefix success cannot affect
answers; eligible/all-selected bounds use fixed task-specific denominators;
unknown is not false; fixed Holm family handles unavailable test; resource partial
workflow cannot masquerade as full cost; task-ratio differs from ratio-of-means;
component bootstrap retains related tasks; duplicate/invalid inputs fail closed.
Use small draw overrides in synthetic unit tests only. Report tests and limits.
