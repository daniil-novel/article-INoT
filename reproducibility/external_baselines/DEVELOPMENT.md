# SCC author-code integration pilot

9 September 2026. Development work only; no external confirmatory claim.

Use the exact 13 upstream source/license files listed in
`vendor/scc_2024/SOURCE_MANIFEST.json`. The adapter invokes the original
`Session.run_session`, role implementations, prompts, extraction and history
updates. It replaces only the model-call boundary and moves the original
`unsafe_execute` into a network-disabled, non-root Docker container. Both raw
answers and upstream-extracted programs are retained. Do not alter upstream code
to improve success rates.

The historic tester asks for printed examples without assertions. Execution
stdout is swallowed; completion without exception can terminate SCC even when
the printed result is wrong. This is an internal stopping signal, never the
benchmark quality label. Original extraction and generated-test limitations
must be reported, not repaired silently.

The Codex adapter serializes the original role/content messages as JSON in one
fresh text-only turn per upstream call. It does not reproduce native API message
roles or the historical max_tokens/temperature/top_p controls. Those requested
upstream values are archived but are **not applied**. The actual runtime is Luna
medium, a 600-second deadline and a 65536-byte full-conversation guard, without
CLI tools or automatic retries. Therefore the correct label is author-code SCC
with a Codex subscription transport adaptation. No equality of original API
sampling conditions is claimed.

The integration pilot uses the first three IDs in the already exposed 40-task
development allocation, selected by order alone. One SCC run per task, at most
four model calls per run; stop on transport/provenance failure. There is no
outcome-based task replacement. These tasks are excluded from scale1000 and the
proposed external main comparison. All three candidates receive independent
native BigCodeBench evaluation and gold/incorrect controls in the final image.
No hidden tests or reference code are supplied to SCC or mounted in its generated
test container. Keep controls, final evaluation and generated tests distinct.

The pilot supplies the complete task context in the requirement but uses
`before_func=''` in the upstream executor: it expects a self-contained returned
program. Historical HumanEval's entry point separately supplied the source
preamble. This is an additional dataset adaptation, not a claim of exact
HumanEval input construction. Verify this mapping before freezing a main series.

After all three pilot generations finished, failure-status hardening added
structured initialization/container errors and cleanup records without changing
successful session behavior. The archived v1 runner remains byte-identical and
its supported source hash is explicitly checked during replay. No old pilot was
rerun or replaced as a consequence of its quality outcome.

Preserve every attempt; existing output folders cannot be reused. A failed pilot
may be followed by an explicitly versioned integration repair, retaining the old
attempt and documenting changes. Such development iterations do not enter any
confirmatory quality denominator or final power analysis.

Implementation acceptance checks exercise the original SCC session with
synthetic responses: early stopping, feedback repair, malformed code, propagated
transport failure, serialization and source hashes. Separate Docker smoke checks
verify success, assertion failure and swallowed printed values. These synthetic
checks are software validation, not empirical model results.

Install development dependencies `openai==1.109.1` and `tqdm==4.67.1` in an isolated
environment. The OpenAI package is imported by the original modules; the patched
call boundary does not create an API client. No API key or paid fallback is used.

Before any main external series: validate full evidence accounting, native task
joins, complete model failures, API-versus-CLI fidelity and cost projections;
freeze new implementation hashes and statistical rules. The current module is
a pilot runner and must not be used as a resumable main-series dispatcher.
