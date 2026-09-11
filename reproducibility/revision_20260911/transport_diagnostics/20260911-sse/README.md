# SSE pause and recovery diagnostic

On 11 September 2026 the primary Luna dispatcher paused under its existing
eight-consecutive-failures rule. The retained session ended at Unix time
1789154144.1776378 with 12,078 completed candidates, 39 submitted-incomplete
assignments and 2,883 untouched assignments. The new session contributed eight
CLI failures reporting an SSE idle timeout and three partial candidates stopped
before their next stage. The diagnostic preserves error events and their source
hashes; full benchmark traces remain in the primary generation archive.

A separate task-free READY check used the same model, reasoning setting and
CLI version. It succeeded with 3,228 input tokens (2,816 cached), five output
tokens and a base-rate valuation of USD 0.00014472. This check is excluded from
the scientific assignment matrix and its resource ledger. It is not an API
payment and does not retry any benchmark task.

The unchanged launcher resumed session `1789154503730123700` with exactly
2,883 untouched assignments. A check against all retained failure IDs found
zero overlap. Earlier completed and interrupted attempts were preserved.
No model, protocol, timeout or dispatch concurrency setting changed.

This record documents a transport interruption and operational recovery;
it is not an explanation of model quality or proof of provider stability.
