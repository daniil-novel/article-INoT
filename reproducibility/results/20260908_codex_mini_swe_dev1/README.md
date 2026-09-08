# One-task SWE-bench development evidence: incomplete generation

The frozen allocation contains one development issue (`pvlib__pvlib-python-1606`), five conditions and two repeat labels: ten candidates. A 180-second model timeout stopped the batch after two completed candidates; eight assigned candidates remain unavailable. This is an infrastructure and repository-repair demonstration, not a benchmark estimate.

Four CLI turns were submitted. Three expose complete usage counters: 56,796 known tokens, valued at USD 0.1379895 using the published standard API rates. The fourth has unknown usage, not zero. Full original generation traces, predictions, native evaluation logs, controls and provenance are retained.

The direct candidate applies but does not resolve the issue: one FAIL_TO_PASS test fails and ten PASS_TO_PASS tests pass. The single-neutral candidate is rejected by native patch application before tests. Its exact patch and the upstream rejection log are retained. Neither candidate is repaired or retried; both are observed failures, separate from the eight missing candidates.

`retrieval/runner-v2` is the frozen generation input; `runner` is an earlier preparation diagnostic. Deterministic retrieval selected nine complete Python files (23,863 source bytes) from the fixed repository commit. No selected file was truncated, but the packet does not contain the whole repository. Original rankings and omissions are retained. The independent retriever used allowed metadata and source files; gold and test patches were evaluator-only.

The original official image failed its gold control because of NumPy compatibility. A separate image pinning NumPy 1.26.4 passes all eleven reference tests; the applicable incorrect control passes ten and fails the target test. All failed setup attempts remain archived. The upstream harness source is pinned. The controller is offline, but its upstream child-container network defaults are an explicit limitation.

The converted evaluator input contains 23 original development rows; only the frozen issue is evaluated here. Source licenses are recorded separately: the harness MIT license is not a blanket license for dataset repository content. See the included pvlib license and `source-licenses/`. `EVIDENCE_MANIFEST.json` hashes the final published bytes.
