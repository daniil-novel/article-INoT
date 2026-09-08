# Final-newline export sensitivity

Specified on 8 September 2026 after the complete ten-candidate native result,
before this additional evaluation. No new model calls are used.

The frozen fence extractor strips outer whitespace, including the final newline.
The native patch logs include newline warnings as well as malformed patch
headers. To test whether this export boundary explains the observed failures,
append exactly one final LF to every one of the ten canonical predictions where
absent, then reevaluate all ten with fresh run IDs in the same controlled image.
No code, file name, hunk count, header, context or reference is changed. Do not
select only failed application cases or keep whichever version performs better.
Preserve original and transformed prediction hashes and all native outcomes.

This is a post-observation sensitivity diagnostic, not a new confirmatory arm.
It cannot retrospectively change the original estimates. Report whether the
native classification changes and whether any issue becomes resolved; if any
does, explicitly attribute the difference to the export transformation. Tests
and candidate code are never repaired using the reports.
