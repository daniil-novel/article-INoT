# Contemporaneous SCC author-code comparison protocol

Protocol prepared 11 September 2026. The source manifest must be committed
before the first main-series call. A development gate on the three previously
exposed pilot tasks precedes that freeze. The scale1000 files and the
9 September development pilot are immutable inputs.

## Scope and estimand

The comparison contains three contemporaneous arms: fresh single-role SR,
fresh single-neutral SN, and the pinned 2024 author implementation (commit
`b471e12051190dbae2c71b429a3c87466df4b336`) adapted to BigCodeBench and to the
same GPT-5.6 Luna medium subscription transport used by fresh SR and SN arms.
The historical `Session.run_session`, role prompts, role-specific histories,
extraction, tester transition, and stopping behavior are retained. The model
call boundary is a text-only JSON serialization bridge; historical
`max_tokens`, temperature, and `top_p` are recorded but not enforced. Generated
tests run in the pinned network-disabled non-root container and never receive
hidden tests or reference programs.

Use the same fixed 1000 task IDs and three fresh repetitions (replicate labels
101, 102, 103) for all three arms. This gives 9000 randomized assignments and
a maximum of 18000 model calls (one each for SR/SN and four for SCC);
the upstream early stop can reduce this count. The three repetitions estimate
per-generation success, averaged within task. They are not provider seeds and
must not be selected by outcome. The 1000-task allocation preserves task
breadth and makes the SCC arm directly joinable to SR/SN by task and repeat;
the previously examined 200 tasks and additional 800 tasks are reported
separately, without calling either subgroup newly held out.

This is a complete-method estimand: SCC includes role orchestration, generated
test feedback, repair transitions, extraction, and stopping. SCC versus SR/SN
therefore cannot be interpreted as an isolated causal effect of role labels.
The factorial component study remains the isolated-label estimand. Results are
reported as a model/dataset/transport adaptation, not as a reproduction of
the historical numerical scores. INoT is excluded until its paper-faithful
PromptCode and stopping specification passes the same offline and development
gates; no INoT result is silently substituted here.

## Allocation, controls, and execution

Freeze the task list, source hashes, control-gate hash, method label, and
randomized task/repeat order before generation. Reuse the existing native gate
only when `controls_complete` is true and the task IDs exactly match. Gold and
incorrect controls must pass/fail respectively for a task to be quality
eligible; all other assignments remain in the ledger and are evaluated where
possible. Candidate evaluation uses the unchanged native BigCodeBench image
and evaluator. Generated-test reports are evidence about SCC's internal
transition only, never the benchmark quality label.

Each assignment writes its task, source manifest, runtime identity, every
serialized request, raw CLI event stream, exposed answer, usage counters,
session history, extracted candidate, generated-test container records, and
terminal status. Input is never shortened. The per-turn deadline is 600 s and
the 65536-byte conversation guard is fatal without truncation. There are no
automatic retries, paid API fallback, answer-based replacement, or reuse of a
submitted attempt. Resume may process untouched assignments only.

The stable assignment schema is `assignment/cell.json`, `task.json`,
`status.json`, `turns/<stage>/`, and (when a final answer exists) `candidate.py`.
`status.json` records `generation_complete`, `outcome_type`, and
`format_extracted`; a transport failure cannot create a fabricated empty SCC
candidate. A completed malformed one-call answer retains its raw answer and
an empty candidate for native format accounting. Every frozen cell remains in
the export ledger, including untouched cells.

Run SCC and fresh SR/SN in one randomized task-repeat block schedule while
the model, reasoning setting, transport policy, and native environment are
unchanged. The process path uses the same assignment worker for one-worker
development probes and the eight-worker main study. Python `spawn` isolates
each process; each worker executes one assignment at a time.
SCC generated-test containers share a multiprocessing semaphore of one, while
the model calls remain independently isolated. Stop new submissions at the shared
known API-equivalent guard or on authentication/quota, provenance, unsupported
model, eight consecutive failures, or unpriceable usage. Preserve unknown
usage separately. The dispatcher accepts a hash-bound `prior_known_valuation`
offset from the shared study ledger, so the USD 285 guard is an envelope
across SR/SN/SCC rather than a separate SCC budget. In-flight calls may use a
predeclared reserve; unknown usage is retained and is never asserted to be
zero. No quota reset is automatic.

The local Docker engine exposes about 7.75 GiB of memory. One SCC generated-test
container (3 GB limit) may run alongside one factorial native-evaluation
container (3 GB limit). This bound is fixed before main generation; queue
waiting is part of elapsed workflow time. The development probe has one
worker and therefore exercises at most one generated-test container.

With eight active assignments, the planning ledger reserves USD 15 for
in-flight calls before applying the shared guard. This is a scheduling reserve,
not an invoice or an increase to the USD 285 envelope; parent-side quota or
guard stops submit no new assignments while active workers finish.

An empty or malformed completed answer is retained as an observed candidate
failure with its raw answer and an empty candidate file for native accounting;
it is not silently converted into an infrastructure exclusion. Timeout,
quota, authentication, provenance, and model-workflow failures retain their
distinct terminal categories.

## Analysis and resource accounting

The two primary contrasts are SCC minus SR and SCC minus SN. For each
contrast, include a control-eligible task only when all three repetitions in
both methods have observed native outcomes. Average the three binary outcomes
within each task and method, subtract the paired means, and apply a two-sided
one-sample t-test of mean difference zero to the task differences. The
familywise significance level is 0.05 with Holm correction over these two
hypotheses. An unestimable test retains its place in the family (p = 1 for
adjustment, reported as unestimable). A constant zero difference has p = 1;
a nonzero constant sample difference has zero sample variance and an undefined
t-statistic and is reported as unestimable. SR minus SN and the
old200/new800 subgroup contrasts are descriptive and cannot expand the
primary family after outcomes become available.

Report 95% percentile bootstrap intervals using 10,000 resamples of whole
tasks, seed 20260911. Resampling preserves the three repetitions as a cluster;
they are not 3,000 independent task units. Intervals describe conditional task
sampling for the observed complete pairs. They do not incorporate provider
changes over time or uncertainty about the missingness mechanism. Alongside
them, report extreme assignment-denominator identification bounds for the
985 eligible tasks and all 1,000 assigned tasks, assigning every unknown
binary endpoint both possible values. Identification bounds are not
confidence intervals.

Quality and resources are separate estimands. Resource summaries include
all retained submitted turns, including unsuccessful calls. Unknown usage is
reported separately from known subtotals. Comparisons of fully observed
resource costs average three runs within task and report paired differences,
mean task ratios and the ratio of paired sample means. Resource bootstrap
seeds are 20260912 for differences and 20260913 for mean task ratios. A
resource interval below zero (or a ratio interval below one) is descriptive
evidence of lower recorded resource use, not a quality-preserving monetary
advantage. No non-inferiority margin, equivalence claim, or combined
cost-and-quality superiority decision is specified for this study.

The transport reports input, cached input, output and, where exposed,
reasoning tokens. Cached input and reasoning output are subsets and are not
added twice. The frozen API-equivalent rates per million tokens are USD 0.20
input, USD 0.02 cached input, and USD 1.20 output. They value subscription
usage counterfactually and are not subscription invoices or actual API
payments. Nonzero unpriced cache-write counters stop new submissions.
Raw timestamps, call counts and generated-test records remain available for
separate execution audits.

## Prospective sensitivity and feasibility

The 985 control-eligible task clusters set the maximum complete-pair sample
size; missing generations can only reduce it. For planning, let d denote the
per-repeat discordance probability and rho the correlation of paired
differences across repeats. Approximate variance of the mean difference is
`d * (rho + (1-rho)/3) / 985`. A normal approximation at two-sided alpha 0.025
(the conservative first Holm threshold) gives the following sensitivity:

| d | rho | 2 percentage-point difference | 5 percentage-point difference |
|---|---|---|---|
| 0.15 | 0.0 | 0.714 | >0.999 |
| 0.15 | 0.5 | 0.399 | 0.997 |
| 0.15 | 0.8 | 0.308 | 0.983 |
| 0.30 | 0.0 | 0.399 | 0.997 |
| 0.30 | 0.5 | 0.201 | 0.898 |
| 0.30 | 0.8 | 0.156 | 0.798 |
| 0.50 | 0.0 | 0.241 | 0.945 |
| 0.50 | 0.5 | 0.125 | 0.683 |
| 0.50 | 0.8 | 0.100 | 0.557 |

These are design sensitivities under hypothetical discordance/correlation
values, not guarantees based on having 1,000 tasks. A null result cannot
establish a two-percentage-point non-inferiority claim. Execution requires up
to 18,000 fresh model turns and nine native evaluation groups, in addition to
SCC's generated tests. The development gate checks this complete procedure;
the main dispatcher resumes only untouched assignments and stops on resource
or infrastructure failures. Subscription quota can pause the study even when
its API-equivalent valuation is below the planning guard.

The runner is deliberately separate from the frozen scale1000 dispatcher:
its dynamic number of upstream calls and generated-test folders cannot be
represented as a fixed one/three-turn factorial cell. Its manifest and
evidence ledger provide the comparable assignment identity and resource
accounting without modifying the frozen scale1000 files.

## Required launch gates

1. `scc_controls.py check` passes against the frozen inputs and native gate.
2. SCC contract tests, source-hash checks, synthetic stopping/repair/failure
   checks, and Docker smoke checks pass.
3. A development probe with complete traces confirms the common Luna
   transport and measures call/resource distributions; development IDs never
   enter the 1000-task denominator.
4. The final SCC/SR/SN analysis family, missingness bounds, and submission
   guard are frozen before the first main-series call.
