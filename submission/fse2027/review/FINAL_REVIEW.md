# Final FSE 2027 gate review

Review date: 2026-09-20
Track: FSE 2027 Research Track
Recommendation: **Weak Accept**
Confidence: **4/5**

## Decision rationale

The revision resolves the earlier desk-reject and major-revision issues. It is now an anonymous `acmsmall` submission within the page limit, framed as a controlled software-engineering experiment rather than a claim about machine cognition. The central contribution is identifiable: named roles and call topology are crossed while operation sentences and supplied context are held fixed, and a direct solver is treated as a first-class baseline.

The evidence is materially stronger than the earlier manuscript. The primary study contains 15,000 assigned generations over 1,000 tasks, uses task-level paired estimands, controls multiplicity, reports uncertainty and missingness bounds, and keeps repeat generations within task clusters. The paper now reports the 200 reused versus 800 newly sampled task-ID sensitivity, source-dependence sensitivity, direct-baseline contrasts, resource accounting, and a separate 2,000-block SCC comparison with explicit transport and missingness limitations. The anonymous artifact independently recomputes both statistical summaries from assignment-level outcome ledgers.

## Review dimensions

| Dimension | Score | Assessment |
|---|---:|---|
| Originality | 3.5/5 | The contribution is an unusually clean decomposition of labels and topology rather than a new agent architecture. |
| Importance | 4/5 | The negative result directly informs expensive role-based code-generation workflows. |
| Soundness | 4.5/5 | Paired task-level analysis, correction, fixed schedules, controls, bounds, and sensitivity analyses are appropriate and disclosed. |
| Evaluation | 4.5/5 | Large executable benchmark study, direct baseline, SCC comparison, resource metrics, and replayable analyses. |
| Presentation | 4/5 | The argument is compact, claim-calibrated, and readable in the FSE template. |
| Related work | 4/5 | The paper now covers the closest multi-agent software-engineering systems, persona prompting, feedback methods, and matched-budget concerns. |
| Reproducibility | 4.5/5 | Anonymous ledgers, protocols, selections, controls, source partitions, pinned dependencies, hash manifest, and full statistical replay are supplied. |

## Closed critical issues

- Replaced the 51-page Springer framing with a 13-page FSE review manuscript.
- Removed author identity, affiliations, acknowledgements, identifying links, and PDF author metadata.
- Replaced broad introspection claims with estimands tied to observable calls and executable outcomes.
- Added a direct solver and showed separately that it matches the one-call staged workflows and exceeds the three-call workflows in exploratory comparisons.
- Distinguished 800 newly sampled task IDs from 200 reused IDs; all generations in the expanded study are fresh.
- Added source-family sensitivity, extreme missingness bounds, and precise eligibility denominators.
- Elevated the completed 1,000-task Luna study and the 2,000-block SCC study; removed the one-issue repository-repair result from the evidence base.
- Expanded related work and verified every rendered reference against a publisher, proceedings, OpenReview, ACL Anthology, or arXiv record.
- Added detailed AI-use disclosure and an exact post-conclusion Data Availability statement.
- Replaced a summary-only artifact check with a replay from anonymous assignment ledgers for both primary and SCC analyses.

## Residual risks reviewers may still weigh

1. The primary claim is based on one model alias at one reasoning setting. It establishes a boundary for this implementation, not a model-family law.
2. BigCodeBench is public, so training contamination cannot be ruled out. The source-family audit addresses task dependence, not memorization.
3. The topology intervention bundles extra calls with repeated context and exposure of intermediate responses. The paper states this precisely and does not call it a pure call-count effect.
4. SCC has substantial infrastructure missingness. Observed-pair estimates are negative, but full-denominator extreme bounds allow either sign; the paper does not rank full-population quality.
5. Reviewers may regard a negative component study as narrower than a new system contribution. The practical value depends on whether they reward causal isolation and cost evidence.

These are limits of the available experiment rather than defects that can be repaired by wording. A new multi-model, private-benchmark experiment could reduce the first two risks, but it is not required to make the current claims valid.

## Gate result

No paper-level P0 blocker remains. The remaining actions are administrative and cannot be completed from the manuscript alone: final author order, conflicts, simultaneous-submission declaration, and the live HotCRP upload. Acceptance cannot be guaranteed at a selective conference; the defensible assessment is submission-ready with a weak-accept recommendation.
