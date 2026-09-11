# Scale1000 Luna readiness audit (2026-09-11)

## Scope and current verdict

This is a read-only audit. No model call, native evaluation, Docker evaluation, retry, or frozen-file edit was performed. The Luna generation dispatcher is currently active (the archive reports `state: running`; the live launcher is owned by the root task). `finish.py` is therefore correctly blocked for now: it requires the terminal generation state `generation_finished` before it creates any pipeline stage.

The frozen execution plan is internally consistent for the intended study: 1,000 unique task IDs, five arms, repeats 101/102/103, 15,000 candidate assignments, and 27,000 planned CLI turns. The control gate is complete, has the same ordered 1,000 IDs as `inputs-v1/selection.json`, and contains 985 quality-eligible IDs. The generation runtime records GPT-5.6 Luna, `codex-cli 0.153.4`, medium reasoning, eight workers, 600 seconds per CLI turn, ChatGPT authentication, and the task-free working directory.

## Generation state observed

At the audit snapshot, `generation/status.json` contained `{"pending_at_start":7576,"session":"1789136025783339200","state":"running"}`. Counts are moving while the dispatcher runs; the last read showed 7,448 completed cell files, 13 failure files, 13,437 turn folders, and 16 temporary in-flight cell IDs with turn evidence but no terminal cell/failure record yet. Turn states were 13,412 completed, 14 started, and 11 blocked. These temporary IDs are not a reconstruction defect while the writer is active; `collect.reconstruct` explicitly refuses to snapshot an archive whose state is `running`.

The previous stale lock/status was handled by the root task before the current launcher was started. Do not remove or rewrite the live `DISPATCH.lock`, status, turns, failures, or session files. The dispatcher’s continuation policy is safe for the protocol: it submits only untouched cells, retains every submitted turn, does not retry a failed cell, and stops on quota/auth, unsupported-model/metadata, eight consecutive failures, or invalid/unpriceable usage. The raw-usage parser rejects nonzero cache-write counters, invalid counters, duplicate usage completions, and cached tokens exceeding input tokens.

## Completeness and missingness checks

`collect.py` reconstructs all 15,000 frozen cells in manifest order. A completed cell must have every expected stage accepted, exact prompt/forwarded-history bytes, matching CLI arguments and runtime, valid usage replay, and unchanged raw-file hashes. A partially submitted cell remains `generation_complete: false`; its known usage is retained in the turn ledger. Missing rows are represented as assignment-level missingness and are not silently converted to failures. `dispatch.validate_turn_inventory` rejects orphan IDs outside the frozen allocation and rejects later stages after an absent or unaccepted prior stage.

`finish.py` is not safe to invoke until the dispatcher writes `generation_finished`. After that, the finish pipeline is resumable by stage: an existing successful stage is skipped, while a failed stage must be diagnosed with its raw logs preserved. It exports completed solutions, native-checks every nonempty arm/repeat export, reconstructs the full 15,000-row candidate ledger, and runs the task-cluster analysis. An empty export is skipped by the native loop, but the corresponding incomplete assignments remain in the reconstructed ledger.

## Native evaluator and environment blocker

The exact final command is:

```powershell
python -X utf8 -m reproducibility.scale1000_luna.finish --gate-dir reproducibility/runs/scale1000-v1/controls-v3
```

It defaults to image `bcb-scale1000:v2`, `reproducibility/scale1000/environment-v2/requirements.txt`, `reproducibility/scale1000/environment-v2/Dockerfile`, and a 14,400-second native-evaluation deadline per arm/repeat. The native runner uses the unchanged BigCodeBench v0.1.4 evaluator, pinned upstream source, network-none/read-only containers, 3 GB memory, two CPUs, 256 PID limit, and no retry. The controls gate and environment provenance must continue to match before native statuses are trusted.

At audit time the Docker CLI was installed but the Docker Desktop Linux engine was unreachable (`//./pipe/dockerDesktopLinuxEngine` missing). This is a concrete prerequisite for finish, not a data-integrity failure. The E: volume had approximately 29.7 GB free. The repository does not declare a numeric free-space threshold; 29.7 GB should be treated as tight for 15 native runs plus logs and image/build cache. Before finalization, start Docker Desktop, confirm the exact `bcb-scale1000:v2` image is inspectable, and verify free space. Do not substitute another image or silently rebuild the frozen environment.

## Analysis contract and power interpretation

`scale1000/analyze.py` enforces exactly 1,000 task clusters, validates unique `(task, arm, repeat)` assignments, excludes any task/arm with an incomplete or unknown repeat from the corresponding complete three-repeat paired contrast, and keeps assignment-level extreme bounds for all missing outcomes. Repeats are averaged within task and are never treated as 3,000 independent tasks. The confirmatory family is exactly four contrasts: SR−SN, MR−MN, MN−SN, and MR−SR; each uses a two-sided one-sample t-test on task-level three-repeat means, followed by Holm over four p-values at familywise alpha .05. Direct comparisons, interactions, old-200/fresh-800 subgroups, repeat variability, and resources remain descriptive.

The predeclared sensitivity grid uses n=1,000, Holm first-step alpha .0125, discordance d in {0.15, .30, .50}, repeat ICC rho in {0, .5, .8}, and effects {0.02, .05, .10}; it is an approximation, not a guarantee. For a 2 percentage-point effect, approximate power ranges from 0.6296 (d=.15, rho=0) down to 0.0624 (d=.50, rho=.8), with intermediate values 0.3093 (d=.15, rho=.5), 0.1393 (d=.30, rho=.5), 0.1044 (d=.30, rho=.8), and 0.0806 (d=.50, rho=.5). Thus N=1,000 does not guarantee detection of a 2-point effect after the four-test correction, especially with high discordance/repeat correlation. The grid is a precision/sensitivity statement and must not be reported as achieved power from observed data.

## Finalization sequence

1. Let the live Luna dispatcher finish or pause only through its own predeclared guards. Confirm `generation/status.json` is `generation_finished`, `DISPATCH.lock` is absent, and no generation process remains.
2. Preserve the final generation status, sessions, failures, turn inventory, runtime provenance, and source copies as evidence. Do not edit the manifest or frozen dependencies.
3. Ensure Docker Desktop is running and the exact `bcb-scale1000:v2` image plus vendor commit/provenance are available; keep the computer running for the long native stages.
4. Run the finish command above from the repository root. If interrupted, resume the same command; successful stage exit files are reused and failed stages remain diagnosable.
5. Publish only after `pipeline/export`, all required nonempty `native-*` stages, `pipeline/collect`, and `pipeline/analyze` have successful exit records and the generated analysis explicitly reports observed counts, incomplete/submitted assignments, all-assignment bounds, the four-primary Holm family, and the 985/1000 control-eligibility denominator.

This Luna work is a new model study under the amendment, not a same-model replication of the rejected GPT-5.4-mini attempt. The final article should preserve that distinction and should not claim that the planned N=1,000 guarantees a powered 2-point test.
