# Method check: source-audit-v2 and family-sensitivity protocol

Date: 2026-09-11. Read-only follow-up to `source-audit.md`. I inspected `reproducibility/task_dependence/PROTOCOL.md`, `audit.py`, `sensitivity.py`, and the actual source-audit-v2 JSON/JSONL artifacts. I did not read model results, candidate records, outcome summaries, or generation traces, and I did not execute the supplementary outcome analysis.

## Audit artifact integrity

`source-audit-v2/summary.json` is internally consistent with the current source and frozen allocation:

- source count 1,140; assigned count 1,000;
- source SHA-256 matches `reproducibility/data/bigcodebench-v0.1.4.jsonl` (`f6704a124f4edcec9d12cc7912f41f3d4207f51b87f091d136e3436f7e25149f`);
- selection SHA-256 matches the frozen `scale1000/inputs-v1/selection.json`;
- recorded protocol and script hashes match the current `PROTOCOL.md` and `audit.py`;
- `model_outcomes_read=false`, zero reference parse errors, zero short instructions, and 37 short reference programs (<20 identifier occurrences);
- `fingerprints.jsonl` has 1,140 rows and `edges.jsonl` has 13 qualifying source edges. The supplementary union graph has 12 edges, as reported.

The source join checks in `audit.py` are appropriately strict: they verify the frozen source hash, every selected source-row byte hash, model-input hash/order, exact `instruct_prompt`/`code_prompt` joins, the 200/800 partition, and the development/segregation subset hashes. The starter paragraph occurs in all 1,140 source instructions, so the case-sensitive split used by `prompt_features` does not silently miss a row in this frozen source.

## Protocol/code correspondence

The implementation follows the stated protocol on the important points:

- exact instructions use whitespace-normalized full `instruct_prompt` text;
- prompt near-edges remove the documented final starter paragraph, case-fold, tokenize Unicode `\w+`, and compare sets of five-word shingles at inclusive 0.50/0.70/0.90 thresholds;
- reference programs are parsed from `code_prompt + canonical_solution`, leading docstrings are removed from module/function/class bodies, and AST hashes retain names, literals, imports, and structure;
- near-code edges require at least 20 identifier occurrences per task, set Jaccard >=0.80, and multiset Jaccard >=0.70;
- components are formed over all 1,140 source rows before intersecting with the 1,000 assigned rows;
- the defined supplementary graph is exactly the union of prompt-0.70, near-code, exact-instruction, and exact-AST edges;
- prompt-only 0.50/0.70/0.90 partitions are reported separately;
- no task is removed and the frozen confirmatory allocation is not changed.

One interpretive detail should remain explicit: `code_features` parses the supplied function scaffold plus canonical solution and removes leading docstrings in every traversed module/function/class scope. This is consistent with “leading docstrings” and produced no parse failures, but AST equality remains a strict structural fingerprint, not semantic equivalence.

## Actual v2 results

The defined `union_070_code_exact` graph has 12 source edges, 1,129 full-source components, 992 assigned-task components, seven assigned non-singleton components containing 15 assigned tasks, and largest assigned component size 3. Its component size histogram is 985 singletons, six pairs, and one triple. The corresponding prompt-only results are: 0.50 has 6 edges, 996 assigned components, seven assigned tasks in three non-singleton components; 0.70 has 3 edges and 999 assigned components; 0.90 has 1 edge and 1,000 assigned components.

The 12 union edges, with original source membership, are:

| edge | source membership | union basis |
|---|---|---|
| 1097–1099 | new800–new800 | near-code |
| 1120–1121 | new800–segregation80 | prompt 0.50/0.70/0.90, near-code |
| 130–131 | new800–new800 | prompt 0.50/0.70, near-code |
| 349–351 | new800–new800 | prompt 0.50, near-code |
| 349–353 | new800–new800 | near-code |
| 351–353 | new800–new800 | prompt 0.50, near-code |
| 369–622 | new800–new800 | near-code |
| 401–413 | new800–new800 | near-code |
| 423–426 | new800–new800 | near-code |
| 673–675 | new800–new800 | near-code |
| 814–826 | development–new800 | near-code |
| 894–895 | development–segregation80 | prompt 0.50/0.70 |

There are no union-graph edges involving an old200 task, an example task, or an “other reserved” task. The two cross-subset assigned connections are 826 to development task 814 and 1120 to segregation80 task 1121; 894–895 is a development/segregation edge with neither endpoint assigned. The 15 assigned tasks in non-singletons therefore should not be described as 15 independent task families: source components can include excluded tasks, and lexical/AST edges do not establish semantic or outcome dependence.

The exact groups are small and transparent: exact instruction has one full-source pair, 1120–1121, with no assigned pair; exact AST has three full-source pairs, 1120–1121, 130–131, and 814–826, of which only 130–131 is an assigned pair. This correctly distinguishes exact instruction duplication from exact reference-program structure.

## Sensitivity-code review

`family_bootstrap` preserves the original task-weighted estimand: it averages repeated paired outcomes within task first, then resamples source components and divides the sampled sum by the sampled task count. Unequal family sizes therefore do not become a family-balanced primary mean. It reports family count, largest family share, effective family count, variance, 10,000 draws, seed 20260911, and flags fewer than two families or degenerate draws. It does not add significance tests or non-inferiority claims.

The implementation also checks duplicate assignment keys, boolean/null quality values, control eligibility, complete frozen assignment matrices, assigned-ID coverage of every graph partition, and source-audit/selection identity. These are appropriate guards. The sensitivity routine is correctly outcome-consuming and remains gated on terminal generation and an existing evidence manifest; it was not run for this method check.

The protocol and code do not support claims that the graph makes tasks statistically independent, that the 992 components are an effective sample size, or that the intervals correct semantic dependence, informative missingness, provider drift, or training contamination. `source-audit-v2` itself correctly states these limitations. The graph is a conditional descriptive sensitivity grouping.

## Bibliography correction

The earlier `source-audit.md` incorrectly called the 2019 duplication paper “Lopes et al.” The cited arXiv work is authored by Miltiadis Allamanis: *The Adverse Effects of Code Duplication in Machine Learning Models of Code*, arXiv:1812.06469, https://arxiv.org/abs/1812.06469. The abstract mentions Lopes et al. (2017) as prior work; Lopes is not the author of the cited 2019 paper. The old report is preserved as requested; this follow-up is the corrected record.

The protocol’s other methodological reference, MacKinnon, Nielsen, and Webb, *Cluster-Robust Inference: A Guide to Empirical Practice*, arXiv:2205.03285, is correctly attributed: https://arxiv.org/abs/2205.03285.

## Recommended bounded wording

The defined 0.70-prompt/near-code/exact-match graph yields 992 assigned connected components from 1,000 unique BigCodeBench IDs, with 12 retained source edges and 15 assigned tasks in seven non-singleton components. This is a source-derived dependence sensitivity partition. It is not evidence that the remaining components are semantically independent, nor does it establish absence of training contamination or equal error processes. The primary analysis should retain the frozen task allocation; any family-bootstrap interval should be labeled supplementary and graph-conditional.
