# Revision 20260911 statistics

This directory contains a post-review, reproducible diagnostic based on the frozen heldout-200 archive. It does not edit the archive, protocol, manuscript, or review files, and it performs no model calls.

Run from the repository root:

```text
python reproducibility/revision_20260911/stats_batch_missingness.py
```

Outputs:

- `batch_missingness_results.json`: source hashes, assignment accounting, estimand definitions, and paired missingness identification bounds.
- `batch_arm_summary.csv`: assigned/observed/unavailable counts and observed pass rates by original/continuation batch and arm.
- `batch_paired_contrasts.csv`: within-batch complete-pair coverage, quality differences, descriptive task-cluster bootstrap intervals, and API-cost differences.
- `cross_batch_coverage.csv`: original–original, continuation–continuation, and cross-batch complete-pair counts by contrast.
- `REPORT_RU_EN.md`: compact Russian and English interpretation and proposed article wording.

The script recovers batch by continuation-manifest cell ID. `original` has 460 assigned cells and `continuation` has 540; 996 cells have retained candidate records and 4 are submitted-incomplete. Identification bounds are not confidence intervals. First-batch-only estimates are not treated as an unbiased counterfactual because task-arm coverage changes across batches.

Cost columns identify their denominators explicitly: the legacy cost field uses quality-complete pairs, while `resource_complete_pairs` uses all pairs with two observed resource endpoints. Cross-batch counts and batch sign differences are coverage diagnostics only; they do not identify provider drift or a causal batch effect.
