# Hybrid-INoT working state

Updated 13 September 2026 during the author's authorized completion task.
This operational note is outside the standalone article and anonymous upload.
Always verify live processes and logs before resuming work.

## Scope and quota

Finish the SCC prefix of 2000 assigned task-repeat blocks (6000 method cells,
956 tasks, 941 control-eligible tasks). This is not a promise of 2000 complete
triples. Preserve all submitted failures and do not regenerate them. Complete
the bilingual paper, repeated language/scientific reviews, Engineering Loop,
and the separate AAMAS branch/package. Actual conference submission, account
creation and correspondence are not authorized.

Stop model work at 65% subscription remaining. The last direct app check was 72%; refresh
it before acting. Guard folder: `reproducibility/runs/subscription_guard65_20260913`.
The old55% pause is historical. No automatic credit resets or account changes.
The standalone watcher subsequently recorded `quota_unavailable`; preserve its
pause record. A fresh direct app query succeeded at 72% remaining. Experimental
generation is finished and must not restart; native evaluation uses no models.
Check the app limit directly before each further review wave.

## Live execution

- Generator parent PID22680, creation1789311147.0121443, module
  `reproducibility.scc2000.continuation generate`.
- Launch/log folder: `reproducibility/runs/scc1000-luna-v1/continuation-20260913d`.
- Operational selection: `reproducibility/scc2000/execution-resume-v2/selection_manifest.json`.
- Scientific analysis selection remains the original
  `reproducibility/scc2000/freeze-v3/selection_manifest.json`.
- Queue PID22852, module `reproducibility.scc2000.queue_finish_parallel`, job
  `reproducibility/runs/scc1000-luna-v1/finish-queue-parallel-20260913`.
- Read the most recent generation session's `progress.json` and the queue's
  `status.json`. Do not start duplicate processes.

Before continuation d there were5252complete,397infrastructure failures
(396Docker failures and1stream failure),8historicalpaused attempts and
343untouched selected cells. All are retained. The new continuation submits
only those343untouched cells. The full9000-row root remains paused because
3000 cells are administratively unselected. See the incident record for the
failed preflight and subsequent repairs; do not describe the Docker failures
as model errors.

The queue waits for complete selected generation, schedules two native groups
at a time with the identical frozen evaluator commands and per-container
limits, then invokes unchanged `finish.py` for all native validation, original
analysis and amended analysis. Do not edit the queue-bound files while active:
`finish.py`, `analyze.py`, `queue_finish.py`, `AMENDMENT.md`,
`parallel_finish.py`, `queue_finish_parallel.py`. Scheduling tests compare
actual generated commands to the unchanged sequential finisher.

The final continuation completed all 343 remaining cells. The selected prefix
now has 5595 completed workflows, 397 infrastructure failures and 8 historical
paused attempts, with no untouched cells. The session progress file is
`generation/sessions/1789311178975778900/progress.json` under the SCC run root;
the root continuation summary updates on exit, so it can remain stale while
the session is active.

Main queue PID 22852 is running native groups and analyses. The separate
partial-program queue PID 16476 WAS CANCELLED before execution: the v2 source
was a combined developer-plus-generated-test payload, not developer code alone.
See PARTIAL_V2_CANCELLATION.md and the cancellation record in
`reproducibility/runs/scc-partial-programs-20260913/queue`. Do not restart v2.
A new 399-program developer-only diagnostic is being prepared, including three
paused workflows with completed developer responses. Its source extraction
must reconstruct the original combined payload exactly before separating the
developer text. No diagnostic native outcomes have yet been produced.

## Completed evidence and manuscripts

The primary1000-task factorial is fully evaluated:15000assigned,14961complete,
39incomplete;985control-eligible tasks and264unknownquality endpoints. The
verified raw archive is `reproducibility/results/20260912_scale1000_luna_full`.
The lossless public archive and per-file byte verification are in
`outputs/evidence`. Do not add its huge unpacked tree indiscriminately to Git.

Primary results are integrated in both full LaTeX/PDF editions. Current full
PDFs are82English/86Russian pages, including complete assignment appendices.
The official-class anonymous AAMAS working source is
`submission/aamas2027/paper`; its current seven-page draft still has SCC pending.
Its entire current PDF was visually inspected, with no clipping; it still
requires final content, readability and anonymity checks after integration.
The known end-document ifx warning also appears in the unmodified official
template and minimal document; preserve the official class unchanged.

The strict SCC publisher is implemented and tested on fixtures and a moved
source closure. It has not yet published the actual completed SCC dataset.
Actual raw/native/statistical replay and moved-archive validation remain
necessary. Its evidence closure must include execution-resume-v2 and the new
administrative scheduling provenance before final publication.

## Reviews and current independent work

Full language R1 reports and applied/adjudicated changes are in
`reviews/2026-09-13-language-full`. Five fresh scientific checkpoint reports
and their immutable full inputs are in
`reviews/2026-09-13-scientific-checkpoint`. These are author-side internal
reviews while SCC is pending, not final conference reviews. Current findings
chiefly concern conditional estimands, the reused200task IDs, workflow-level
interpretation, missingness, supplement availability and AAMAS scope.

The author-side `checkpoint_text_adjudication` agent completed bounded EN/RU
clarifications. Both PDFs were rebuilt with no overfull or unresolved references.
The `partial_diagnostic_harness` agent is validating a separate native audit
of396retained developer programs from Docker-failed SCC workflows. Their exact
source is the code field of generated-test input, not a newly extracted tester
response. This diagnostic must not replace any primary SCC quality endpoint.
It has not run native tests yet. Root corrected repeat identity, allocation
order, raw control validation and report reconciliation in the helper. Nine
actual tests pass; the real 396-program v2 setup and preflight unknown report
are retained. See PARTIAL_ROOT_CORRECTIONS.md; original agent claims are
preserved but do not override the coordinator validation.

The `anonymous_semantic_package` agent prepared a candidate anonymous primary
supplement. The `anonymous_package_audit` agent is checking its actual portable
replay, retained content and field transformations. Broad regex redactions
and a local replay wrapper failed independent verification. A revised portable
package is being built with full decoder and archive-local replay. The old
candidate must not be released. The measured primary
prototype uses standard ZIP-LZMA with a128MiB dictionary:12,404,424bytes, with
all53,904prompt/result mappings verified. It is not yet anonymous, combined
with SCC or submission-ready. The64MiB version is14,503,492bytes. Retain exact
scientific texts; omit only documented operational/derived redundancy.

After final SCC integration, repeat full language checks and fresh scientific
critics, resolve material findings, perform the explicit Engineering Loop in
`ENGINEERING_LOOP.md`, and run a new review. That post-review loop has not yet
been executed. Save every report and decision in REVIEW_CHANGE_LOG.md.

## AAMAS and author details

Use no more than8content pages plus references, an unchanged official class,
one anonymous ZIP no larger than25,000,000bytes, source files, AI assistance
disclosure, author-form draft and upload guide. An extended paper is forbidden
as the supplement. Essential evidence must remain in the main paper. Generic
prompt/code-generation work without a central agent/MAS contribution has a
scope risk; explain the actual workflow-evaluation contribution honestly.

Author: Daniil Privezentsev, daprivezentsev@edu.hse.ru, second-year master's
student at HSE Faculty of Computer Science. The user supplied FKN SPI /
системное программирование; do not infer an unverified English program name.
No external funding or conflict of interest. The OpenReview profile, ORCID
and submission number are unknown. A Findings-choice question is pending.
The author-registration deadline is17September2026. See
`submission/aamas2027/AUTHOR_FORM_DRAFT_RU.md` for confirmed fields and unknowns.

## Git

Work is in `codex/development-scale`, latest committed ddc6784 at this note.
Create/update the final `codex/aamas-2027` in a separate worktree after the
evidence and revisions are ready. Frequent meaningful commits/pushes are
authorized. Preserve unrelated changes, including the existing guide edit,
research_program_2026-09-08.md and unaccepted experimental drafts. Do not
include own commit links or repository dependence in the scientific paper.
