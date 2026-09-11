# Statistics audit: SCC/SR/SN analysis chain

Date: 2026-09-11
Scope: preparatory code audit of the future 1,000-task SCC/SR/SN series
Files changed by this audit: `reproducibility/revision_20260911/scc_analyze.py`, `reproducibility/revision_20260911/tests_scc_analysis.py`

This is a reviewer-style technical audit of the analysis contract and its
offline fixtures. It is not a full independent review of the final article,
provider execution, native benchmark evidence, or the complete SCC pipeline.

## Files and interfaces read

The audit read `scc_export.py`, `scc_finish.py`, `scc_dispatch.py`,
`scc_protocol.md`, the existing `scc_revision_tests.py`, the scale-1000
selection/control-report code, and the revised analyzer/tests. The relevant
finish output is a complete 9,000-row assignment ledger with unique
`task_id × method × replicate_id` keys, methods SR/SN/SCC, replicate IDs
101--103, `outcome_type`, `native_status`, `format_extracted`, `quality`, and
nested `resource_usage`.

## Findings and fixes

The initial analyzer treated every null quality value as the same missingness
mechanism and did not consume nested resource usage. It also inferred control
eligibility only from optional row labels, which would silently use all 1,000
tasks when called on the finish ledger. The analyzer now distinguishes:

- observed native or model format failures as `quality=False`;
- control-ineligible, generation-unavailable, transport, quota,
  authentication, provenance, workflow, and native-unavailable rows as
  `quality=null`;
- direct and nested resource fields, including `api_equivalent_usd`,
  `resource_usd`, `resource_cost`, and `total_tokens`.

The finish `outcome_type=control_ineligible` fallback recovers the 985-task
quality-eligible set when the external gate is not passed. Strict analysis also
accepts explicit `--selection` and `--control-gate` inputs, verifies the
1,000-task assignment set, requires a 200/800 subgroup partition and exactly
985 eligible IDs, and enforces the full 9,000-cell matrix. It rejects
quality=True on infrastructure/control-ineligible outcomes and, in strict mode,
requires `quality=False` for a model format failure after native accounting.

The statistical contract averages the three repeats within task before paired
contrasts; primary tests are SCC−SR and SCC−SN only, using two-sided paired
t-tests and Holm correction over those two p-values. SR−SN remains descriptive.
Task bootstrap uses 10,000 resamples with seed 20260911. Resource outputs
include paired three-repeat task means, mean paired differences, mean paired
ratios, ratio-of-means, and bootstrap intervals. Extreme assignment bounds are
reported for the 985 eligible and all 1,000 assigned tasks. No
non-inferiority margin is introduced.

## Tests

The added tests cover duplicate cells, invalid repeat IDs, task-level pairing
against repeat pseudoreplication, actual two-test Holm adjustment, finite-sample
bounds, strict contract rejection, control-gate selection, nested resource
fields, format-failure versus infrastructure semantics, and rejection of
quality=True on ineligible rows. The finish-schema fixture uses the fields
emitted by `scc_finish._records` and does not call a model.

Executed checks:

`python -m unittest reproducibility.revision_20260911.tests_scc_analysis reproducibility.revision_20260911.scc_revision_tests`

Result: 17 tests passed. Python bytecode compilation for both revised files
also passed.

## Remaining limitations

No 9,000-row future execution was available for numerical re-analysis, so this
audit verifies the contract and synthetic finish-shaped fixtures rather than
provider outcomes or native reports. Resource completeness can only be
reported for rows whose nested usage values are present; unavailable usage is
not zero-imputed. The task bootstrap quantifies conditional task-sampling
uncertainty for observed complete pairs and excludes provider/time variation
and missingness mechanisms. The SCC comparison remains a complete-method
contrast and cannot identify an isolated role-label effect. Replicate IDs are
repeat labels, not provider seeds.

## Independent CLI smoke audit (2026-09-11)

This additional check read the dispatcher and development-smoke entrypoints
without modifying them or invoking a model/native evaluator. Both help
entrypoints completed successfully (exit 0). A preparation-only smoke run on
the pinned three development tasks also completed with 9 cells and an explicit
`model_calls: 0` record. The `--execute` path correctly refused to start when
`--execution-root` was omitted. A missing-input dispatcher invocation failed
before runtime/authentication/model work with `FileNotFoundError`.

Offline guard checks passed: `dispatch_lock` creates an exclusive lock,
rejects a second owner, and removes its own lock on exit; deterministic cell
planning produced unique IDs for every task/replicate/method combination. The
source inspection confirms resume checks for the frozen manifest, instruction
bytes, runtime/native hashes, prior-valuation source/hash, non-terminal status,
and preserved candidate files on observed malformed answers. No live model,
Docker, or native benchmark call was made.

The scale report was separately checked as the five-arm, 15,000-assignment
primary ledger (`direct`, `single_roles`, `single_neutral`, `multi_roles`,
`multi_neutral`; three repeats), not the 9,000-row SCC ledger. Its readiness
gate refuses outcome bounds until `generation_finished`, and its session split
uses an explicit session field only; timestamps alone are not treated as a
reliable original/resume mapping. The scale-report test suite and the existing
SCC offline tests passed together (21 tests).

Concrete blockers for a full end-to-end smoke remain:

1. `scc_dev_smoke.py` exposes preparation and an explicitly opt-in
   `--execute`, but no `--run` option; a requested `--run` smoke cannot be
   exercised through that CLI name.
2. The full dispatcher run requires the frozen inputs, the recorded runtime,
   authentication, and live upstream/native execution; this audit therefore
   verifies guards and refusal paths only.
3. Original/resume batch sensitivity is not identifiable from timestamps alone;
   rows without an explicit session/assignment label must remain unmapped.
4. Resource denominators remain ledger-dependent: missing or unknown usage is
   retained as missing and is not silently treated as zero cost.

This is a preparatory code/entrypoint audit, not a complete independent review
of the final article or of future provider/native results.

## Follow-up contract audit (2026-09-11)

The analyzer was checked against the actual `scc_export._resource` schema:
`turns`, `known_turns`, `unknown_turns`, token subtotals, and
`known_api_equivalent_usd`. Complete cost and token metrics are now emitted
only when `turns > 0`, `known_turns == turns`, and `unknown_turns == 0`.
Known cost and token subtotals remain separate fields; an unavailable resource
object is not converted to zero.

The Holm family size remains fixed at two primary contrasts even when one
primary p-value is unestimable; the unestimable adjusted value remains null.
Strict control-gate validation now rejects any quality value other than null
for gate-ineligible tasks before contrasts are reported. Russian scale-report
fragments use plain Russian wording and short contrast labels.

Added tests exercise the real export resource helper schema, incomplete versus
complete usage accounting, fixed-family Holm behavior, strict gate semantics,
and the Russian renderer. Combined offline checks: 24 tests passed.
