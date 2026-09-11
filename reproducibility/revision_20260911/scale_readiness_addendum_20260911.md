# Scale1000 Luna readiness addendum (2026-09-11)

The Docker engine prerequisite was rechecked after the initial readiness audit. The exact image ID reported for `bcb-scale1000:v2` is:

`sha256:afeb8d78b76f6a7b1fbf427d78a55bd35dbfcf58387711b47f8a8ba00e16b580`

This matches `image_id` in `reproducibility/runs/scale1000-v1/controls-v3/heldout200_control_gate.json`. The gate also records the pinned vendor source tree hash `9cbdc69ea1e61fe7bf32ad5ef7720cfb3116eb838497676c9593eed990dc0bd0`. Docker availability removes the earlier environment blocker, subject to the unchanged generation completion and finish-stage checks in `scale_readiness.md`.

The publisher implementation was added at `reproducibility/revision_20260911/publish_scale.py`. It is deliberately refusal-first: it never runs generation or native evaluation, refuses an active/nonterminal generation archive, refuses any existing output directory, checks all 15,000 candidate records and submitted-turn ledger coverage, requires successful finish exit records, checks every retained turn has `status.json`, and records frozen input/runtime/source hashes before creating a new dated archive. It excludes CLI/package binaries and runtime authentication material while retaining full raw traces, source copies, controls, inputs, licenses, relevant tests, and an offline verifier.

No prior observations, frozen helper, manuscript, or generation archive was rewritten by this addendum.
