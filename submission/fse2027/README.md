# FSE 2027 submission package

This directory contains the anonymous Research Track paper and its reviewer artifact.

## Deliverables

- `paper/main.pdf`: submission-ready anonymous PDF.
- `translation-ru/main.pdf`: expanded Russian reading version, preserving the September 22 author-comment revisions; not the official submission.
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

## Revision audit, 3 October 2026

Seven independent AI review contexts covered methods, numerical results, novelty, journal-level scope, academic English/reference integrity, reproducibility, and Russian concepts. These are internal reviews, not human native-speaker or external peer reviews. Initial reports and bounded follow-up verifications are in `review/2026-10-03/`; the 17-part synthesis is `review/FINAL_REVIEW.md`.

The English revision contains 16 pages: content ends on page 14; exempt Data Availability and references begin on page 15; references span two pages. The expanded Russian reading version contains 27 pages and preserves the September 22 author-comment explanations. Both PDF builds completed without unresolved references or overfull boxes; all pages were rendered and visually checked, fonts are embedded, and author metadata is empty. All eight quantitative table sequences match after decimal normalization. Exact bytes are recorded in `review/FINAL_VALIDATION.json` and `upload/SHA256SUMS.txt`.

New analyses use retained data only: four retrospective simultaneous precision intervals, first-session/later-session diagnostics, and absolute resource-scale differences. They are marked retrospective and do not replace the original Holm tests. The manuscript corrects actual execution dates, cost-subtotal scope, local prespecification versus external preregistration, and prior negative multi-agent results. No new model generations, independent-family experiment, equal-compute comparison or mechanistic ablation was conducted.

The revised artifact contains 337 files, including 336 manifested payloads. Its native environment recipe now uses archive-local inputs, the complete historical freeze, exact selected evaluator dataset and strict NLTK hash verification. The retained historical Dockerfile remains evidence. The reconstructed recipe is not a byte-identical historical-image export; a fresh build/native rerun remains unverified because the Docker engine was unavailable. The replay helper prints a command by default and requires `--execute` to launch isolated generated-code tests.

The final archive passed the table checkpoint, full primary/mini/SCC statistical replay, all 16 source-component draw distributions, retrospective-diagnostic checkpoint and verification of all 14,961 primary candidate-to-report records/control hashes. Run the new diagnostic after extracting:

```text
python revision_diagnostics.py --expected primary/revision_diagnostics.json
```

## Public package and live submission

Reviewer materials are available at <https://anonymous.4open.science/r/role-calls-replication-2026/>. The source is the artifact-only branch `codex/fse2027-review-artifact`; auto-update is disabled, and expiry on 30 September 2027 removes content without redirecting to the author repository. The current frozen commit and access-verification boundary are recorded in `review/FINAL_VALIDATION.json`.

HotCRP paper **#2886** was finalized after author approval on 2 October 2026 with the original 15-page PDF (checksum prefix `1c37bf6a`). A newly built local PDF or GitHub publication does not replace that submission. A materially revised PDF/abstract requires concrete author approval and live confirmation. The release record distinguishes local revision, public artifact and HotCRP state.
