# Preparing the AI-method-assistance disclosure

Status: preparation record, 12 September 2026. This is not the final anonymous
disclosure or evidence that the conference requirement has already been met.

The [AAMAS author instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/instructions/)
require details of AI assistance in forming hypotheses or methods, including
experimental design: the prompt, tool and version must be provided in the paper
or supplement. Assistance in this study extended to design and statistical
planning, as the revised EN/RU declarations now state.

## Evidence recovered so far

The retained coordinator-session metadata identifies OpenAI Codex, a recorded
CLI/runtime version of 0.153.4, and the model identifier `gpt-6-astra`, with
`high` and `xhigh` settings across the inspected turn contexts. These identify
recorded configurations, not immutable model weights or an independently
verified backend snapshot. Do not present the CLI version as the desktop-app
version.

The retained records for 29 descendant sessions now confirm the recorded child
configuration: `gpt-5.6-luna`, `medium`, and CLI/runtime 0.153.4. All 172 inspected
child turn-context entries agree. This is stronger evidence than a requested
configuration, but it still does not independently verify backend weights.
The root contains 30 spawn requests; one was rejected because the concurrent
agent limit had been reached. It must not be counted as a thirtieth executed
critic. Session counts are not counts of independent scientific reviews.

A local inventory preserves visible user inputs and records of delegation requests,
together with their source positions, timestamps and a checksum of the inspected
conversation prefix. The initial description of this inventory did not
distinguish readable user inputs from opaque stored delegation payloads.
The latter do not provide recoverable verbatim prompt text in the inspected
records. Child user-message records contain environment announcements rather
than the original methodological task instructions. Preserve this limitation;
do not present encoded payloads or reconstructed summaries as exact prompts.

The inventories deliberately exclude internal reasoning, system and developer
instructions, tool outputs and execution code. They are private working records
excluded from Git and must not be inserted into the anonymous ZIP. The separate
read-only metadata check of the failed spawn establishes only that it was
rejected; it is not part of the disclosed prompt corpus.

A [draft of ten selected original author inputs](preparation/AI_METHOD_INPUTS_DRAFT.md)
now retains the original Russian text with English summaries. Two occurrences
of the manuscript-hosting URL have been replaced explicitly. A private ledger
preserves the original and edited input hashes and exact source locations.
The draft is not a complete interaction history, the final supplement or proof
of conference compliance. It omits repetitive, administrative and editorial
inputs, attached documents, other context and unavailable delegated prompt text.
The input about 1,000 independent units remains a quotation of the author's
request; independence is not inferred from that wording.

The experimental GPT-5.4 mini and GPT-5.6 Luna generation settings belong in the
experimental methods. They are distinct from the models assisting the author.
The exact experimental prompts already in the article do not, by themselves,
disclose the prompts used to develop the study.

## Work required before packaging

1. Refresh the inventory after the completed research and final reviews. Its
   present coverage includes retained root inputs and descendant metadata from
   8–12 September; do not call it a complete history of the original article
   or a complete readable record of all child-agent inputs.
2. Identify the actual inputs that led to hypotheses, interventions, statistical
   rules and methodological revisions. Separate human requests from automatic
   continuation messages and factual retrieval. Include relevant delegated
   methodological-review instructions and identify inherited manuscript context.
3. Prepare a compact tool/version/settings table supported by retained records.
   Label unavailable versions or provenance gaps explicitly rather than guessing.
4. Retain the original wording of relevant prompts. Remove author-identifying
   paths, names, account references and manuscript-hosting links only in a
   separate anonymous copy. Mark each such substitution and keep a private
   redaction ledger; do not describe edited prompts as wholly verbatim.
5. Explain which parts of the final method each input affected and how factual,
   software and statistical checks addressed the suggestions. Do not claim a
   human check that has not occurred, or imply AI reviews were conference reviews.
6. Place the anonymous disclosure with the technical supplement, check it for
   identifying content, and review it alongside the final main-paper declaration.

Unresolved provenance must remain visible in the final disclosure. Access to the
private preparation record is not an instruction to publish the conversation.
