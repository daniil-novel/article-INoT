# Retained developer-program diagnostic

Frozen 13 September 2026 before any diagnostic native tests. This replaces the
cancelled developer-plus-tester preparation documented in
`reviews/2026-09-13-scc2000-runtime/PARTIAL_V2_CANCELLATION.md`. Its original
artifacts remain available but are not the accepted diagnostic inputs.

## Fixed population and extraction

Evaluate the 396 developer programs retained in Docker-failed SCC workflows
and the three completed developer responses in historically paused SCC
workflows. These 399 assignments are identified without inspecting native
outcomes. Repeat groups 101, 102 and 103 contain 140, 147 and 112 programs.
Six other incomplete selected assignments have no retained developer program.
No new model request, generated check, repair or candidate replacement occurs.

Use the original SCC `code_truncate` and `find_method_name` on the completed
developer turn's `final_text`. For each Docker-failed case, require exact equality
between the archived combined test input and the extracted developer code,
one newline, the extracted tester code, one newline and `check(method_name)`.
Its separate report field must be empty. Only the unchanged developer code
enters the benchmark evaluator. For the three paused cases the completed
developer response supplies the code; there is no invented tester response.

Preserve assignment, response, request and status snapshots. Validate the
selected identity, source hashes, frozen extraction functions, sample bytes
and allocation order before execution. The reference-control environment,
dataset and task input hashes are the original study's fixed inputs.

## Evaluation and interpretation

After the main native queue finishes successfully, run the three diagnostic
groups sequentially through the unchanged official observed-native evaluator
and frozen Docker image. Each container retains the original 2 CPU, 3 GB memory,
network-disabled configuration. Preserve native reports and execution metadata.
Do not rerun an already started diagnostic group or edit a supplied program.

Verify every report against its exact source programs and original controls.
Report pass, fail, timeout and unknown explicitly. An invalid evidence group
has unknown diagnostic quality; control-ineligible tasks retain raw statuses
but no quality standing. Preserve partial reports if the queue stops.

This is a descriptive audit of intermediate programs, not an SCC method arm
or a new inferential comparison. Every original infrastructure-failed or paused
SCC workflow remains unknown in the main analysis, irrespective of its retained
developer program's diagnostic outcome. Do not merge these results into the
primary SCC numerator or use them to change its bounds or tests.

The accepted prepared run is `scc-developer-diagnostic-20260913-v2`. Six actual
tests cover source extraction, altered assembly, analyst-only text, the complete
399-program source closure, sample tampering and quality imputation. The earlier
agent tests contained a hand-repeated assembly expression; they were replaced
by tests invoking the actual preparer and frozen extraction functions.
