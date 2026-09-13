# Full raw anonymous portability report

Date: 2026-09-13

The staging copy at `E:/Temp/aamas-full-anon-v1` was built from
`reproducibility/results/20260912_scale1000_luna_full` without compression.
It contains 177,241 files (340,433,367 bytes after the regenerated inventory),
including all 26,968 `generation/turns/*/events.jsonl` streams and their
transport records. The helper used was
`reproducibility/aamas_supplement/full_raw_anonymize.py`.

The transformation is restricted to operational JSON metadata: local command
paths and session/thread identifiers in turn transport records, runner/session
metadata, and selected control metadata. Prompt files (26,968 exact byte
matches) and all retained `result.json.final_text` values (26,936 exact value
matches) were checked. Science-bearing ledgers and inputs were byte-identical:
`analysis/candidate_records.jsonl`, `analysis/summary.json`,
`analysis/native_audit.json`, `generation/results.jsonl`, `generation/tasks.json`,
and `inputs/scale1000-v1/input/prepared.jsonl`. Frozen replay source files were
copied unchanged. Per-turn `result.json.files_sha256` entries were rebased for
the transformed transport files; the pricing sidecar and exact-byte evidence
manifest were recomputed from the staged records.

## Commands and exits

1. `python reproducibility/aamas_supplement/full_raw_anonymize.py ...` — exit
   0; 26,974 JSON records transformed, 107,744 transport hash fields rebased.
2. `python E:/Temp/aamas-full-anon-v1/provenance/scale_replay.py --archive E:/Temp/aamas-full-anon-v1` — first probe exit 1 because the original pricing sidecar no longer matched transformed session metadata.
3. Recomputed `pricing_scope.json`, refreshed `EVIDENCE_MANIFEST.json`, then ran
   the same unchanged command — exit 0; 15,000 assigned rows and all raw,
   native, usage, control, ledger, and complete statistical checks passed.
4. `python E:/Temp/aamas-full-anon-v1/source_family_replay.py` — exit 0; 15,000
   rows, 4 graphs, 17 replayed files.
5. `python E:/Temp/aamas-full-anon-v1/replay_verify.py` — exit 0; 15,000
   records, 1,000 task clusters, all four primary contrasts recomputed.

The archive remains an uncompressed staging copy pending the coordinator’s
publication decision. No live SCC source or original verified archive was
modified.
