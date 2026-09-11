# Pricing-scope audit: coordinator decisions

The [original technical review](pricing-scope-audit.md) and the same agent's
[implementation follow-up](pricing-scope-implementation.md) are retained
separately. The follow-up is implementation work, not another independent
scientific vote.

The absence of a long-input scope check was confirmed. The base formula itself
matches the registered Luna coefficients. The README had presented only mini
rates under a general model-accounting heading; `ce8414d` separates the models
and adds the Luna formula and its source to both manuscripts. The diagnostic
SSE recovery probe is documented separately and excluded from the benchmark.

The original suggestion to apply long-context multipliers directly to CLI-turn
totals is not adopted as an exact tariff correction. Those totals do not expose
each internal HTTP inference. The added sidecar flags unresolved scope and
withholds a tariff-corrected amount. It preserves the registered base valuation.

After review of the first implementation, the coordinator required:

- relocation-safe output and exact saved-report recomputation;
- enumeration of submitted directories even when their event file is missing;
- disjoint unknown and rejected categories;
- explicit separation of unreported cache-write counters from measured zero;
- retention of known subtotals while withholding a complete observed-scope claim;
- mandatory recomputation in both large-study archive verifiers, with the
  standalone helper and report included in their evidence manifests.

These changes are implemented. The coordinator also added rejection of
non-object JSON events and type-sensitive comparison of JSON values. A record
above the input threshold is a scope flag, not evidence of a known surcharge;
an unreported cache-write field is not evidence of its absence. The audit never
estimates a subscription invoice or reads quality outcomes.

Validation: 30 targeted tests passed across pricing, both publishers and the
full primary portable replay. Artificial fixtures cover threshold boundaries,
missing/invalid counters, missing event files, SCC directory layout, relocation,
and tampering with the pricing report after its byte inventory is refreshed.
The existing raw/native and statistical replay checks remain mandatory.

The sidecar was also run on the real, completed SCC dev9 generation archive:
all 18 submitted turns expose valid usage and explicit zero cache-write counts;
their maximum input counter is 4,476, with no threshold flag. The base subtotal
reproduces USD 0.02301176 up to floating-point representation. The original
review's 16,186 figure came from an aggregated development summary; it is not
the maximum per-turn input count. The per-turn result is retained separately in
`reproducibility/revision_20260911/scc_dev9_pricing_scope.json` and does not alter
the original dev9 archive. It proves no property of the unfinished main runs.

The updated PDFs contain 43 English and 47 Russian pages. Changed formula and
reference pages were visually inspected, with no out-of-page words or replacement
characters in the whole-document bounding-box check. Exact PDF hashes are in
`reproducibility/revision_20260911/pdf_audit.json`.

The large experiments are still running. This technical closure does not assert
that their complete resource ledgers or scientific conclusions already exist.
