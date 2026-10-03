# R1: independent verification of retrospective revision analyses

**Status: confirmed numerical agreement; no substantive analysis-code flaw found in the checked scope.** This is internal AI-assisted verification of retained data, not external peer review or a new hosted-model experiment.

I reviewed the retrospective plan, `artifact/revision_diagnostics.py`, phase ledger, current diagnostic checkpoint, English/Russian methodological and result claims, and both temporal tables. I independently reconstructed the four precision intervals from the original 15,000-row assignment ledger, checked original control eligibility and generation markers, reconstructed the phase task/repeat sets and equal-task means, and reproduced all eight phase bootstrap intervals with independently batched 125-draw sampling. The current checkpoint retains those endpoints after the implementation changed to 250-draw batches. Resource means and exact contributing task sets were independently recalculated with standard-library arithmetic and checked against both the original summary and new checkpoint.

## Confirmed findings

1. **Precision — reanalysis, confirmed.** Complete observed quality endpoints imply completed generation and membership in the 985-task control gate. All four counts, means, standard errors and two-sided Bonferroni 98.75% t intervals agree within numerical rounding. Four contrasts form the stated interval family. Dependence between contrasts does not invalidate the Bonferroni union bound; individual task-level interval validity still requires the disclosed assumptions. Coverage is approximate and conditional on the observed task subsets, not a guarantee against source/provider correlation or nonrandom missingness. No equivalence margin or new confirmatory decision is introduced.

2. **Phases — reanalysis, confirmed.** All 14,961 supplied phase IDs match completed original generation rows: 5,551 in the first completed session and 9,410 later. Pairing uses the same task and repeat, with both observed endpoints in the same phase, then equal task weights. All counts, means and bootstrap endpoints match. Phase task overlap is 691, 685, 686 and 687 respectively in the contrast order below. Both topology means are negative in both phases; the early MR–SR interval crosses zero. These are overlapping available-case diagnostics, not independent replication, a phase-difference test, or evidence that provider drift is absent.

3. **Absolute resources — reanalysis, confirmed.** Resource eligibility requires all six completed, finite-counter endpoints, independently of quality eligibility. All four means and original task memberships agree. The rounded topology additions of 8,582/8,510 tokens per generation and about $1.60 per 1,000 generations are correct. English and Russian paragraphs distinguish valuation from invoices, latency and total deployment cost.

4. **Chronology — text correction, confirmed locally.** Actual pending/completion markers establish primary execution on 8–11 September UTC. The Luna amendment commit precedes the first marked request by approximately 38 seconds. This supports local prespecification; independent public registration remains unverified. The source audit was specified during generation, after early outcomes existed, and must remain described as such.

## Compact numerical evidence

| Contrast | Quality tasks | Simultaneous interval, percentage points | Resource tasks | Tokens/generation | Valuation/1,000 generations |
|---|---:|---:|---:|---:|---:|
| SR–SN | 982 | [-2.32, +0.83] | 997 | -58.024072 | -$0.058172 |
| MR–MN | 964 | [-0.20, +2.90] | 979 | -130.810010 | -$0.057136 |
| MN–SN | 968 | [-6.04, -2.29] | 983 | +8581.769413 | +$1.596241 |
| MR–SR | 971 | [-3.80, -0.46] | 986 | +8510.412441 | +$1.598588 |

All eight temporal rows in the English and Russian tables agree with independently reconstructed task counts, matched-repeat counts, means and intervals; means/endpoints agree within 1e-14. Token means agree within 1e-11 and dollar means within 1e-15.

## Sources and boundaries

- Original primary `analysis/candidate_records.jsonl`, `analysis/summary.json`, `controls/controls-v3/heldout200_control_gate.json`, streamed `generation/results.jsonl`, session `pending.json`/`completion.json`, and final `generation/status.json` under `reproducibility/results/20260912_scale1000_luna_full/`.
- `review/2026-10-03/ADDITIONAL_ANALYSIS_PLAN.md`, `generation_phases.jsonl`, `revision_diagnostics.json`; `artifact/revision_diagnostics.py`; both current `body.tex` sources and `temporal_diagnostics.tex` tables.
- Ledger SHA-256: `a2a8b8045f1c32dd76c783dc00f20bf5bef49ec63c58d11139e7187a61963ad6`; phase SHA-256: `d9fad504bdcfedd8aa3b26f31888feb1c07eb45fa89048d4c5cc0090e52d96c3`.
- Local Luna amendment commit: `d15cbe582096f1fab5271fc49ab0e68f38568463`, 8 September 17:17:15 UTC; first pending marker 17:17:52.970591 UTC; first completion 22:11:07.409946 UTC; final completion 11 September 21:46:30.602644 UTC. Source-audit protocol commit `19d45aed92f60304f0010f19ee510ffb01e393b5`, 11 September 15:42:18 UTC.

This audit makes no fresh PDF-build, native-environment rebuild, anonymous-package publication, immutable-model-version, independent SCC replication, or full-population SCC ranking claim. Existing-data reanalysis improves precision disclosure and temporal transparency; those broader limitations require additional evidence or new controlled generations.