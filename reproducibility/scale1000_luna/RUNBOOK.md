# Execute the separate Luna study

See PROTOCOL.md and MODEL_AMENDMENT.md. All original mini sources, the failed
launch and the three completed native control attempts remain unchanged.
The dataset contains 1000 unique tasks, five conditions and three fresh repeats.
The shared final control gate permits quality inference on 985 task IDs.

Publish the final frozen plan before executing benchmark calls:

```sh
python -X utf8 -m reproducibility.scale1000_luna.dispatch freeze --inputs reproducibility/scale1000/inputs-v1 --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --manifest reproducibility/scale1000_luna/generation_manifest.json
```

Generate (or resume untouched assignments only):

```sh
python -X utf8 -m reproducibility.scale1000_luna.dispatch run --inputs reproducibility/scale1000/inputs-v1 --gate-dir reproducibility/runs/scale1000-v1/controls-v3 --manifest reproducibility/scale1000_luna/generation_manifest.json --out reproducibility/runs/scale1000-luna-v1/generation --npm-root tmp/codex-runtime
```

Only after state generation_finished, native-check every completed candidate
and analyze the complete 15000-row assignment ledger:

```sh
python -X utf8 -m reproducibility.scale1000_luna.finish --gate-dir reproducibility/runs/scale1000-v1/controls-v3
```

The finish command defaults to bcb-scale1000:v2 and its recorded environment-v2
sources. Keep the computer running for the local process. Each completed
response is retained immediately. Quota or availability pauses do not redeem
credits or switch to paid API access. A resume uses the same manifest and
runtime, preserving all submitted failed/partial attempts.

Do not edit frozen dependencies after generation starts. A missing usage
counter is unknown, not zero. The task-free READY probe is excluded from the
benchmark and valued separately. The failed mini launch is also separate.
The inherited statistical analysis averages the three outcomes within each
task and keeps all-assignment missingness bounds; repeats are not independent
tasks. New model results do not establish a same-model replication of mini.
