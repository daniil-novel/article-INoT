# Coordinator presentation validation

The preparatory renderer was not accepted solely on its initial tests. It used
the wrong completed-generation status, accepted an empty manifest, emitted
unescaped implementation names, and put all 956 task rows into one table. Those
issues were corrected. Its original preparation report remains as history.

The current renderer binds the actual published amendment selection, verifies
the complete file manifest, checks all 6,000 task/method/repeat identities and
the 941 eligible tasks, and requires the final amended study scope and both
contrasts. It preserves native status, quality, format and generation state in
the selected CSV. Unknown is never converted to failure by presentation code.

The coordinator rewrote summary tables to report percentage points, readable
contrast labels, both fixed-denominator scopes, two distinct resource-ratio
estimands with intervals, and source-group and restart sensitivities. Tiny
p-values use scientific notation; unavailable tests remain unestimable.

Five focused tests pass against a synthetic fixture processed by the actual
amended analysis function. The fixture contains 956 tasks, 941 eligible tasks,
2,000 selected blocks and 6,000 cells. It is not a sample of native results.
Both language layouts were compiled with the unchanged full-paper class:
27 pages each, no overfull boxes or LaTeX errors after repair. Ten rendered
pages were visually inspected: EN 1–4 and 27; RU 1–4 and 15. The first, middle
and last assignment tables, all summary table types, and unselected versus
ineligible marks are legible. The final real-data versions still require
their own rendering and numerical reconciliation.

Synthetic sources, PDFs and logs are retained privately in
`tmp/revision/presentation-preview-v2`. They must not enter a manuscript,
results archive or conference supplement as research outcomes.
