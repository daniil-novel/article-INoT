# SCC author-code development pilot: all three assignments checked

This is a feasibility pilot, not a ranked external benchmark or confirmatory
comparison with Hybrid-INoT. The source, adaptation and three task IDs were
published in commit `92ddafe` before generation. Tasks are the first three in
the previously exposed dev40 allocation, with one run each and no replacement.

| Task | Model calls | Gold | Incorrect control | SCC candidate |
|---|---:|---|---|---|
| BigCodeBench/325 | 4 | pass | fail | pass |
| BigCodeBench/322 | 3 | pass | fail | fail |
| BigCodeBench/1036 | 4 | pass | fail | fail |

All **3/3 candidates** were generated and independently evaluated by original
native BigCodeBench tests. No assignment or usage counter is missing. Eleven
model calls consumed **48023 tokens** (43763 input, 4260 output, zero cached
input), valued at **$0.0138646 API-equivalent** using Luna's recorded standard
input/output rates of $0.20/$1.20 per million tokens. This is not an API invoice
or a full compute-cost estimate. The final candidate for each task is the native
upstream-selected result, not a best-of-repeat selection.

The historical author source is
[SCC revision b471e12051190dbae2c71b429a3c87466df4b336](https://github.com/YihongDong/Self-collaboration-Code-Generation/tree/b471e12051190dbae2c71b429a3c87466df4b336).
The original Session, role prompts, histories, extraction and stopping are used.
The Codex bridge changes the transport and sampling controls; see
[DEVELOPMENT.md](DEVELOPMENT.md). Every requested upstream parameter is retained
alongside the actual CLI command. GPT-5.6 Luna medium is different from the
historical article's mini model, so these pilot outcomes are not compared with
historical arm percentages.

The model-generated print-based test is an internal exception check. It can stop
the session without establishing correctness; all final candidates receive the
independent official evaluation. Internal test containers have no hidden tests
or reference solutions. The pilot supplies full task text and expects complete
returned programs; unlike the historical HumanEval loader it does not separately
prepend `before_func`. That dataset adaptation must be reviewed before scaling.

All gold and negative controls were evaluated in the same pinned image as final
candidates. Controls ran during this development pilot, not as a prior frozen
confirmatory eligibility gate. No quality inference or significance test is
performed on these three exposed tasks.

Contents: `generation` has full prompts, raw CLI event streams, usage, histories,
programs, original adapter snapshots and generated-test executions;
`native-preparation` and `native-controls` hold exact evaluation inputs and native
reports; `software-checks` contains synthetic Docker checks and integration
records. `summary.json` is reconstructed from raw events and the upstream session,
then joined against the exact native-evaluated programs. `EVIDENCE_MANIFEST.json`
preserves all published bytes. Source and dataset licenses are retained.

From the repository root, after installing the publication and external-baseline
requirements:

```sh
python -m reproducibility.evidence_manifest verify reproducibility/results/20260909_scc_dev3
python -m reproducibility.external_baselines.audit reproducibility/results/20260909_scc_dev3 --whole-pilot
```

Replay performs no model calls and executes no generated program. It proves
consistency of the retained evidence and the original controller transitions;
it does not prove deterministic model regeneration or statistical superiority.
