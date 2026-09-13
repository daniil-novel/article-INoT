# Follow-up statistical review: matched-repeat amendment

This follow-up incorporates the clarified amendment. The target is the first 2,000 preassigned randomized task-repeat blocks, not 2,000 tasks. Each block contains the three method cells, yielding 6,000 amended-prefix assignments. The remaining 3,000 blocks are administrative nonselection for this amendment and are excluded from its denominator, while remaining in the legacy 9,000-assignment ledger and report. The eight interrupted cells remain paused unknowns with no candidate, retry, or replacement.

Before any resumed call, freeze and hash the exact 2,000-block prefix and its cell IDs. The current dispatcher scans the full planned inventory, so it must receive a hash-bound prefix filter and reject any new submission outside that set. Existing out-of-prefix records are not part of the amended denominator. The amendment date must be recorded as post-call; it must not be described as preregistered before the original calls.

For contrast (c\in\{SR,SN\}), task (t) has selected replicate IDs (S_t) in the prefix. Let (R_{tc}\subseteq S_t) contain exactly the IDs where both SCC and (c) have observed native endpoints. The observed matched-repeat task difference is

\[
d_{tc}=|R_{tc}|^{-1}\sum_{r\in R_{tc}}(Y_{t,SCC,r}-Y_{t,c,r}),
\]

and the estimate is the equal-task mean of (d_{tc}) over control-eligible selected tasks with (|R_{tc}|\ge1). Report the task count and the distribution of matched repeat counts. This avoids pseudoreplication and avoids assigning a task greater weight because more repeats happened to be observed.

The assigned-prefix estimand is separate: for each selected task, average all intended replicate differences over the fixed denominator (m_t=|S_t|), then average those task means equally. Unknown endpoints remain unknown. Compute extreme lower and upper bounds twice, over all selected tasks and over control-eligible selected tasks, by assigning every missing binary endpoint to the direction that minimizes or maximizes the contrast within each task's fixed (m_t) denominator. A cell outside the prefix is excluded administratively; a never-submitted cell inside it is missing. Completed malformed answers are observed quality failures; transport, quota, authentication, provenance, workflow, and paused cells are unknown.

The sole primary family remains SCC−SR and SCC−SN with Holm adjustment at familywise alpha 0.05. Use the task-level paired analysis of (d_{tc}); do not introduce additional tests after seeing outcomes. The original three-complete-repeat analysis remains a separate result using tasks with all three repeats observed for both methods. No non-inferiority, equivalence, or quality-cost superiority claim follows from either analysis.

For quality uncertainty, use 10,000 percentile bootstrap draws of whole tasks, seed 20260911, retaining all matched repeats within each sampled task. Add the source-component bootstrap specified in the task-dependence protocol as a dependence sensitivity, reporting component count, largest-component share, effective count, variance, and degenerate draws. These intervals condition on observed matched pairs and do not resolve informative missingness, training overlap, provider drift, or restart-time effects.

The resource analogue uses the same prefix and selected-repeat denominators. For each method and selected task, average resource values over selected repeats with known, complete accounting; pair methods only on the same selected replicate IDs with known resource endpoints, and give each task equal weight. Keep known subtotals and unknown usage separate, never zero-impute an unknown turn, and exclude outside-prefix resources from the amended denominator while retaining them in the legacy ledger. Report paired differences, task ratios, and ratio-of-means only for the prespecified resource estimands; resource intervals describe recorded use and do not imply quality preservation.

Eligibility is not an observed-outcome bias in the current record builder: `scc_finish._records` sets `quality=None` and `outcome_type=control_ineligible` for observed candidates from ineligible tasks, while unavailable candidates remain unknown. The analyzer's use of the all-task list for primary contrast calls is therefore a boundary weakness and auditability risk, not demonstrated bias. Pass the eligible selected task set explicitly and retain all-selected missingness bounds. The unequal-repeat path must be separate because the existing analyzer requires all three repeats.

Report completion by prefix position, method, replicate, and restart/calendar segment. Treat the reserve stop as administrative; do not choose time segments or further tests after quality outcomes are available. Claims are limited to the selected task prefix, model/dataset/transport adaptation, observed time window, and stated missingness assumptions.

