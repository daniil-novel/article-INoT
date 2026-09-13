# SCC-2000 bounded launch review

## Scope and evidence

This review read `reproducibility/scc2000/continuation.py`, `AMENDMENT.md`, `AUTHORIZATION.md`, and `freeze-v1/selection_manifest.json` read-only. No model call, Docker/native evaluation, recovery, outcome read, or benchmark inspection was performed. The offline test run completed with **20 passed** across the SCC-2000 continuation, finish, and analysis test files.

The amendment is internally explicit: 2,000 randomized task-repeat blocks, 6,000 method cells, 956 distinct tasks, 941 control-eligible allocated tasks, 65% remaining-reserve stop, and the eight historical interruptions retained as paused unknowns. The selection manifest records 6,000 ordered IDs, the original 9,000-cell manifest hash, source hashes, amendment hash, adapter hash, and the unchanged eight-worker Luna runtime. The amended analysis and resource rules are stated in `AMENDMENT.md`, including matched replicate IDs, fixed assigned denominators, separate all-9,000 legacy reporting, and no outcome-triggered extra tests.

## Checks that are substantively covered

`selected_prefix()` groups the frozen 9,000-cell schedule into three-cell blocks and rejects a short, mixed-task, mixed-repeat, duplicate-ID, or non-factorial block (continuation.py:54–71). The prepared manifest requires exactly 6,000 unique selected cells, stores the ordered selection, and checks that pre-existing assignment folders are inside the prefix (continuation.py:104–148). `selection_adapter()` passes only selected pending cells to the unchanged coordinator and returns unselected pending cells to the parent status accounting (continuation.py:154–171). Because the frozen dispatcher skips every existing terminal status, including `paused`, the eight interrupted assignments are not submitted again.

Raw evidence is copied byte-for-byte during recovery with `read_bytes()`/`write_bytes()` and hashed in the recovery manifest; `validate_recovery()` compares the preserved copy and live archive inventories, and rejects tampering (continuation.py:306–338). The tests exercise CRLF preservation, same-basename files in different turns, completed-turn/candidate rejection, PID reuse, and post-recovery tampering. The recovery code therefore has concrete evidence for its no-retry and raw-byte requirements.

`validate_generate()` binds the selection, amendment, adapter, recovery manifest, and authorization file to the current `HEAD` via tracked-file and `git diff --quiet HEAD` checks (continuation.py:240–245). It recomputes the frozen prefix and checks the 65% threshold, finite remaining reserve, reserve policy, unlatched state, authorization markers, eight workers, Luna model, medium reasoning, and pinned CLI version (continuation.py:207–253). The selection and amendment hashes also prevent silent replacement of the 9,000-cell schedule or the 6,000-cell prefix.

## Mandatory launch blockers

1. **Recovery is not fully liveness-preflighted before mutation.** `recover()` performs an idle-process check at line 346, but then copies assignments and rewrites their live `status.json` files at lines 359–371. It performs the second `assert_recovery_idle()` only at line 376, after those mutations. A dispatcher that starts after the first check can therefore race with recovery; the second check can detect the race only after archive/status changes have happened. The smallest valid fix is to make the liveness check and mutation one exclusive critical section (for example, acquire an exclusive recovery lock before the first check and hold it through status rewrites and historical lock release), or to abort before any mutation if the lock/PID state changes. The existing tests prove the checks reject known live/reused PIDs, but do not prove race-free preflight.

2. **Watcher liveness is checked at one instant, not held as a launch invariant.** `validate_generate()` matches `watch.lock` to a live process and runs a fresh strict-65 guard command at lines 220–233, then writes `launch_check.json` and enters `dispatch_processes()` at lines 264–267. There is no final watcher identity/heartbeat recheck between the guard result and the first submission, and no coordinator-side assertion that the same watcher remains alive while the frozen worker runs. If the watcher exits in that gap, the process can proceed after a stale successful check. The smallest launch fix is a final identity-and-heartbeat check immediately before dispatch, with the watcher itself retaining the stop latch; if the watcher cannot provide a reliable live lease, generation must refuse to start. Do not weaken the strict `remaining_percent > 65` check or treat the 65% threshold as an invoice.

These are launch-control blockers, not evidence of benchmark-quality bias. The tests and code reviewed do not show a prefix-selection error, retry, raw-byte alteration, or model/runtime substitution. The explicit 65% guard is present; the concern is the race between a successful check and actual submission.

## Required preflight order

Before any recovery mutation, verify that the historical dispatcher and watcher are absent, the historical 55% pause evidence and lock bytes match their recorded hashes, and the eight candidate folders satisfy the nonterminal/no-candidate predicates. Hold the exclusive recovery lock through the archive copy, paused-status writes, recovery-manifest write, and historical-lock release. Before any model submission, verify the tracked `HEAD` bindings, recomputed prefix digest, authorization markers, fresh strict-65 guard, and the same live watcher identity/heartbeat immediately before entering the unchanged worker. Keep all selected and unselected pending IDs in separate status views so the frozen 9,000-cell dispatcher cannot be mistaken for amended completion.

## Future finalization work

After generation, independently verify all selected cells are terminal, reconstruct raw bytes, evaluate every observed candidate with the original native harness, and run both the amended 6,000-cell matched-repeat analysis and the historical three-repeat/9,000-cell analysis. Source-component dependence sensitivity, resource intervals, restart-segment diagnostics, manuscript integration, and AAMAS packaging are post-generation finalization tasks; they are not additional launch gates unless they alter the frozen dispatch or analysis contract.

