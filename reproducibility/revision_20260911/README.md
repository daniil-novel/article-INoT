# Revision 20260911

## Subscription reserve: mandatory before further model work

The author requires at least **55% subscription remaining**. The separate
[operational guard and pause policy](SUBSCRIPTION_RESERVE.md) now applies to both
studies and subsequent reviewer/editing work. Confirm the live watcher and run
`python -m reproducibility.revision_20260911.subscription_guard check` before
starting or resuming generation. A nonzero result or the persistent pause file
forbids launch; do not bypass it through a reset or another model. Frozen study
sources and allocations remain unchanged. The existing heartbeat has the same
restriction. This rule supersedes the launch instructions below when paused.

## Manuscript policy from 11 September

The author requests standalone EN/RU articles: no commit identifiers, repository
URLs, internal archive paths, or raw-replay dependencies in the manuscript.
Put scientifically necessary inputs, selection rules, evaluator settings,
extraction, statistical rules and SCC transitions in the text or its own
appendices. Preserve exact executed prompts, numerical results, provenance and
immutable archives outside the paper. Do not promise raw-data replay from a PDF,
or access on request that the author has not committed to provide.
The [focused language and self-containment reviews](../../reviews/2026-09-11-standalone/DECISIONS.md)
are distinct from the final five scientific critics, who remain pending until
both large studies are complete. The author confirmed no external funding and
no competing interests; both declarations are already in the articles.

The historical diagnostic below reuses the frozen heldout-200 archive without new model calls. The separate SCC comparison adds a prospective protocol and real generation/evaluation tools; it does not change the frozen factorial study.

## New SCC comparison

Read [scc_protocol.md](scc_protocol.md) for the 1,000-task, three-method,
three-repeat contract. The [nine-assignment development archive](../results/20260911_scc_comparison_dev9/README.md)
contains the completed feasibility gate. The main comparison must pass the
frozen manifest check before its first call:

```text
python -m reproducibility.revision_20260911.scc_controls check --inputs reproducibility/scale1000/inputs-v1 --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --manifest reproducibility/revision_20260911/scc_manifest.json
python -m reproducibility.revision_20260911.start_scc_study
```

Run from the repository root in an environment containing both the publication
requirements and `reproducibility/external_baselines/requirements.txt`.
The launcher refuses to start until factorial generation has ended; after SCC
generation it runs native evaluation and the registered analysis. It preserves
submitted attempts and pauses on quota or evidence failures. It never spends
a quota-reset credit or switches to a paid API automatically. Model calls and
native evaluation are real work; these launch commands are not offline replay.

## Publication and complete offline replay

Publication follows completion of generation, all native groups, the registered
analysis, and the source-family sensitivity commands in
[task_dependence/README.md](../task_dependence/README.md). The publishers refuse
to produce a successful archive while these stages are incomplete.

After publication and the full replay below, `plot_quality_effects.py` can render
the registered quality-contrast family directly from either completed archive:

```text
python -m reproducibility.revision_20260911.plot_quality_effects --archive PATH_TO_COMPLETED_ARCHIVE --output NEW_FIGURE_DIRECTORY
```

The separate figure directory receives EN/RU PDF and PNG, exact chart values in
CSV, and input/output hashes with renderer versions. The renderer checks archive
bytes, terminal generation, and summary scope; it does not replace statistical
replay or recompute inference. Use `reproducibility/requirements-publication.txt`.
The plot preserves asymmetric marginal 95% task-bootstrap intervals, complete
paired-task counts, unavailable estimates, and Holm-adjusted p-values in the
original family. Missingness identification bounds and source-group sensitivity
remain separately reported quantities. No plot from either unfinished large
study has been produced; renderer tests use explicit software fixtures only.

For the factorial archive, the original `replay_verify.py` checks only the
primary means and counts without scientific Python dependencies. The added
`provenance/scale_replay.py` uses the retained frozen implementation to rebuild
every raw-response/native-report join, all assignment and usage records, and
the entire registered statistical summary. From a downloaded completed archive:

```text
python -m pip install -r requirements-publication.txt
python provenance/scale_replay.py --archive .
python source_family_replay.py
```

The publisher must successfully run full replay in a new interpreter from a
directory outside the checkout before returning success. The replay copies
preserve the frozen source bytes and separately verified Luna protocol;
imports from a local checkout are rejected. The source-family command performs
the separate supplementary calculations. Neither command calls a model or
executes benchmark programs. Both depend on complete retained native evidence.

Publication helpers and host dependency declarations are retained with their
own evidence hashes. They are distinct from the sources bound by the original
generation manifest. Tests of this packaging use explicitly artificial ledgers,
responses and native-report fixtures; they are not scientific observations.
The completed real archive still must pass the same replay after native testing.

## Supplementary pricing-scope audit

The completed-study publishers also generate `pricing_scope.json` and retain a
standalone `provenance/pricing_scope.py`. Main archive verification recomputes
this supplementary audit from every submitted turn directory. It distinguishes
missing files, unknown/rejected usage, unreported cache writes, and recorded
input totals above 272,000 tokens. Neither a known base-rate subtotal nor the
audit is a subscription invoice. CLI-turn totals do not identify every internal
HTTP inference; unresolved request-level surcharges are not guessed. The frozen
valuation, dispatch guard and statistical analyses remain unchanged.

From a downloaded completed archive:

```text
python provenance/pricing_scope.py --generation generation --verify pricing_scope.json
```

The separate `scc_dev9_pricing_scope.json` has been computed from the completed
real development archive: 18 valid usage records, maximum input 4,476 tokens,
and 18 explicit zero cache-write counters. It leaves that archive unchanged and
does not stand in for either main-study audit. From the repository root, replay:

```text
python -m reproducibility.revision_20260911.pricing_scope --generation reproducibility/results/20260911_scc_comparison_dev9/generation --verify reproducibility/revision_20260911/scc_dev9_pricing_scope.json
```

## Historical sensitivity diagnostic

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
