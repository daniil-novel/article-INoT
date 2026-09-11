# Supplement preparation: audit decisions and verified scope

Date: 2026-09-12.

This is one bounded technical reviewer, GPT-5.6 Luna medium, with one follow-up.
It is not one of the five final scientific critics. Both reports and the exact
authored requests remain separate: [initial audit](ANONYMITY_METADATA_AUDIT.md),
[correction](ANONYMITY_FOLLOWUP.md), [requests](REVIEW_REQUEST.md).

## Anonymity and replay

Accepted the identified metadata categories: local executable/workspace paths,
session labels and provider thread IDs. The absence of credentials and
manuscript-host links reported by the reviewer is limited to the metadata
inspected; it is not a completed whole-package secrecy or anonymity check.
Scientific URLs must be classified, not blindly removed from prompts or answers.

Rejected the first report's conclusion that a replay adapter is necessary for
path-bearing commands. The collector takes the path values from the command
itself, and the unchanged builder only stringifies them. The reviewer corrected
this inference in a separate report. The coordinator then checked every retained
command array: 26,968 of 26,968 matched the frozen builder before transformation,
and all matched after an in-memory transformation to single-component relative
placeholders. Non-path arguments remained identical. Windows and POSIX path
semantics were checked; changing the model or reasoning argument still caused a
comparison failure. This was metadata-only work and executed no recorded command.

The follow-up's slash-containing placeholder examples are not adopted as a
universal representation: single-component values avoid separator normalization.
No anonymous copy has yet been created. Changed argv/event bytes require new
per-turn hashes and updates to every affected derivative sidecar and outer
manifest. Frozen instructions, source code and all scientific values must stay
unchanged. SCC, native metadata and complete-package replay remain separate work.

## Actual archive readback

The coordinator saved two private TAR/LZMA ZIP representations of all completed
primary `cells` and `turns`, then checked each ZIP CRC and read back every member.
All 176,737 file names, lengths and complete byte sequences matched their source.
No retained source file, metadata snapshot or generation status changed.

Path order produced 14,087,713 bytes; grouping by basename produced 15,721,711
bytes. The latter is larger and is not selected. Both results are retained,
including the negative size comparison. The original streaming measurement and
the saved seekable path-order ZIP differ by 24 bytes of container overhead;
their source inventories are identical.

This was streaming readback with the Python standard library, not extraction to
a clean filesystem and not a scientific replay. The private ZIPs remain
unredacted and are not upload artifacts. The measured subset omits other
generation metadata, SCC, native records, datasets, sources and documents. It
therefore does not prove that the final 25 MB supplement fits.

Exact counts, hashes and scope are in the
[supplement preflight](../../submission/aamas2027/SUPPLEMENT_SIZE_PREFLIGHT.md)
and its linked machine-readable records. No large-study quality outcomes were
inspected for this work, and the manuscript/PDF scientific claims were unchanged.
