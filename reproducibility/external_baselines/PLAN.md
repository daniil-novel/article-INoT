# External baselines: source audit and proposed study

8 September 2026. **Design proposal, not a frozen protocol or completed experiment.**
The running scale1000 Luna study and its frozen files remain unchanged.

## Recommendation

Add an author-code SCC comparison on BigCodeBench first, accompanied by a
more tightly specified paper-based INoT implementation. Then evaluate complete
repository-repair systems against Agentless and mini-SWE-agent on SWE-bench.
Increasing the number of internal ablation tasks cannot replace either comparison.

The paper retains Hybrid-INoT as its architecture. The BigCodeBench comparison
concerns its one-call role-organized core, with final external evaluation; it does
not establish the performance of adaptive routing or a repair loop. A separate
repository experiment must specify an executable Hybrid-INoT repair system before
claiming a comparison of complete systems.

## Verified sources and implementation fidelity

| Method | Source inspected | Finding and next step |
|---|---|---|
| SCC, historical author code | [2024 source](https://github.com/YihongDong/Self-collaboration-Code-Generation/tree/b471e12051190dbae2c71b429a3c87466df4b336) | Recommended starting point. Preserve its role classes, prompts, session transitions and stopping logic; add dataset, transport, isolated execution and evidence adapters. |
| SCC, current author code | [2026 source](https://github.com/YihongDong/Self-collaboration-Code-Generation/tree/a6490a9d0d32f3238cc5b776d2de8d2134d2b138) | A later tool-using system. Do not silently identify it with the paper-era method. |
| INoT | [Paper v1, sections 3.1 and 3.3](https://arxiv.org/html/2507.08664v1) | No author implementation was identified in the paper links and targeted search. This is a bounded search result, not proof that none exists. Existing local implementation is an adaptation. Specify PromptCode, task wrapper, stopping interpretation and all deviations before a new run. |
| Agentless | [Author source](https://github.com/OpenAutoCoder/Agentless/tree/5ce5888b9f149beaace393957a55ea8ee46c9f71) | Preserve localization, candidate generation and patch selection. Porting only its repair prompt would not reproduce Agentless. |
| mini-SWE-agent | [Author source](https://github.com/SWE-agent/mini-swe-agent/tree/04d809ceab9df28f9adaed044884180159172930) | Practical maintained repository-agent baseline. Freeze the exact agent, model interface and SWE-bench configuration. |
| SWE-agent | [Source inspected at](https://github.com/SWE-agent/SWE-agent/tree/3ea751c087f32b16e039a2233dd6eefecef325d5) | Its README recommends mini-SWE-agent going forward. Original SWE-agent remains an optional additional baseline; mini is not an execution of the original system. |

SCC, Agentless and mini-SWE-agent repository metadata identifies MIT licensing.
Retain the license of the exact revision if vendoring its source. These source
pins record this audit; they do not establish installation or runtime readiness.

### SCC discrepancy that must be reported

[Paper v2, section 3](https://arxiv.org/html/2304.07590v2) describes simulated
testing and tester reports. The historical author implementation's
[session.py](https://github.com/YihongDong/Self-collaboration-Code-Generation/blob/b471e12051190dbae2c71b429a3c87466df4b336/session.py)
instead executes model-generated tests and sends execution feedback to the coder.
Its default entry point specifies two coder rounds, with an analyst call and an
intermediate tester call; successful generated tests may end the session early.
This difference is material. Call this baseline **SCC author implementation
(2024), adapted to BigCodeBench**, not an exact reproduction of paper v2.

The current 2026 implementation adds tool actions and history trimming. Taking
the latest default branch without checking history would introduce further
changes. The proposed historical baseline already uses output extraction and
role-specific histories: retain these documented native behaviors and archive
raw messages before extraction. Do not claim every external system forwards
every previous raw answer unchanged.

SCC's internally generated tests are permitted by its algorithm. Hidden benchmark
tests and reference programs are never available to the generator. The comparison
with the one-call core is therefore a **complete-method comparison**, not an
isolated causal test of role labels. The existing factorial study serves the latter
question. A neutral core with the same verification/repair loop could be added
only under a separate, explicitly defined component experiment.

## Track A: closest methods on 1000 tasks

Proposed allocation: the same fixed 1000 task IDs, **three fresh repeats**, and
four methods: Hybrid-INoT core (SR), neutral core (SN), historical author-code
SCC, and paper-based INoT. This is **12000 final-candidate assignments**.
With two SCC coder rounds the nominal maximum is 21000 model calls before
transport retries; early stopping or failures can reduce it. Archive every call,
including tester calls and unsuccessful attempts. Repeats are fresh runs, not
provider seeds and not best-of-three selection.

Run all four methods in a seeded randomized order within each task-repeat block.
Use one available model, reasoning setting and transport throughout. Luna medium
is the current candidate, subject to adapter feasibility. Fresh SR/SN runs avoid
using a different historical model or running only the competitors in a later
service period. Reusing the running study as a historical comparator is possible
as a secondary analysis, but would not give contemporaneous randomized comparisons.

These task IDs include previously examined tasks and must not be described as a
new untouched test set. Freeze adaptations without consulting the running study's
answers or scores. Report the original 200 and additional 800 separately. Use
only already designated development tasks for integration debugging; no pilot
candidate enters the final series.

Retain the complete task input and avoid added compression. Reuse the verified
native BigCodeBench environment when its identity matches; 985/1000 tasks passed
the existing control gate. Generate and attempt native evaluation for all 1000,
retaining raw outcomes and resource records for control-ineligible tasks as well.
Execute SCC-generated tests inside an isolated container without hidden tests.

Before freezing, settle source-to-adapter fidelity, generation limits, timeout
and transport retry rules. A 512-token historical default must not be silently
transplanted to a modern reasoning model, nor changed without disclosure. State
the resulting comparison as a model/dataset adaptation, not reproduction of the
authors' original numerical scores.

Proposed primary contrasts are SR minus SCC and SR minus INoT. Average repeated
binary outcomes within task, use paired two-sided tests on task means with Holm
correction for this fixed two-contrast family, and task-cluster bootstrap intervals.
SN comparisons are descriptive unless a larger family is frozen in advance.
Predefine complete-pair rules and bounds for missing outcomes. Do not count 3000
replicates as 3000 independent tasks. No non-inferiority or equivalence claim is
planned; finalize power calculations and the analysis implementation before runs.

Report success, failure categories, calls, input/cached/output tokens, conditional
API valuation and elapsed time. Lower observed cost alone does not establish
quality preservation. Analyze cost differences independently of quality claims;
any formal monetary-superiority decision needs its own predeclared rule/family.

## Track B: real repository repair

Recommended systems: a frozen executable Hybrid-INoT repair workflow, **full
Agentless**, and **mini-SWE-agent**. Original SWE-agent is optional and would be
listed separately. Do not adapt repository agents to isolated function tasks and
then present those runs as their native SWE-bench implementations.

Begin with a small integration pilot on disjoint development issues, covering
multiple repositories. The target empirical extension is the full **300-issue
SWE-bench Lite, three repeats, three systems: 2700 episodes**. This remains 300
issue clusters, not approximately 1000 independent units. Previously inspected
issues, including the existing one-issue pilot, must be disclosed. Do not select
the final issues because a method succeeded on them. Feasibility and power must
be demonstrated before committing this target to a confirmatory protocol.

Every system receives the same issue and base repository revision, equal access
to allowed repository files/tools, and no gold localization or hidden test patch.
Preserve each system's native search and candidate-selection logic. Agentless
intrinsically localizes and reduces context; disabling that changes the baseline.
Record this difference and restrict compression-free causal claims to Track A's
controlled core design. Internal candidate counts need not be equal, but every
internal attempt counts toward measured resources. An equal-budget variant is
secondary and must carry a distinct label and frozen budget.

All final patches are evaluated by the
[official SWE-bench harness](https://www.swebench.com/SWE-bench/guides/evaluation/).
Use distinct evaluation identities for every system/repeat/patch to avoid stale
cached reports. Check gold and negative controls before generation. Preserve
all assignments: confirmed empty or non-applying model patches are failures;
infrastructure/ambiguous failures require log-based classification and remain
visible. Missing report.json alone does not imply an infrastructure exclusion.

## Codex subscription, fidelity and budget

An adapter can use Codex CLI to obtain model responses while upstream code
controls the workflow. It must preserve and log message order/content, exposed
responses, available usage counters and all changes to role serialization.
SCC's old chat interface and modern native tool-calling interfaces are not
automatically interchangeable with a CLI text prompt. Synthetic-response contract
tests and real development probes must establish the supported surface first.
Do not label a CLI serialization bridge as a native Chat Completions API run.

mini-SWE-agent supports a
[documented text-action interface](https://mini-swe-agent.com/latest/advanced/v2_migration/),
which is a plausible CLI integration path. Its native agent must still control
action parsing, state transitions and isolated command execution. Do not let
Codex independently solve the issue with its own tools and call that mini-SWE-agent.
This path has not been implemented or benchmarked here.

If required API parameters or message semantics cannot be preserved, use a common
API backend for all methods in that separate comparison, with documented prices
and actual billing. Do not silently switch only one method or fall back from the
running subscription study to a paid API. No additional key is needed to begin
source integration and offline checks. Live API feasibility would require the
configured provider key and verification that the selected model is available.

No credible dollar estimate for these new workflows exists yet. Measure complete
per-method trajectories on the development pilot; project total input, cached
input and output tokens separately using published model prices, with a stated
reserve for retries and compute. Account for internal tests and all Agentless
candidate stages. Subscription API-equivalent valuation is not an invoice.
Keep the previously authorized $300 limit separate from free quota and do not
promise that both tracks fit it before measuring them.

The local E: volume had about 36.4 GB free during this audit. The
[SWE-bench project](https://github.com/SWE-bench/SWE-bench) recommends at least
120 GB free storage, 16 GB RAM and 8 CPU cores. Disk location and Docker capacity
must be checked separately: E: free space is not a measurement of Docker's image
store. A larger disk or a suitable Linux host may be needed for the full series;
a GPU is not required for remotely served model inference.

## Implementation acceptance gates

1. Pin upstream sources and licenses; publish a per-file adapter/deviation map.
2. Test recorded/synthetic success, repair, stopping, malformed response and
   transport-failure paths against upstream transitions without model calls.
3. Complete the development pilot with full traces and native checks; measure
   actual call counts, resource distributions and system capacity.
4. Publish a final executable protocol, task allocation, test family, power and
   budget calculation before any new main-series generation. Launch only after
   those gates pass, without changing the running study's frozen dependencies.
5. Evaluate every submitted assignment and publish traces, patches, test reports,
   missingness and costs. Update the manuscript and both PDFs with observed
   outcomes; source availability and this plan are not empirical results.

At this audit's completion, source inspection and this proposal are complete.
Adapters, offline contract tests, live pilots and external main-series results
remain outstanding. An author-code run can close the absence-of-baselines
criticism; whether it supports Hybrid-INoT is an empirical question.
