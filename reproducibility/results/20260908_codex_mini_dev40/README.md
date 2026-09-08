# Completed development experiment: 40 tasks, 400 candidates

GPT-5.4 mini with medium reasoning generated all 400 assigned candidates in 720 fresh Codex CLI turns: 40 randomly selected development tasks, five conditions, two repeat labels. Context and exposed stage outputs were retained in full. Repeat labels are not controlled model seeds.

Original BigCodeBench tests were executed for every candidate. Reference and incorrect controls make 39 tasks eligible, giving 390 evaluable attempts; the ten attempts on `/1005` remain unavailable in the analysis. All 400 native input/code/status joins pass the evidence audit. Observed success varies by condition from 34/78 to 42/78, so there is no ceiling in these labels. Development comparisons are descriptive and cannot establish non-inferiority.

Recorded candidate usage totals 3,703,821 tokens. Published standard API rates value it at USD 6.6113451, or USD 7.7687595 without cache discounts. These values are counterfactual API prices, not subscription charges or total research costs.

- `generation/`: every original prompt, exposed response, event stream, CLI argument list, runtime record and frozen assignment.
- `predictions/`: exactly extracted native evaluator inputs.
- `evaluations/`: unchanged upstream CLI reports, logs and environment provenance.
- `analysis/`: all 400 joined candidate records, per-task controls, descriptive task bootstrap and resource summaries.
- `controls/attempt3/`: final instruct-mode controls; earlier attempts are retained as diagnostics.
- `software-checks/`: separate evaluator/bridge verification.

This is selective BigCodeBench instruct evaluation in a pinned custom offline environment, not a full official benchmark score. Original prompts and tests were not rewritten; documented prompt/test disputes remain limitations. Only reasoning exposed by the service is available, not private internal reasoning. `EVIDENCE_MANIFEST.json` hashes the published archive bytes when assembled.
