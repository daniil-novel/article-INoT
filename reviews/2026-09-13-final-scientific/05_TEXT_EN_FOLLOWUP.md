# English follow-up after post-review edits

## Coverage

This is a targeted follow-up to the prior English audit. I inspected the current source TeX and current rendered PDFs (`submission/aamas2027/paper/main.pdf`, 7 pages; `converted_article_springer.pdf`, 111 pages) for the reported post-review changes and nearby terminology. I did not reread the 111-page edition as a new independent review and did not inspect other critics’ reports. No manuscript files were edited.

## Changes verified

- The current AAMAS source and PDF consistently use “planner, implementer, and reviewer” for the intervention (`submission/aamas2027/paper/body.tex:2,43`); the former “critic” wording is gone from the checked main paper.
- The AAMAS introduction now defines “native evaluation” as execution of the original benchmark tests in a pinned offline environment (`body.tex:4`). This is a useful reader-facing definition.
- The Springer abstract now reports the SCC amendment as “fixes 2,000 assigned task-repeat blocks …: 5,595 workflows complete and 405 remain incomplete” (`sections/revision_en.tex:5`). This removes the earlier implication that all 2,000 blocks were completed.
- The abstract’s “BigCodeBench task clusters” wording was changed to “BigCodeBench tasks” (`sections/revision_en.tex:5`), and the requested conditional/observed-pair scope remains explicit.
- The exact executed prompt strings in the AAMAS paper remain unchanged; no wording change was found in the prompt contract or operation sentences.

## Remaining issues and regressions

1. The task terminology change is incomplete in the converted edition. `sections/scale1000_results_en.tex:4` still says “1,000 task clusters” and then “The task clusters are the task-level units”; `sections/development_calibration_en.tex:7` and `sections/dev40_contrasts_en.tex:2` also retain “task clusters.” If these are ordinary BigCodeBench task IDs, replace them with “tasks” or define “task cluster” once and use it consistently. The current sentence is tautological and may suggest a distinct clustering unit.

2. The SCC abstract rewrite is factually clearer but “fixes 2,000 assigned task-repeat blocks” is still slightly administrative and can be misread as completing them. A smoother form is: “An amended SCC comparison selects the first 2,000 task-repeat blocks (6,000 method assignments) across 956 tasks; 5,595 workflows are complete and 405 remain incomplete.” The current text is acceptable if “fixes” is defined in the methods as schedule selection.

3. The converted edition continues to repeat “native evaluation” throughout the narrative and appendices. The AAMAS definition improves the short paper, but the Springer version should define the term locally or use “original benchmark-test evaluation” in prose.

4. The pricing-date inconsistency remains: methods state rates were checked on 13 September 2026, while the bibliography still says the pricing page was accessed on 8 September 2026 (`sections/standalone_details_en.tex:57`; `sections/revision_references.tex:15`). This is metadata, not a language regression, but it should be aligned before release.

5. The prior terminology/repetition issues remain outside the edited sentences: the Springer text still contains multiple near-identical “does not establish” caveats and the SCC software reference still lacks a direct official repository URL (`sections/revision_references.tex:3`).

## Current disposition

The post-review changes visible in the current AAMAS PDF are coherent and introduce no new English defect in the checked passages. The main unresolved editorial item is incomplete replacement of “task cluster”; secondary cleanup concerns the SCC “fixes” wording, repeated native-evaluation terminology, pricing access date, and the software-reference URL. No conclusion about AI authorship is warranted from these textual observations.
