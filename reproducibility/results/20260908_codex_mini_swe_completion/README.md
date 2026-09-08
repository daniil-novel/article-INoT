# Complete ten-assignment SWE development demonstration

This prospective extension completes the eight previously unavailable assignments
on pvlib__pvlib-python-1606. The earlier immutable archive remains in
../20260908_codex_mini_swe_dev1. Seven assignments are first submissions after
the old batch stop; multi_roles repeat 2 is a separately recorded full recovery
after its original interrupted second turn. The new deadline is 600 seconds per
turn, versus 180 seconds in the original run. This mixed operational history is
not a homogeneous first-attempt benchmark estimate.

All eight new candidates completed. All ten candidates, including the two old
ones, have valid response-to-patch-to-native-result joins. None resolves the
issue: eight patches fail native application, and two apply but fail tests.
The new gold control passes all 11 tests; the applicable incorrect control
fails the target regression. No candidate is repaired using evaluation feedback.

The original run submitted four turns (three with known usage, one unknown).
The extension submitted all 16 planned turns with known usage. Combined known
usage is 371,589 tokens and USD 0.8969655 in standard API-equivalent valuation,
including the original interrupted attempt's known first stage. The unknown
original turn is not zero. New generation alone uses 314,793 tokens and
USD 0.758976. Subscription fees are not measured API charges.

The generation protocol was published before dispatch in commit 5f7ebf9.
Original model inputs, full stage outputs, exact diff exports, runtime package
identities, native logs, control attempts and hashes are retained. The upstream
SWE-bench harness is unchanged and pinned; the task image has the previously
documented NumPy adaptation. This is one issue, not a SWE-bench Lite score.

Replay without model calls or Docker:

    python -m reproducibility.swe_smoke.completion_evidence --archive reproducibility/results/20260908_codex_mini_swe_completion --original-root reproducibility/results/20260908_codex_mini_swe_dev1 --out tmp/swe-completion-replay

The ten-row CSV replays byte for byte. The JSON additionally contains resolved
local provenance paths, which change when the archive is relocated. Third-party
source licenses are retained in the original companion archive.
