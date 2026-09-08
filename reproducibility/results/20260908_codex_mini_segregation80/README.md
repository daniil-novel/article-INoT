# Independent 80-task role-label and layout experiment

All 320 assigned candidates were generated once and evaluated with the unchanged
native BigCodeBench test suite. There are no missing generations or evaluations.
The final gold controls pass on 80/80 tasks; the incorrect control also passes on
BigCodeBench/59. All four candidates for that task remain in the archive but are
control-ineligible for quality inference, leaving 79 task pairs (316 outcomes).

| Condition | Completed | Success / quality-eligible |
|---|---:|---:|
| Role labels, headings (RB) | 80/80 | 44/79 |
| Neutral labels, headings (NB) | 80/80 | 44/79 |
| Role labels, prose (RP) | 80/80 | 42/79 |
| Neutral labels, prose (NP) | 80/80 | 43/79 |

The two prespecified role contrasts have exact two-sided McNemar p=1 and Holm
p=1. Quality differences are 0.00 pp (descriptive 95% task-bootstrap interval
[-6.33,+6.33]) and -1.27 pp [-10.13,+6.33]. API-equivalent paired mean ratios
are 0.989674 and 0.999583; both difference intervals cross zero. The primary
series' 18.45% lower valuation is not reproduced convincingly here. Differences
between batches are not a formal heterogeneity test. Neither equivalence nor
the absence of a small effect follows from these estimates.

All calls use GPT-5.4 mini, medium reasoning, Codex CLI 0.153.4 through the
subscription, with tools disabled, one response, identical full supplied
context, no compression and no retry. This manipulates observable role labels
and instruction layout; it does not observe private role separation.
The sample is disjoint from the primary and development samples. Selection was
published at 1b72638 and the final executable plan at 24ba687 before generation.
The 600-second deadline differs from the primary series; results remain separate.

Complete usage: input 932,812 (including 797,696 cached), output 467,794
(including 373,494 reasoning), total 1,400,606 tokens. Standard API-equivalent
valuation is USD 2.2662372; without cache discounts USD 2.804682. These are
counterfactual API valuations, not subscription charges or a complete TCO.

The archive retains full model-visible prompts, exposed responses, CLI events,
source snapshots, exact program exports, native logs, all reference-control
attempts, final environment package identities and the full assignment ledger.
Preparation diagnostics are not used as the final control gate. See
environment-history/README.md for the corrected library contracts and the
explicitly retained diagnostic metadata discrepancy. Tests and reference
programs were not edited. Third-party source licenses remain applicable.

Replay from the repository root without model calls or Docker (use a fresh
output directory):

```sh
python -m reproducibility.evidence_manifest verify reproducibility/results/20260908_codex_mini_segregation80
python -m reproducibility.segregation80.collect collect --archive reproducibility/results/20260908_codex_mini_segregation80/generation --inputs reproducibility/segregation80/inputs-v2 --export-dir reproducibility/results/20260908_codex_mini_segregation80/predictions --native-dir reproducibility/results/20260908_codex_mini_segregation80/native --gate-dir reproducibility/results/20260908_codex_mini_segregation80/controls-v4 --manifest reproducibility/segregation80/generation_manifest.json --out tmp/segregation80-replay
python -m reproducibility.segregation80.analyze --records tmp/segregation80-replay/candidate_records.jsonl --selection reproducibility/segregation80/inputs-v2/selection.json --out tmp/segregation80-replay/summary.json
```

The summary and all 320 candidate records replay byte for byte. Native evaluation
requires rebuilding the recorded environment; retained-report replay checks
provenance, program identity and computations, without claiming deterministic
provider regeneration or a bitwise-reproducible container build.
