# Source-task dependence audit (frozen scale1000 inputs)

Date: 2026-09-11. This is a source-only audit. It does not read generated solutions, outcome-quality files, or model traces, and it does not change the frozen inputs.

## Scope and checked artifacts

Checked:

- `reproducibility/scale1000/inputs-v1/selection.json` (schema `scale1000-selection-v1`): `assigned_task_ids` (1,000), `prior_primary_task_ids` (200), `new_task_ids` (800), `replicate_ids` (`[101,102,103]`), `source_task_count` (1,140), `fresh_pool_size` (812), `excluded_task_ids` (128), `source_row_sha256` (1,000 entries), and the recorded `duplicate_exact_instruction_groups` (empty).
- `reproducibility/scale1000/inputs-v1/input/prepared.jsonl`: 1,000 rows. Every row has exactly the fields `task_id`, `prompt`, `context`, `benchmark`, and `metadata`; `benchmark=bigcodebench` and `metadata.source=bigcodebench` throughout the checked rows. All task IDs are unique and agree with `selection.json` order.
- `reproducibility/data/bigcodebench-v0.1.4.jsonl`: 1,140 source rows with fields `task_id`, `complete_prompt`, `instruct_prompt`, `canonical_solution`, `code_prompt`, `test`, `entry_point`, `doc_struct`, and `libs`.
- `reproducibility/data/bigcodebench-split/prepare_manifest.json`: source SHA-256 `f6704a124f4edcec9d12cc7912f41f3d4207f51b87f091d136e3436f7e25149f`, source count 1,140, and the 40-row dev split metadata.
- `reviews/2026-09-09-editorial/accepted-en-and-alignment.json`, `R1.md`, and `R3.md` for the existing limitation that repeated generations are not independent tasks and that the prior 200-task design represents at most 200 sampling units.

Frozen selection records the rule “all prior 200 plus first 800 unused IDs in the original frozen random reserved order; exclude dev40, segregation80 and examples /0-/7”. Its own `independence_note` says that unique IDs are task clusters, not proof of semantic independence or unseen training data. The input is therefore reproducible as a sampled ID set, but the ID set alone cannot establish semantic independence or decontamination.

## Exact duplicate checks

I checked the selected rows using Unicode NFKC, lower-casing, trimming, and collapsing whitespace. Results:

| field / comparison | unique values | duplicate groups | rows in groups |
|---|---:|---:|---:|
| `prompt` | 1,000 | 0 | 0 |
| `prompt` after removing the standard code-fence/starter boilerplate | 1,000 | 0 | 0 |
| `context` | 975 | 22 | 47 |

Thus, no selected task has an exact duplicate instruction under the checked normalizations. The 22 exact `context` groups are starter-code collisions, not evidence that the task requirements are identical. They are useful dependence candidates because multiple tasks share the same function signature/import scaffold. The complete list is:

`[960,959]`, `[824,818]`, `[1033,1030]`, `[513,506,511]`, `[156,1083]`, `[131,130]`, `[668,669]`, `[389,380]`, `[423,426]`, `[353,351]`, `[1079,567]`, `[673,675]`, `[251,519,523]`, `[296,110,112]`, `[1053,1052]`, `[599,598]`, `[212,209]`, `[512,507]`, `[136,304]`, `[119,142]`, `[968,920]`, and `[522,520]` (all IDs are `BigCodeBench/<id>`).

## Near-duplicate candidate screen

For a bounded, reproducible screen, I removed the standard instruction boilerplate and code fence, represented the remaining instruction text with word 1–2-gram TF-IDF, and computed pairwise cosine similarity over all 1,000 selected prompts. This is a lexical candidate screen, not semantic clone detection.

- At cosine >= 0.95, 0.90, and 0.85: one pair, `BigCodeBench/131`–`BigCodeBench/130` (0.986). It is already one of the identical-context groups.
- At cosine >= 0.80: three pairs / five task occurrences: `131`–`130` (0.986), `349`–`351` (0.821), and `353`–`351` (0.814). The latter two form a three-task lexical family around a sales-report task. They should be inspected as a sensitivity cluster if task-level results are later summarized.
- The next candidate pair is `423`–`426` at 0.743, below the proposed high-similarity flag. Other nearby pairs are similarly plausible topical families (for example, image thresholding, football-result data frames, and file reversal), but this screen does not justify treating them as duplicates.

If exact-context groups and the >=0.80 lexical links are collapsed only for a descriptive sensitivity analysis, the 1,000 rows become 974 connected components (975 after exact-context grouping; one additional link joins task 349 to the 351/353 component). This is an optional cluster sensitivity, not a claim that 974 independent semantic units exist. A conservative primary analysis can retain all pre-registered task IDs and report cluster-robust or task-cluster bootstrap sensitivity after outcomes exist.

## Interpretation and limits

The audit supports the narrow statement “the frozen sample has 1,000 unique BigCodeBench IDs and no exact duplicate selected instructions under the stated normalization.” It does not support “1,000 independent tasks.” Shared scaffolds, common libraries, repeated task families, and common benchmark construction can induce correlation without exact text duplication. The three model repetitions are repeated measurements on the same task IDs, not additional independent tasks.

The audit also does not test training-data contamination, canonical-solution overlap, test overlap, repository provenance, or semantic equivalence. In particular, the local source contains `canonical_solution`, `test`, and `libs`, but these were not used to infer independence; generated solutions/outcomes were intentionally not read. The selection manifest's `duplicate_exact_instruction_groups: []` should therefore be described as an exact instruction check, not as a semantic deduplication guarantee.

For the paper, the defensible wording is to call the 1,000 IDs “task clusters” or “sampled benchmark tasks,” state that all three repeats share each task, and optionally report the 974-component lexical sensitivity as exploratory. Do not convert the 974 number into an effective sample size or use it to claim independence without an outcome-level correlation model.

## Primary external references

- BigCodeBench paper (primary): Zhuo et al., *BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions*, arXiv: https://arxiv.org/abs/2406.15877. The paper describes 1,140 fine-grained tasks, diverse libraries/domains, executable tests, and the Complete/Instruct task variants.
- BigCodeBench official repository and release notes (primary): https://github.com/bigcode-project/bigcodebench and https://github.com/bigcode-project/bigcodebench/releases. The repository documents the full/instruct splits, selective task evaluation, and versioned task-data maintenance; release notes show that benchmark task text/tests can be revised across versions.
- BigCodeBench ICLR 2025 paper PDF (primary): https://proceedings.iclr.cc/paper_files/paper/2025/file/a6a90bcc2aa470c3871b2d39a67d26e8-Paper-Conference.pdf. The paper discusses task construction and reports a low likelihood of description contamination; that is benchmark-level evidence and does not certify this experiment's model snapshot or semantic independence.
- For duplicate/dependence framing, the audit follows the standard distinction between exact duplicates and near-duplicate/clone candidates; the relevant primary code-duplication evidence is Lopes et al., “The adverse effects of code duplication in machine learning models of code,” ACM SIGPLAN 2019: https://doi.org/10.1145/3359591.3359735. This reference motivates treating lexical similarity as a dependency risk, not as a proof of equal tasks.

## Bottom-line evidence statement

The frozen 1,000-task source sample is reproducible and instruction-unique under exact normalized matching. It contains 22 shared-context groups (47 rows) and three high lexical-similarity candidate pairs at the stated threshold, consistent with the manifest's warning that task IDs are clusters rather than proven independent semantic units. The strongest paper claim is therefore cluster-aware task sampling with transparent duplicate screening, plus an optional outcome-level cluster sensitivity—not semantic independence.
