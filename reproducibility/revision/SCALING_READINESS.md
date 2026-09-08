# BigCodeBench development scaling readiness

This review covers the frozen 40-task development permutation, the Codex subscription protocol, the upstream evaluator, and the remaining 32 development tasks. It does not inspect model answers and it does not authorize or perform generation.

## Decision

The initial assessment below identified prerequisite work. That work is now complete: the third control attempt uses the unchanged official CLI in `instruct full` mode, with 39 passing gold controls and 40 failing negative controls; `/1005` remains unavailable offline. Exact task/solution records and environment hashes were independently reconciled before generation. Earlier attempts remain diagnostic records. The two-repeat, 400-candidate extension is frozen in [DEV40_PROTOCOL.md](DEV40_PROTOCOL.md), including its amended maximum of eight concurrent CLI processes, and has started. The eight-task run remains a pilot.

The selected development permutation has 40 tasks from the seeded split (`seed=20260908`): the first eight already used, followed by:

`1029, 894, 858, 678, 451, 734, 374, 855, 573, 964, 303, 533, 155, 681, 1110, 421, 839, 745, 107, 356, 615, 640, 814, 757, 464, 892, 468, 549, 529, 1022, 173, 544`.

The split contains 40 development tasks and 1,100 held-out confirmatory tasks. The 40-task stage is still development calibration; it must not be presented as benchmark performance or as evidence over the confirmatory set.

## Evaluator readiness gates

The current upstream-core image covers the common numerical, tabular, plotting, Excel, HTTP, and standard-library imports used by these tasks. Static inspection of the remaining tasks found two additional runtime requirements that are not present in the recorded CLI image:

- `BigCodeBench/734` imports `nltk` and calls `nltk.download('punkt')` and `nltk.download('averaged_perceptron_tagger')` at module import. Network is disabled during evaluation, so the pinned NLTK package and the exact required resource files must be pre-bundled in the image or in an explicit read-only mount, with hashes recorded. The task cannot be considered evaluable until its gold control passes without network access.
- `BigCodeBench/964` imports `docx` and constructs DOCX files in its tests. Add a pinned `python-docx` dependency and verify the gold control in the final image.

`BigCodeBench/421` uses `requests`, but its tests patch the HTTP call. `BigCodeBench/745` uses `subprocess`, but its tests patch the call. These are still controls to run because they exercise evaluator isolation. The remaining tasks use combinations of pandas, NumPy, Matplotlib/Seaborn, scikit-learn, openpyxl, filesystem fixtures, randomness, and standard-library code; the current image already records the first group of those dependencies.

Before any model generation, build one final image and run all 40 gold and deliberately incorrect controls with the same local upstream CLI path, `calibrated=False`, network disabled, and the exact selected IDs. Require gold `pass` and negative `fail` or `timeout` for each task. Preserve every control record, including failures. The existing eight-task controls already show why this gate matters: `/1005` has a gold failure, so its model results must remain in the assigned denominator but be ineligible for confirmatory quality analysis.

This 40-task control gate has now been executed in `reproducibility/runs/dev40-controls-v3/`. The first attempt (`dev40-controls-v1`) was retained as incomplete because `/839` exposed a missing `Faker` dependency; v2 fixed that dependency but used the wrong upstream CLI split label and is retained as a diagnostic. Fresh v3 controls use `instruct full`, all 40 negative controls failed as intended, and 39 gold controls passed. `/1005` remains ineligible because its original tests reach an external URL while network is deliberately disabled. The other 39 tasks are control-eligible. The authoritative v3 gate is `dev40_control_gate.json`, with SHA-256 `bbe6aa2b707bae20982bbf662641b51515bacfd44a562f4e36d9e3e6afafcdf7`. The final image is `sha256:5697a0648acccd249a9027f48af42a42a4a8e27b6cdb626906142a480683978a`; NLTK package-resource hashes and the complete package freeze are retained beside both reports.

The v2 launcher was found to pass `dev` as the upstream CLI split argument. That was a mode-labeling error: the 40 tasks are the development partition, while the upstream CLI must receive `instruct`. The old v1/v2 archives remain preserved as diagnostics. Fresh v3 controls in `reproducibility/runs/dev40-controls-v3/` use `instruct full`, and the validator now rejects any metadata whose argv is not frozen to `instruct full`. The v3 gate has the same substantive result—40 negative failures, 39 gold passes, and `/1005` ineligible—and is the only control gate usable for the next stage. A generic 40-ID prediction launcher is available at `reproducibility/scale_env/run_dev40_predictions.ps1`; it rejects missing or duplicate IDs before execution and preserves missing report rows as missing.

The fixed eight-task `bcb_pilot_evaluator.py` is not a scale evaluator. It hardcodes eight IDs and the first-eight prepared split. A scale run therefore needs a frozen 40-ID evaluator or an equivalent aggregation layer before generation; it must retain the same control-derived eligibility rule, null unknown/evaluator-error outcomes, and report denominator, evaluable-only rate, pessimistic lower bound, and optimistic upper bound separately.

The upstream evaluator has a 240-second timeout floor, despite smaller requested limits. A hanging task can therefore consume roughly 241–242 seconds. The launcher should retain a run-level wall deadline and classify an externally killed or incomplete archive as infrastructure-missing data, never as a failure or success. The official CLI result files and the raw stdout/stderr, image ID, source tree hash, dependency freeze, dataset hash, and exact argv must be retained per arm and replicate.

## Recommended frozen series

Use the 40 development tasks, all five existing arms (`direct`, `single_neutral`, `single_roles`, `multi_neutral`, `multi_roles`), and **two paired replicate IDs**. This is 400 assigned generations and 720 fresh CLI turns: nine turns per task and replicate because each multi arm has three turns. Pair all arms within task and replicate, randomize submission order with the existing manifest seed, and run at most two concurrent generations.

Two replicates are a practical first scale stage because the CLI does not expose a verified sampling seed, temperature control, or matched hard completion allowance. Replicate IDs are labels for repeated subscription calls, not controlled provider seeds. A third replicate can be added only after the two-replicate archive is complete, controls remain valid, and subscription quota, wall time, and the predeclared budget still permit it. Do not splice a partial archive into a later matrix.

The eight-task v2 token record implies approximately USD 0.09 API-equivalent list-price valuation per task across all five arms, with multi-turn arms accounting for most of it. That projects to roughly USD 3.7 for one 40-task replicate and USD 7.4 for two, before uncertainty from task difficulty and native stopping. These are counterfactual list-price valuations, not subscription charges. The observed v2 wall times imply about 1.5–2 hours per 40-task replicate with two workers, excluding evaluator control time and infrastructure stalls.

The next objective checkpoint is a complete 40-task matrix with the fixed random development permutation, with no selection of a lighter subset based on task appearance. Before a larger held-out series, freeze an explicit allocation from the already randomized 1,100-task confirmatory list, a power calculation and stopping rules. A 200-task × 3-replicate × 5-arm matrix would be 3,000 generations and 5,400 CLI turns. The measured v2 turn time projects about 47 hours sequentially or 23.5 hours at two workers, and the measured token valuation projects about USD 55.63. These are planning estimates, not quota or completion guarantees; the current subscription weekly window is already materially used, so the run should be checkpointed by immutable manifests and stopped cleanly on quota or infrastructure exhaustion.

## Analysis freeze

Freeze the 40-task manifest, model (`gpt-5.4-mini`), medium reasoning, CLI version, instructions, five arms, two replicate IDs, worker limit, timeout, image/dependency hashes, evaluator arguments, control gate, and missing-data rules before opening any model output from the scale stage. Report raw task-level statuses and paired arm contrasts. Keep the all-40 assignment denominator even when controls or model evaluations are ineligible; do not call an evaluable-only rate a benchmark pass rate.

This stage estimates the implemented Codex subscription protocol. It does not identify the original API protocol with fixed sampling controls, and it does not support a claim about the 1,100-task confirmatory split. A confirmatory launch should wait until the 40-task control/evaluator gate passes and the resulting analysis code and budget are frozen.
