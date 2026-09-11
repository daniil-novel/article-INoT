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
None of those final checks is established by this size measurement.

Do not silently omit assignments or replace full responses with summaries to
meet the limit. If every desired raw record still cannot fit, state the exact
supplement scope and preserve the complete original records separately. The
paper must remain scientifically understandable without a repository. Lossless
file packaging does not change the uncompressed prompts used in the experiment.
