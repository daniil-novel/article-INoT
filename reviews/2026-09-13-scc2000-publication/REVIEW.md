# SCC-2000 publication audit (2026-09-13)

Scope: static audit of the uncommitted `reproducibility/scc2000/publish.py` and `reproducibility/tests/test_scc2000_publish.py`, compared with `reproducibility/revision_20260911/publish_scc.py`. No SCC native outputs, quality outputs, queue state, or model calls were inspected or changed.

## Findings

### Withdrawn after call-chain verification — frozen source hashes are checked indirectly

`publish()` iterates the keys in `generation/manifest.json` and copies the current repository files directly (`publish.py:250`), then copies the same current source tree into the archive (`publish.py:287-293`). It never computes the normalized SHA-256 values recorded in `manifest["source_files_sha256"]` (or in the continuation selection) and compares them with those files. `evidence_manifest.write()` then records the copied bytes as the archive’s new manifest, so the archive can be internally self-consistent while containing source files different from the frozen SCC protocol.

This is an actual acceptance path for any listed file that is not re-read by the replay. For example, a listed revision helper can be changed after the frozen generation; publication copies the changed helper and the archive evidence manifest happily hashes the changed bytes. If an attacker changes a replayed helper and its retained source-audit artifacts coherently, the current code has no frozen-manifest hash gate to stop that pair either. The older publisher has the same general copy pattern, but the SCC-2000 publisher’s explicit frozen-source/replay claim makes this omission material.

This earlier concern is withdrawn. Both publication and verification call `finish._verify_prefix`, which calls `scc_export._expected`; `_expected` requires `frozen == scc_controls.plan(inputs, gate)`. `scc_controls.plan` recomputes the normalized SHA-256 for every source listed in the frozen plan. Verification first enters `_archive_source_context`, binding `scc_controls.ROOT` and `REV` to the archive’s copied `sources/` tree, so the same check also covers a moved archive. A listed-source mutation therefore fails the frozen-plan equality check before acceptance. No P1 source-hash bypass was found.

### P2 — The tests do not exercise the self-contained archive path or frozen metadata identity

The test suite only tests helpers and a synthetic amended analysis. `test_small_status_gate_rejects_live_lock_and_touched_unselected` monkeypatches `continuation.load_selection` and `finish._verify_prefix` (`test_scc2000_publish.py:21-22`), removing the real freeze-v3 schema, amendment binding, and fixed-prefix checks from the only status-gate test. `test_count_only_fake_archive_cannot_pass` stops at a missing evidence manifest (`:48-50`); it never builds an archive and runs `python provenance/publish_scc.py --verify --archive .` from outside the repository. No test mutates a frozen control gate, original manifest, source file, native group, raw request/response, recovery tree, or original analysis evidence.

As a result, the suite can pass while a packaging regression breaks imports/path roots after the archive is moved, or while frozen metadata is copied from the wrong location. Minimal fix: add one fixture that creates a minimal complete archive layout from freeze-v3 metadata, invokes the verifier in a subprocess with the repository off `sys.path`, and asserts rejection after changing each of (a) source bytes, (b) amendment/selection metadata, and (c) a retained draw/summary file. Keep the existing synthetic tests for fast unit coverage.

### Withdrawn after call-chain verification — source-audit identity is replay-bound

The publisher accepts a caller-supplied `source_audit` path (`publish.py:211-218`), but this is not a demonstrated acceptance hole. `analyze._validate_metadata` requires the source-task-overlap schema, partitions, and selection binding; `_recompute_source_graph` verifies the retained evidence manifest and byte-for-byte compares the supplied audit against a fresh audit from the archived source/data closure. The audit’s `source_inputs` also checks the frozen whole-1140 dataset and subset definitions. An alternate directory with different evidence therefore fails.

No code fix is required from this audit; a same-schema alternate-audit negative test would still be useful regression coverage.

## Correction

The initial P1 claim about an unchecked source closure was based on reading the copy loop in isolation and was incorrect. The indirect plan-equality check described above already protects all frozen source hashes. The source-audit concern is likewise protected by exact replay. The remaining finding is a test coverage gap and should not be treated as a demonstrated publication acceptance defect.

## Positive checks

The new publisher does enforce several important SCC-2000-specific invariants: exactly 9,000 unique ledger cells (`publish.py:50-56`), selected-view byte/value equality (`:147-155`), selected prefix and paused original dispatcher (`:128-143`), nine native method/repeat groups with status agreement (`:59-75`), complete resource join (`:78-90`), amended summary plus draw-tree replay (`:158-172`), and source-graph tree replay (`:175-186`). It also retains the recovery tree, selected view, amended analysis, and all nine native groups during packaging (`:240-249`).

## Validation performed

Read-only inspection only. The repository’s active evaluation queue was left untouched, and no publisher or test was run because the parent task reported publisher tests already running and prohibited duplicate execution.

## Resume snapshot addendum (2026-09-13)

I audited `reproducibility/scc2000/resume_snapshot.py`, `reproducibility/tests/test_scc2000_resume_snapshot.py`, and `reviews/2026-09-13-scc2000-runtime/INCIDENT.md` before the administrative resume.

No invariant failure was found. `prepare()` reloads the original freeze-v3 selection through `load_selection`, requires an idle dispatcher and absent lock, rebuilds the current assignment inventory against the frozen selected-cell identities, requires every present assignment to be terminal, and calls the original strict `validate_recovery`. `extend_inventory()` verifies the original inventory digest, rejects duplicate/missing/out-of-prefix IDs, preserves every previous row byte-for-byte (including the eight pre-recovery rows), and appends only current selected-prefix rows. The scientific-selection comparison is unchanged before the administrative metadata is added. The four tests cover preservation and malformed ID sets.

The only limitation is test scope: the tests exercise `extend_inventory()` with synthetic rows, while the strongest checks live in `prepare()` and the original recovery verifier. A future regression test should construct a small real recovery fixture and assert that a changed historical file, a changed old status hash, or an unselected current assignment is rejected. This is coverage improvement rather than a demonstrated launch blocker.
