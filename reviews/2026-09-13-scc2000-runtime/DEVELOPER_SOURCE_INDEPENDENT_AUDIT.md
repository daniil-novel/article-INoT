# Independent developer-source audit

Date: 2026-09-13  
Scope: read-only audit of `reproducibility/scc2000/developer_diagnostic.py`,
`queue_developer_diagnostic.py`, the diagnostic protocol, and the frozen
`reproducibility/runs/scc-developer-diagnostic-20260913-v2/setup.json`.

## Result

The retained source closure is consistent with the stated diagnostic scope:
399 unique assignments are represented as 396 Docker infrastructure-failure
records and 3 paused developer-turn records. Replicate counts are 140, 147,
and 112 (101/102/103). All records have `native_outcome: unknown`, and the
prepared samples contain the extracted developer program only. The 396 Docker
cases are checked against the frozen `code_truncate`/`find_method_name`
functions and exact developer + tester + `check(method)` assembly with an
empty report field. The three paused cases have no invented tester response.

The live queue binding is coherent: PID 17060 is running
`queue_developer_diagnostic`, bound to PID 22852, whose command line is the
authorized `queue_finish_parallel`; both processes have the repository as
working directory. The diagnostic queue status is still
`waiting_for_main_queue`, so no native diagnostic result is available yet.

The specified test command passed: **6 passed in 11.12s**.

## Validation gaps

1. `validate_setup()` checks `native_executed is False` but does not validate
   the separate `original_partial_diagnostic_v2_executed` field, despite that
   field being recorded in setup and the protocol requiring the earlier
   partial diagnostic to be cancelled/unaccepted. A tampered setup could set
   this metadata to `true` while still passing source and sample validation.
   This is provenance metadata only; it does not permit primary SCC
   imputation, because `native_outcome` and `primary_scc_quality` remain
   unknown.

2. `validate_setup()` verifies the cell’s recorded `method` and the extracted
   source hash, but never asserts that the extracted method name equals the
   record/cell method. The exact Docker assembly is built with the extracted
   method, so this cannot change the submitted developer code, but it leaves a
   metadata-to-source mismatch undetected if a method field is altered in a
   frozen record.

## Primary SCC scope

No source or queue defect was found that broadens the diagnostic into the
primary SCC analysis. Diagnostic outcomes, when eventually produced, must
remain descriptive: original infrastructure-failed and paused workflows stay
unknown in the primary analysis and must not alter its numerator, bounds, or
tests.
