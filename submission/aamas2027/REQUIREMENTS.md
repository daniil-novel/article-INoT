# Verified requirements

Checked 12 September 2026, Europe/Moscow. Recheck the official pages and the live
form before submission: the current form is the abstract-registration stage.

## Schedule

| Item | Official date, end of day AoE (UTC−12) |
|---|---|
| Author registration in OpenReview | 17 September 2026 |
| Abstract | 1 October 2026 |
| Full paper | 8 October 2026 |
| Rebuttal | 20–24 November 2026 |
| Decision | 21 December 2026 |
| Camera-ready | 25 January 2027 |
| Conference | 3–7 May 2027 |

Source: [main-track call](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/call-for-main-track/).
Use the listed dates as the working deadlines; never rely on a platform grace
period. OpenReview currently records the abstract cutoff as 2 October 11:59 UTC
(14:59 Moscow), consistent with 1 October AoE.

## Main paper and supplementary material

English, double-blind PDF, mandatory LaTeX, at most eight content pages plus
references. Do not alter the style or layout. Abstract registration precedes the
paper; the recommended abstract length is 100–300 words. Every author needs an
OpenReview account. Choose an area.

Optional supplements: one anonymous ZIP, at most 25 MB. Core claims and evidence
belong in the main paper; supplements cannot replace it with an extended version.
Reviewers need not read supplements. Accepted supplements need an archival
public version referenced from the camera-ready paper.

AI help with hypotheses or methods requires tool/version and prompt disclosure
in the paper or supplement. AI is not an author; human authors retain
responsibility. Simultaneous substantially similar archival submissions are
prohibited; preprints are permitted.

Source: [submission instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/instructions/).

## Official template details

The downloaded 2027 template uses `\documentclass[sigconf,anonymous]{aamas}` for
review and `\submissionType{Research Paper Track}`. Supply the actual number
obtained from abstract registration through `\acmSubmissionID`. Preserve the
2027 copyright block and Libertine fonts. Table captions go above; figure captions
below. Figures need plain-text `\Description` entries, at most 2,000 characters,
and must remain legible in greyscale. Use the supplied ACM bibliography style
and complete author names. Balance the last page for the final published paper.

Source: [official 2027 template](https://warwick.ac.uk/fac/sci/dcs/aamas2027/aamas_2027_template.zip),
`AAMAS_2027_sample.tex`. Its original files are retained without modification.

## Area and contribution

GAAI (Generative and Agentic AI) is the working candidate. Its scope includes
agent architectures, orchestration, interaction and evaluation. Generic prompt
engineering or code generation without a clear agents/MAS contribution is
excluded. The conference paper must establish the relevance of its controlled
workflow comparison and SCC evidence. Calling prompt labels independent agents
does not establish that relevance. Final fit must be reviewed after the studies.

Source: [GAAI area description in the main-track call](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/call-for-main-track/).
The proposed area is our assessment, not approval from the conference.

## Reciprocal reviewing and author declarations

Nominate a qualified author or declare an applicable exemption at abstract
submission. Exemptions include no qualified author, or all qualified authors
already holding specified official AAMAS roles. Eligibility normally requires a
relevant PhD, or a PhD student in year three or later with at least three relevant
peer-reviewed publications. Do not invent eligibility, a nominee or an exemption.

Sources: [reciprocal policy](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/reciprocal-reviewer-policy/),
[reviewer eligibility](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/reviewer-guidelines/).
Our internal author-side AI critics are not official AAMAS reviewers and cannot
perform a nominated human author's conference-reviewing obligations.

The author has confirmed no external funding and no competing interests. Still
needed for final form preparation: OpenReview profile, current student status,
final author list, actual reciprocal-reviewing status, any overlapping submissions,
and the actual submission number after abstract registration.

## Findings

The form requires a Yes/No choice for consideration in Findings if the paper is
not selected for Proceedings. Findings is an archival category, not a separate
submission. It has the same format; negative results and replications are not
automatically relegated to it. Record the author's choice; do not silently opt out.

Source: [Findings policy](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/findings/).

## Live form and remaining ambiguities

The public API snapshot records required title (up to 250 characters), author
profiles, abstract (platform maximum 5,000 characters), primary area, one to three
topics, Findings choice, reciprocal-reviewing confirmation and policy attestations.
TL;DR (250 characters) and up to two secondary areas are optional. The PDF field is
currently optional because this is abstract registration; that does not waive the
full-paper deadline. The current PDF field has a platform size parameter of 50;
the ZIP parameter is 25 and its description explicitly specifies MB.
No student-paper field is present in this public snapshot, although the website
requires it for eligible students. Check the actual later form before final upload.

Source: [public OpenReview submission invitation](https://api2.openreview.net/invitations?id=ifaamas.org/AAMAS/2027/Conference/-/Submission).
Do not assume the current schema is the final paper-revision form.

The reviewer page mentions appendices outside its eight-page count, whereas the
author instructions explicitly allow only references after the eight content
pages and place supplements in a ZIP. Until clarified, put technical appendices
in the supplementary ZIP, leaving only references after page eight. This is a
conservative implementation choice, not a claimed clarification by the chairs.

No cover letter, author biography or signed copyright form is specified for
initial main-track submission in the checked instructions. Recheck for new
requirements; do not label invented forms as mandatory. Camera-ready requirements
must be revisited if accepted.
