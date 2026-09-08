# Frozen decisions and separate attempts

The following repository milestones identify the decisions used for the executed study. Times are the recorded Git author times (UTC+03:00), not an independent registration service or attestation of provider execution time. Full commits and subsequent repository publication are available in Git history.

| Milestone on 8 September 2026 | Commit | Recorded time | Scope |
|---|---|---|---|
| Main allocation frozen after native controls | `1c8aead` | 04:43:44 | 200 reserved task IDs, five conditions, 1,000 candidates, 1,800 planned CLI turns; 193 reference-eligible tasks |
| Independent INoT allocation frozen | `d6bd632` | 04:50:39 | Same 200 tasks, separate prompt adaptation and batch |
| Administrative continuation rule disclosed | `0916888` | 05:14:55 | Only assignments with no submitted stage may continue; started cells never retry |
| Exact untouched INoT subset frozen | `2ab5821` | 05:21:25 | 137 assignments after the first 63 submitted calls |
| Exact untouched primary subset frozen | `5001239` | 06:13:48 | 540 assignments after the original 460 submitted cells; the original archive is hashed in the new manifest |

The qualitative example rule was subsequently recorded in commit `65c8e4a`, while the primary continuation was active and before primary quality evaluation or inspection. It is descriptive and does not alter the four-test family. The primary original attempt, its continuation, and the two INoT attempts retain distinct directories and statuses. A generation deadline is not a license to replace a response, and usage from an interrupted candidate is retained when available.

The pre-control `heldout200_selection.json` intentionally retains its original `controls_complete: false` and empty eligibility fields. Those fields describe the moment of selection; they are not a live study-status file. Final eligibility comes exclusively from the separately hashed `controls/attempt3/heldout200_control_gate.json`, which was frozen before model generation. Neither later diagnostics nor final result publication rewrites those historical selection bytes.

The 40-task, two-repeat development results are a separate prior stage and do not enter the main-sample tests. INoT quality was collected only after the primary pending list had been frozen and published. Primary quality was held until the fixed continuation became terminal. Administrative amendments are disclosed; the paper does not describe the experiment as an unchanged preregistered execution.
