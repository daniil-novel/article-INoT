# FSE 2027 submission package

This directory contains the anonymous Research Track paper and its reviewer artifact.

## Deliverables

- `paper/main.pdf`: submission-ready anonymous PDF.
- `translation-ru/main.pdf`: expanded Russian reading version, preserving the September22 author-comment revisions; not the official submission.
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

The PDF is 15 pages in total. The conclusion ends on page 13, Data Availability spans pages 13--14, and references occupy pages 14--15, so it remains below the 18-page content and 4-page reference limits. The review class, anonymity switch, embedded fonts, detailed AI-use disclosure, and post-conclusion Data Availability statement are present. The archive has an internal SHA-256 manifest and is scanned for author names, local user paths, and institution names during every build. Benchmark code examples are allowed to contain synthetic addresses and generic filesystem literals.

Before uploading, the authors must complete the HotCRP-only items: freeze the author list and order, enter conflicts, confirm no simultaneous refereed submission, and check the live deadline countdown.

## Final audit, 30 September 2026

Five independent AI review contexts covered methodology, novelty, numerical consistency, FSE compliance, and academic English. Their reports and the resolution ledger are in `review/`; the final gate is `review/FINAL_REVIEW.md`. The English PDF remains 15 pages and the expanded Russian reading version 26 pages. The supplement now contains 325 files, including the frozen SCC controller, upstream prompts/license, adapter and dispatcher. All principal numerical replays and 16 source-component bootstrap distributions passed. `review/FINAL_VALIDATION.json` records the release checks and exact file hashes.

The scientific claim remains specific to the tested fixed-context workflows. Acceptance is not guaranteed. Author details, conflicts, originality/simultaneous-review declarations and final author approval must be completed before external submission.

The concurrent GitHub commit `149f5f8c` was integrated without discarding its author-comment revisions. The Russian version now has extra definitions and formula explanations, so exact structural parity with English is not intended; the numerical sequences in all seven original experimental tables match (`review/RU_NUMERICAL_PARITY.json`). The official English PDF and supplementary upload bytes are unchanged by this integration.

## Anonymous reviewer access, 2 October 2026

The replication package is published at <https://anonymous.4open.science/r/role-calls-replication-2026/>. The mirror freezes commit `5498b5378d4167083eeca40fe0c930b322af362e` of the artifact-only branch `codex/fse2027-review-artifact`, with automatic updates disabled. It contains the 325 extracted supplement files plus the original archive. The mirror expires on 30 September 2027 and then removes the material without redirecting reviewers to the author's repository.

The live HotCRP form has only a paper upload field, so the English PDF and Russian reading version now include this link in Data Availability. Both PDFs were rebuilt and visually checked; the scientific content and supplement archive are unchanged. See `review/ANONYMOUS_ACCESS_2026-10-02.md` for the access checks and their limitations.

The sole author's ORCID was registered, its email was verified, and the identifier was saved in HotCRP. After explicit author approval, submission **#2886** was finalized on 2 October 2026. HotCRP confirms that the paper is **ready for review** and no further action is required. The uploaded PDF checksum prefix remains `1c37bf6a`; see `review/SUBMISSION_STATUS_2026-10-02.md`.
