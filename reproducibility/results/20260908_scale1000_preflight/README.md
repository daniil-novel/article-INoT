# Scale-1000 pre-generation reference controls

This archive contains reference controls and environment preparation, not model
generations or experimental success estimates. The allocation of 1000 unique
tasks and three new repeats was published before controls in commit 9b32e12.
All task IDs and inputs are retained in reproducibility/scale1000/inputs-v1.

The first environment passed 949 gold programs, failed 49 and timed out on two.
The incorrect control failed on 999 tasks and timed out on one, leaving 948
quality-eligible tasks. Missing packages motivated the separate recorded
environment amendment before any new model call. Every first-attempt outcome
is preserved. Later complete attempts are appended, never substituted for the
first attempt. A gate is published only after both full-allocation controls
complete and pass provenance validation.

The amended image identity is
sha256:b7f201e6c68020a9f8bf5250d0bc09ff56cd35b918fcce75976140143ac7a0ad.
Image build logs, exact native inputs/reports, package freezes and source
identities are retained. Upstream tests and reference code are unchanged.
Rebuilding is not promised to recreate a bitwise-identical container.

The second gold attempt passed 986 tasks, failed 12 and timed out on two.
A remaining missing librosa import motivated the separate environment-v2
layer before model generation. Its bcb-scale1000:v2 image identity is
sha256:afeb8d78b76f6a7b1fbf427d78a55bd35dbfcf58387711b47f8a8ba00e16b580.
The complete third attempt, when available below, repeats both controls in
that final environment. Per-ID CSV and JSON summaries are under readable/;
eligibility is copied from the validated gate, never inferred from an error
excerpt. A gold pass alone does not imply quality eligibility.

Published complete attempts:

[
  {
    "attempt": "controls-v1",
    "assigned": 1000,
    "eligible": 948
  },
  {
    "attempt": "controls-v2",
    "assigned": 1000,
    "eligible": 984
  }
]
