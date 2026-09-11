# Metadata-copy review decisions

One preparation critic, GPT-5.6 Luna medium, reviewed this bounded technical
change twice. These reports do not count toward the five final scientific
critics. Exact requests were saved before dispatch in REVIEW_REQUEST.md and
FOLLOWUP_REQUEST.md. Neither critic inspected candidate quality outcomes.

## Accepted changes

The [first review](CODE_REVIEW.md) identified gaps in the preparation gate and
reporting, not damage to the experiment. The new terminal inventory check ties
the frozen assignment set to completed candidate files, submitted turns, failure
identities, the result index, final session and terminal counts. It preserves
interrupted assignments without requiring a failure JSON that the original
process never wrote. Frozen reconstruction remains necessary to validate each
prompt, forwarded response, accepted result, command and usage counter.

The new verifier runs the archived frozen source in a separate interpreter and
working directory, compares all raw candidate and usage rows, and separately
compares failure details. Only the failure record's session identifier may
differ. A change to a diagnostic is rejected for explicit follow-up.

Preparation v2 labels source-file preservation and replay requirements explicitly
and scans both initial runtime paths and metadata paths discovered during the
transform. The copy report groups counts by record category, avoiding thousands
of individual assignment identifiers in console output.

## Scope and validation

Eighteen focused tests passed. They include missing completed/interrupted records,
inconsistent result indexes, failure identity, preserved Unicode event text,
protected responses/counters and rejected scientific command changes.

The actual private copy was produced by v1, before this follow-up. Its exact
preparation code and v1 report remain with the copy. It is not retroactively
described as a v2 product; its residual-path scan covers initial runtime paths
only. The new verifier was used as the separate acceptance gate for that
existing copy. Its completed [machine report](../../submission/aamas2027/preparation/primary_metadata_raw_replay.json)
records equality of all 15,000 reconstructed assignment rows and 26,968 submitted
turn resource rows. All 176,821 derivative files matched the new manifest; the
original source inventory matched the preparation snapshot. The 14,961 completed
candidates, 39 submitted incomplete assignments, zero untouched assignments and
31 retained failure records matched the terminal inventory. All failure details
matched after removing only the session field. The worker loaded the frozen
source outside the checkout and exited successfully. This establishes raw
generation equivalence, not native quality or final statistical equivalence.

The [follow-up review](FOLLOWUP_REVIEW.md) found no additional demonstrated defect
within this generation-only scope. Its two limits remain explicit: structural
inventory is not raw reconstruction, and failure checks implement the current
flat JSON schema. Future sidecars would be rejected by the gate and would need
an explicit extension. This is not a full anonymous supplement, native evaluation
or statistical replay. SCC, native outputs, pricing/source-family sidecars,
clean extraction and final anonymity review remain separate checks.
