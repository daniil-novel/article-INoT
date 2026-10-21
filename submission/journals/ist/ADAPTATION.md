# IST adaptation record

Canonical basis: FSE-2027 commit `008b730a905277079710092ecf3881770eb100fc`, manuscript “Role Labels or Extra Calls? A Controlled Study of Quality and Cost in LLM Code Generation.” The provided canonical PDF is 16 pages. All source parts and that complete PDF, including bibliography, nine tables and workflow, were read. This package changes only its separate IST copy; it neither changes the canonical branch nor adds experimental evidence.

## Substantive changes

The IST version presents a software-engineering decision about executable quality and resource evidence. The new title, five-part abstract, introduction and contribution statement distinguish lexical stage names from information flow between calls. The contribution is an empirical separation of interventions, rather than a newly demonstrated agent architecture. The revised conclusion preserves the observed-pair conditions and the limits of the population claims.

A new practitioner-implications subsection explains which workflow decisions the estimates can inform: preserving simple baselines, describing operations/information flow, retaining different quality/resource denominators, reporting missing workflows, and measuring deployment-specific constraints before treating token valuation as an economic result. It explicitly avoids a productivity claim, a quality-equivalence claim or a total-cost estimate.

The closest recent IST article, [Wen, Liu and Du, *Consensus planning boosts LLM code generation*](https://doi.org/10.1016/j.infsof.2026.108030), is added to the literature discussion. The publisher's abstract, introduction and section preview were read. The added claim is limited to its planning and hierarchical-coding mechanisms; no unverified numerical comparison or purported replication is added. SCC already includes a role-removal comparison, and the six-model AdaCoder preprint already reports adverse SCC quality/resource patterns, so neither is represented as a previously unknown phenomenon.

The format uses official `elsarticle` and a numbered reference list, restores the known author information, removes ACM/FSE running matter, and adds a dataset citation and separate Elsevier AI preparation disclosure. Bibliographic Unicode is expressed with TeX diacritics to preserve Nielsen, Röttger and Schmidhuber correctly under standard BibTeX. Historical web-document access dates are retained in rendered notes.

## Preserved evidence

All nine original table inputs and `workflow.tex` are byte-identical to the canonical input; `qa/preserved-inputs.json` retains paired SHA-256 values. This includes the entire SCC-comparison source and its numerical table. All methods, numerical result paragraphs, inferential rules and limitations remain present. The changes to the introduction and conclusion repeat existing findings; they do not recalculate effects.

The quality estimands still require complete eligible task pairs; resource ratios still use complete resource pairs. The primary study has at most 1,000 sampled task units with three repeated requests per condition, not 15,000 independent tasks. Non-rejection after Holm correction is not equivalence. The SCC whole-population bounds still allow either sign. Two aliases from one provider family do not become independent model families. Monetary values remain API-equivalent counter valuations, not bills or total cost.

Data availability points to the public frozen archive at the exact source commit. The historical filename remains identifiable, and the root package supplies a verified copy as `replication-data.zip`. The text removes the promise of a later release after double-anonymous review while retaining omissions of conversation bodies, SCC candidate text and operational traces, and the unverified fresh-environment/native-execution boundary.

## Fit and material scientific risks

The [official IST scope](https://www.sciencedirect.com/journal/information-and-software-technology/publish/guide-for-authors#about-the-journal-aims-and-scope) includes empirical research, quality, metrics, programming and software-development practice. That supports topical fit. The editorial assessment can still question the breadth and incremental contribution: one function benchmark, one main model alias, same-family corroboration, no repository workflow and no matched-compute causal contrast. More journal-specific prose cannot create independent models or deployment evidence.

The remaining submission gates are factual author decisions in `REQUIREMENTS.md`: postal address, funding, competing interests, authorship/approval and existing submission status. No acceptance likelihood or official article-level Q1 grade is assigned. The technical package can be reviewed now; submission readiness still depends on those gates.

## Rebuild and QA

Run `build.ps1` from PowerShell with an installed LaTeX distribution. The source archive includes the class and bibliography style and requires only standard TeX packages. The package compiles locally with MiKTeX through PDFLaTeX, BibTeX and two further PDFLaTeX passes. `qa/verification.json` records source preservation, abstract/highlight lengths, conservative length accounting, reference and layout checks. All final pages were rendered for visual inspection; PNGs/contact sheets in `qa/` are review evidence, not submission files. Numerical replay, fresh provider calls and native candidate execution are outside this adaptation's verification.
