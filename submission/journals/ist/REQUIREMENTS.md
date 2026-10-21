# Information and Software Technology: submission preparation

Checked 21 October 2026 against the live [official guide for authors](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors), read through the in-app browser. The web-search fetch returned HTTP 403; browser access exposed the actual guide. This is a prepared alternative journal version, not a submitted manuscript. Select one venue only after checking the existing FSE or other submission status.

## Mandatory journal rules and package status

| Rule | Status in this package | Official guide section |
|---|---|---|
| Research Papers may contain at most 15,000 words, including references and appendices; each table or figure adds 200 words. | Nine tables and one figure retained. A conservative PDF-text count plus 2,000 words is recorded in `qa/verification.json`; it includes table text as well, so intentionally overcounts it. | [Article types](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#about-the-journal-article-types) |
| The abstract needs five headings: Context, Objectives, Methods, Results, Conclusion, and at most 300 words. | Present; counted in `qa/verification.json`. | [Structured abstract](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-structured-abstract) |
| Include 1–7 English keywords. | Six supplied. | [Keywords](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-keywords) |
| Supply editable manuscript source; PDF alone is insufficient. | Self-contained `.tex`, bibliography, class and style files are in `manuscript/`; `manuscript-source.zip` is the upload source bundle. | [File format](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-file-format) |
| Include accurate names, affiliation postal addresses, country and corresponding-author email. | Name, institution, city, country and email are supplied. Full affiliation postal address still needs author confirmation. | [Title page](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-title-page) |
| Research-data policy Option C requires repository deposit and dataset citation/link, or a reason sharing is impossible. A data statement is required. | Frozen archive linked to commit `008b730a905277079710092ecf3881770eb100fc`, cited as a dataset, with omissions and fresh-execution limitations retained. Root audit verifies the public archive against the retained copy. | [Research data](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-research-data), [Data statement](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-data-statement) |
| Declare generative AI preparation assistance in a dedicated section before references. | Present separately from research-method disclosure; current journal adaptation is disclosed. It does not invent completed independent human review. | [AI declaration](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#ethics-and-policies-declaration-of-generative-ai-use) |
| Complete the publisher competing-interest tool and upload its resulting Word file. Disclose research/preparation funding and sponsor involvement truthfully. | Pending author confirmation; neither a no-conflict nor a no-funding attestation has been invented. | [Competing interests](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#ethics-and-policies-declaration-of-competing-interests), [Funding](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#ethics-and-policies-funding-sources) |

IST uses single-anonymized review, so the author remains identified in this version. This is not a reason to retain ACM conference headers or double-anonymous release promises; they were removed. [Peer-review policy](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#about-the-journal-peer-review).

## Recommended or optional materials

- Highlights are encouraged: 3–5 bullets, each at most 85 characters including spaces. Four validated bullets are in `highlights.txt`.
- A graphical abstract is encouraged, rather than required. None is supplied; the scientific workflow figure remains in the manuscript.
- The publisher encourages its LaTeX template. This package uses the unmodified installed official `elsarticle` class, version 3.5 (9 January 2026), and numeric bibliography style. Consistent initial reference formatting is accepted; the package follows numbered citations in order of appearance.
- `cover-letter.txt` is a factual, unsigned preparation draft. It does not attest originality, exclusive submission, or author approval on the author's behalf.

Sources: [Highlights](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-highlights), [Graphical abstract](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-graphical-abstract), [LaTeX](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-latex), [References](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#writing-and-formatting-references).

## Unconfirmed author actions before submission

- Confirm all authors, the English spelling, affiliation and full postal address; confirm the corresponding author. ORCID has not been invented or asserted to be mandatory by this guide review.
- Confirm actual funding, sponsor roles and competing interests; complete the Elsevier declaration tool and retain its Word output. Confirm any applicable CRediT roles rather than attributing unverified contributions.
- Personally review and approve the scientific content, source citations, final AI disclosure and submission version. The package's AI-assisted preparation checks do not establish human oversight of every change.
- Resolve whether FSE 2027 or another venue is still considering any overlapping manuscript. Verify prior publication/preprint history and obtain required institutional/author approvals. Exclusive submission and originality remain unconfirmed; this package is not permission to submit simultaneously.
- Confirm licenses/permissions for benchmark data and source material, and choose the publishing route only in the submission process. No APC purchase, transfer request or publishing agreement is authorized by this package.
- Recheck the live upload system and guide when submitting; it may request additional fields. Upload manuscript sources, the review PDF, highlights, the verified replication archive and the author-approved declarations; keep `qa/`, `REVIEW.md` and working checks out of the submission.

The [submission declaration](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#ethics-and-policies-submission-declaration) is consequential: none of its unverified factual attestations has been silently inserted into this draft.


## Confirmed author information and institutional address

On 21 October 2026 the author confirmed the sole author name Daniil Privezentsev, affiliation National Research University Higher School of Economics, Moscow, Russia, and email daprivezentsev@edu.hse.ru. The public institutional legal/postal address is 20 Myasnitskaya Ulitsa, Moscow 101000, Russia, verified at https://www.hse.ru/en/contacts.html on the same date and used in the title page. This is the institution's address, not a verified private or department address. Earlier checklist notes asking for these already confirmed identity fields are superseded by this record. Funding and competing-interest answers remain separate and unconfirmed.


## Final author confirmation update

The author explicitly confirmed on 21 October 2026 that there was no external funding and no financial or other competing interests. The statements in author-declarations.txt and the relevant manuscript declarations are filled accordingly. Earlier review/checklist notes describing these facts as unconfirmed refer to the pre-confirmation draft and are superseded. No publisher declaration tool, journal submission or legal attestation has been completed by this preparation step.
