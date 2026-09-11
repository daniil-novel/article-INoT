# Official-template preflight

12 September 2026, Europe/Moscow. This is a build check of the conference's
example, not of our future eight-page submission.

- Downloaded the ZIP linked by the official 2027 submission-instructions page.
- Extracted all eight files after checking that each destination remains within
  the template directory. Original bytes are unchanged; hashes are in
  `template_provenance.json`.
- Compiled a separate temporary copy of `AAMAS_2027_sample.tex` with the existing
  MiKTeX/latexmk environment, without modifying `aamas.cls` or its layout.
- Build completed successfully. PDF: two US Letter pages (612 × 792 points),
  PDF 1.5, no encryption or JavaScript. All listed fonts are embedded; Libertine
  and Biolinum are present. No unresolved-reference or overfull warning was found.
- Visually checked the first page: anonymous author display, placeholder
  submission number, Research Paper Track heading, Hanoi dates and the 2027
  reference/copyright block render as supplied.

The unchanged official example produces the existing compiler diagnostic
`\end occurred when \ifx on line 20 was incomplete`. Compilation still returns
success. This is recorded for the final build audit; the style was not patched
to suppress it. The actual manuscript must be checked independently, including
its references, all pages, metadata and figure descriptions.

The real submission number is not available before abstract registration. The
template's placeholder is not acceptable in the final upload. No inference about
scientific quality, AAMAS scope or readiness to submit follows from this smoke test.
