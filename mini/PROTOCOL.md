# Held-out allocation fixed before any generation or quality inspection

8 September 2026. This extension addresses the distinction between 400 programs
and 40 independent development tasks. It follows the frozen development run,
without changing its prompts or recycling its responses.

## Selection and treatment

Take the first 200 IDs in the original seeded **random** reserved-task order,
after excluding the eight IDs `/0` through `/7` whose dataset-card snippets were
incidentally exposed (see `DATA_EXPOSURE_LOG.md`). This is a prefix of a frozen
random permutation, not the first 200 dataset rows or a difficulty-selected
sample. Do not replace tasks because a control fails or a test is disputed.
Freeze the exact IDs and source hashes before evaluator controls.

Use the unchanged subscription-v2 runner: GPT-5.4 mini, medium reasoning,
Codex CLI 0.153.4, full supplied context and full previous exposed outputs,
no tools, test feedback, retries, compression, provider seed or temperature
control, and native completion stopping. One new replicate label (4), five
existing conditions, gives **1,000 assigned candidates and 1,800 CLI turns**.
The label is not a random seed. The two development repeats remain separate.
There is no matched hard output allowance. Do not claim that a single held-out
generation estimates per-task sampling variance.

Use four disjoint index-modulo-four shards, two workers per shard, at most eight
CLI processes. Freeze the generation manifests after control eligibility is
known and before dispatch. If a shard fails or quota is exhausted, stop that
shard, allow active shards to finish, retain every submitted trace and cost,
and report the allocation as partial. No automatic quota credit, paid-API
fallback, replacement task, rerun or restart is authorized by this protocol.

## Evaluator controls

Run original reference and deliberately incorrect programs for all 200 tasks
through the unchanged pinned BigCodeBench CLI in `instruct full` mode. Use
separate offline, non-root, resource-limited containers. First try the exact
development image. Any dependency amendment must occur before model
generation, be reported with all previous control failures, and trigger fresh
controls on the complete allocation. Gold must pass and the incorrect control
must fail for a task to be quality-evaluable. Keep unavailable tasks in the
assignment denominator and retain original test outcomes as well as missing
analysis status. Never rewrite original tests or prompts to improve the score.

## Analysis and sample-size interpretation

Each task is one paired observation. Report all task-by-condition outcomes,
format failures, token components, API-equivalent valuation, no-cache
sensitivity, and assigned/evaluable denominators. Missingness ranges count all
unavailable assigned outcomes first as failures and then as successes; they
are not confidence intervals.

The four predeclared contrasts are roles minus neutral within each call
topology and three calls minus one within each label condition. Use complete
paired tasks for each contrast. For binary quality, report the paired mean
difference, a task-bootstrap percentile 95% interval (10,000 resamples, seed
20260908), both discordant counts, and the exact two-sided McNemar binomial
p-value with Holm adjustment across these four comparisons at familywise
alpha 0.05. Each two-sided null is a zero quality difference. Report an interval
for the quality interaction as descriptive. Direct-solver comparisons are
exploratory, with the same effect/interval reporting, without additional
confirmatory significance claims. Report paired resource mean differences,
ratios of means and task-bootstrap intervals; token and price effects are
descriptive, not separate families of significance tests.

With 200 evaluable independent tasks, a single-proportion worst-case normal
95% half-width is about 6.9 percentage points. This is precision planning,
not a claim of 80% power for a chosen paired effect. A paired difference has
variance determined by discordance; report its observed uncertainty. Although
149 zero-harm pairs would put an idealized one-sided exact upper harm bound
below 2%, that special calculation does not power a general two-point
non-inferiority test. **Do not claim non-inferiority from this allocation.**
Do not label the 1,000 candidates as 1,000 independent tasks.

The claim concerns these fixed prompts and this requested model alias on the
reserved sample. A held-out sample within a public benchmark does not rule out
training contamination, related-task dependence, evaluator-contract errors,
or drift in a provider alias. Native INoT and repository-agent baselines are
not silently represented by the four constructed conditions.

## Resource envelope

The eight-task pilot projects about USD 18.54 at published API list prices for
1,000 candidates, with substantial usage variance. This is a counterfactual
valuation, not subscription billing. All observed failed-attempt usage is
additional and must be reported. The latest observed account-wide weekly
usage was 60% consumed; this is not a guarantee that the allocation fits.
