# Decisions on statistical reporting in the standalone appendix

Date: 2026-09-12

This is one preparatory reviewer (GPT-5.6 Luna, medium), followed by a second
round with the same reviewer. Neither round counts as one of the five fresh
scientific critics required after both large studies finish. The exact authored
requests are retained in [REVIEW_REQUEST.md](REVIEW_REQUEST.md).

## Reports and decisions

- [Initial methods audit](METHODS_REVIEW.md): accepted the distinction between
  the four-test factorial family and two-test SCC family, task-level repeat
  aggregation, bootstrap generators, seeds, order and percentile interpolation.
  The EN/RU appendix now gives the test statistic and defines its quantities.
- [Resource follow-up](RESOURCE_FOLLOWUP.md): accepted the separate eligibility
  rules. Factorial resource contrasts require completed generations and complete
  records in both conditions. SCC's full API-equivalent valuation and total-token
  measures require known counters for every submitted turn; an incomplete
  workflow can still have fully known consumed resources. Known subtotals remain
  separate. The follow-up's field-specific qualification was applied in both
  languages using readable metric names.
- Accepted the distinction between a ratio of paired means and a mean of
  within-task ratios. The appendix gives both equations and identifies exactly
  which interval each analyzer computes, its seed and relevant pair count.
- Accepted the conditional numerical-degeneracy clarification. The frozen
  factorial implementation can emit p = 0 with a null t statistic and a flag for
  constant nonzero differences; SCC reports that test unestimable. The manuscript
  does not present the sentinel as an ordinary valid t-test rejection and does
  not claim that this case occurred. The initial review's suggested shorthand
  about all identical differences was narrowed to the nonzero case; the separate
  p = 1 convention for a constant zero vector is stated explicitly.
- Removed a stale operational-status row from the design table. Its caption
  still makes clear that large-study outcome analyses have not yet been reported.
- The coordinator clarified the Russian wording for complete task data and
  undefined tests and defined the sample mean and sample standard deviation in
  both languages. These are reporting edits, not changes to statistical rules.

## Scope and remaining work

No live quality outcomes were inspected for these edits. Frozen protocols,
manifests, analyzers, assignments and generated records were not changed. No
experimental model requests or additional native tests were started for this
review. Operational status checks were limited to whether the existing pipelines
were running and their completed stages.

The final result integration must check actual degeneracy flags and how any
sentinel affects the fixed Holm family. Raw outputs must remain intact; there is
no permission to silently replace p values or introduce a retrospective test.
The [final readability checklist](../../reproducibility/revision_20260911/FINAL_READABILITY_CHECKLIST.md)
now includes this check and the distinct resource estimands.

## PDF verification

Both manuscripts were rebuilt after the final wording edit: EN 51 pages and RU
55 pages. All page texts were compared with the previous published PDFs. Changed
pages EN 40–41 and RU 44–55 were rendered at 1,800 pixels on the long edge and
visually inspected, including formula layout, table alignment and references.
The added Russian page shifts the later appendices and references. All pages
were checked for words outside the page and replacement characters; neither was
found. The final TeX logs contain no overfull boxes, unresolved references or
oversized-float warnings. Exact hashes and scope are in [PDF_AUDIT.json](PDF_AUDIT.json).

This focused inspection does not replace the full final readability and visual
review after the new results have been integrated. The sparse last Russian
bibliography page is a pagination consequence, not missing content; final
conference pagination will be handled in the separate AAMAS manuscript.
