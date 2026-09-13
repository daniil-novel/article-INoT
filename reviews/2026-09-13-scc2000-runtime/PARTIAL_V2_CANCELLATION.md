# Cancellation of the unexecuted partial-program diagnostic

13 September 2026. This correction supersedes the developer-source claim in
PARTIAL_ROOT_CORRECTIONS.md and the v2 preparation protocol. Earlier reports
and artifacts are retained, including their incorrect interpretation.

The coordinator inspected the actual frozen upstream Session.run_session and
an archived generated-test input. The `code` field passed to docker_execute
contains the developer program, the extracted tester function, and an appended
`check(function_name)` invocation. Its `report` field is empty. It is therefore
an execution payload, not the developer-only candidate claimed in v2.

The nine passing v2 software tests did not establish this semantic distinction.
No diagnostic native outcomes had been produced. Queue PID 16476 was verified
as `reproducibility.scc2000.queue_partial` in
`waiting_for_main_native_queue`, then terminated before any native evaluation.
The cancellation record is retained in its queue directory. The main SCC
queue PID 22852 and all original study evidence were left unchanged.

The corrected diagnostic will extract `turns/001/result.json.final_text` using
the original `code_truncate` function and validate `find_method_name`. For each
of the 396 Docker-failed workflows it must additionally reconstruct the exact
stored combined execution payload from the developer response and tester
response, proving the separation without editing program text. Three paused
SCC workflows also retain completed developer responses. The new diagnostic
therefore has 399 programs, frozen before any diagnostic outcomes are observed.

All 397 infrastructure-failed and eight historically paused primary SCC
assignments remain incomplete and unknown in the main comparison. A successful
partial developer program cannot complete its interrupted SCC workflow. The
six remaining incomplete assignments have no retained developer program.

The v2 candidate files, setup, tests and preflight are rejected as evidence for
developer-only evaluation. They must not be launched or advertised as an
accepted diagnostic. The new preparation and its source-level checks require
an independent record before execution.
