# Source-task dependence audit and supplementary inference

Defined on 11 September 2026 while the Luna factorial generation is running.
This is an additional analysis after the original registration, not an amendment
to its hypotheses or task allocation. Historical mini outcomes were already
known. The source audit reads no generated candidates, model outcomes or usage.
It cannot prove statistical independence or absence from model training data.

## Fixed source checks

Use the exact 1,140-row BigCodeBench source whose SHA-256 is recorded in the
frozen scale-1000 selection. Verify all 1,000 selected row hashes, the 200/800
partition and the source/model-input joins. Retain the remaining source tasks
for detecting connections to development and other excluded tasks; do not add
them to any generation or quality denominator.

Report exact instruction equality after whitespace normalization and exact
Python AST equality of the supplied reference program after removing only
leading docstrings. AST equality retains names, literals, imports and structure.
Parsing failures must be listed, never silently treated as unique tasks.

For instructions, remove only the final documented starter-code paragraph
beginning `You should write self-contained code starting with:`. Case-fold and
tokenize words with Python's Unicode `\w+`, then form sets of five consecutive
words. Compare exact set Jaccard similarity for every eligible pair. Report
thresholds 0.50, 0.70 and 0.90, all inclusive. Instructions with fewer than five
words retain exact-match checks and are listed as unavailable for this metric.

For reference code, tokenize the docstring-free program into non-keyword
identifiers and string/number literals. Preserve identifier spelling and literal
token spelling. A near-code edge requires at least 20 identifier occurrences
in each program, set Jaccard at least 0.80 and multiset Jaccard at least 0.70.
This is an explicit Python adaptation of the token-fingerprint approach in
Allamanis (2019), not a semantic clone oracle or a reproduction of its corpus
results. Record shorter programs and tokenization errors separately.

For each graph, form connected components over the full source and then
intersect them with the 1,000 allocated tasks. Connectivity is a conservative
grouping convention; similarity itself is not transitive. Retain every task,
including singletons. Report numbers and sizes of components, all retained
edges, exact-duplicate groups, old200/new800 connections and connections to
development, segregation80, examples and the other reserved tasks. The primary
supplementary family uses the union of prompt edges at 0.70, near-code edges,
and the two exact-match definitions. Also report the prompt-only 0.50/0.70/0.90
partitions without selecting a threshold by its inferential result.

## Supplementary analysis once outcomes are complete

Preserve each study's original estimand, complete-pair requirements, eligibility
gate, all assigned rows, missingness bounds, primary tests and multiplicity
family. Average the three repeated paired outcomes within each task first.
Only then group those task means using the source-derived components.

For each original quality contrast, report the usual mean over available tasks
with a 95% percentile pairs-cluster bootstrap interval: resample the observed
source components with replacement, keeping every available task in a sampled
component together. Each bootstrap mean is the sum of sampled task differences
divided by the sampled task count. Thus unequal family sizes do not change the
point estimand into a mean over families. Use 10,000 resamples and seed 20260911,
reporting the family count, largest family share, effective count
`(sum n_g)^2 / sum n_g^2`, bootstrap variance and the full retained draw vector.
Fewer than two contributing families give an unestimable interval. Degenerate
draw distributions must be flagged. No new significance test or non-inferiority
claim is introduced. A family-balanced mean may be reported separately as a
different descriptive estimand, not substituted for the original mean.

These sensitivity intervals condition on the graph and observed pairs. They
cannot correct unknown families, informative missingness, provider drift or
training contamination; few or highly unequal groups limit their reliability.
Failure to detect source overlap is not evidence of independent errors.

## Sources

- BigCodeBench, ICLR 2025: https://arxiv.org/html/2406.15877v4 — benchmark
  construction and diversity do not constitute a within-study independence test.
- Allamanis, 2019: https://arxiv.org/html/1812.06469 — token-based near-duplicate
  detection and the distinction between exact and near duplication, §3.
- MacKinnon, Nielsen and Webb, 2023: https://arxiv.org/html/2205.03285v1 —
  cluster inference, cluster-size imbalance and limitations of bootstrap methods.

Retrieved 11 September 2026. No model reruns or benchmark changes are part of
this audit. All findings are reported, including empty graphs and failures.
