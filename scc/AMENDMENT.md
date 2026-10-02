# SCC comparison: fixed 2000-block amendment

Recorded 13 September 2026 after an account-reserve interruption and before any
resumed generation or SCC benchmark-quality inspection. This is a disclosed
change after original calls began, not a preregistration before those calls.
The author requested a smaller completed comparison and then preparation of
the standalone bilingual manuscript and AAMAS 2027 submission package.

## Allocation and stopping

The original randomized schedule contains 3000 task-repeat blocks: 1000 tasks
times three repeat labels, each with SCC, single-role (SR), and single-neutral
(SN) assignments. The amended scope is exactly its first **2000 blocks**, or
**6000 method assignments**. It contains 956 distinct tasks: 212 assigned once,
444 twice, and 300 three times. Of these, 941 pass the previously completed
reference/incorrect-program control gate. These are allocation counts, not
counts of observed or successful programs, and source similarity does not
establish independence of their errors.

Selection is determined by the original seeded schedule, never by quality,
completion speed, usage, or method success. The remaining 1000 blocks (3000
method assignments) are administrative nonselection in the amended study.
Retain their IDs in the original 9000-row ledger, but exclude them from the
amended denominator. Never-started cells *inside* the prefix remain unavailable
assigned observations. Do not extend the prefix until a desired number of
successful or completely observed comparisons is obtained.

Before this amendment, 3849 assignments had completed generation and eight
had been interrupted by the previously authorized stop at 55% account reserve.
The eight have no final candidate and each last archived model turn lacks a
completed response. Preserve their original statuses and raw file hashes,
classify them as paused unknowns, and do not resubmit them. Exactly 2143 selected
assignments were untouched at allocation freeze. No original response, prompt,
usage counter, runtime pin, or benchmark test is replaced.

The renewed authorization uses a stricter external **65% account reserve**.
The account showed 99% remaining at restart preparation. This allows at most
34 percentage points before the reported stop threshold; the guard polls every
30 seconds and dispatch requires a valid heartbeat no older than 75 seconds
before every new assignment. In-flight work can affect the final counter. Keep
the original known API-equivalent valuation envelope and unknown-usage checks.
No reset, alternate account, paid-API fallback, model substitution, or automatic
clearing of a pause latch is authorized by this amendment.

A separate, source-bound coordinator restricts dispatch to the prefix while
calling the unchanged frozen assignment worker, prompts and SCC author
controller. Original model, medium reasoning, CLI version, eight workers, one
generated-test container, timeouts and complete input context are unchanged.
All methods receive the same task data; hidden benchmark tests remain external.
The original 9000-cell dispatcher status must not falsely report full completion.
Separate amendment status records whether all selected attempts are terminal.

## Quality estimands and inference

For selected task t, let S_t be its fixed set of selected replicate labels.
For comparator c in {SR,SN}, let R_tc contain only selected labels with observed
native endpoints for *both* SCC and c. On control-eligible tasks with nonempty
R_tc, calculate the mean of the paired binary differences over R_tc. Average
those task means equally across contributing tasks. Never pair different
replicates, weight tasks by their number of observed repeats, or treat repeated
generations as independent task units. Explicitly mask control-ineligible tasks.

The amended primary family consists only of SCC minus SR and SCC minus SN.
Use the two-sided one-sample t-test on task differences, with Holm correction
over these two hypotheses at familywise alpha .05. An unestimable test occupies
its family slot with adjustment input p=1 and is labelled unestimable. Constant
zero differences have p=1; nonzero constant differences do not produce a valid
t-test or a scientific p=0 claim. No additional inferential tests are selected
after outcomes become available.

Report 95% percentile intervals from 10000 whole-task bootstrap draws, seed
20260911, using NumPy default_rng (PCG64) and linear-interpolated percentiles,
preserving the matched-repeat task means. Retain the draw vectors,
contributing task IDs and matched-repeat counts. These intervals describe the
conditional observed matched-pair estimand; they do not resolve informative
missingness, model drift, training overlap, or dependencies between tasks.

For the assigned-prefix estimand, average paired differences over *all* S_t
using each task's fixed assigned-repeat denominator, then average tasks equally.
Compute extreme identification bounds by setting unknown binary endpoints to
their lower/upper possible values in the direction that minimizes/maximizes
each contrast. Report these separately for eligible selected tasks and all
selected tasks. These bounds are not confidence intervals. Transport, quota,
workflow and native-infrastructure unknowns remain unknown. A completed
malformed answer follows the frozen observed-format-failure rule.

Also report the original three-complete-repeat analysis, unchanged, as a
separate analysis with its own explicitly labelled original two-contrast Holm
family. Its all-9000 ledger bounds are historical-plan bounds, not amended-prefix
bounds. Do not promote whichever analysis is more favourable. SR minus SN,
old200/new800 partitions, and marginal method success rates remain descriptive.

Apply the previously defined source-component bootstrap to the amended task
differences, using its fixed source partitions, seed20260911 and10000 draws.
Intersect components with the actual contributing tasks and divide each draw
by its sampled task count. Report component count, largest share, effective
count, variance and degenerate draws. This is a sensitivity analysis, not a
new significance test or a change to the task-weighted point estimand.

## Resources and restart diagnostics

Report all retained submitted-turn known token/cost subtotals and unknown
counters, including interrupted attempts, by method and restart segment.
Subscription usage is not an invoice: the frozen published API-equivalent
rates remain a counterfactual valuation. Do not substitute percentage of a
shared subscription for a per-method monetary endpoint.

For paired resource contrasts, use the same selected replicate labels in each
method and include a pair only when both whole-workflow resource totals are
complete and priced. Average within task and then equally across tasks.
Resource eligibility is separate from quality/control eligibility. Report paired
differences, mean task ratios where denominators are positive, and the ratio of
paired-sample means as distinct estimands. Use 10000 whole-task draws with the
original resource seeds20260912 for differences and20260913 for mean task
ratios; use seed20260914 for a separately recomputed ratio-of-means interval.
Use NumPy default_rng (PCG64) and linear-interpolated percentiles for these
amended resource intervals as well; original analysis RNGs remain unchanged.
Retain draw vectors and counts. Do not silently turn undefined ratios or unknown
usage into zero. Resource intervals imply neither quality non-inferiority nor
joint monetary-and-quality superiority.

Prespecify descriptive generation/availability summaries by method, repeat,
original block position and before/after interruption. Classify block segments
by whether their scheduled cells had been touched at the freeze; mark any
block spanning restart separately. Show within-segment matched quality effects
descriptively after evaluation, without new p-values, segment selection or
outcome-based additional sampling. Preserve runtime identities and calendar
timestamps across both periods. Broader model-, repository- or task-population
claims remain outside this experiment.

## Evidence and completion gates

Before calls: commit this amendment, the deterministic prefix manifest,
coordinator code, recovery audit and independent preparation review; pass the
prefix/no-retry/guard tests and the original source/runtime checks. No SCC
benchmark outcomes are inspected before these gates.

After generation: require no live dispatcher, all selected assignments terminal,
byte-preserving raw reconstruction and evaluation of every observed candidate
with the original native harness. Retain the original9000-row record plus an
explicit6000-row selected view. Verify both original and amended analyses,
then integrate actual results into the articles. Full manuscript critics and
all-page visual review occur after integration, followed by the separately
formatted anonymous AAMAS paper and supplement.
