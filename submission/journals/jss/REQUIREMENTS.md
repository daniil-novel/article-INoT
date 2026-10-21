# JSS requirements and package status

Checked against the current official [Guide for authors](https://www.sciencedirect.com/journal/journal-of-systems-and-software/publish/guide-for-authors) on **21 October 2026**, including its embedded aims and scope. The web reader returned HTTP 403; the complete official page was accessible through the in-app browser. The rules below are factual paraphrases, rather than a reproduction of the guide.

The proposed route is an ordinary full-length research article. The manuscript is an empirical study of code-generation workflow configuration. It supplies neither an industrial case study for **In Practice** nor a speculative proposal for **New Ideas and Trends Papers**. The exact portal article-type label must be selected when an actual submission is authorized.

## Mandatory or applicable publisher requirements

| Requirement | Current package treatment | Source location in official guide |
|---|---|---|
| Single-anonymized review | Named author, affiliation, and corresponding email on the title page; ACM anonymous-review metadata removed | Peer review |
| Editable source files | Complete LaTeX sources, bibliography, local class/style, and rendered PDF in `manuscript/`; PDF is a review copy, not the sole source | File format; LaTeX |
| Title-page metadata and full postal affiliation | Name, institution, city, country, correspondence included; postal details require author confirmation | Title page |
| Abstract of at most 250 words | Rewritten abstract, 233 whitespace-delimited words with each math expression counted as one; independently under 250 by ordinary reading | Abstract |
| 1-7 English keywords | Six supplied | Keywords |
| Separate editable highlights, 3-5 bullets, at most 85 characters each including spaces | Five bullets in `highlights.txt`; checked lengths in `qa/document-check.json` | Highlights |
| Research data deposit, citation and link, or explanation of inability to share (Option C) | Frozen version-pinned archive linked and cited as a dataset; exclusions and limitations stated. Parent-task audit verifies all 336 manifest files and the public download; author must confirm metadata, suitable deposit, and redistribution conditions | Research data deposit, citation and linking |
| Data-availability statement at submission | Present at end of manuscript; historical filename explained; no future release promise tied to anonymous review | Data statement |
| Disclosure of competing interests | Author action. Complete Elsevier's [declarations tool](https://declarations.elsevier.com/) and upload its generated `.doc`/`.docx`; no unconfirmed absence-of-interests statement inserted | Declaration of competing interests |
| Disclosure of funding and sponsor roles | Author action. Funding and its role must be stated accurately; the guide's no-specific-grant sentence applies only if the author confirms it | Funding sources |
| Generative AI preparation declaration before references | Separate declaration includes historical research assistance and the 21 October journal adaptation; no unsupported claim of independent human review | Declaration of generative AI use |
| No concurrent consideration elsewhere and final author approval | Author action before any journal submission. The cover letter makes no unverified exclusivity assertion | Submission declaration; Authorship |
| Consistent citations and references | Elsevier author-year style; all rendered citations and cross-references resolved; access dates and preprint identifiers carried into visible references | References |

## Recommendations, not hard page or artifact requirements

- Full-length papers are encouraged to stay below 36 single-column or 18 double-column pages. A longer paper requires a length explanation. This version is 21 A4 single-column pages, including references.
- Elsevier encourages its [LaTeX template](https://www.elsevier.com/latex). This version uses `elsarticle` with its author-year bibliography style and retains vendor notices in the copied files.
- A graphical abstract is encouraged, not mandatory. The manuscript retains an editable workflow diagram; no separate graphical abstract is supplied.
- JSS welcomes negative results and replication studies. Its optional Open Science Initiative reviews availability and usability after acceptance for participating papers; no Open Science validation or badge is claimed here.
- ORCID and a DOI-backed archival deposit can improve identification and preservation. Neither an ORCID nor a new repository DOI is invented.

## Remaining author actions

See `AUTHOR_CHECKLIST.md`. The package is a concrete journal-specific draft, not evidence that a journal submission has occurred. Prepare journal versions as alternatives and resolve any active conference or journal consideration before submitting one of them.


## Confirmed author information and institutional address

On 21 October 2026 the author confirmed the sole author name Daniil Privezentsev, affiliation National Research University Higher School of Economics, Moscow, Russia, and email daprivezentsev@edu.hse.ru. The public institutional legal/postal address is 20 Myasnitskaya Ulitsa, Moscow 101000, Russia, verified at https://www.hse.ru/en/contacts.html on the same date and used in the title page. This is the institution's address, not a verified private or department address. Earlier checklist notes asking for these already confirmed identity fields are superseded by this record. Funding and competing-interest answers remain separate and unconfirmed.


## Final author confirmation update

The author explicitly confirmed on 21 October 2026 that there was no external funding and no financial or other competing interests. The statements in author-declarations.txt and the relevant manuscript declarations are filled accordingly. Earlier review/checklist notes describing these facts as unconfirmed refer to the pre-confirmation draft and are superseded. No publisher declaration tool, journal submission or legal attestation has been completed by this preparation step.
