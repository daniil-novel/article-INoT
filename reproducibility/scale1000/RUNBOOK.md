# Execution and recovery

Selection and protocol were published at 9b32e12 before native controls.
The full pipeline and task-cluster analysis were published at 46daa74.
The first control attempt is `reproducibility/runs/scale1000-v1/controls-v1`.
All paths below are relative to the repository root. These commands use
existing subscription authentication, not an OpenRouter/API key.

## Controls before generation

```sh
python -X utf8 -m reproducibility.scale1000.run_controls --out reproducibility/runs/scale1000-v1/controls-v1
```

The attempt directory is exclusive: do not rerun this command on an existing
directory or delete a failed attempt. Any dependency amendment must precede
generation, use a new recorded image/attempt directory and rerun both gold and
incorrect controls on all 1000 tasks. The final gate preserves every original
outcome, even for quality-ineligible tasks. A full-assignment control report
does not guarantee that all 1000 tasks are quality-eligible.

## Freeze and publish the executable generation plan

The amended environment is bcb-scale1000:v2, recorded under environment-v2.
The final full control attempt is controls-v3; its completion and strict
validation are prerequisites for generation. All earlier attempts remain.
After reviewing the final control attempt, point `--gate-dir` to that attempt:

```sh
python -X utf8 -m reproducibility.scale1000.dispatch freeze --inputs reproducibility/scale1000/inputs-v1 --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --manifest reproducibility/scale1000/generation_manifest.json
```

Commit and publish that plan and the final control evidence before calling
`run`. The dispatcher checks exact task/source/protocol/control identities.
Do not edit frozen dependencies after generation starts. If a genuine bug is
found, preserve the frozen version and document a new amendment or replay path.

## Generate and resume untouched assignments

```sh
python -X utf8 -m reproducibility.scale1000.dispatch run --inputs reproducibility/scale1000/inputs-v1 --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --manifest reproducibility/scale1000/generation_manifest.json --out reproducibility/runs/scale1000-v1/generation --npm-root tmp/codex-runtime
```

The same command resumes untouched assignments after a quota/authentication
pause. It never resubmits a cell with an existing turn folder. Original failed
and partial cells remain in the full 15000-row assignment ledger. Completed
answers are not selected by quality and tests are never fed back to generation.
Each resume has separate runtime/order/session metadata. A `DISPATCH.lock`
prevents simultaneous dispatchers; after a host crash, verify the recorded
process is no longer running before manually removing only this stale lock.

The USD 285 guard concerns known counterfactual valuation at submission time,
not paid billing. Already active calls may finish above it. Unknown usage is
reported explicitly, including malformed/truncated event-line annotations.
No automatic purchase, paid fallback or quota-reset redemption occurs.

## Native evaluation and final analysis

When status is `generation_finished` (zero untouched assignments), use:

```sh
python -X utf8 -m reproducibility.scale1000.finish --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --image bcb-scale1000:v2 --requirements reproducibility/scale1000/environment-v2/requirements.txt --dockerfile reproducibility/scale1000/environment-v2/Dockerfile
```

If the final gate used an amended image, supply its exact `--image`,
`--requirements` and `--dockerfile` to the finish command. The native audit
must match the final controls. Every completed candidate is evaluated,
including invalid-format model responses; such responses count as failures,
while infrastructure-unknown outcomes remain explicit. Native reports are
grouped by arm and repeat, each preserving original task order.

The final summary requires all 1000 task identities, retains missing
assignments and averages three repeats within each task for paired inference.
The primary family has four tests, regardless of missingness. Describe the
800 fresh tasks separately from the prior 200. Report all known submitted-turn
costs, including unsuccessful attempts, separately from complete-candidate
resource comparisons.

Before updating the empirical claims/PDFs: verify all native joins, all
15000 assignment records, repeat denominators and missingness; publish full
raw archives with SHA-256 and exact Git blobs; replay analyses on Linux;
regenerate tables/figures and visually check both PDFs. Until then the current
article continues to report only the completed 200-task and 80-task studies.
