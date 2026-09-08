# Exploratory INoT algorithm replication

This is a new exploratory treatment for the held-out 200-task sample. It does
not alter the frozen five-arm matrix, its manifest, or its allocation. No
verified executable implementation from the paper authors was identified for
this setup; the wrapper is an independent prompt-level replication.

The treatment uses the exact held-out task IDs and full task/context text. It
uses GPT-5.4 mini at medium reasoning through the audited Codex CLI transport,
one fresh CLI turn per task, a 180-second timeout, two workers, no retries,
and the existing final-output format. Every record is labelled
`arm=inot_algorithm_replication`; the shared CLI transport is an implementation
detail and this treatment is never an ordinary direct baseline.

The independently worded method description has at most 140 words and uses a
compact XML-like PromptCode wrapper around hybrid Python/natural-language
pseudocode. It models two virtual debaters, obtains initial answers, then
iterates arguments, mutual critique, rebuttal, adjustment, and agreement checks
for at most ten rounds. The code is conceptual LLM-read guidance, not host
execution. The stopping rule follows the paper prose, “agreement or ten rounds”;
Listing 3's `while` condition is recorded as ambiguous. If ten rounds finish
without agreement, this replication returns Agent A's latest answer; that is
an explicit additional convention because Listing 3 leaves `final_result`
undefined in that case. Image augmentation is omitted because these are text
tasks. The final output uses the existing `FINAL` instruction.

Fidelity source: Sun and Zeng, *Introspection of Thought Helps AI Agents*,
arXiv:2507.08664v1, Sections 3.1 and 3.3, Listings 1 and 3:
https://arxiv.org/abs/2507.08664v1

The archive records the protocol hash, implementation hash, task hash, CLI
version, complete prompts and outputs, usage, and treatment labels. The plan
requires the frozen selection, task bytes, and control-gate hashes, and is
intentionally not frozen or executed by this setup task. The 200 calls would
be a separate batch; wall time and cache state can therefore confound
comparisons with the exploratory direct treatment.
