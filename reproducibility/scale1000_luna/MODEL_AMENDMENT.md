# Model availability amendment, 8 September 2026

The original 1000-task plan and implementation were published at e7e6b5f.
Its launch created 187 turn folders: 180 retain explicit provider rejections
of GPT-5.4 mini with ChatGPT authentication, and seven were interrupted when
the dispatcher was stopped. No candidate response or usage completion was
obtained. Unknown usage is not reported as zero. The entire failed attempt
is retained under results/20260908_scale1000_mini_unavailable and is never
relabelled as Luna evidence. All 15000 original assignment states are retained.

Official Codex documentation states that GPT-5.4 mini is retired for ChatGPT
sign-in and recommends GPT-5.6 Luna as its replacement:
https://learn.chatgpt.com/docs/models. Luna appears in the current account's
model catalog. Published prices are .20/.02/1.20 USD per million input,
cached-input and output tokens:
https://developers.openai.com/api/docs/models/gpt-5.6-luna.
Model choice was based on availability and price before any Luna benchmark
response. One task-free READY transport probe succeeded and is archived in
results/20260908_scale1000_luna_preflight. It used 3224 input and five output
tokens, valued separately at USD .0006508. It is not a benchmark observation.

This is a new model study, not a same-model replication of the mini results.
All 15000 assignments are generated afresh under Luna, including assignments
attempted in the rejected launch. Conditions, complete prompts, task selection,
three repeats, native evaluator and statistical contrasts remain unchanged.
The native controls-v3 gate retains 985 quality-eligible tasks among all 1000
assigned. No task is replaced. Historical source and evidence stay unchanged.

The revised dispatcher stops new submissions on unsupported/deprecated model
or model-metadata errors, after eight consecutive failed candidates, or on
invalid/unpriceable usage counters. A successful candidate resets the failure
counter. Nonzero cache-write counters require a separate accounting amendment;
their charge is never silently omitted. These are transport/accounting stop
rules, not answer selection. Resumptions within the Luna study submit only
untouched assignments. The failed mini attempt remains a separate study.

The Luna protocol, implementation hashes, fixed assignment manifest and this
amendment must be published before any Luna benchmark call. Medium reasoning,
CLI 0.153.4, eight workers, complete context and the 600-second per-turn deadline
are retained. The USD 285 known-valuation submission guard remains unchanged.
