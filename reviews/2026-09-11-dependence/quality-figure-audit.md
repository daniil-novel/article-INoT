# Quality-figure builder: limited technical audit (2026-09-11)

This is a bounded software audit of `reproducibility/revision_20260911/plot_quality_effects.py` and its artificial-fixture tests. It is not a final scientific review and does not inspect live model outputs or current study runs.

## Verified agreement

- Factorial contrast keys and directions match `reproducibility/scale1000/analyze.py:20-25`: SR−SN, MR−MN, MN−SN, and MR−SR. The renderer multiplies the stored probability difference and interval endpoints by 100 at `plot_quality_effects.py:86-89`; the fixture test confirms −0.02 → −2 p.p. and preserves asymmetric −7.1/1.3 p.p. bounds.
- SCC directions match `scc_analyze.py:14-16` and `plot_quality_effects.py:24-27`: SCC−SR and SCC−SN. Descriptive SR−SN is deliberately excluded from the plotted primary family, consistent with `scc_analyze.py:255-260,312-314`.
- The plotted factorial n is `eligible_tasks` plus unique `task_ids` (`plot_quality_effects.py:61-67`), while SCC n is `n_tasks` and is checked against `bootstrap_task_sampling.n_tasks` (`:69-73`). This matches the task-level complete-pair unit in `scale1000/analyze.py:136-140` and `scc_analyze.py:158-170`.
- The renderer consumes registered `bootstrap_95`/`ci95` and Holm-adjusted p fields; it does not recompute either. The underlying procedures use 10,000 task resamples (`scale1000/analyze.py:32-42`; `scc_analyze.py:136-143`) and fixed Holm family sizes 4 and 2 (`scale1000/analyze.py:205-210,237-240`; `scc_analyze.py:255-260,307-314`).
- The 11 targeted tests pass: `python -m pytest -q reproducibility/tests/test_plot_quality_effects.py` → `11 passed`.

## Findings and limits

### Medium: schema checks are not a full statistical-contract check

`chart_rows` checks the factorial schema/task/repeat/missing-row counters and Holm family size (`plot_quality_effects.py:40-47`), and SCC rows/task count/strict flag/expected cells/replicates/primary family (`:48-55`). It does not check factorial `arms`, bootstrap resample/seed metadata, or inference method text; for SCC it does not check `strict_contract.methods`, `task_cluster_count`, `unit`, or the declared two-test Holm alpha. A software fixture with the required checked fields but contradictory omitted or altered contract metadata is accepted. This is a boundary of the renderer, not evidence that a real archive is wrong: the README explicitly requires the separate full replay (`revision_20260911/README.md:40-57`).

### Low: missingness is conditionally represented, not validated as zero

The renderer rejects nonzero `missing_rows` for the factorial archive and requires the SCC strict 9,000-cell shape, but it does not reject `quality_unknown_assignments` or analogous SCC unknown-quality counts. This is consistent with the plot’s stated estimand: complete-pair n and intervals are conditional, while missingness bounds are reported separately (`plot_quality_effects.py:135-141`; `scc_analyze.py:262-265,306,314`). It means the plot must not be read as an all-assignment success-rate estimate. The tests cover missing-row/strict-contract rejection, but do not test nonzero unknown-quality counts.

### Low: archive verification is integrity/terminal-state gating only

`render` verifies the byte manifest, terminal status, and summary schema (`plot_quality_effects.py:146-155`), then records hashes and states that replay is separate (`:169-175`). The manifest verifier checks exact retained bytes, but it does not rerun joins, cell semantics, control eligibility, subgroup partitions, or the statistical calculations. This is the intended archive boundary; it should be treated as a limitation of provenance checking rather than scientific validation.

## Explicit non-defects checked

- No sign inversion was found in either family.
- No probability/percentage-point unit mismatch was found in the CSV/figure path.
- Asymmetric intervals are retained even when the point lies outside them; the targeted test covers this (`test_plot_quality_effects.py:76-86`).
- `None` estimates and p-values remain unavailable for zero complete pairs (`plot_quality_effects.py:74-85`); numeric zero is not silently substituted.
- Holm multiplicity is displayed as adjusted p (`pH`) while intervals remain unadjusted, matching the analysis outputs and figure footer (`plot_quality_effects.py:135-141`).

The current audit therefore found no confirmed direction, n, bootstrap, Holm, zero-imputation, or unit-conversion defect in the new plotting path. Remaining risk is the intentionally narrow archive/schema gate described above; completion of the real Luna1000 and SCC archives plus their independent replay is outside this audit.
