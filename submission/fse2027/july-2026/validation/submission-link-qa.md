# Independent QA: anonymous replication-link addition

**Result: PASS**

Baseline: `43ab3c43`. Final PDF SHA-256: `058b76af30825e465ce26f214d927d10056c5a0a54032b68f1ecdf7c200754d1`; **16 pages**.

Only the Data Availability paragraph changed: its local-only accompaniment statement now gives the anonymous repository URL and names the downloadable archive. The scientific body is byte-identical, and title, abstract, keywords and all 30 bibliography entries remain unchanged. Pages 1-14 also have identical extracted PDF text to the committed version.

All 21 font resources are embedded; author Info is empty and XMP creator is anonymous. No checked personal identifiers or obsolete role-calls link occur in the PDF. The new anonymous URL is a clickable URI annotation. Build log has no errors, overfull boxes, unresolved references or package/LaTeX warnings. Seven nonblocking underfull-box diagnostics are retained in the JSON report; the reviewed pages show no resulting layout defect.

Rendered pages 1, 15 and 16 were inspected: no clipping, overlap or broken bibliography; the URL wraps correctly. Renders postdate the rebuilt PDF.

This audit validates the administrative change and its link annotation. Live repository/download verification is recorded by the submitting agent. This reviewer's web fetch returned URL not accessible, so independent live access is not asserted; scientific acceptance is not assessed. The previous frozen QA files were not altered.

- PASS: only data availability source change.
- PASS: data availability change is exactly url plus downloadable archive.
- PASS: scientific body byte identical to commit.
- PASS: references bib byte identical to commit.
- PASS: title abstract keywords unchanged.
- PASS: all 30 bibliography entries retained.
- PASS: pdf expected sha256.
- PASS: pdf pages 16.
- PASS: pages 1 to 14 extracted text identical to committed pdf.
- PASS: all fonts embedded.
- PASS: author info empty.
- PASS: xmp creator is anonymous.
- PASS: no identifying terms or old artifact link.
- PASS: anonymous link is pdf uri annotation.
- PASS: build has no errors, overfull boxes, unresolved references or package warnings; underfull diagnostics recorded separately.
- PASS: visual pages 1 15 16 pass.
- PASS: renders are newer than pdf.
