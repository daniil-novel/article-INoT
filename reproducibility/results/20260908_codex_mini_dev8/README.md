# Complete Codex development evidence, 8 September 2026

Requested model: **gpt-5.4-mini**, medium reasoning. The replacement uses official Codex CLI 0.153.4 via ChatGPT login. Official standard API list rates are 0.75/0.075/4.50 USD per million input/cached-input/output tokens; these values are counterfactual valuations, not subscription invoices.

- [Completed matrix](attempt2/): 40 candidates, 72 fresh CLI turns, 387125 tokens, USD 0.7417401. [Audited results](attempt2/pilot_summary.json).
- [Rejected first attempt](attempt1-rejected/): 21 submitted turns, 12 complete candidates; all usage retained, USD 0.2493285. Planning-tool activity invalidated the attempt. No rows were reused in the replacement.
- [Every generation trace and valuation](all_attempts_ledger.json), including [excluded preflights](excluded-preflights/). Spark has no assigned tariff and is excluded from the benchmark comparison. Coding/research worker usage is outside this experiment ledger.
- [Exact exported solutions](predictions/), [upstream-core tests and controls](evaluations/), [native official instruct CLI reports](official-cli/), [native controls](official-cli-controls/).
- [Native/core reconciliation](attempt2/official_cli_crosscheck.json): 40/40 raw statuses agree; seven evaluable tasks plus one network-related missing task in every condition. Native no_gt=True disables internal reference caching; separately executed gold/incorrect controls supply eligibility.

All prompts, exposed intermediate/final text, stdout JSONL and stderr are stored unshortened. No secret/login files are included. Paths in argv/metadata identify the original local execution; they are not expected to exist on another machine. Byte preservation is enforced through .gitattributes. The audit accepts relocated archives while validating original argument paths against saved provenance.

The archive retains original metadata as written. Some native metadata/supplements used a PowerShell culture-dependent source-file ordering (e9c97246...). The same unchanged source tree in ordinal UTF-8 path order hashes to 9cbdc69ea1e61fe7bf32ad5ef7720cfb3116eb838497676c9593eed990dc0bd0, matching the Linux core evaluator. The tracked launcher now uses ordinal ordering. This is a hash-ordering difference, not an unreported source change; the pinned tracked checkout was verified clean.

Task /1036 tests a chart title absent from the supplied prompt; /45 conflicts on names; /322 mocks specific APIs. These post-evaluation findings limit construct validity. No tasks or original scores were removed retrospectively. This is an eight-task development experiment, not a large confirmation study or a full official benchmark score. See the bilingual manuscript and ../../CODEX_GUIDE.md for reproduction and limitations.
