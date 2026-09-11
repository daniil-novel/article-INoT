# Pricing-scope audit: GPT-5.6 Luna long-context handling

Date: 2026-09-11  
Scope: read-only inspection of the Luna subscription transport, scale1000 collector/protocol, SCC dispatcher/analyzer/publishers, and the retained SCC development summaries. No model, evaluator, or live-quality job was run.

## Reference tariff

The [official GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) lists USD 0.20 per million input tokens, USD 0.02 per million cached input tokens, and USD 1.20 per million output tokens. It also states that a prompt with more than 272K input tokens receives 2x input and 1.5x output pricing for the full request, and that cache writes are billed at 1.25x the uncached input rate.

## Findings

The base rates are encoded in `reproducibility/codex_luna_subscription.py:21-25`, and `value_usage()` prices `(input - cached_input)` at the uncached input rate, cached input at the cached rate, and output at the output rate (`:115-118`). This is consistent with the standard-scope tariff and the repository's stated convention that cached and reasoning counters are subsets.

There is no implementation of the official long-context scope in the inspected pricing path. `value_usage()` has no input-token threshold or full-request multiplier. The same function is used by `scale1000_luna/collect.py:32-35,59-63,81-84` and by SCC accounting through `scc_dispatch.py:252-260,271-280`; the analyzers and publishers consume those saved valuations. A repository-wide search over the requested pricing/protocol/publisher files found no `272K` or equivalent long-context branch.

The only prompt-size protections are byte guards, not token-scope checks: the factorial prompt builder rejects UTF-8 input above 65,536 bytes (`codex_luna_subscription.py:78-83`), and the SCC transport rejects serialized conversations above the same byte guard (`external_baselines/scc.py:58-66`). Neither guard computes provider input tokens or applies the >272K price rule. The scale protocol records the 65,536-byte guard (`scale1000_luna/PROTOCOL.md:35-40`) but does not add a pricing-scope rule.

Cache-write handling is conservative but incomplete as tariff support. `parse_events()` rejects nonzero `cache_write_input_tokens` (`codex_luna_subscription.py:99-106`); the scale collector and SCC dispatcher independently reject the same counter (`scale1000_luna/collect.py:22-35`; `scc_dispatch.py:195-217`). This prevents an accepted valuation from silently treating cache writes as ordinary uncached input, but it does not implement the documented 1.25x cache-write tariff. The SCC protocol records this as a stop condition (`scc_protocol.md:135-140`).

The publishers verify ledger coverage, hashes, native joins, and replay equality, but do not independently validate pricing scope. `publish_scale.py:163-176` checks that the turn ledger covers submitted turns, then `:179-195` replays the frozen collector/summary. `publish_scc.py:79-91,107-117` checks the candidate/resource joins and strict analysis replay. These checks can establish that the stored valuation is reproducible under frozen code; they cannot establish that it used the current tariff's long-context multipliers.

The retained development summaries do not exercise the missing branch. In `results/20260909_scc_dev3/summary.json`, the maximum reported input counter is 16,200 and cached input is 0 (`:6-43`). In `results/20260911_scc_comparison_dev9/summary.json`, the maximum reported input counter is 16,186 and the maximum cached-input counter is 2,816. Both are far below 272K. These are development feasibility summaries only; they provide no evidence about a long-context request or about the unobserved 1,000-task runs.

## Bounded supplementary publication check

Before publication of any completed scale or SCC archive, add a small offline, sidecar audit over the retained per-turn usage ledger (`turn_usage.json` for scale; `resource_usage.jsonl` plus raw turn usage for SCC). Do not modify the frozen runner, protocol, or saved valuation. For every submitted turn with known usage:

1. Validate nonnegative integer `input_tokens`, `cached_input_tokens`, and `output_tokens`, with cached input no greater than input; retain unknown and rejected turns as unknown rather than imputing them.
2. Flag every turn with `input_tokens > 272000`. For those turns, recompute a parallel `long_context_api_equivalent_usd` using 2x the input rate and 1.5x the output rate over the full request, while applying the cache component according to the provider tariff and recording the exact treatment of cached tokens.
3. Flag every nonzero cache-write counter. If present, compute a separate tariff-corrected valuation using 1.25x the uncached input rate, or mark the corrected amount unavailable if the counter's semantic decomposition is not retained.
4. Emit counts, maximum input tokens, maximum cached input tokens, flagged turn IDs, the standard frozen valuation, and the tariff-corrected sensitivity as a sidecar JSON/Markdown artifact. Require zero long-context/cache-write flags for a “standard-scope only” publication claim; otherwise qualify the resource statement and report the corrected sensitivity.

The check should be run against the final retained ledger and raw event streams, not against model text or quality outcomes. For the currently retained dev3/dev9 summaries, the bounded result is simply “no observed >272K input counter and no cache-write counter reported”; it should not be generalized to the prospective full studies. This is a publication-scope audit, not a reason to relaunch or alter frozen data collection.

## Verdict

The repository correctly records the standard Luna rates and rejects unpriced cache writes, but it does not check or price the documented >272K long-context scope. The supplementary offline ledger audit above is required before describing any final resource valuation as tariff-complete. The current dev3/dev9 development summaries remain within standard input scope on their reported counters, with no observed long-context case.
