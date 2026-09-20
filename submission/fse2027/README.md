# FSE 2027 submission package

This directory contains the anonymous Research Track paper and its reviewer artifact.

## Deliverables

- `paper/main.pdf`: submission-ready anonymous PDF.
- `paper/main.tex`, `paper/body.tex`, `paper/workflow.tex`, table inputs, and `paper/references.bib`: paper sources.
- `artifact/fse2027-anonymous-analysis-artifact.zip`: anonymous supplementary archive.
- `review/FINAL_REVIEW.md`: final reviewer-rubric gate review and residual-risk ledger.
- `review/REFERENCE_AUDIT.md`: source-level audit of every reference rendered in the PDF.
- `REQUIREMENTS.md`: verified FSE 2027 requirements and final administrative checklist.

## Build and verify

Compile from `paper/` with a current `acmart` installation:

```text
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Build the supplementary archive from the repository root:

```text
python submission/fse2027/artifact/build_artifact.py
```

After extracting the archive, run its dependency-free table check:

```text
python reproduce_tables.py
```

The stronger replay installs the two pinned scientific packages and recomputes both statistical summaries from anonymous assignment ledgers:

```text
python -m pip install -r requirements.txt
python reproduce_full_analysis.py
```

## Submission state

The PDF is 13 pages in total. Main material ends and references begin on page 12, so it remains well below the 18-page content and 4-page reference limits. The review class, anonymity switch, embedded fonts, AI-use disclosure, and post-conclusion Data Availability statement are present. The archive has an internal SHA-256 manifest and is scanned for author names, e-mail addresses, local paths, and institution names during every build.

Before uploading, the authors must complete the HotCRP-only items: freeze the author list and order, enter conflicts, confirm no simultaneous refereed submission, and check the live deadline countdown.
