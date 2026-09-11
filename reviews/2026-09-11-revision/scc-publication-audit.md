# Future SCC publication audit (preparatory)

Added `reproducibility/revision_20260911/publish_scc.py` as a future-facing
publisher for the completed SCC 1,000-task study. It is intentionally separate
from the frozen dispatcher, exporter, and finisher and was not run against the
main study.

The publisher refuses active or unfinished generation, an active dispatch
lock, an incomplete 9,000-row ledger, missing saved strict analysis/native
audits, incomplete nine-group native evidence, and an existing output folder.
Before copying bytes it regenerates the immutable export in a temporary
directory, compares it byte-for-byte with the retained predictions, revalidates
all nine retained native groups and the control environment, joins native
audits back through `scc_finish._records`, and recomputes strict `scc_analyze`
in a temporary directory for exact comparison with the saved summary. The
output copy retains raw turns, requests, histories, generated tests,
native/control evidence, inputs, runtime metadata including safe token
counters, source hashes, requirements-related source files, licenses, and a
portable verifier. It excludes secrets/authentication data, virtual
environments, binaries, and Git metadata.

The publisher has an offline `--verify --archive` mode performing the same
export/native/join/recompute checks against the archive's local source tree.
Focused refusal and tampered-ledger tests pass **4/4** in the isolated replay
environment. No model calls, Docker/native evaluations, or main-study
publication were performed. A completed main-study archive still requires
root-side protocol freeze and independent review of the final 9,000-row and
nine-native-group evidence before publication.
