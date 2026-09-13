# Paused-program inventory (2026-09-13)

This is a bounded read-only inventory of the eight paused selected-method assignments (four SCC and four SR/SN) plus stream-failed `bb91c43531a11932f802d7b9` in `reproducibility/runs/scc1000-luna-v1/generation/assignments`. It does not infer native outcomes or repair primary statuses.

The frozen extraction rule is the byte-identical generation source `reproducibility/runs/scc1000-luna-v1/generation/sources/reproducibility/external_baselines/scc.py` (SHA-256 `5349376721b3938deec45fc1c8b05ce33f7804c792209a1ff34c217ca36801e1`), whose `pilot()` writes `candidate.py` only after `run_session` returns (lines 178–187), and whose upstream transition is `vendor/scc_2024/session.py`. Developer text was extracted with the frozen `code_truncate` and checked with `find_method_name` from `vendor/scc_2024/utils.py` (SHA-256 `b591deeb5d083399730062369afec279954831474677459948506c9857ed2328`). In each archived turn result, the response text field is `result.json` → `final_text`. No Docker or model execution was performed.

Three paused assignments retain an actual developer program in `turns/001/result.json`; the extracted text is not persisted as `candidate.py` because the session was interrupted before return. Their source hashes are recorded in the machine-readable inventory [inventory.json](../../tmp/revision/paused-inventory/inventory.json):

| assignment | task | source | extracted program |
|---|---|---|---|
| `0c1ca5b96627cc9e217c36fd` | BigCodeBench/74 | `turns/001/result.json`; upstream request SHA-256 `cae8f0f79ea52f77c5ae8b359f18c7ff1818fcdee5c83887ac816cac5a9d2747` | 838 bytes; SHA-256 `5e91de1b89216fb2db7814d746ba22529161250e2a1cecb31ed5968d3260127a` |
| `3a7a8311ed77c570b188d89c` | BigCodeBench/31 | `turns/001/result.json`; upstream request SHA-256 `2cf8c43796786fb21dfe95b423261a400f379458e7c367dd925e285cb39103e0` | 711 bytes; SHA-256 `0063db1d79bb1fdcdc2c037ade0a72b4244570c96f5b370fababb74f874a00b9` |
| `aa5b1774457304d543d858b9` | BigCodeBench/1015 | `turns/001/result.json`; upstream request SHA-256 `ac11bea171f68d2c63e8c570350dad267d984f0a2b050b6232970f58ccc5d672` | 1679 bytes; SHA-256 `14111322730b59340a7692dfc205eab6485d443c2d99ad0461fe509b499586a4` |

`195574fb38a0ac2b3e025d14` has only analyst `turns/000/result.json` (BigCodeBench/899); frozen extraction yields zero bytes and no function. `64af9e48fc0b34112bd610ef`, `9552f3c35a0b9df456c9aebb`, `d8c2cd87336c15c99306a81d`, and `ff9e78f3a8c62514ab53891b` have no `result.json`, `candidate.py`, or generated-test input. Stream-failed `bb91c43531a11932f802d7b9` (BigCodeBench/794) has raw `calls_attempted: 0`, no completed first-turn result retained, and no candidate or generated-test input; submitted-turn usage is unresolved. Its status records `CLI exit 1; original stderr retained`, while the turn ledger contains the stream-disconnect error and unknown usage.

The retained three programs are inventory candidates only. Any native diagnostic requires a new, separately frozen diagnostic run; this report assigns no quality or native outcome.
