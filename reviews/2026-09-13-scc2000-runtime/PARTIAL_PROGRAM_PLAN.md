# Partial SCC program plan

The incident records 396 SCC infrastructure failures caused by the Docker
daemon path, while final SCC workflows remain incomplete. Retained completed
developer responses are therefore suitable for a separately labelled
diagnostic inventory when present. The new read-only extractor scans the
retained run tree, verifies exactly 396 selected SCC container failures against
the frozen selection manifest, and copies the exact `code` field from the
latest generated-test input before failure. It preserves source/input hashes
and marks every extracted artifact with `native_outcome: unassigned`.

The separate diagnostic should use the existing official BigCodeBench native
evaluator (`run_observed_native`) on each exact recovered developer program,
with the frozen task identity and environment. It must preserve raw logs and
keep all results outside the primary ledger. A native result is a partial
program diagnostic only; it cannot complete an SCC workflow or support SCC
inference.

The retained run tree is `reproducibility/runs/scc1000-luna-v1/generation/assignments`.
The validated inventory contains exactly 396 selected SCC container failures
and 396 recoverable developer programs. A bounded check recomputed a copied
program hash from its source `generated_tests/000/input.json` and confirmed
that native outcomes remain unassigned. No native checks were run during this
plan. An earlier zero-count report is withdrawn: it scanned the wrong recovery
path and schema and did not represent the retained 5,043-cell run.
