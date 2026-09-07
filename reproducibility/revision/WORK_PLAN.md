# Scientific revision, 8 September 2026

Audience: author and journal reviewers. Scope: replace the confounded architectural claim with a falsifiable, compression-free study; retain historical evidence without relabelling it as new. Deliverables: English and Russian LaTeX/PDF, executable experiment and evaluation interface, source audit, reproducibility instructions, frequent scoped commits, GitHub update.

Assumptions: the user authorizes repository edits/publication and up to USD 300 total OpenRouter spending. No model generation can run while the existing key has zero remaining allowance. Use inexpensive GPT-5.3-Codex-Spark/high CLI workers for bounded implementation, with coordinator review. Their work is development, never experimental observations.

Primary sources: original INoT paper; official Agentless and SWE-agent repositories; BigCodeBench dataset and evaluator; official SWE-bench evaluator and dataset cards; model provider API metadata; immutable local historical results. Planning API is unavailable in this session, so this file is the explicit plan.

1. **Completed:** inspect manuscript, historical artifacts, local research source, runtime and key status; preserve pre-existing untracked research_program_2026-09-08.md.
2. **Completed for this revision:** primary-source audit, prospective estimands, sampling, budget and failure rules; generator, official-format export/collection and analysis implemented. Final confirmatory freeze awaits development calibration.
3. **Software checks completed; empirical execution blocked:** 26 synthetic-fixture unit tests passed. Official BigCodeBench data downloaded and 40/1100 split verified. Docker default context is live, but the candidate evaluator image has 9.27 GB compressed layers and exceeds the approximately 8.6 GB free on C: before unpacking. Official controls and native baselines remain unexecuted. The existing key remains valid with USD 0 remaining; USD 300 is author authorization, not available API allowance.
4. **Completed:** both manuscripts rewritten, historical arithmetic and rerun counts audited, PDFs built and selected pages visually inspected. No new model or official benchmark outcome is claimed.
5. **Completed publication:** six scoped revision commits through `cbe2b27` were fast-forwarded and pushed to GitHub `main`; the repository About description was updated and read back successfully. The validation record identifies tested artifacts and the remaining experimental gates. This publication-status note is a subsequent documentation commit.

Runtime evidence: 32 GiB host RAM, 8.32 GB Docker VM memory; C: approximately 8.6 GB free, E: approximately 114 GB free. Docker context default is available; desktop-linux is not. No key value is stored in this record. Existing user research_program_2026-09-08.md remains untouched and excluded from commits.
