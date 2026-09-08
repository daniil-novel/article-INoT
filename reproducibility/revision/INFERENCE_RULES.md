# Which inference belongs to the executed study?

This clarification is written after the completed primary outcomes were observed, at manuscript commit `84cc037`. It does not change the frozen protocol, raw evidence, test family, coefficients, missingness or numerical results, and is not a new preregistration.

| Study component | Entry point | Inference |
|---|---|---|
| Completed primary, 200 task units | `heldout200.assemble collect` → `heldout200.analyze.summarize` | Four exact two-sided McNemar tests; Holm across those four; familywise alpha 0.05 |
| Development, 40 task units and two repeat labels | `assemble_scale collect` → `analyze_scale` | Descriptive task-cluster bootstrap; no confirmatory tests |
| Primary interaction, resources, direct and independent INoT comparisons | Primary summary and `heldout200.exploratory_inot` | Descriptive intervals; not additional confirmatory tests |
| Earlier alternative API proposal | `analyze_factorial.py --legacy-exploratory` | Five sign-flip sensitivity contrasts with explicitly named Holm output; no primary test or quality-preservation decision |

The primary quality family is SR−SN, MR−MN, MN−SN and MR−SR. Each uses eligible observed pairs, counts the two discordant directions, tests the two-sided null of zero difference, and reports both raw and Holm-adjusted p. The descriptive 10,000-resample percentile intervals are neither simultaneous intervals nor rejection rules. The four-condition interaction uses the common complete set, not subtraction across different pair subsets. Original McNemar values and public-archive replay remain unchanged.

## Quality-loss margin

The completed study does not use a non-inferiority decision. The earlier 0.02 margin had no independently supplied application loss model, stakeholder tolerance or external validation. It is therefore not an acceptable-loss standard. A special zero-harm sample-size calculation does not justify the margin. The legacy analyzer now returns `not_assessed` with `margin: null`, even for arbitrarily favorable data. Frozen historical proposals remain accessible but do not govern current claims.

## Meaning of a monetary difference

For each reported contrast, use the same observed complete resource pairs in both arms. A ratio of mean API-equivalent valuations below 1, equivalently a negative paired mean difference, means a **lower observed list-price valuation**. Report its magnitude and descriptive 95% interval, the no-cache sensitivity, pair counts and unknown-usage inventory. An interval below zero is still a descriptive interval in this study; it is not a retrospectively registered economic-superiority test. Unknown usage and separate batch/cache conditions limit the scope. Lower valuation alone never establishes quality preservation, subscription savings or total cost of ownership.

## Before any later confirmatory run

A later confirmatory claim needs a separate manifest, new uninspected tasks and an analysis frozen before generation. If it permits quality loss, the author/application stakeholders must provide an externally motivated delta and its rationale before outcomes; this revision does not choose one from the existing data. The economic estimand, currency/rate snapshot, whether zero or a practically meaningful saving is the threshold, joint quality-and-cost acceptance rule, multiplicity family, missingness handling and power under plausible paired discordance must all be specified then. Without these inputs, report measured differences only and do not launch a study labelled confirmatory economic superiority. No new confirmatory generation is performed in this correction.
