# Code review: primary metadata-neutral generation copy

Reviewed files:

- `reproducibility/revision_20260911/prepare_primary_metadata_copy.py`
- `reproducibility/tests/test_primary_metadata_copy.py`
- frozen command builder `reproducibility/codex_luna_subscription.py`
- frozen primary collector `reproducibility/scale1000_luna/collect.py`

This is a bounded source review. I did not run the native generation/evaluation
pipeline or inspect candidate quality outcomes.

## Findings

### [P1] The preparation gate does not prove that the source is a complete frozen primary archive

`prepare()` checks only `manifest.planned_candidates == 15000` and
`manifest.planned_cli_turns == 27000` (lines 137–147). It does not validate the
manifest cell set against `cells/`, validate the expected turn/session/failure
inventory, or apply the frozen collector's `validate_turn_inventory` and raw
reconstruction rules. A source with the frozen planning numbers but omitted
candidate/cell/turn files, or with a terminal status that is inconsistent with
those files, can therefore produce a successful derivative report. The report's
`original_evidence_unchanged` only means that the files found were copied
without changing the source; it does not mean all assigned candidates and
failures were present.

This is a demonstrated validation gap in the preparation tool, rather than a
claim that the current archive is incomplete. The coordinator's independent
original-versus-copy reconstruction must remain the acceptance gate; ideally the
preparer should either validate the frozen collector inventory or make the
report explicitly say that completeness was not checked.

### [P1] The report can claim a complete file-preserving copy while not proving all response/failure semantics

The copy loop transforms selected JSON files with generic `metadata()` and
copies all other files byte-for-byte (lines 161–189). It only checks JSON
structure for files in selected directories and only rebuilds hashes for
`result.json`/`empty_response_classification.json` (lines 193–210). It does not
cross-check candidate rows against raw turn acceptance, forwarded history,
failure records, or the collector's usage/event ledger. Consequently, malformed
or internally contradictory but parseable candidates/failures are preserved and
reported as copied; scientific response text may remain present while replay
semantics are still unverified. The existing `limits` text acknowledges this,
but `original_evidence_unchanged: true` and the file counts are easy to read as
a stronger integrity result than they establish.

This is a scope/reporting gap, not an accidental redaction bug. The report
should expose a stronger name such as `source_files_unchanged` or include an
explicit `replay_validation_required: true` field; final acceptance must use the
frozen collector reconstruction.

### [P2] Runtime path residual scanning is deliberately narrower than the copy's metadata transformation

The final scan searches only the exact paths collected from the runtime prefix
and three provenance fields (lines 214–228). Generic absolute paths discovered
later by `metadata()` are added to `transform.paths`, but `original_runtime_paths`
is captured once in `__init__` (line 59), so those dynamically discovered paths
are not included in the residual scan. Any path-bearing diagnostic or metadata
field that is not one of the three recorded provenance paths can remain in the
derivative without appearing in `residual_recorded_runtime_paths`.

This is consistent with the stated limitation that the scan is not a whole
package anonymity certification, but it means the field is not a complete
residual-path report. A whole-package scan/review is required before publication.

## Test coverage gaps

The tests cover the pure transform helpers and command rejection, but do not
exercise `prepare()` with a representative archive. In particular, they do not
assert preservation of failure files and counters through a copy, absence of
source mutation after hash rebuilding, output manifest mapping/counts, or
rejection of an archive with frozen planning numbers but missing cells/turns.
They also do not test a valid event containing a `thread_id` alongside escaped
Unicode response text; `events()` reserializes such a line (lines 120–125), so
the response string should be compared semantically while raw-byte preservation
is expected only for lines without a rewritten thread ID.

## What is sound in the reviewed scope

- Source and destination overlap/overwrite are rejected before output creation.
- Directory traversal rejects links/reparse points and non-regular evidence
  files.
- The command is accepted only when it exactly matches the frozen builder, and
  the derived command is checked against that same builder.
- Prompt files, cell `final_text`/`solution`, usage objects, and resource values
  are intentionally excluded from generic string rewriting; malformed event
  fragments are retained byte-for-byte.
- Per-turn hashes are rebuilt after command/event metadata changes, and source
  bytes, sizes, and mtimes are checked again before the report is written.

