# Compression-free factorial protocol v1

Status: **prospective; no new model outcomes observed**. This is a version-controlled analysis plan, not an externally registered or completed study. It becomes frozen only when its commit, dataset manifest, prompts, model/provider choices and analysis code are recorded before confirmatory generation. Amendments get a dated commit and a reason; completed outcomes never determine exclusions or stopping.

## Question and scope

Does assigning planner/implementer/reviewer labels improve independently tested code quality, and does combining the same three operations in one call change quality and cost? The historical B2/B3 contrast jointly changed compression and call count. It cannot answer this question. All new principal arms use exactly the same complete supplied task/context bytes. No selection, summarization, context cap, synthetic padding, routing, small-model checker, adaptive retry or oracle feedback is allowed.

The reviewer suggested topology × compression. Because the author explicitly requires **no compression**, this replacement crosses **call topology × role labels** while holding compression absent. This removes the confound from the new contrast and directly tests the proposed role contribution; it does not retroactively decompose the old compressed package. A compression factorial would be a separate future experiment, requiring an explicit scope amendment.

| Arm | Calls | Prompt organization | Operations |
|---|---:|---|---|
| single_neutral | 1 | Neutral stage instructions | Plan, implement, review |
| single_roles | 1 | Planner, implementer, reviewer labels | Same three operations |
| multi_neutral | 3 | Neutral stage instructions | Same operations, separate calls |
| multi_roles | 3 | Planner, implementer, reviewer labels | Same operations, separate calls |

The role effect is an intervention on textual instructions, not evidence of independent hidden agents. The call intervention also changes generation boundaries and intermediate output exposure: it estimates this implemented protocol, not an abstract topology independently of all information flow. Multi-call inputs contain the full original context and all earlier outputs. Intermediate outputs are never shortened.

## Task populations and scale

Primary executable target: BigCodeBench Instruct, full release (1,140 tasks before a development split), using its official tests and pinned evaluation image/source. Freeze dataset revision and bytes. Select 40 development tasks by seeded random permutation (20260908), retaining all remaining 1,100 for confirmation; never use first-k. The published Hard subset is a pre-existing sensitivity stratum, not a second independent dataset. No development task enters confirmatory estimates. Three recorded sampling seeds (17, 43, 101), four arms and two model families imply **26,400 planned generations / 52,800 planned calls** over 1,100 independent tasks; these counts are targets, not observations.

Secondary repository-repair target: all 500 SWE-bench Verified instances, three seeds, four arms, one initial inexpensive model: **6,000 planned generations / 12,000 planned calls**. Run official per-instance Docker tests. Before inference, construct a frozen retrieval packet using issue text and files at base_commit only. Complete bytes of that supplied packet must be identical across arms; selection of repository files is retrieval and must be disclosed even though no selected file is compressed. The current generator alone does not implement repository retrieval. Do not call this end-to-end repair until retrieval, patch application and official tests have actually run. No gold patch, test patch, FAIL_TO_PASS names or future commits enter the model prompt.

Verified provides comparability, not immunity to contamination or flawed tests. A temporally separated repository benchmark is required before claiming generalization to recent engineering work. Official SWE-bench tests and expanded code-generation tests reduce the old evaluator defect but do not prove the absence of test errors. Preserve disputed instances in the denominator and report an outcome-blind sensitivity set only with independent adjudication.

## Models, budgets and execution

Initial low-cost candidates: qwen/qwen3-coder-30b-a3b-instruct and google/gemini-2.5-flash-lite, verified in the OpenRouter catalogue on 8 September 2026. Snapshot returned model/provider IDs, parameters, prices, routing and caching metadata. API aliases are not immutable weights. Pin one provider per model after a capability canary; reject unavailable required parameters, disable provider fallbacks. Record server acceptance of seeds without claiming bitwise determinism.

Primary output allowance: 12,288 completion tokens per task and arm, equally divided (4,096 each) across three-call arms. The single-call arm gets the full 12,288. This matches the allowance, not actual compute, total tokens or dollars. Include returned reasoning tokens in the allowance and accounting. This fixed partition is itself an implementation constraint; if any arm has >5% length-limited outputs on development, stop and amend the allowance/allocation before confirmatory runs. Never discard length-limited outcomes from analysis. A per-stage matched allowance is a secondary sensitivity experiment, not interchangeable with the primary budget.

No spending until API access is funded. Total OpenRouter hard envelope is USD 300 across **all** phases and resumed runs, including canaries and failed requests. Allocate at most USD 10 development, USD 190 primary, USD 75 repository repair/baseline pilots, USD 25 reserve. These are spend ceilings, not a guarantee that the full matrices fit. Compute conservative envelopes from full payload length, output limit and current provider price; freeze feasible sample/model allocations before confirmation. If the planned full matrix cannot fit, report it as unexecuted and publish a smaller explicitly exploratory pilot; do not market budget-exhausted rows as the full experiment. Unknown charges reserve the whole request envelope until reconciled. No automatic retry of ambiguous network failures. Keep an inter-process budget lock when parallelism is added; current sequential runner must be the sole owner of a ledger.

Randomize task/seed block order and arm order within each block; measure queueing and generation latency separately if concurrency is introduced. Hold temperature, model, supplied context, output format and evaluator constant within blocks. Prompt paraphrases may be a predeclared robustness experiment, never chosen on test outcomes. Test execution is isolated from credentials and outside the generator process.

## Outcomes, hypotheses and analysis

Primary quality outcome: all required official tests pass (binary), one final candidate per seed. Report mean single-attempt success over seeds, not pass@3. Primary efficiency outcome: provider-reported USD per assigned task; report total input/output/reasoning/cache tokens, calls, latency and truncation separately. Cost per solved task is a ratio of total cost to total successes, undefined when none succeeds. No arbitrary maintainability-weighted score or model judge replaces tests.

Let Y_i,t,r be seed-averaged success for task i, topology t∈{single,multi}, roles r∈{neutral,roles}. Estimate role effects within each topology, topology effects within each role setting, and interaction (Y_single,roles−Y_single,neutral)−(Y_multi,roles−Y_multi,neutral). Use the analogous difference in log cost only for strictly positive costs; separately retain zero/missing costs. Also report absolute USD contrasts without logs. State which marginal contrasts average cells equally.

Primary mechanism hypothesis: internal role labels improve success relative to matched neutral stages (two-sided interval and test; do not assume direction). Efficiency hypothesis: single_roles reduces USD relative to multi_roles. Quality preservation is a separate non-inferiority claim with a prespecified 0.02 absolute success margin; declare it only if the one-sided 97.5% lower bound for single_roles−multi_roles exceeds −0.02. Combined success requires both quality and cost criteria; failing either does not establish the advertised tradeoff. Apply Holm correction to the prespecified role effects, topology effects and interaction within each benchmark/model quality family; do not choose significant contrasts after inspection. Report paired estimates and simultaneous decision rules, not only p-values.

Resample **tasks**, retaining all arms/seeds/models together; 10,000 bootstrap draws, seed 20260908. Report each model separately, and bootstrap paired model contrasts only where needed. Repeated seeds and overlapping benchmark subsets do not increase the independent task count. Sparse discordance: additionally report discordant-pair counts and conservative exact bounds for a single prespecified seed; zero-width bootstrap intervals at a ceiling are not evidence of non-inferiority. Complete-task primary contrasts require all expected cells; give pessimistic/optimistic bounds over unresolved infrastructure outcomes instead of silently deleting them. Invalid/empty model outputs are model failures; infrastructure failures are explicitly missing and must not be reported as model failures or successes.

Power planning: for one seed, paired difference D∈{−1,0,1} with discordance d and true mean near zero, n≈(z_.975+z_.80)^2 d / .02^2. At d=0.05, 0.10, 0.20 this is approximately 982, 1,963, 3,925 independent tasks. These are approximations; simulate clustered seeds using development-only nuisance estimates before freeze. 149 zero-harm pairs only describe a best-case one-sided binomial bound at alpha=.05; they are **not** an 80%-powered non-inferiority design. Neither 500 nor 1,100 tasks guarantees adequate power. Publish inconclusive results when bounds cross the margin.

## Baseline fidelity and evidence gate

INoT must use the original published PromptCode faithfully, with source/version and its loop ambiguity documented. An independently implemented bounded adaptation is labelled INoT-inspired and never a reproduction. Agentless and SWE-agent must be run from pinned upstream source with common task IDs/model, full trajectories and stated budget overrides. Their native search/retrieval/test loops are external system baselines, not extra factorial cells. Published leaderboard percentages are background only, never paired observations.

Store each full request (without Authorization), original response JSON, exposed assistant text, usage, final code/patch, timestamps, run/config/task/source hashes, provider identity, errors and finish reason. Persist before requesting the next call. Preserve officially produced test reports, stdout/stderr, environment/image digest, command, test script and patch hash. Audit completeness and integrity before analysis. An aggregate runs.json without complete output and evaluator evidence cannot pass this gate. Never attempt to reconstruct historical answers by regenerating them.

## Publication gate

Do not state that causal effects, non-inferiority, routing, baseline superiority or repository repair have been established until complete replayable observations support them. Current deliverable may contain a corrected historical audit plus prospective protocol; it must say so in title/abstract/results/README. Q1 acceptance is not established by formatting, a larger planned grid, or a longer bibliography.
