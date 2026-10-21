# JSS-specific adaptation

Prepared 21 October 2026 from the complete English manuscript snapshot supplied for source commit `008b730a905277079710092ecf3881770eb100fc` on `FSE-2027`. No scientific data or experimental metric was changed, and no new experiment or candidate execution was performed.

## Venue fit and concrete text changes

The [official JSS guide and scope](https://www.sciencedirect.com/journal/journal-of-systems-and-software/publish/guide-for-authors), checked live on 21 October 2026, include AI applied to software engineering, development-resource metrics, empirical research methods, replication, and negative results. The version addresses this ordinary research-article audience through workflow configuration and auditable engineering evidence.

1. **Title and abstract.** The new title is *Configuring LLM Code-Generation Workflows: Role Labels, Call Structure, and Resource Use*. The 233-word abstract starts from the configuration decision, identifies the unchanged-operation intervention, reports primary quality and valuation effects, and states the non-equivalence and SCC-missingness limits.
2. **Introduction and contributions.** The introduction was rewritten around the prompt contract, exposed intermediate state, call boundaries, and external executable acceptance. Three explicit contributions distinguish the intervention, the evidence/accounting method, and the bounded configuration result. It identifies the disabled parts of the broader Hybrid-INoT prototype.
3. **Engineering implications.** The discussion was substantially rewritten into call-boundary interpretation, baseline-first evaluation, role labels as an interface choice, separate quality/resource/availability accounting, and the requirements of subsequent broader workflow evaluations. Its three-step evaluation sequence is expressly not an evaluated adaptive routing algorithm.
4. **Conclusion and validity.** The conclusion now reports a configuration result for the tested interface rather than a general architecture claim. The limitations section is titled *Threats to Validity and Reproducibility*. Task reuse, immutable-model uncertainty, benchmark contamination, unmatched compute, and missingness remain visible.
5. **Journal front matter and format.** ACM/FSE conference metadata and anonymous-author formatting were removed. Named Elsevier front matter, correspondence, six keywords, an A4 single-column layout, and an author-year bibliography were added. The local `elsarticle` class and style preserve their original license notices. The global TikZ font is set explicitly so the unchanged workflow geometry remains legible in the larger manuscript type size.
6. **Data and AI statements.** The data statement now cites a version-pinned nonanonymous archive and explains its historical `FSE2027-supplement.zip` filename. The review-era mirror remains secondary. The promise to release a complete archive after double-anonymous review was removed. Actual omissions and the unverified fresh-build/native-equivalence boundary are retained. The final AI declaration includes this adaptation on 21 October 2026 and preserves the historical human-review limitation.
7. **Companions.** A substantive cover-letter draft, five compliant highlights, a mandatory/recommended requirements map, an author checklist, a methods-review report, and a repeatable manuscript build are supplied.

## Evidence retained without alteration

All nine original table-source files and the workflow diagram source are copied byte-for-byte. `qa/table-preservation.json` records source and adapted hashes and equality checks. Methods and results retain the original task units, eligibility rules, four-test Holm family, exploratory labels, source-group audit timing, phase overlap, and API-equivalent accounting. The bibliography retains source metadata while converting unsupported entry types to BibTeX-compatible `misc`, escaping non-ASCII name characters for correct initials, displaying recorded access/preprint metadata, and adding one dataset citation.

## Remaining scientific and author risks

Reframing cannot supply unobserved evidence. The topology contrast bundles computation, repeated context, and message exposure; the mini study reuses task IDs; benchmark contamination and provider-level drift remain unresolved; SCC's assignment bounds permit both signs. The study does not establish a general multi-agent, repository-level, or full-Hybrid-INoT deployment result. These are disclosed design limits, not defects solved by editorial rewriting.

Postal affiliation, funding, competing interests, optional ORCID, final human approval, and exclusive-submission eligibility require author verification in `AUTHOR_CHECKLIST.md`. The parent task verified public archive access, all 336 manifest hashes/sizes, nine table inputs, and the primary ledger; the evidence is copied to `qa/data-audit.json`. Archive inspection does not establish fresh native replay. No acceptance probability or journal endorsement is claimed.

## Verification

The manuscript is 21 A4 single-column pages. The final build has no unresolved citations/references and no overfull boxes. All pages are rendered and inspected under `qa/`; the workflow diagram is checked at full-page resolution as well as in contact sheets. Numerical table files are compared by SHA-256, not represented as newly reproduced experimental results. Details are in `qa/VERIFICATION.md`.
