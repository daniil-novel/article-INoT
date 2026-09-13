# Partial SCC candidate diagnostic

The 396 SCC cells that stopped with a Docker infrastructure failure may retain
the last completed developer response even though their workflow did not
finish. `reproducibility/scc2000/partial_candidate_audit.py` provides a
read-only inventory for these artifacts. It scans the selected SCC cells in the
retained run tree, requires exactly 396 container failures, and takes the exact
`code` field from the latest `generated_tests/*/input.json` preceding failure.
This avoids accidentally selecting a tester response from a model turn. The
program bytes, generated-test report, input hash, and program hash are retained.
The audit also checks selected cell, status, and source-file hashes against
`execution-resume-v1/current_inventory.json`; existing artifacts are immutable
and mismatches fail closed. No code is executed, no native outcome is assigned, and the primary ledger is
not modified.

Run the audit against `reproducibility/runs/scc1000-luna-v1/generation/assignments`
with `reproducibility/scc2000/freeze-v3/selection_manifest.json` and output
directed to `tmp/revision/scc-partial-audit`. The output records
the assignment identity, task, method, repeat, terminal reason, source result,
program hash, and `native_outcome: unassigned`.
`code` is reported explicitly; it is never reconstructed from prose or an incomplete
turn. A pre-existing `candidate.py` is not substituted for a developer turn.

If the separate diagnostic is run, each recovered program should be passed to
the unchanged official BigCodeBench native evaluator (`reproducibility.heldout200.run_observed_native`) in
a fresh diagnostic output tree, with the frozen environment and task identity.
The result is a partial-program diagnostic, never a primary SCC quality
endpoint or workflow completion. Do not rerun the generated-test helper, add
records to the primary ledger, relabel infrastructure failure as a test
failure, or retry model calls.

Comparability is limited. A recovered developer program stopped before the
workflow's native benchmark evaluation and may have been produced after a
partial history; SCC's actual workflow also includes analyst/developer/tester
transitions and generated-test feedback. A container smoke check can establish
that the program is executable under the frozen helper, but it cannot recreate
the missing workflow state, certify the generated check's validity, or support
SCC--SR/SN inference. Unknown and incomplete resource counters remain unknown.
