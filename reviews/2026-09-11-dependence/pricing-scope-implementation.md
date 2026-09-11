# Pricing-scope audit implementation follow-up

Date: 2026-09-11

Added `reproducibility/revision_20260911/pricing_scope.py` and its fixture tests in `reproducibility/tests/test_pricing_scope.py`. The helper is an offline, deterministic sidecar audit over retained `events.jsonl` files and works with both scale-style `generation/turns/*` and SCC-style nested assignment turn directories.

It records a path-independent per-turn event SHA256, the three usage counters when valid, cache-write state (`not_reported`, `reported_zero`, `reported_nonzero`, or `reported_invalid`), standard base valuation, input-scope flag, and explicit invalid/unknown reasons. It enumerates only the known scale (`generation/turns/*`) and SCC (`generation/assignments/*/turns/*`) submitted-turn layouts, retaining missing `events.jsonl` directories as unknown evidence. Duplicate, malformed, or invalid-completion usage is rejected; an otherwise valid turn with no completion is unknown. A complete standard-scope valuation is withheld whenever usage is incomplete, any known turn lacks an explicit cache-write field, a nonzero cache-write counter is present, or an input counter exceeds 272,000, while the valid-turn base subtotal remains available.

The helper exposes `audit(generation)`, `write_sidecar(...)`, and exact `verify_saved(generation, sidecar)` recomputation. Its standalone mode supports mutually exclusive `--output` (refuses overwrite) and `--verify`. Output is relocation-safe and includes the explicit scope limitation that CLI-turn totals are not a per-inference HTTP ledger; no actual invoice or corrected long-prompt cost is inferred.

The sidecar deliberately emits no tariff-corrected long-context amount. A >272,000 counter is a request-level pricing-scope flag, and the retained CLI totals are not an HTTP inference ledger. The helper does not alter frozen dispatch, protocol, run data, or registered base valuations.
