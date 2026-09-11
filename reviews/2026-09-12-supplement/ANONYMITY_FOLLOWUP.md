# Anonymity metadata audit follow-up

Date: 2026-09-12

Purpose: correct one replay inference in `ANONYMITY_METADATA_AUDIT.md`.

## Correction

The current collector does not resolve or open the `cwd` and instruction paths extracted from `argv.json`. It constructs `Path(...)` objects, then calls `cli_command(runtime['prefix'], cwd, instructions)` and compares the resulting list for exact equality (`generation/sources/scale1000_luna/collect.py:55-57`). `cli_command` stringifies its arguments and inserts them into the command/configuration list; it does not resolve them or test their existence (`generation/sources/codex_luna_subscription.py:121-146`).

Therefore, a consistent in-memory/package transformation can satisfy the existing command equality without a replay adapter: replace the executable/script entries in `runtime.json['prefix']` and every turn's `argv.json` with the same stable relative placeholders, and replace the `--cd` and `model_instructions_file` values in both places with the same stable relative placeholders. For example, `__ANON__/node.exe`, `__ANON__/codex.js`, `__ANON__/empty`, and `__ANON__/instructions.txt` are sufficient as strings for this comparison. The collector's separate checks still read the real archived `generation/instructions.txt` by archive path and compare its bytes to the fixed model policy, so the placeholder need not name an existing file.

This does not make the transformation free. Every changed `argv.json` changes its recorded `files_sha256['argv.json']` in the corresponding `result.json`; those per-turn hashes must be rebuilt. Any changed metadata covered by the outer evidence manifest also requires a new manifest for the anonymous derivative. Session `command.json`, session/runtime metadata, `runtime_provenance.json`, and any copied metadata inventory must be transformed consistently if included. The original archive's manifest and hashes remain valid only for the immutable original; they cannot be reused as the derivative's identity.

The unresolved issue is thus narrower than stated in the first report: the existing replay logic can accept a path-neutral relative representation if all equality participants are rewritten consistently. A separate adapter is optional, useful only if the public package should validate host-independent path semantics explicitly. The required work is a field-aware derived-copy transform, per-turn hash rebuild, outer derivative manifest, and clean extraction/replay check while preserving every prompt, response, candidate/assignment, failure/unavailable record, and usage counter.

No original evidence or scientific outcome was changed during this follow-up.
