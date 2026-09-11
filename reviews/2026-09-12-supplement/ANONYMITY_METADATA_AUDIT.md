# Anonymity metadata audit for a future AAMAS supplement

Date: 2026-09-12

Scope: read-only inspection of `reproducibility/runs/scale1000-luna-v1/generation`, the portable replay/publisher path, and `submission/aamas2027/PREPARATION_PLAN.md`.

## Finding

The completed generation archive is scientifically useful but is not anonymous as retained. Its metadata contains repeated absolute Windows paths, local executable and workspace locations, session labels, and provider thread identifiers. The preparation plan already requires these classes of data to stay out of the anonymous upload while preserving the originals separately (PREPARATION_PLAN.md:46-80).

No credentials or secret values were found in the inspected provenance fields: `runtime_provenance.json` records only boolean ambient-setting presence and explicitly says that auth material was not archived. The generation metadata does contain a public pricing documentation URL and task-content URLs (for example benchmark examples); these are not manuscript-host links. No OpenReview, manuscript-host, or author repository link was identified in the portable metadata inspected here. URL-bearing task/prompt content is scientific input and should be retained only where the supplement's prompt policy permits it.

## Compact inventory

The following categories contain identifying or host-dependent values. Examples are deliberately shortened; no full absolute value, opaque payload, credential, or generated reasoning is reproduced.

| Category | Representative fields/files | What is exposed | Replay relevance |
|---|---|---|---|
| Local user/workspace paths | `runtime_provenance.json`: `empty_working_directory`, `instructions_path`, `native_executable_path`, `prefix`; `runtime.json` and session `runtime.json`: `prefix` | Drive letters, the Russian workspace name, `tmp/codex-runtime`, Node/Codex executable paths, and the generation `empty` directory | Operational in reconstruction: `collect.py` extracts `--cd` and `model_instructions_file` from each turn's `argv.json` and compares the full command to the recorded runtime prefix (collect.py:55-57). |
| Per-turn command metadata | every turn `argv.json`; session `command.json` | Same executable, `--cd`, and instruction-file paths plus model/provider/configuration arguments | The command is parsed and checked for exact equality; it is not merely covered by a hash (collect.py:55-57). |
| Generation/session identifiers | top-level `status.json`; failure records; `sessions/*/completion.json`, `pending.json`, and `command.json`; session directory names | Numeric session labels and the session field copied into status/failure records | Used for provenance/accounting and inventory linkage, but not as a scientific input to the portable summary. |
| Provider thread identifiers | `turns/*/events.jsonl`, `thread.started.thread_id` | Opaque per-turn thread IDs | Parsed event streams are used for response/usage reconstruction; the thread ID itself is not used to select assignments or calculate statistics. |
| Scientific URL content | `tasks.json` and some prompt/response payloads; `manifest.json` pricing `source` | Benchmark/example URLs and one public model-pricing documentation URL | Input/response content must remain exact for scientific reproducibility; URLs should be classified rather than blindly redacted. No manuscript-host URL was found in this scan. |

As a compact programmatic check, the archive has 26,968 JSON/text files matching the absolute-path pattern and 26,968 matching the workspace-path pattern under the selected generation tree; 14,998 JSON files contain a `session` field or path-like session metadata, and turn event streams contain `thread_id` records. These counts are inventory signals, not a claim that each file has a distinct path or identifier. The large counts arise because per-turn command and event metadata are repeated across the archive.

## Immutable evidence versus anonymous derivative

The original generation tree, its evidence manifest, and all recorded hashes must remain unchanged and private. A future anonymous supplement should be a separately created derived package. Replacing path or identifier strings in the original files would change their bytes, invalidate their exact evidence-manifest entries, and make the old hashes false; refreshing a manifest after redaction would describe a different archive rather than preserve the original evidence identity.

The smallest defensible package procedure is:

1. Copy the complete scientific subset required by the supplement into a new staging directory, keeping all prompts, complete responses, candidates/assignments, failures and unavailable records, and every usage counter. Do not alter scientific JSON values or truncate response text.
2. Apply a field-aware metadata transform only in the copy: replace absolute paths in `runtime_provenance`, runtime/session command records, and per-turn `argv` with stable placeholders; replace session directory labels, `session` values, and provider `thread_id` values with deterministic opaque labels; remove or replace only non-scientific host/account fields. Preserve model, version, provider, reasoning setting, timestamps where scientifically required, assignments, responses, failures and counters.
3. Add a small mapping-free replay profile or adapter for the derived package. It must resolve placeholders to the staging tree and compare the normalized command structure, or explicitly skip host-path equality while still checking model/configuration semantics and all scientific file hashes. Do not silently use the original replay script against transformed `argv`.
4. Recompute a new manifest for the derived package, record that it is an anonymous derivative of the immutable archive, and run extraction plus portable replay from a clean unrelated directory. Keep the original manifest/hash inventory beside the private source archive; do not claim its hashes remain valid for the derivative.
5. Scan the staged ZIP for absolute paths, credentials, Git history, internal review logs, manuscript-host links, and archive names before measuring the final package. Follow the plan's 25 MB measurement and extraction checks (PREPARATION_PLAN.md:67-80).

This preserves every requested scientific record while changing only host/account metadata in the future upload. It also keeps AI-method disclosure recoverable as required by the plan (PREPARATION_PLAN.md:48-54), subject to the same field-aware path/identifier transformation.

## Portable replay issue and conclusion

The current portable replay is archive-relative for its source installation and analysis outputs: `scale_replay.py` verifies frozen source/protocol hashes, imports the archived source tree, and compares reconstructed ledgers and summary bytes (scale_replay.py:23-39, 51-80). However, the archived collector still consumes path-bearing `argv` values to derive the instruction and working-directory paths and requires exact command equality (collect.py:55-57). Therefore an anonymous copy with paths replaced cannot pass the current replay unchanged, even if all response, assignment and usage records are untouched. Session and thread identifiers appear to be safe to relabel for scientific computation, but this was not treated as proof that every downstream tool ignores them.

The unresolved action is consequently a packaging/replay adapter: either make the derived package's replay normalize these host paths before comparison, or retain a private path-bearing replay sidecar unavailable in the anonymous ZIP. The current evidence supports the first option as the smallest public-package change, provided the adapter's own code and checks are included and a fresh derived-package manifest is published.
