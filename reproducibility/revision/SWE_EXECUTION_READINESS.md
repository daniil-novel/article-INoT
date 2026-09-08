# SWE-bench execution readiness

This note records a bounded development smoke-test and the preparation path for
later predictions. No model response was generated. Reference patches were
used only inside evaluator-only gold controls. The official task image was
staged by digest, and a separately labelled dependency-adjusted image was used
for the passing control.

## Fixed upstream and data

- SWE-bench source: `reproducibility/vendor/swebench`, detached at
  `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`.
- Source tree digest (portable SHA-256 over every non-`.git`, non-`__pycache__`
  file, sorted by UTF-8 relative path, hashing path length, path, file length,
  and file bytes):
  `7b27fd73cab5977cab1fa3864d36b7f35a45a7bcb1a7745da50c27f418077d8e`.
- Official dataset endpoint identified by the pinned repository documentation:
  `SWE-bench/SWE-bench_Lite`, `dev` split, file
  `data/dev-00000-of-00001.parquet` from the Hugging Face dataset repository.
  Downloaded file SHA-256:
  `B90BCBFACA1B5F65155500124A977876C264A4003AB384ACA4DFC39A54BEF89`.
- The dev parquet contains 23 rows. A fixed, before-outcome sample was drawn
  with Python `random.Random(20260908)` and sorted only for stable reporting;
  the eight IDs are recorded in the ignored
  `reproducibility/data/swebench-lite/dev8_manifest.json` (SHA-256
  `1ad4cbf163a6ef2ae16aaee4c598120d4563f8ddc5ab670b13211349057854d6`).
  They are:

  `pvlib__pvlib-python-1606`, `pvlib__pvlib-python-1854`,
  `pydicom__pydicom-1139`, `pydicom__pydicom-1256`,
  `pydicom__pydicom-901`, `pylint-dev__astroid-1333`,
  `sqlfluff__sqlfluff-1733`, `sqlfluff__sqlfluff-1763`.

  The manifest was made by reading metadata columns only; `patch` and
  `test_patch` were deliberately not read or copied into the manifest. The raw
  parquet remains ignored local input for a future official harness run.

## What the official harness requires

The pinned README recommends x86_64, at least 120 GB free storage, 16 GB RAM,
and eight CPU cores, and specifically warns that Docker Desktop should have
about 120 GB of free virtual disk. The pinned harness reference documents the
same requirement and describes `none`, `base`, `env`, and `instance` image cache
levels; its indicative storage figures are about 120 GB for the minimal cache,
about 100 GB for `env`, and about 2,000 GB for `instance`.

The supported path is the unchanged upstream command, for example:

```text
python -m swebench.harness.run_evaluation \
  --dataset_name SWE-bench/SWE-bench_Lite --split dev \
  --predictions_path predictions.jsonl --instance_ids ... \
  --max_workers 1 --timeout 1800 --run_id <fresh-id>
```

The CLI's `swebench eval` wrapper calls this same function. A prediction record
must contain `instance_id`, `model_patch`, and `model_name_or_path`. Each task
image is looked up locally and, if absent, the harness attempts a registry pull
(`swebench/harness/run_evaluation.py`, `create_container`). Thus `network=none`
is possible only after every image and every declared binary asset has been
staged; it is not a way to bootstrap the run.

The harness applies the patch, runs `/bin/bash /eval.sh` inside the instance
container, records test output, and enforces a per-instance timeout (default
1,800 seconds). A fresh `run_id` is mandatory when changing a patch because
results are cached by `run_id` and instance ID, without hashing patch content.
Missing reports and timeouts must remain explicit infrastructure statuses, not
failures silently folded into a quality denominator.

The current machine is a Docker Desktop Linux context (`desktop-linux`, Docker
27.2.0, LinuxKit kernel 6.10.4, x86_64, 12 CPUs, 7.75 GiB Docker memory). At
the start of the check the host had about 7.29 GiB free on C: and 100.70 GiB
free on E:. The official task image was then staged and its custom derivative
was built; the remaining free space stayed above 7.0 GiB on C: and about 91 GiB
on E:.

The exact first dev8 task metadata names the official image
`swebench/sweb.eval.x86_64.pvlib_1776_pvlib-python-1606:latest`. A registry
manifest lookup, without pulling it, returned manifest digest
`sha256:67af22e57989f01d55a8e783ce6afeacfecdf439bf3cba65f53eb5f0a311eb3e`,
config digest
`sha256:6816a8bcdf28b9660ac7af12a7861a80141be55d4e761eff7d53c1fe6b650213`,
and 15 gzip layers totaling 1,692,673,802 bytes (1.576 GiB compressed). This
is a concrete single-instance candidate: the compressed transfer fit within
the available space, while the actual staged image occupied 3,972,991,320
bytes unpacked. A manifest does not reveal how much layer space would be shared
with other task images. One sequential smoke test was completed; the documented
120 GB/16 GB recommendations remain a conservative blocker for a full local
Lite run.

## Controls and safe execution plan

The reusable prediction launcher is
`reproducibility/swe_smoke/evaluate_predictions.py`. It accepts one JSONL
prediction for the fixed first ID, rejects non-empty output directories,
verifies source/dataset/image/controller IDs and hashes, records exact argv and
provenance, applies an outer deadline, cleans only its owned container name,
and validates the prediction-to-report join. It does not generate model
responses. The next executable gate should use the fixed eight IDs above, `--split dev`,
`--max_workers 1`, a fresh run ID for every arm, and an outer process deadline
longer than the per-instance timeout. It should preserve the complete argv,
stdout/stderr, image IDs, source/dataset digests, package lock, and per-task
report. Run with explicit Docker `desktop-linux` context and no whole article
workspace mount. Once images and binary assets are staged, evaluation containers
should run with network disabled, no credentials, no user-folder mounts, a
read-only source/input mount, a dedicated writable log directory, dropped
capabilities, non-root user, and memory/PID limits. The upstream harness itself
does not provide all of those policy controls, so the launcher must enforce
them or the run must be labelled as a non-equivalent harness execution.

Use two declared control arms over the same eight IDs:

1. **Gold control:** the official reference patch, supplied only to the
   evaluator as a control and never exposed to a model or used for retrieval.
2. **Negative control:** an intentionally malformed or no-op patch, with the
   expected result recorded as fail/error. It must be checked for exact task ID
   coverage and must not be treated as a missing prediction.

The chronological diagnostic runs and final controls are all retained in
`reproducibility/runs/swe-smoke-dev1`: the original official-image gold run is
`gold-dev1-v3` and is unresolved because NumPy 2 breaks the old pvlib source;
the final dependency-adjusted controls are `gold-dev1-numpy126` (resolved) and
`negative-noop-dev1-numpy126` (unresolved after tests ran). The malformed
negative run is retained separately as an evaluator-error diagnostic. These
results are one-task controls, not an eight-task or full-benchmark score.

## Model-driver integration

The read-only source audit found no native Codex CLI subscription adapter in
either driver:

- Agentless README setup requires `OPENAI_API_KEY`. Its code dispatches to
  `openai.OpenAI` (`agentless/util/api_requests.py`) and has explicit OpenAI,
  Anthropic, and DeepSeek backend classes; it does not invoke `codex` or a
  subscription login/session.
- SWE-agent's `GenericAPIModelConfig` documents an API-key field and the model
  implementation calls `litellm.completion(..., api_key=...)`. Its key resolver
  reads configured values or environment variables. The source contains no
  Codex CLI subprocess/provider path.

Consequently a Codex subscription run would require an explicitly documented
adapter that invokes the local Codex CLI and converts its patch output into
SWE-bench prediction records, or an API key and a supported LiteLLM/OpenAI
provider. A subscription login must not be represented as API-equivalent usage.
The adapter and its output parser are not part of this readiness check.

## Actual one-instance smoke-test

The first fixed ID was then evaluated with the unchanged pinned harness after
staging its exact registry image by manifest digest. The controller used
`swe-smoke-controller:20260908-v3` and mounted only the pinned SWE-bench source,
the evaluator-only converted JSON dataset, the negative prediction file, a
dedicated output directory, and `/var/run/docker.sock`. The controller itself
had `--network none`; the upstream harness creates the task container without a
network override, so the child container's default Docker network remains a
limitation of this unchanged-harness smoke-test.

Raw archive: `reproducibility/runs/swe-smoke-dev1` (ignored). Its
`provenance.json` records the actual image IDs, manifest digest, source and
dataset hashes, controller Dockerfile/requirements/pip-freeze hashes, exact
argv files, and control report hashes.

- Gold control: run `gold-dev1-v3`, one completed report, no timeout, no
  infrastructure error, but unresolved. The patch applied cleanly and the
  test output ended with exit code `4`: the image's test environment has NumPy
  2 while this old pvlib source references removed `np.Inf`. This is an
  environment compatibility failure, not evidence that the reference patch is
  wrong; it prevents calling this gold control a pass.
- Negative control: run `negative-dev1-v3`, one expected evaluator error. The
  deliberately malformed patch was rejected by `git apply`; no test was run.

Earlier controller attempts are retained in the same archive. The first two
had the same test-environment failure and additionally exposed that the
controller needed the Docker CLI for the upstream cleanup helper; v3 includes
that CLI and completed with zero unstopped containers. At the end of v3, the
official image was locally present at 3,972,991,320 bytes unpacked; host free
space remained above 7.0 GiB on C: and about 91 GiB on E:. No model calls were
made. The smoke-test proves the official image can be staged and the harness
can produce reports for one task, but it does not establish a passing gold
baseline or full Lite feasibility.

To separate image dependency drift from harness behavior, a second task image
was built from the exact official manifest above with only `numpy==1.26.4`
installed in its existing Python 3.9 testbed environment. SciPy remained
`1.13.1`, compatible with that NumPy version. This is an explicitly labelled
custom image, not the official release image. Its actual image ID and
Dockerfile/package hashes are in `provenance.json`.

- Custom gold control: `gold-dev1-numpy126` resolved the fixed task; 11 tests
  passed and the recorded test exit code was `0`.
- Custom semantic negative control: `negative-noop-dev1-numpy126` used an
  applicable comment-only patch, so patch application and tests both ran; 10
  tests passed, one regression test failed, and the task remained unresolved.
  The earlier malformed-patch run remains archived separately as an evaluator
  error diagnostic.

These controls establish a functioning one-instance path only under the
declared NumPy-adjusted custom environment. They do not turn the official
release-image gold failure into a pass and do not justify an official
release-image benchmark result.

## Decision

The official evaluation route is technically compatible with Windows through
Docker Desktop's Linux context. A single fixed task now has a reproducible
custom-image smoke path, while the documented multi-task Lite run still needs
its resource plan and pre-staged task images. The reusable
`reproducibility/swe_smoke/evaluate_predictions.py` launcher is ready for
fixed-task prediction files; it has not executed a candidate prediction. Any
future multi-task result must retain the fixed development manifest and must
not be presented as a full SWE-bench benchmark.
