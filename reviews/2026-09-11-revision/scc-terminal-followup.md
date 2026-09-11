# SCC terminal-state follow-up audit

This follow-up covers the two terminal-state defects found in the pre-freeze
read-only audit. It is limited to generation-to-native evidence semantics.

`scc_export._row_for` now treats only `state == "completed"` as a candidate
eligible for native export. A partial `candidate.py` left beside an
infrastructure or transport failure remains inspectable evidence, but its row
has `observed_candidate=false`, `quality=null`, and the submitted terminal
state. A completed malformed one-call response remains observed with an empty
candidate, `format_extracted=false`, and `outcome_type="model_format_failure"`.

`scc_finish._records` now preserves the distinction between never-started
assignments (`generation_unavailable`) and submitted incomplete assignments
(for example `infrastructure_failure`). Neither receives a quality value.

Regression evidence: `reproducibility/tests/test_scc_native_pipeline.py`
passes 11/11 in `tmp/revision/replay-venv`, including incomplete-candidate
exclusion, transport-state preservation, and completed malformed-output
classification. No model calls, native evaluation, freeze, or commit were
performed.
