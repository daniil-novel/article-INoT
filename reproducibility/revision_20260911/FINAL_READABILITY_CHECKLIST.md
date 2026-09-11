# Final readability and visual review

The author explicitly requests a complete readability review **after all results
have been integrated into both manuscripts**. The focused review of 11 September
does not satisfy that later requirement. The subscription reserve has priority:
do not perform model work at 55% remaining or below, or after a latched pause.

## Timing and scope

After the factorial and SCC studies have finished, their recorded outcomes have
been replayed, and the registered analyses and separate sensitivity intervals
have been incorporated, review the entire EN/RU manuscript from abstract through
appendices. Coordinate this with the five fresh scientific critics; preliminary
editorial agents must not be counted as fresh final scientific critics.

1. Read each paragraph for a clear subject, defined terms, a stated comparison,
   and an understandable implication. Remove formulaic transitions, repetitive
   limitations and reviewer-response language while retaining scientific caveats.
2. Define D, SN, SR, MN, MR, SCC and INoT* at their first use. Distinguish a task,
   assignment, repeated generation, model call and evaluated candidate. Identify
   the study and denominator behind each count, rate, contrast and interval.
3. Use labelled tables for task identifiers and dense numerical groupings.
   Explain counts rather than leaving slash-delimited sets in prose. Preserve
   all assignment records, group membership, selection rules and exact values.
4. Check every algorithm and flowchart against the executed procedure. Separate
   prescribed prompt content from observed host execution. Show full input and
   response flow, stopping conditions, extraction and evaluation. The external
   benchmark evaluator must never appear to provide generation feedback in an
   experiment where it did not. Keep SCC-generated tests distinct from hidden
   benchmark tests and environment controls.
5. Prefer an overview flowchart and short, ordinary-language steps. Keep exact
   executed instructions in a legible appendix; typography may change, but not
   the experimental instruction. Explain every placeholder and fallback.
6. Check all plots against the final published data: scales, units, denominators,
   contrast direction, error-bar meaning and descriptive versus adjusted
   inference. Captions must make each panel understandable without guessing.
   Resource ratios must identify their estimand: the factorial interval is for
   the ratio of paired means; the SCC ratio interval is for the mean of within-task
   ratios, with its zero-denominator subset count. SCC's ratio of means is a point
   estimate. Distinguish completed-generation resource pairs, SCC full counters
   for submitted turns, and incomplete known subtotals.
7. Compile both PDFs without unresolved references or overfull boxes. Render
   **every page**, inspect all figures, algorithms and tables at readable scale,
   and inspect the rest for clipping, broken symbols, orphan headings and bad
   float placement. Machine checks for page bounds do not replace visual review.
8. Check EN/RU agreement in facts, qualifications, labels and references. Keep
   the articles self-contained; no repository links, commit identifiers or
   internal artifact paths in either manuscript.
9. Save each reviewer report separately, document accepted/rejected findings and
   remaining limitations, record the exact PDF hashes and verification scope in
   a new review directory, and append REVIEW_CHANGE_LOG.md. Publish the revised
   TeX/PDF/README and check the resulting GitHub checks. Do not describe an
   internal AI review as a journal acceptance or a guarantee of Q1 publication.

## Numerical reporting check after the completed analyses

Inspect the frozen factorial output's `degenerate_difference_vector` flag together
with its t statistic and p value. A constant nonzero task-difference vector is
encoded as p = 0 with a null t statistic; that sentinel is not an ordinary t-test
rejection. SCC marks the corresponding test unestimable. Retain the raw frozen
outputs and fixed test families. If this case actually occurs, report the
constant magnitude and undefined test explicitly, audit its effect on the family
correction, and avoid inferring significance from the sentinel. Do not silently
replace p values, change the frozen analyzer or introduce a retrospective test.
The [preparatory methods review](../../reviews/2026-09-12-decision-rules/DECISIONS.md)
established code behavior only; it did not establish occurrence in the data.

## Existing focused work

[The 11 September readability decisions](../../reviews/2026-09-11-readability/DECISIONS.md)
cover the current §13.4, core algorithm, INoT instruction and relevant figures.
They are an intermediate improvement while the large studies run.
