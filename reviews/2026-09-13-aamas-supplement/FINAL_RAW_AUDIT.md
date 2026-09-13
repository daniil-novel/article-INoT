# Final raw archive audit

Date: 2026-09-13

Audited staging root: `E:/Temp/aamas-full-anon-v1`. Source science archive:
`reproducibility/results/20260912_scale1000_luna_full`.

The staging tree contains 26,968 turn directories and 26,968 retained
`events.jsonl` streams. The regenerated inventory reports 177,240 inventoried
files and 340,433,195 inventoried bytes (the tree also contains the manifest
and ledger). The six science-bearing files checked against the source archive
were byte-identical: `analysis/candidate_records.jsonl`,
`analysis/summary.json`, `analysis/native_audit.json`,
`generation/results.jsonl`, `generation/tasks.json`, and
`inputs/scale1000-v1/input/prepared.jsonl`.

Transport replay from a foreign working directory passed:

- `replay_verify.py`: 15,000 records, 1,000 task clusters, all four primary
  contrasts recomputed;
- `source_family_replay.py`: 15,000 rows, four graphs, 17 replayed files;
- the retained raw streams and all 26,968 turn directories were present.

The original staging ledger was preserved privately at
`tmp/revision/20260913-original-anonymization-ledger.json`. Its public copy
was repaired so `source` and `destination` contain no institution or local
path, and `EVIDENCE_MANIFEST.json` was regenerated afterward. The final public
ledger has `prompt_files_exact: 26968`, `changed_json_records: 26974`, and
`rebased_transport_hash_fields: 107744`.

The metadata scan found local identity outside the ledger. Examples remain in
`controls/*/argv.json`, `controls/*/run-metadata.json`,
`provenance/runtime_identity_noauth.json`, and turn `argv.json`/events: these
include `E:\\ВШЭ\\Курсовая работа\\article\\springer-article`, `C:\\Python311`,
`C:\\nvm4w\\nodejs`, and `.git`-related runtime paths. The scientific payloads
and prompts were not rewritten. This is therefore a reproducible raw archive
with a sanitized operational ledger, but it is not fully author/local-metadata
anonymous until those remaining operational records are separately scrubbed.

`outputs/evidence/aamas-primary-raw-v1.tar.xz` contains the complete staging
root. Its measured size is 22,041,292 bytes (uncompressed tar:
513,951,232 bytes). Extraction completed to an isolated directory with 177,240
non-manifest files, and hashes matched for the ledger, regenerated manifest,
two science payloads, and a retained turn event stream. The SCC archive is
separate and already exceeds the 25 MB combined-package budget; no
combined-package readiness is asserted here.
