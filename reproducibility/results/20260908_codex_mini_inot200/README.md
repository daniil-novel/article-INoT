# Exploratory INoT algorithm replication: 200 assigned tasks

This is an independently worded PromptCode adaptation of Sun and Zeng's INoT, not native author code or an author-validated replication. It uses GPT-5.4 mini medium through official Codex CLI 0.153.4, the same 200 held-out BigCodeBench task IDs, full supplied context, one fresh call per task, no tools or compression, and the same native evaluator/control gate as the primary matrix.

**Observed result: 96/192 evaluable programs pass original tests (50%).** There are 199 complete generations out of 200 assignments, no final-format failures, seven control-ineligible tasks, and one missing generation (`BigCodeBench/779`). All-assignment missingness bounds are 48–52%, not a confidence interval.

The initial batch completed 62 of its 63 submitted calls before one 180-second timeout. A separately frozen administrative continuation submitted only the 137 untouched assignments and completed all 137. The timeout was never retried. The continuation manifest was published in commit `2ab5821` before dispatch. All original and continuation bytes are retained under their original directory basenames.

| Generation batch | Submitted calls | Complete answers | Known tokens | API-equivalent USD | Unknown-usage calls |
|---|---:|---:|---:|---:|---:|
| Original | 63 | 62 | 240,312 | 0.34433145 | 1 |
| Never-submitted continuation | 137 | 137 | 527,367 | 0.71452890 | 0 |
| Combined | 200 | 199 | 767,679 | 1.05886035 | 1 |

The no-cache valuation is USD 1.33326675. Completed-program means are 3,857.68 tokens, USD 0.00532091 with cache discounts, and USD 0.00669983 without them. Known token components are 565,677 input (including 406,528 cached input) and 202,002 output (including 150,174 reported reasoning tokens). Subsets are not added twice. Unknown usage is not zero; these are observed API-list-price equivalents, not subscription invoices or research/evaluation compute costs.

The wrapper models two virtual debaters and at most ten conceptual rounds. It follows the paper prose's agreement-or-cap stopping condition, discloses the listing ambiguity, uses an explicit latest-A fallback at the cap, and omits image augmentation for text tasks. The trace does not attest to hidden agents or execution of a fixed number of internal rounds. The complete instruction and frozen source are included.

`generation/` contains all prompts, uncompressed answers, raw JSONL events, exact CLI arguments, terminal statuses, original runtime/protocol/source records and partial-call evidence. `predictions/` contains the 199 observed programs. `evaluation/` contains the unchanged pinned native BigCodeBench CLI reports; every report row was joined to its exact program and task. `analysis/` contains the reconciled rows, gate-derived analysis statuses, native audits and separate submitted-turn ledgers. `diagnostics/` retains an initial launcher preflight that rejected a 199-row export before any container was launched, plus the successful native process log. No program was regenerated to fix that launcher check.

The common 200-task inputs and all original control attempts are in [the held-out evidence directory](../20260908_codex_mini_heldout200/README.md), with exact dataset bytes in `controls/attempt2/input/` and final controls in `controls/attempt3/`. The final gate makes 193 tasks eligible. The executed image identity is sha256:76d84f87bb98a10e358e19d58b84c2eed3dc24c1e8431582ae1dd9874faa7667; the native metadata and control gate retain its source and package provenance.

Use [SCALE_GUIDE.md](../../SCALE_GUIDE.md) for audit/evaluator reconstruction. `EVIDENCE_MANIFEST.json` inventories exact retained file bytes. Do not normalize archived line endings. Preserve both generation directory basenames when invoking the original INoT auditor, which writes its inventory with the archive name. Reference task/test content retains its upstream license; this independent adaptation cites the source paper and does not redistribute a claimed author implementation.

Cross-batch comparisons with the primary direct and single-role conditions are exploratory. They retain dispatch-time and cache-state limitations and do not enter the four predeclared primary quality tests.
