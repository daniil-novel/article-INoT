# Codex subscription amendment, 8 September 2026

Status: development pilot; this amends the execution channel before benchmark generation. The user requested subscription execution with transparent token accounting and rejected Spark as the study model because a standard API price is unavailable. Spark arithmetic canaries are software preflight only and are excluded from scientific outcomes.

## Model and valuation

Use **gpt-5.4-mini, medium reasoning**, through a ChatGPT-authenticated Codex CLI. OpenAI describes this as a coding-capable mini model. This is an economical coding choice, not a claim that no cheaper GPT exists: GPT-5.4 nano and GPT-5.6 Luna have lower prices but target the nano/cost-sensitive tier. Their code quality is not established by their price. A model change after this pilot must be recorded before confirmation.

Published standard API list rates, accessed 8 September 2026: input USD 0.75/M, cached input USD 0.075/M, output USD 4.50/M. Sources: https://developers.openai.com/api/docs/pricing and https://developers.openai.com/api/docs/models/gpt-5.4-mini . The documented API snapshot is gpt-5.4-mini-2026-03-17; CLI uses the requested alias, and the returned CLI stream does not independently establish the served weight snapshot.

From the actual `turn.completed.usage`, let I=input_tokens, C=cached_input_tokens, O=output_tokens. Compute:

`API-equivalent USD = ((I-C)*0.75 + C*0.075 + O*4.50)/1e6`.

Cached input is part of I. Reasoning output is part of O; do not add either subset twice. Retain reasoning_output_tokens separately, with missing values marked unavailable. Also report a no-cache sensitivity using `(I*0.75 + O*4.50)/1e6`. These are counterfactual list-price valuations of observed CLI usage, **not charged dollars, OpenRouter billing, or an allocation of the subscription fee**. No cost per solved task is reported before independent evaluation. Source for JSONL: https://developers.openai.com/codex/noninteractive .

## Explicit pilot matrix

Take the first eight IDs in the already seeded, random **development** permutation: BigCodeBench/325, /322, /1036, /1005, /361, /1087, /45, /309. No confirmatory task is used. Preserve all eight regardless of difficulty, reference-control failures or model outcomes. One replicate per task, four factorial cells plus a direct solver: **40 assigned generations, 72 planned fresh CLI turns**. Randomize blocks and cell submission order with seed 20260908; allow two concurrent generations. These are pilot counts, not a large independent sample. No significance or non-inferiority conclusion is based on eight tasks.

The four cells remain one/three turns × neutral/role-labelled plan/implement/review stages. The direct solver receives the same task and context without prescribed stages. Each CLI turn starts a fresh ephemeral thread. Multi-turn cells forward the complete task/context and all previous exposed outputs. No text is compressed or truncated. A 65,536 UTF-8-byte guard rejects overlong payloads before submission. A very high compaction threshold is configured; compaction, retry/error events, unexpected tools or incomplete usage invalidate that run as infrastructure/treatment failure, never success.

The CLI is not a drop-in replacement for the OpenRouter design. It does not expose a verified sampling seed, temperature or a matched hard completion limit in the inspected interface. Replicate IDs are not provider seeds. The export's legacy `seed` field carries the replicate ID only. All cells use medium reasoning and native stopping; total completion allowance is **not matched**. Therefore the pilot estimates this implemented Codex protocol, not the original fixed-output-budget estimand. Full CLI input usage includes harness overhead. A CLI turn count is not an independently verified count of all internal backend requests.

## Runtime and evidence

Codex CLI 0.144.1 is pinned by the execution record. Use an empty working directory, replacement fixed instructions, ignore user configuration and project documents, disable shell, web, apps, plugins, browser and multi-agent tools, and use a read-only sandbox. Force ChatGPT login and remove explicit API-key environment variables from the child process. A named authenticated OpenAI provider selects HTTPS with zero configured HTTP/stream retries; the built-in provider cannot be overridden in this version. Do not reuse the rejected built-in-provider configuration.

Save exact user prompts, instruction file, argv, CLI version, full stdout JSONL, full stderr, raw usage counters, exposed intermediate/final text, latency and SHA-256 values before analysis. A blocked turn is retained, not silently retried. CLI traces do not expose the complete raw backend HTTP request or undisclosed reasoning content; do not describe them as such. Subscription limits remain applicable and no extra credits or resets are purchased/consumed.

Official BigCodeBench core and original tests may be exercised in a separately isolated, documented development environment with gold and deliberately wrong controls. Such a narrower environment is labelled an upstream-core pilot, not the full official release evaluator. All environment failures remain missing. SWE-bench and native INoT/Agentless/SWE-agent comparisons remain outstanding. Confirmation cannot start until the evaluator, final model/configuration, feasible scale and analysis plan are frozen.
