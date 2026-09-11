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

The existing editorial reports identify GPT-5.6 Luna for the economical child
critics. The inspected delegation requests also specify `gpt-5.6-luna`; a
requested child configuration alone does not independently verify execution.
Check the corresponding child records when preparing the final tool table.

A local inventory preserves visible user inputs and delegation instructions,
together with their source positions, timestamps and a checksum of the inspected
conversation prefix. It deliberately excludes internal reasoning, system and
developer instructions, tool outputs and execution code. It is a private working
record and is excluded from Git. It contains identifying information and must
not be inserted into the anonymous ZIP.

The experimental GPT-5.4 mini and GPT-5.6 Luna generation settings belong in the
experimental methods. They are distinct from the models assisting the author.
The exact experimental prompts already in the article do not, by themselves,
disclose the prompts used to develop the study.

## Work required before packaging

1. Refresh the inventory after the completed research and final reviews. Its
   present coverage is limited to the retained root conversation; do not call it
   a complete history of the original article or all child-agent inputs.
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
