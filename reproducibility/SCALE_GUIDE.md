# Compression-free experiment: audit and reproduction

The development block contains 40 task clusters, two labelled repeats and 400 actual programs. The reserved allocation contains 200 new task clusters and 1,000 assigned programs. The INoT algorithm replication is a separate 200-program allocation. Candidate counts are never independent-task counts. The reserved and INoT execution amendments retain every first attempt and only continue assignments with no submitted turn.

## What can be checked without new model calls

The published subscription analyses use Python 3.11 with the actual host versions in `requirements-publication.txt`; `revision/analysis_runtime.json` records their provenance. The older `requirements-revision.txt` belongs to the initial alternative API/preparation workflow and is not the environment used for the published subscription result tables. Benchmark containers retain their own independent package freezes.

```powershell
python -m venv .venv-publication
.\.venv-publication\Scripts\python -m pip install -r reproducibility/requirements-publication.txt
.\.venv-publication\Scripts\python -m pytest reproducibility/tests -q
python -m reproducibility.evidence_manifest verify reproducibility/results/20260908_codex_mini_inot200
```

Every published evidence directory contains a byte-level `EVIDENCE_MANIFEST.json`. Verify each SHA-256 and file length before using its contents. The raw archives preserve original CRLF where applicable; do not normalize archived files. `audit_codex_pilot.py` checks completed initial/development shards; `heldout200/partial_audit.py` checks terminal original and continuation archives. These audits compare full prompts, complete forwarded histories, original event streams, exact CLI arguments, the captured runtime, result rows and token accounting. A modified artifact is an audit failure, not silently classified as missing quality.

The combined reserved export is produced from audited archives, not hand-entered scores:

```powershell
python -m reproducibility.heldout200.assemble export --archive ORIGINAL_GENERATION --continuation CONTINUATION_GENERATION --predictions NEW_PREDICTIONS_DIRECTORY
python -m reproducibility.heldout200.assemble collect --archive ORIGINAL_GENERATION --continuation CONTINUATION_GENERATION --predictions NEW_PREDICTIONS_DIRECTORY --native NATIVE_REPORT_ROOT --controls FINAL_CONTROL_DIRECTORY --output NEW_ANALYSIS_DIRECTORY
```

Replace uppercase placeholders with the actual published or local archive paths. Native subdirectories are named by condition (`direct`, `single_neutral`, `single_roles`, `multi_neutral`, `multi_roles`). Only existing candidate programs are exported; missing assignments remain in the 1,000-cell denominator. Empty format extraction is retained as an observed empty program, not removed. The collector reconstructs exports from original answers and fails on mismatched bytes, controls, image identity, process status or native report coverage.

The published development archive already includes its exact `generation/`, `predictions/`, `evaluations/` and `analysis/` folders. Its 400 records and original evaluator reports are sufficient to reconstruct all tables without spending subscription quota. The initial eight-task run is documented separately in `CODEX_GUIDE.md`.

The complete INoT publication can be replayed from repository root without model calls or new evaluator execution:

```powershell
python -m reproducibility.heldout200.inot_evidence collect --original reproducibility/results/20260908_codex_mini_inot200/generation/codex-inot200-v1 --continuation reproducibility/results/20260908_codex_mini_inot200/generation/codex-inot200-continuation-v1 --tasks reproducibility/results/20260908_codex_mini_heldout200/controls/attempt2/input/prepared.jsonl --selection reproducibility/results/20260908_codex_mini_inot200/protocols/heldout200_selection.json --gate reproducibility/results/20260908_codex_mini_heldout200/controls/attempt3/heldout200_control_gate.json --protocol reproducibility/results/20260908_codex_mini_inot200/protocols/INOT_PROTOCOL.md --predictions reproducibility/results/20260908_codex_mini_inot200/predictions --native reproducibility/results/20260908_codex_mini_inot200/evaluation --controls reproducibility/results/20260908_codex_mini_heldout200/controls/attempt3 --output tmp/inot-replayed-analysis
```

The output directory must be new. The replay independently verifies the two original archives, excludes all attempted cells from continuation, reconstructs the exact 199 programs, verifies the native reports and reapplies the original eligibility gate. Its summary and candidate records match the published analysis byte for byte. Preserve generation directory basenames because the original INoT auditor writes an inventory carrying the archive name.

## Rebuilding the native environment

The image chain is explicit:

```powershell
docker build -f reproducibility/pilot_env/Dockerfile -t bcb-pilot:dev .
docker build -t bcb-official-cli:dev reproducibility/pilot_env/official_cli
docker build -t bcb-scale40:v2 reproducibility/scale_env
docker build -t bcb-heldout200:v3 reproducibility/heldout200/environment
```

These commands rebuild the documented recipe; mutable parent tags and downloaded NLTK assets do not guarantee the original image bytes. The archives record original image IDs, source tree hashes, pinned requirements, complete package freezes and NLTK file hashes. A rebuilt image must receive fresh gold/incorrect controls before new generation. Do not overwrite the original controls or claim a rebuilt image has the old digest. No original test or task may be changed to pass a control.

The evaluator source is the unchanged BigCodeBench commit `09dd993f46c3fbf3a799465bb96d524edcb0b199`, under `reproducibility/vendor/bigcodebench`. The selected full dataset and prepared model input are the exact bytes in the reserved archive's `controls/attempt2/input/`; final controls are in `controls/attempt3/`. Native model evaluation uses the same complete 200-row dataset/input while selecting only real observed candidate IDs:

```powershell
python -m reproducibility.heldout200.run_observed_native --dataset EXACT_EVALUATOR_DATASET --prepared EXACT_MODEL_INPUT --samples ONE_EXPORTED_ARM --output NEW_NATIVE_ARM_DIRECTORY --image VERIFIED_IMAGE --selection reproducibility/revision/heldout200_selection.json --requirements reproducibility/heldout200/environment/requirements.txt --dockerfile reproducibility/heldout200/environment/Dockerfile
```

Use at most two native evaluators concurrently on this host. Each runs offline, non-root and read-only with 3 GiB memory and two CPUs; only its result directory is writable. Original reports use the official `instruct full` CLI with explicit selective IDs. Control-ineligible tasks are still evaluated but have null analysis status; raw test results are retained.

## New model execution

Use the separately installed official Codex CLI 0.153.4 and ChatGPT authentication, as documented in `CODEX_GUIDE.md`. Do not use Spark as a substitute. GPT-5.4 mini medium is a requested alias, not an independently attested weight snapshot. All calls are fresh, ephemeral and text-only; automatic tools and paid API keys are disabled. The byte guard is 65,536 UTF-8 bytes and the per-turn deadline is 180 seconds. Inputs are never shortened to fit. No provider seed, temperature or matched hard output-token allowance is claimed.

The frozen generation manifests bind tasks, prompts, controls and implementation. A fresh replication requires its own output directories and recorded execution dates. Never overwrite a published attempt. The continuation commands refuse a nonterminal parent, hash the complete original archive and exclude every cell with any submitted stage. A timeout or identified stream interruption may end that cell; quota/authentication and unknown errors stop dispatch. There are no automatic retries or credit resets.

## Interpretation

Quality comparisons use task pairs and show both missingness bounds and evaluable denominators. Four reserved binary contrasts use exact two-sided McNemar tests with Holm adjustment; other intervals are descriptive. Administrative amendments are disclosed. There is no non-inferiority claim.

Input tokens include cached input; output tokens include reasoning output. Counterfactual standard API valuation is `((I-C)*0.75+C*0.075+O*4.50)/1e6` USD. Also report `(I*0.75+O*4.50)/1e6` without cache discounts. Missing failed-turn counters are unknown, not zero. Candidate-only totals omit incomplete multi-call attempts, so the submitted-turn ledger is also required. Subscription billing, research-worker usage and evaluator compute are separate.
