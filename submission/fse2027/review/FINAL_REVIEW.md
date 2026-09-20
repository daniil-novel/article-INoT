# Final FSE 2027 gate review

Review date: 2026-09-20
Track: FSE 2027 Research Track
Recommendation: **7/10 — Weak Accept**
Confidence: **4/5**

## Decision rationale

No desk-reject blocker remains. The 15-page anonymous `acmsmall` paper is within the stated 18-page content and 4-page reference limits, has embedded fonts and anonymous metadata, and contains no hidden instructions or critical compilation error. Claims are tied to the actual estimands: null results are not called equivalence, the direct comparison is exploratory, and SCC population quality is not ranked under unresolved missingness.

The contribution is a controlled decomposition of lexical role labels and call topology. The main study retains 15,000 assignments on 1,000 BigCodeBench tasks, task-paired three-repeat inference, Holm correction, assignment-level missingness bounds, an 800-new-task subgroup, and source-component sensitivity. External-validity evidence includes a second model alias on the reused 200 task IDs, a direct solver, and a separately prespecified SCC comparison. The related-work section now contrasts the design with MapCoder, AdaCoder, PairCoder, OneFlow, DATS, execution-guided repair, and cost-aware agent evaluation.

## Reproducibility gate

- Anonymous artifact: 302 files; internal manifest covers 301 payload files and all hashes match.
- Primary evidence chain: all 14,961 completed candidate programs match staged native inputs, native reports, and outcome-ledger statuses.
- Statistical replay: primary summary, mini numerical fields, SCC summary, and all 16 source-component bootstrap distributions reproduce.
- Control evidence: gold and incorrect-program metadata, samples, reports, and gate hashes verify.
- Anonymity: no submission author name, institution, user profile, repository path, account identifier, or credential was found. Machine-local JSON paths are replaced by documented neutral markers.
- Final supplement SHA-256: `085CFB6384CBBC87B8FA0E64DEBE02F315E20B34ACAA2B52D87A5B106562DC3E`.

## Remaining reviewer risks

1. The primary result uses one public function-level benchmark and one mutable closed model alias. The mini study reuses the same 200 task IDs and is corroboration, not an independent replication.
2. The contribution is a measurement and component-isolation study. Some reviewers may consider it narrower than a new software-engineering system, even though the practical cost and quality result is strong.
3. The topology intervention necessarily changes repeated context, exposed intermediate history, and computation together. The paper states this boundary and does not claim a pure call-count mechanism.
4. Full conversation bodies and SCC candidate source are withheld during review. The primary candidate-to-report chain is fully auditable, while every SCC intermediate cannot be independently reconstructed until the retained archive is released.

These are external-validity and scope limits rather than repairable inconsistencies. Acceptance cannot be guaranteed at a selective conference; the defensible final assessment is submission-ready with a weak-accept recommendation.
