# Supplement size preflight

Measured on 12 September 2026 from the terminal primary-study generation.
This is a packaging check, not a new experimental result or a ready upload.

The [AAMAS instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/instructions/)
allow one anonymous supplementary ZIP of at most 25 MB. We use 25,000,000 bytes
as the conservative working limit rather than relying on a binary interpretation.

## Measured payload

The inspected payload contains all 14,961 retained candidate-cell files and every
file in all 26,968 retained CLI-turn directories: prompts, responses, events,
arguments, statuses and standard-error logs. In total, 176,737 files contain
199,732,768 bytes. The two independent sizing passes obtained the same inventory
of paths, lengths and file hashes. The original contents were not edited.

This is only the `cells` and `turns` portion of the completed primary generation.
It excludes other generation metadata, native evaluation reports, the SCC study,
benchmark data, analysis, source code and scientific documents. Counts of stored
turn files are not counts of successful candidates or observed quality outcomes.

| Lossless representation | Exact ZIP bytes | Decimal MB | Below working limit? |
|---|---:|---:|---|
| One ZIP member per original file, Deflate 9 | 122,705,888 | 122.71 | No |
| One JSONL member containing paths and Base64 bytes, Deflate 9 | 48,728,795 | 48.73 | No |
| One normalized TAR member, Deflate 9 | 25,474,954 | 25.47 | No |
| One normalized TAR member, ZIP LZMA | 14,087,737 | 14.09 | Yes, for this payload only |

ZIP headers were streamed to a counter and checksum sink; no upload archive was
saved. Entry dates were fixed, and the TAR preserved file contents with normalized
metadata. Deflate used level 9. ZIP LZMA used Python's default encoder; it was not
assigned a claimed numeric preset. The exact settings and checksums are retained
in [the measurement record](preparation/supplement_size_measurements.json).

## Consequences for the final package

There is a feasible representation for this primary-generation payload alone.
Its remaining allowance of 10,912,263 bytes must not be presented as enough for
the unmeasured SCC records, native evidence and documents. Measure the complete
anonymous supplement after both studies finish; do not extrapolate a finished
package size from this subset.

Keep the main technical appendix, instructions and complete assignment/resource
tables directly accessible in the outer ZIP. A nested archive for large raw
records is an option only after the full package has been measured and tested.
Deflate has broader reader support than ZIP LZMA; include clear extraction
instructions and verify the chosen format in a clean environment. If needed,
test different lossless member ordering or packaging before deciding what fits.

The current raw files may contain identifying local paths. They have not passed
anonymity review and must not be uploaded as measured. Prepare a separate copy,
preserve generated programs and assessed outputs, and document any metadata
redactions without overwriting the original evidence. A final package requires
an extraction and byte/record round-trip check, scientific replay at its stated
scope, an anonymity check, and an inventory of all included and omitted material.
None of those final checks is established by the initial size measurement.

Do not silently omit assignments or replace full responses with summaries to
meet the limit. If every desired raw record still cannot fit, state the exact
supplement scope and preserve the complete original records separately. The
paper must remain scientifically understandable without a repository. Lossless
file packaging does not change the uncompressed prompts used in the experiment.

## Saved archives and byte-for-byte readback

A subsequent check saved two private ZIPs containing the same 176,737 files and
199,732,768 source bytes. Both passed a complete ZIP CRC check and streaming TAR
readback: every recovered member name, size and byte sequence matched the retained
original. The source inventory and metadata snapshots remained unchanged.

| Order of files inside TAR | Saved ZIP bytes | Full byte comparison |
|---|---:|---|
| Original path order | 14,087,713 | Passed for all 176,737 files |
| Basename, then path | 15,721,711 | Passed for all 176,737 files |

Grouping by basename did not improve size. Retain path order as the current
candidate. The saved path-order archive uses a seekable ZIP output, whereas the
initial measurement used a non-seekable counter; the 24-byte size difference is
container overhead, with an identical source inventory. This check uses Python
3.11.5's standard ZIP LZMA reader and TAR reader. It establishes recoverability
of the measured files, not compatibility with every desktop archive application.
The records include exact settings, archive hashes and limitations:
[path order](preparation/supplement_roundtrip_path.json) and
[basename order](preparation/supplement_roundtrip_basename.json).

These private archives remain unredacted and must not be uploaded. The readback
was into streams, not a clean filesystem tree; final extraction, anonymity review
and scientific replay are still required. Other metadata, SCC records, native
reports, datasets, code and documents remain outside this measured subset. The
10,912,287 bytes left below the working limit are not proof that the complete
supplement fits.

## Metadata transformation and replay

The [metadata review and correction](../../reviews/2026-09-12-supplement/DECISIONS.md)
identified local paths and session/thread identifiers in the retained metadata.
The first review overstated the need to change the replay code. A separate check
of all 26,968 retained command arrays shows that consistent relative placeholders
can pass the frozen command comparison without an adapter. Single-component
placeholders avoid differences between Windows and POSIX path separators.
Model, reasoning level and every other non-path argument remain unchanged;
deliberately changed model/reasoning arguments still fail the comparison.
[The metadata check](preparation/anonymous_command_check.json) does not claim
that an anonymous derivative or full replay has already been completed.

Apply such a field-aware transformation only to a new copy. Rebuild all hashes
of changed command/event files and every affected reference in per-turn records,
pricing/provenance sidecars and the new outer manifest. Keep frozen model
instructions, scientific prompts, full responses, candidates, assignments and
usage counters intact. The original hashes identify only the original archive.
Inspect SCC and native metadata separately, then verify the complete anonymous
copy by extraction and scientific replay.
