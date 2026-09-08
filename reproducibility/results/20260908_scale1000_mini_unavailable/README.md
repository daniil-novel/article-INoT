# Scale1000 mini attempt: unavailable diagnostic

This directory preserves the first interrupted availability attempt for the
prospective 1,000-task, three-repeat study. It is **not model-quality data**
and must not be included in quality, pass-rate, or treatment comparisons.

The original generation tree and launcher evidence were copied byte-for-byte
from `reproducibility/runs/scale1000-v1`. The copied generation retains the
stale `status.json` value `running` and the original `DISPATCH.lock` on
purpose. `manual_stop.json` records the later manual-stop evidence and the
process check; it is the authoritative archive-level stop record.

The frozen manifest contains 15,000 assignments. The preserved attempt has
187 submitted turn folders, zero completed result files, and zero completed
cells. The assignment status ledger records 180 unsupported-model traces, 7
interrupted traces, and 14,813 untouched assignments. Every assignment has
`quality: null`; no unknown usage counter is converted to zero spend.

The unsupported traces contain the Codex CLI's unsupported-model/fallback
metadata failure. The interrupted traces were still active when the parent
dispatcher was manually stopped. No successful model completion was observed.

The BigCodeBench license is preserved as `BigCodeBench-LICENSE`. This archive
does not replace the original run and does not authorize resubmission of any
submitted assignment.
