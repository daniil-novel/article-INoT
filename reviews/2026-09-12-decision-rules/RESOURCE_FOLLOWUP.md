# Resource-reporting follow-up audit

Date: 2026-09-12

## Scope

This follow-up checks the revised English and Russian standalone details against the frozen factorial and SCC analyzers only. It is read-only: no outcomes were inspected, no models or native tests were run, and no manuscript or analysis file was changed. The numerical-degeneracy language was also checked for conditional wording.

## Findings

### Eligibility scopes

The revised paragraph is substantively accurate. The factorial resource contrast (`reproducibility/scale1000/analyze.py:143-157`) includes a task only when all three repeats exist in both arms, every resource value is finite and numeric, and `generation_complete` is true for all six task-arm-repeat cells. Thus “all six generations and resource records” correctly describes the frozen code's complete-pair gate.

SCC has a distinct scope. `_task_means` averages whatever `_metric` returns and does not check `generation_complete` (`reproducibility/revision_20260911/scc_analyze.py:91-93`). For `api_equivalent_usd` and `total_tokens`, `_metric` returns a full value only when `turns > 0`, `unknown_turns == 0`, and `known_turns == turns` (`scc_analyze.py:96-120`). Consequently, an incomplete workflow can contribute to a full-resource task mean if every submitted turn has known counters; a missing or unknown turn makes the full metric unavailable. Known subtotal fields (`known_api_equivalent_usd`, `known_input_tokens`, and `known_output_tokens`) have looser handling and are distinct from complete-cost measures (`scc_analyze.py:103-119`). The revised EN/RU text correctly separates these cases.

One precision improvement is advisable: qualify “SCC's full-resource measures” as the analyzer's full `api_equivalent_usd` and `total_tokens` measures. Other direct resource fields, if present in records, are returned directly by `_metric` and do not necessarily inherit the turn-counter completeness check. This is a wording clarification only; it does not suggest altering the frozen analyzer.

Neither analyzer's resource eligibility requires reference-control quality eligibility. The revised paragraph states this correctly.

### Ratio estimands and intervals

The two equations in the revised sections match the frozen semantics:

\[
R_{\mathrm{pooled}}=\frac{\sum_i A_i}{\sum_i B_i},\qquad
R_{\mathrm{task}}=\frac{1}{n_R}\sum_{i:B_i\ne0}\frac{A_i}{B_i}.
\]

For the factorial analyzer, `A_i` and `B_i` are three-repeat task means; `_resource_contrast` reports the ratio of their sums and bootstraps the aligned task pairs with NumPy's PCG64 generator seeded 20260909 (`analyze.py:143-157`). Its difference interval uses the same seed. The revised statement that the component study reports intervals for pooled ratio and mean paired difference is correct.

For SCC, the code forms per-task ratios only for complete task pairs with `B_i != 0`, then reports their arithmetic mean. The interval labelled `ratio_bootstrap_task_sampling` bootstraps this ratio vector, so it is an interval for `R_task`, with Python's `random.Random` (Mersenne Twister), seed 20260913, and 10,000 draws (`scc_analyze.py:128-143, 284-295`). `ratio_of_means` is computed from all complete pairs whose mean denominator is nonzero and is a point estimate only; it is not passed to the bootstrap. The revised EN/RU paragraph states this distinction correctly. The SCC mean-difference interval uses seed 20260912.

The revised text also correctly requires ratio tables to identify the quantity and applicable pair count. The zero-denominator subset count `n_R` should be reported for `R_task`; the complete-pair count should be reported for the pooled ratio and difference.

### Generators, ordering, and percentile rule

The revised method paragraph correctly distinguishes the generators and order dependence: factorial uses NumPy 1.26.4's PCG64 path and SCC uses Python's Mersenne Twister. Factorial resampling follows the analyzer's task order; SCC's validated task list is lexicographically sorted (`scc_analyze.py:63-71`). Both use 10,000 resamples and linear interpolation at `(N-1)p` over sorted bootstrap means. The factorial implementation delegates to NumPy's default linear quantile method (`analyze.py:31-37`), while SCC implements that interpolation explicitly (`scc_analyze.py:128-143`). A fresh seeded generator is used per statistic in the relevant calls.

### Numerical degeneracy wording

The revised EN/RU wording remains properly conditional. It describes what the frozen implementations record if every task difference is the same nonzero value, identifies factorial `p=0` as a numerical sentinel with undefined t statistic, and says that SCC marks the test unestimable. It does not claim that either condition occurred and does not purport to amend or recompute the frozen tests. The statement that unestimable tests are not reported as numeric rejections is an appropriate reporting rule for the appendix.

## Concrete correction

No substantive correction to the two ratio equations, zero-denominator handling, interval seeds, or degeneracy paragraph is required. For maximum code fidelity, revise one phrase in both languages:

- EN: “SCC's full-resource measures” → “SCC's full `api_equivalent_usd` and `total_tokens` measures”.
- RU: “Полные ресурсные показатели SCC” → “Полные показатели SCC `api_equivalent_usd` и `total_tokens`”.

Retain the following qualification immediately after it: an incomplete workflow may contribute when every submitted turn has known counters, while known subtotal fields remain separate and are not complete-cost estimates. This keeps the manuscript aligned with the frozen analyzer's field-specific behavior.
