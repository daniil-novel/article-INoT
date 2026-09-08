# Segregation-80 preparation protocol

This is a preparation-only extension. It freezes the next 80 IDs in the existing randomized confirmatory order after excluding the heldout-200 allocation, the development IDs and BigCodeBench/0--7. No task is selected by content and no model call is made here.

The extension has four single-call arms: role labels (`planner`, `implementer`, `reviewer`) crossed with explicit stage headings versus prose, and neutral labels (`stage 1`, `stage 2`, `stage 3`) crossed with the same two boundary forms. Every arm uses the same three operations, requested intermediate checkpoints, full supplied task/context, and one fenced Python output contract. The boundary factor is an observable prompt-structure intervention; it does not establish separate latent agents.

The primary family is the two role-versus-neutral exact two-sided McNemar contrasts, one within each boundary level, with Holm adjustment at familywise alpha 0.05. Boundary contrasts and the role-by-boundary interaction are descriptive. Task-level percentile bootstrap intervals use 10,000 resamples with analysis seed 20260908. No non-inferiority margin or composite quality--cost rule is used.

The paired unit is the task. Controls and the original native BigCodeBench evaluator are evaluator-only artifacts. Gold and deliberately incorrect controls must be completed before any generation, with no task replacement after a failed control. Native evaluation is post-generation and never feeds test results back to the model. All prompts, events, full responses, extracted programs, usage counters and native reports must be retained by the later runner.

This size is a precision-limited extension, not a fine-effect power study. With 80 paired tasks, a single proportion's worst-case normal 95% half-width is about 10.9 percentage points; paired McNemar precision depends on discordance. The series can reveal large role effects but cannot substantiate a two-point non-inferiority claim. Results must be reported as a protocol-specific prompt intervention under one model alias, CLI version and task sample.

Execution is frozen on 8 September 2026: GPT-5.4 mini, medium reasoning,
Codex CLI 0.153.4, ChatGPT subscription, fresh ephemeral text-only calls with
the same audited configuration as the primary study. Four concurrent calls;
one candidate per task/arm, 600 seconds per call, 65,536 UTF-8 input-byte guard.
No retry, output truncation, model tools, compression, sampling seed control or
test feedback. All 320 assignments remain in the denominator. A failed call
does not cancel other cells; authentication/quota failures stop after the current
four-cell wave. Generation also stops between waves at USD 25 known token
valuation. This is a planning bound, not a strict unknown-usage bound or invoice.
The official rates remain USD 0.75/0.075/4.50 per million input/cached-input/output
tokens. Cached tokens are part of input and reasoning tokens are part of output.
Interrupted usage is retained separately; unavailable usage is not zero.

The four treatments differ only in label substitutions and bracket/newline
versus colon/space formatting. They request the same internal operations and
suppress intermediate commentary in the final output. Internal compliance is
unobservable: this tests the causal effect of the specified instructions, not
verified internal role execution. The final analysis code and power sensitivity
grid are frozen before model generation. The grid sums exact McNemar rejection
probabilities over the random number of discordant pairs, using the conservative
first Holm threshold 0.025. There is no claim of 80% power for small effects.
