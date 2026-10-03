# July 2026 Hybrid-INoT: anonymous ACM formatting edition

This edition preserves the selected July scientific manuscript. It is a formatting and anonymity conversion, not a revised experiment or a new scientific paper.

## Files

- `paper/main.pdf`: complete anonymous ACM review PDF, 16 pages.
- `review/Hybrid-INoT-July-2026-yellow-review.pdf`: original 20-page paper with five proposed compression passages highlighted; no text removed.
- `FORMATTING_PLAN.md`: approved plan and implementation status.
- `replication/hybrid-inot-july-2026-anonymous.zip`: anonymous July evidence and offline replay package.
- `hybrid-inot-july-2026-anonymous-source.zip`: editable anonymous LaTeX project.
- `validation/independent_format_qa.md`: independent format and preservation audit.
- `validation/replication_offline_report.json`: historical evidence replay.

## Formatting

The class is `acmart` v2.20 with `[acmsmall,screen,review,anonymous]`, a single column and the default ACM fonts and margins. The ACM reference-format and permission blocks are retained. The full title is preserved; a short running title prevents header overlap. All 30 references are retained.

The main narrative reaches page 15; references occupy pages 15–16. Counting the shared page in both categories gives a conservative 15 content pages + 2 reference pages, below the initial 18+4 limit. Data Availability follows Conclusion. No scientific text was shortened and no article content was moved to a supplement.

Official rules: https://conf.researchr.org/track/fse-2027/fse-2027-papers

The ACM download endpoint returned HTTP403. The official `acmart` package was recovered from CTAN; `acmsmall-conf.tex` is the current package's renamed conference-small example, generated from its official `samples.dtx`/`samples.ins`. Template class and bibliography style are vendored with their hashes.

## Rebuild

With Python and a LaTeX distribution containing pdfLaTeX, BibTeX and the standard ACM dependencies installed:

```text
python build.py
```

The build runs pdfLaTeX, BibTeX and two resolving passes. It writes the PDF to `paper/main.pdf` and logs under `validation/`. Bibliographic style warnings about fields absent from the original entries are recorded; no missing fields or author names were invented.

## Review materials and boundaries

Only `paper/main.pdf`, the anonymous source ZIP and the anonymous replication ZIP are intended for blind review. This public author-owned Git repository, the historical source snapshot, the yellow review copy and provenance are delivery/audit materials; do not link them from a blind submission. The private origin manifest is excluded from Git and both review ZIPs.

The package records metrics and usage, not complete generated solutions. Its original HumanEval context profile is retained, not reconstructed from fresh benchmark/tokenizer caches. The SWE-bench path remains approximate, and the original generation environment is not fully locked; the successful offline replay environment is recorded. No new model calls were made. These limitations are preserved rather than masked.

This delivery does not change any HotCRP submission or establish scientific acceptance. The independent audit is a formatting/preservation check.
