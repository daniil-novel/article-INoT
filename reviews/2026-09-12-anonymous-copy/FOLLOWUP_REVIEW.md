# Follow-up code review: primary metadata-copy verifier

Reviewed the updated preparation script, `verify_primary_metadata_copy.py`,
and `reproducibility/tests/test_primary_metadata_copy.py`. This review is
source-only and does not claim that the live raw replay has succeeded.

## Findings and bounded limits

### [P2] The terminal inventory gate is structural; raw turn validity still depends entirely on the collector replay

`validate_terminal_inventory()` verifies assignment membership, terminal
counts, accepted-turn presence for completed candidates, session linkage,
failure identity, and the `results.jsonl` index (lines 47–99). It deliberately
does not validate the contents of each turn folder, its raw event stream,
prompt forwarding, command, usage, or per-turn hashes. An archive can pass this
gate with a structurally present but malformed turn, and the same is true of a
copied archive. This is an explicit limit in the function's docstring and is
covered by the subsequent frozen `collector.reconstruct()` calls, so it is not
a demonstrated acceptance bypass when `verify()` completes. The final report
should continue to treat the inventory result as a prerequisite, never as raw
replay evidence.

### [P2] Failure-detail comparison is intentionally separate and does not cover arbitrary non-JSON failure sidecars

The verifier compares every original `failures/*.json` after removing only the
session field (lines 146–154). The terminal inventory gate rejects non-JSON
files directly under `failures/`, so this is complete for the current failure
directory contract. It does not inspect nested failure directories or sidecar
files, should that layout be introduced later. That is a bounded schema limit,
not a current bug; the generation-only report should retain the stated scope.

## Checks that are now sound

- The preparation path calls the terminal inventory gate before copying and
  records its counts in the v2 report.
- The verifier reconstructs both original and derivative in a subprocess whose
  imports are copied from the archive's recorded frozen source tree; it rejects
  modules resolved outside that tree.
- It compares every reconstructed candidate row and every usage-ledger row,
  then performs a separate failure-detail comparison.
- It independently verifies derivative file inventory/hashes, the original
  snapshot hash, frozen source hashes, protocol hash, and the derivative's
  terminal inventory.
- The v2 report uses `source_files_unchanged`,
  `residual_discovered_metadata_paths`, and
  `replay_validation_required`, which accurately avoid presenting preparation
  as scientific replay or whole-package anonymity certification.

## Focused-test coverage

The added tests cover the terminal count/index contract, interruption without a
failure JSON, failure identity, and the prior transform/command cases. They do
not replace the coordinator's actual raw replay: no test here exercises the
full 15,000-row frozen collector reconstruction or native/SCC outcomes, by
design.

I found no additional demonstrated correctness defect in the updated verifier
within the requested generation-only scope. The remaining acceptance condition
is the coordinator's independent raw replay result.

