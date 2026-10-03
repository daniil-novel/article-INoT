# July 2026 Hybrid-INoT: anonymous ACM formatting edition

This edition preserves the selected July scientific manuscript. It is a formatting and anonymity conversion, not a revised experiment or a new scientific paper.

## Files

- `paper/Hybrid-INoT.pdf`: submitted anonymous ACM review PDF, 16 pages; named after the article.
- `paper/main.pdf`: identical technical build output.
- `review/Hybrid-INoT-July-2026-yellow-review.pdf`: original 20-page paper with five proposed compression passages highlighted; no text removed.
- `FORMATTING_PLAN.md`: approved plan and implementation status.
- `replication/hybrid-inot-july-2026-anonymous.zip`: anonymous July evidence and offline replay package.
- `hybrid-inot-july-2026-anonymous-source.zip`: editable anonymous LaTeX project.
- `validation/independent_format_qa.md`: independent format and preservation audit.
- `validation/submission-link-qa.md`: verification of the final PDF with the anonymous replication link; the original formatting audit remains frozen.
- `SUBMISSION_RECEIPT.md`: verified HotCRP update record.
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

Only `paper/Hybrid-INoT.pdf` (identical to `paper/main.pdf`), the anonymous source ZIP and the anonymous replication ZIP are intended for blind review. This public author-owned Git repository, the historical source snapshot, the yellow review copy and provenance are delivery/audit materials; do not link them from a blind submission. The private origin manifest is excluded from Git and both review ZIPs.

The package records metrics and usage, not complete generated solutions. Its original HumanEval context profile is retained, not reconstructed from fresh benchmark/tokenizer caches. The SWE-bench path remains approximate, and the original generation environment is not fully locked; the successful offline replay environment is recorded. No new model calls were made. These limitations are preserved rather than masked.

The original formatting release (`43ab3c43`) did not change HotCRP. Following the author's explicit submission instruction, paper **#2886** was updated on 3 October 2026 with this complete July manuscript, its title and abstract. HotCRP confirmed **"The submission is ready for review"**. The submitted 16-page PDF has SHA-256 `058b76af30825e465ce26f214d927d10056c5a0a54032b68f1ecdf7c200754d1`.

The final Data Availability links to <https://anonymous.4open.science/r/hybrid-inot-july-2026/>. This separate, frozen anonymous repository contains the July replication files and downloadable archive; it does not use the later Role Labels artifact. The link addition did not change the scientific body or bibliography. See `validation/submission-link-qa.md` and `SUBMISSION_RECEIPT.md`. Submission readiness is not an acceptance decision.

The submitted filename was changed to `Hybrid-INoT.pdf` at the author's request on 3 October 2026. HotCRP confirmed the update and retained ready-for-review status. PDF bytes and checksum are unchanged.
