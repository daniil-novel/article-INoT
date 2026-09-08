# Completed primary experiment: 200 tasks, 996 observed programs

The task IDs were fixed from the original randomized reserved split before controls or generation. The five-condition design assigns 1,000 candidates and 1,800 CLI turns on GPT-5.4 mini, medium reasoning through subscription authentication. The 2×2 crosses one/three calls with neutral/role-labelled stages, plus direct solving. All supplied context and prior exposed responses are retained without compression. The 40 development tasks are disjoint.

All 1,000 cells were submitted: **996 completed and four remain missing**, with no retries. The original attempt completed 457/460 submitted cells; the separately frozen continuation completed 539/540 previously untouched cells. Original failures: D /1028 (transport), SN /249 (deadline), SN /388 (transport). Continuation: SN /1028 (180-second client deadline). The last raw stream includes a completed response and usage, but the terminal deadline criterion failed, so it is not accepted as a candidate. Event arrival times are not independently timestamped. No missing program was filled from another answer. See the disclosed [execution amendment](../../revision/HELDOUT200_EXECUTION_AMENDMENT.md).

All **996 observed programs** were checked by the unchanged upstream native CLI and joined to their exact responses and original tests. Of these, 963 are reference-eligible (453 pass, 507 fail, three native timeouts); 33 have unavailable quality under the common control gate. Two final-format extraction failures remain observed empty programs: MR /100 and D /494. Missing generations are distinct from failed native tests.

| Condition | Completed | Eligible passes | Rate | All-200 missingness range | Mean tokens | Mean API-equivalent USD |
|---|---:|---:|---:|---:|---:|---:|
| D | 199 | 94/193 | 48.70% | 47.0–50.5% | 4159.84 | 0.006550 |
| SN | 197 | 93/191 | 48.69% | 46.5–51.0% | 5122.31 | 0.010711 |
| SR | 200 | 92/193 | 47.67% | 46.0–49.5% | 4703.32 | 0.008875 |
| MN | 200 | 86/193 | 44.56% | 43.0–46.5% | 14577.70 | 0.022570 |
| MR | 200 | 88/193 | 45.60% | 44.0–47.5% | 14381.75 | 0.022221 |

Ranges are extreme missing-outcome bounds, not confidence intervals. Resource means use all completed candidates, including reference-ineligible tasks. The sampling unit is the task, not the program. The repeat label is not a provider sampling seed.

## Paired results

The four predeclared exact McNemar tests use Holm adjustment. SR−SN: −1.05 percentage points, 191 pairs, descriptive bootstrap 95% interval [−4.71,+2.62], adjusted p=1. MR−MN: +1.04, 193 pairs, [−3.11,+5.70], p=1. MN−SN: −4.71, 191 pairs, [−9.42,0.00], p=0.3134. MR−SR: −2.07, 193 pairs, [−6.22,+2.07], p=1. No contrast rejects at familywise 0.05. The interaction uses the common 191-task four-condition set: +2.09 points [−4.19,+8.38]. No equivalence or non-inferiority claim follows.

On 197 complete resource pairs, SR/SN is 0.9124 in tokens and 0.8155 in valuation (0.8379 without cache discounts). The paired USD difference is −0.0019761 [−0.0027617,−0.0012296]. MN/SN costs 2.0879 times as much; MR/SR 2.5037 times. Multi-call role labels have an uncertain cost difference. Resource intervals are descriptive task bootstraps, outside the four-test family.

## Full usage ledger

`analysis/submitted_turns.csv` has one row per submitted turn, including failures. Known usage from 1,797/1,800 turns totals **8,585,185 tokens**: 5,776,714 input (including 4,097,536 cached), plus 2,808,471 output (including 2,076,742 reasoning). Three calls lack final usage and are never assigned zero. Valuation is **USD 14.2048182**, or **USD 16.970655** with no cache discount. Completed-candidate totals are separately 8,569,456 tokens and USD 14.1467676; the difference is known interrupted-call usage.

Published standard GPT-5.4 mini rates are USD 0.75 input, 0.075 cached input and 4.50 output per million tokens: `((I-C)*0.75+C*0.075+O*4.50)/1e6`. This is counterfactual list-price valuation of subscription counters, not an invoice or total research cost. No paid OpenRouter call was used. Reasoning is a subset of output, cached input a subset of input.

## Controls and original evidence

Control attempt 2 used the original development image: 181 reference programs passed and all 200 incorrect programs failed. Before generation, environment attempt 3 added pinned library dependencies and offline NLTK corpora: 193 references passed and all 200 incorrect programs failed. Seven tasks remain unavailable for quality analysis and stay in every assignment denominator. Their original native details contain DNS errors (/101, /590), missing TensorFlow (/418), an unsupported encoder argument (/686), degenerate-moment assertions (/276), and archive/logging assertions (/14, /1028). The earlier statement that six lacked diagnostics was incorrect: per-test details are present. [The diagnostic note](../../revision/HELDOUT200_CONTROL_DIAGNOSTICS.md) distinguishes observations from inference and retains the original eligibility gate. TensorFlow was excluded because its assessed protobuf requirement conflicts with the evaluator environment.

All original task, reference, test and incorrect-program bytes remain fixed. `controls/attempt3/independent_pre_generation_audit.json` (or the adjacent audit file) records the independent checks. The environment files record the actual image and verified parent image IDs. The Dockerfile uses a local parent tag; the parent identity was independently checked, not implied by an immutable FROM declaration. Earlier controls and build diagnostics are retained. No model success rate is inferred from a passing reference control.

The unchanged upstream source is commit `09dd993f46c3fbf3a799465bb96d524edcb0b199`. The actual evaluation image is `sha256:76d84f87bb98a10e358e19d58b84c2eed3dc24c1e8431582ae1dd9874faa7667`. Rebuilding is not promised to recreate that image bit for bit; new controls are required for a new environment.

`generation` preserves both attempts, exact prompts, final answers, events, arguments, statuses and hashes. `predictions` preserves strictly extracted programs; `evaluations` preserves native reports and provenance. `analysis` contains all candidate rows, assignments, contrasts, ledger and deterministic case selection. `protocols` records frozen decisions and the administrative amendment; the execution is not called unchanged preregistration. `analysis_sources` retains analysis implementations. `EVIDENCE_MANIFEST.json` inventories exact bytes. Original licenses accompany third-party data.

## Replay without model calls

Install `reproducibility/requirements-publication.txt` from the repository root, then run:

```text
python -m reproducibility.heldout200.assemble collect --archive reproducibility/results/20260908_codex_mini_heldout200/generation/codex-heldout200-v1 --continuation reproducibility/results/20260908_codex_mini_heldout200/generation/codex-heldout200-continuation-v1 --predictions reproducibility/results/20260908_codex_mini_heldout200/predictions --native reproducibility/results/20260908_codex_mini_heldout200/evaluations --controls reproducibility/results/20260908_codex_mini_heldout200/controls/attempt3 --output tmp/primary-replay
python -m reproducibility.evidence_manifest verify reproducibility/results/20260908_codex_mini_heldout200
```

Use a new output directory. Compare `summary.json`, `candidate_records.jsonl` and `assignment_availability.json` byte for byte with `analysis/`. This checks retained responses, inputs, native joins and statistics; it does not rerun the model or Docker. Native re-execution and source setup are documented in [SCALE_GUIDE](../../SCALE_GUIDE.md).
