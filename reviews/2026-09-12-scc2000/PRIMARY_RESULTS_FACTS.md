# Primary-results fact sheet (completed Luna archive)

This is an evidence index for later manuscript integration. It uses the completed primary archive only; no SCC-2000 continuation outcomes are used. Numerical values below are copied from JSON fields, with proportions shown as percentages only where labelled.

## Archive and manuscript locations

- Primary archive: `reproducibility/results/20260912_scale1000_luna_full/`.
- Main analysis: `analysis/summary.json`, schema `scale1000-task-cluster-analysis-v1`.
- Reproducibility description: archive `README.md`; source-family discussion: `source-family-sensitivity/summary.json`.
- Existing bilingual manuscript sections relevant to integration: `sections/heldout_quality_en.tex`, `sections/heldout_quality_ru.tex`, `sections/heldout_resource_contrasts_en.tex`, `sections/heldout_resource_contrasts_ru.tex`, `sections/heldout_sensitivity_en.tex`, `sections/heldout_sensitivity_ru.tex`, `sections/heldout_limitations_en.tex`, `sections/heldout_limitations_ru.tex`.

## Allocation, denominators, and marginal rates

Source: `analysis/summary.json`; fields `tasks`, `planned_candidates`, `planned_cli_turns`, `repeats`, `arms`, `by_arm`.

- 1,000 tasks, 15,000 planned candidate assignments, 27,000 planned CLI turns, five arms, and three repeat IDs (`101`, `102`, `103`).
- Every arm has 3,000 assigned and 3,000 recorded assignments. Generation-complete counts are: direct 2,996; single-roles 2,997; single-neutral 2,998; multi-roles 2,987; multi-neutral 2,983.
- Marginal observed quality rates (`by_arm.pass_rate_observed`) use the `known_repeat_outcomes` denominator, not `quality_observed_tasks`: direct 0.5459166384 (1,611 passes / 2,951 known repeat outcomes); single-roles 0.5355691057 (1,581 / 2,952); single-neutral 0.5431764307 (1,604 / 2,953); multi-roles 0.5146159075 (1,514 / 2,942); multi-neutral 0.5006807352 (1,471 / 2,938). The separate `quality_observed_tasks` fields are 981, 982, 983, 972, and 968 respectively and identify tasks with observed quality, not the marginal-rate denominator.
- Assignment-denominator bounds (`by_arm.assigned_rate_bounds`) are respectively direct [0.537, 0.5533333333], single-roles [0.527, 0.543], single-neutral [0.5346666667, 0.5503333333], multi-roles [0.5046666667, 0.524], and multi-neutral [0.4903333333, 0.511]. These are missingness bounds, not confidence intervals.

## Registered quality contrasts

Source: `analysis/summary.json`; fields under `contrasts`: `eligible_tasks`, `mean_difference`, `t_statistic`, `two_sided_p`, `bootstrap_95`, `holm_p`, `full_assignment_quality_difference_bounds`. The registered family is four contrasts (`inference.holm_family_size = 4`), with two-sided one-sample task-level tests after averaging three repeats within task.

| Contrast | Eligible tasks | Mean difference | 95% bootstrap interval | Two-sided p | Holm p | Full-assignment bounds |
|---|---:|---:|---|---:|---:|---|
| single roles − single neutral | 982 | -0.0074677529 | [-0.0196877122, 0.0044127631] | 0.2357490026 | 0.2357490026 | [-0.0233333333, 0.0083333333] |
| multi roles − multi neutral | 964 | 0.0134854772 | [0.0017289073, 0.0255878285] | 0.0299323451 | 0.0598646903 | [-0.0063333333, 0.0336666667] |
| multi neutral − single neutral | 968 | -0.0416666667 | [-0.0564738292, -0.0275482094] | 3.3505202e-08 | 1.3402081e-07 | [-0.06, -0.0236666667] |
| multi roles − single roles | 971 | -0.0212838998 | [-0.0343288706, -0.0082389289] | 0.0014829247 | 0.0044487740 | [-0.0383333333, -0.003] |

The archive explicitly records `bootstrap.resamples = 10000`, `bootstrap.seed = 20260909`; the amended SCC analysis has a separate seed contract. None of the four primary difference vectors is constant (`degenerate_difference_vector = false` for all four). The analysis records `inference.noninferiority = "not assessed"` and `inference.equivalence = "not assessed"`; therefore no non-inferiority decision is supported by this archive.

## Resource contrasts

Source: `analysis/summary.json`; fields under `resource_contrasts[contrast][metric]`: `eligible_tasks`, `mean_difference`, `ratio_of_task_mean_sums`, `ratio_bootstrap_95`, `bootstrap_95`. These are complete three-repeat resource pairs and are descriptive.

- Single-roles − single-neutral: 997 eligible tasks; tokens mean difference -58.0240722, ratio 0.9859546254, ratio interval [0.9834443049, 0.9883482082]; API-equivalent USD mean difference -0.0000581723, ratio 0.9392289711, ratio interval [0.9264711998, 0.9516339231]; uncached ratio 0.95494564999, interval [0.9467067902, 0.9629486351].
- Multi-roles − multi-neutral: 979 eligible tasks; tokens mean difference -130.8100102, ratio 0.9897094894, ratio interval [0.9880836758, 0.9912619259]; API-equivalent USD mean difference -0.0000571359, ratio 0.9776115435, ratio interval [0.9693956843, 0.9854592773]; uncached ratio 0.9860694181, interval [0.9810774879, 0.9908796516].
- Multi-neutral − single-neutral: 983 eligible tasks; tokens ratio 3.0782686103; API-equivalent USD ratio 2.6716924048; uncached ratio 2.7766738775.
- Multi-roles − single-roles: 986 eligible tasks; tokens ratio 3.0898109492; API-equivalent USD ratio 2.7802250893; uncached ratio 2.8665378714.

The archive reports the resource point and intervals in the fields above; it does not establish a quality-preservation or joint cost-and-quality claim.

## Missingness and limitations

Source: `analysis/summary.json`, field `missingness`; and `README.md`.

- `missingness.tasks = 1000`, `assignments = 15000`, `missing_rows = 0`, `quality_unknown_assignments = 264`, and `generation_incomplete_assignments = 39`.
- Quality unknowns are not failures; assignment bounds retain the full assignment denominator.
- Source-family sensitivity is in `source-family-sensitivity/summary.json`, fields `graphs`, `families`, `tasks`, `mean_task_difference`, `family_balanced_difference`, `ci95`, `size_effective_family_count`, and `largest_family_share`. It covers four source graphs and all four descriptive/registered factorial contrasts, uses 10,000 draws with seed 20260911, and is explicitly labelled supplementary with no new hypothesis family.
- The `union_070_code_exact` graph gives these source-family 95% intervals: single-roles − single-neutral [-0.0199459094, 0.0047282523] (982 tasks, 974 families); multi-roles − multi-neutral [0.0013816926, 0.02598752599] (964 tasks, 956 families); multi-neutral − single-neutral [-0.05687693899, -0.02721070866] (968 tasks, 960 families); multi-roles − single-roles [-0.03436426117, -0.00789564023] (971 tasks, 963 families). The corresponding fields are `graphs.union_070_code_exact.<contrast>.ci95`, `tasks`, and `families`.
- The archive README says the archive omits CLI binaries, Docker layers, and credentials; runtime metadata and source/image hashes are retained. It also states that subscription usage is not an invoice and that the valuation is a registered API-equivalent counterfactual.
- The source-audit summary (`source-task-audit/summary.json` or the corresponding retained source-family package) records that lexical/AST similarity is not semantic equivalence, singleton tasks may remain correlated, and training contamination is not identifiable.

## Evidence limits

The fact sheet records archive fields and does not infer values absent from those fields. In particular, exact manuscript wording for a non-inferiority decision, any SCC-2000 result, and any causal interpretation of source overlap remain unverified here.
