# Repository-patch development demonstration

Fixed before model generation, 8 September 2026. This is one task, not a
SWE-bench Lite score or a test of repository-level generalization.

Task `pvlib__pvlib-python-1606` is the first ID in the previously frozen dev8
list. Its gold and applicable comment-only negative have already been run with
the unchanged official SWE-bench harness. The original task image fails from
NumPy dependency drift; a separately recorded image changing only NumPy to
1.26.4 gives 11 passing gold tests and 10 passing/one failing negative tests.
Preserve both environments and their reports. The custom environment is not
an unchanged official release image.

A separate retrieval worker reads only instance ID, repository, base commit,
problem statement and version, never hints, reference patches, test patches
or evaluation logs. Deterministic BM25 ranks eligible tracked Python files,
excluding tests/examples/docs/benchmarks. Greedy selection includes whole files
within 24,000 UTF-8 source bytes. Actual selected files total 23,863 bytes;
larger files that cannot fit are listed explicitly. No file truncation or
summary is allowed. This fixed retrieved packet is not the whole repository;
retrieval omissions remain part of the system's limitations. All five arms
receive the same packet and forward complete exposed stage outputs.

Use the unchanged subscription-v2 model/CLI protocol: GPT-5.4 mini, medium,
CLI 0.153.4, fresh ephemeral text-only turns, native stopping, no retries,
no provider seed/temperature control, 180 seconds per turn and 65,536 bytes
before dispatch. Replicate labels 1 and 2 yield 10 candidate patches and 18
turns. Two concurrent workers; no test feedback or patch repair. The final
solution is extracted by the existing strict `swebench` fenced-diff parser.
Formatting/application failure remains an outcome, not a reason to generate
a replacement. Record complete traces, patch bytes and token valuation.

Every candidate is applied and tested by the unchanged pinned upstream
harness in the validated custom image. Record unique run IDs, exact argv,
image/source/data hashes, full reports, test logs, and code-to-report joins.
The controller is offline but the unchanged upstream child container retains
its default Docker network; report that limitation explicitly. No credentials
or personal folders are mounted. Distinguish application rejection from an
infrastructure failure; unresolved is not missing merely because a patch is
wrong. Do not infer a pass from a missing report.

Report all 10 assignments, outcomes and observed resources. No significance
test, non-inferiority claim or confidence interval over this single task.
Neither this retriever nor these constructed arms are Agentless or SWE-agent.
