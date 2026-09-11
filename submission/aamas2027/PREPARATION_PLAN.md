# Conference adaptation after the research is complete

This plan extends the existing research objective. It does not authorize changing
frozen experiments, selecting favourable results, or skipping the final reviews.

## Prerequisite evidence

Complete the primary 1,000-task/5-condition/3-repeat study and the paired SCC
1,000-task/3-method/3-repeat study. Preserve all submitted failures and unavailable
observations; do not retry them or treat unknown outcomes as failures. Finish
native evaluation, replay the published records and statistics, and report the
separate source-group sensitivity intervals. Integrate findings into the full
EN/RU articles, complete the final readability checklist, and obtain five fresh
scientific reviews with adjudication and separate records in REVIEW_CHANGE_LOG.md.

## Separate branch

`codex/aamas-2027` is reserved for conference preparation. While experiment
dispatchers are alive, do not switch their working directory to another branch.
Use a separate worktree when actual conference editing starts. Bring in the
completed reviewed research version without replacing or rewriting the main
research history. Keep subsequent conference commits on this branch.

## Eight-page argument

Write an independent conference paper from the completed evidence, preserving
Hybrid-INoT's connection to the original work. Do not squeeze the existing long
article into the template by changing fonts, margins or spacing. Retain the
scientific essentials in the main PDF; detailed inventories belong in a separate
technical supplement. A provisional content budget is:

| Content | Approximate pages |
|---|---:|
| Problem, contribution and close prior work | 1.5 |
| Method, observable boundaries and readable workflow | 1.5 |
| Experimental design, controls and statistical rules | 1.5 |
| Completed primary and SCC evidence with intervals | 2.0 |
| Robustness, limitations and implications for agent workflows | 1.5 |

This is an editorial allocation, not a conference rule. Revise it for the actual
findings. Lead with the supported scientific contribution, including a null or
negative result if warranted. Distinguish instructed roles, separate calls,
actual SCC interaction and external evaluation. Do not rebrand unobserved roles
as independently acting agents to satisfy the GAAI scope.

## Files to deliver when ready

- `upload/main.pdf`: anonymous 2027-format paper with real submission number.
- `upload/supplementary.zip`: one anonymous ZIP below the 25 MB limit, containing
  a technical appendix, exact experimental instructions, complete compact
  assignment/outcome/resource tables and the necessary additional calculations.
  Include an accurate AI-method-assistance disclosure with recoverable prompts,
  tool names and recorded versions. Follow [the disclosure preparation record](AI_ASSISTANCE_PREPARATION.md)
  and do not misdescribe this work as polishing only.
- `author-kit/source.zip`: clean compilable TeX, supplied unmodified style and
  bibliography files, and vector figures. This author package is separate from
  the anonymous upload and is not claimed to be required at abstract submission.
- `author-kit/openreview_fields.md`: final matching title, abstract, TL;DR,
  area/topics and clearly separated author-only declarations. Do not fill unknown
  personal declarations with guesses.
- `author-kit/SUBMISSION_GUIDE_RU.md`: short instructions tied to the actual final
  files and current OpenReview form, including how to obtain and insert the ID.
- `author-kit/VALIDATION_REPORT.md`: page count, template identity, fonts,
  anonymity findings, supplement contents/size, completed scientific reviews,
  figure/data checks, remaining author actions and exact package identity.

Supplementary tables preserve all assignments; ZIP compression is only file
packaging, not experimental context compression or selective evidence removal.
Measure the package early. Do not claim a complete raw-output archive fits into
25 MB without testing it. The [first measured size preflight](SUPPLEMENT_SIZE_PREFLIGHT.md)
shows 14.09 MB for only the completed primary cells/turns in a TAR/LZMA ZIP;
an ordinary file-by-file Deflate ZIP is 122.71 MB. Neither is a finished anonymous
supplement. Re-measure the complete contents and test extraction before choosing
the final layout. If full raw outputs cannot fit, disclose the exact
contents and preserve complete compact records plus methods; arrange any further
anonymized material only under the final official rules and the author's scope.
The subsequent saved-archive check in the same preflight document recovered all
176,737 measured files byte-for-byte; path order was smaller than basename order.
It still does not establish complete-package size or final filesystem extraction.
For the anonymous derivative, the primary command comparison accepts consistent
single-component relative placeholders without changing frozen replay code.
Rebuild all affected metadata hash references and sidecars, preserve scientific
values and frozen sources, and test the complete derivative after extraction.
The primary command-only check does not cover SCC or native metadata.
Never include credentials, personal paths, Git history or internal review logs in
the anonymous upload. Preserve original records separately without destructive
redaction. Any accepted supplement's later archival publication is a separate
step, not a reason to require a GitHub repository for reading the main paper.

## Final checks on the conference version

After adapting the paper, have separate author-side critics inspect conference
scope/contribution, methods and evidence, and clarity/format/anonymity. These
checks supplement the five full scientific critics, because editing to eight
pages can introduce omissions. Save every report and coordinator decision.
Use the user-approved economical model only while quota permits.

Compile with the official class unchanged; inspect every page and all figures at
two-column print size, including greyscale, `\Description` text, references and
PDF metadata. Check the paper independently of the supplement. Recheck every
numerical claim against the final tables and preserve test families, units and
unknown-outcome distinctions. Check anonymous ZIP contents after extraction in
a clean directory. Rebuild source.zip in a clean directory.

Refresh the official pages and form, insert the actual OpenReview submission
number and rerun PDF validation. Publish the completed conference branch and
give the author the exact two upload files plus the author kit. Do not submit to
OpenReview, accept a licence or attest author declarations on the user's behalf:
the user requested a package they can upload. Only then is the conference
preparation complete. The existing continuation automation must not finish merely
because the long research article has been published.
