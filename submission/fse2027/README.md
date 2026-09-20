# FSE 2027 submission package

This directory contains the anonymous Research Track paper and its reviewer artifact.

## Deliverables

- `paper/main.pdf`: submission-ready anonymous PDF.
- `paper/main.tex`, `paper/body.tex`, `paper/workflow.tex`, table inputs, and `paper/references.bib`: paper sources.
- `artifact/fse2027-anonymous-analysis-artifact.zip`: anonymous supplementary archive.
- `upload/`: allowlisted final upload copies and their SHA-256 checksums; build logs and local path metadata are excluded.
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

After extracting the archive, run its dependency-free table checkpoint and native-evidence check:

```text
python reproduce_tables.py
python verify_native_evidence.py
```

The stronger replay installs the two pinned scientific packages and recomputes both statistical summaries from anonymous assignment ledgers:

```text
python -m pip install -r requirements.txt
python reproduce_full_analysis.py
python reproduce_source_sensitivity.py
```

## Submission state

The PDF is 15 pages in total. Main material, including the Data Availability statement, ends on page 13 and references occupy pages 14--15, so it remains below the 18-page content and 4-page reference limits. The review class, anonymity switch, embedded fonts, detailed AI-use disclosure, and post-conclusion Data Availability statement are present. The archive has an internal SHA-256 manifest and is scanned for author names, local user paths, and institution names during every build. Benchmark code examples are allowed to contain synthetic addresses and generic filesystem literals.

Before uploading, the authors must complete the HotCRP-only items: freeze the author list and order, enter conflicts, confirm no simultaneous refereed submission, and check the live deadline countdown.
