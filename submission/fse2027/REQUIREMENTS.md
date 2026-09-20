# FSE 2027 Research Track — submission requirements

Verified on 2026-09-20 against the official Research Track CFP and submission site.

## Authoritative links

- Research Track CFP: https://conf.researchr.org/track/fse-2027/fse-2027-papers
- Submission system: https://fse2027.hotcrp.com/
- ACM proceedings templates: https://www.acm.org/publications/proceedings-template
- ACM authorship policy: https://www.acm.org/publications/policies/new-acm-policy-on-authorship
- ACM policy on simultaneous submissions: https://www.acm.org/publications/policies/simultaneous-submissions
- ACM policy on research involving human participants: https://www.acm.org/publications/policies/research-involving-human-participants-and-subjects

## Track and scope

The paper must be submitted to the **FSE 2027 Research Track** and present original, unpublished software-engineering research. The track accepts theoretical, empirical, conceptual, experimental, emerging-problem, and replication research.

Hybrid-INoT directly matches these listed topics:

- artificial intelligence and machine learning for software engineering;
- empirical software engineering;
- dependability, safety, and reliability;
- program analysis and program comprehension;
- program repair and program synthesis;
- software engineering for machine learning and artificial intelligence;
- software testing, symbolic execution, tools, and environments.

The contribution should be framed as a controlled empirical study of role-conditioned LLM workflows and external executable verification for code generation. Claims of genuine model introspection or demonstrated multi-agent cognition should not exceed the evidence.

## Submission deadline and system

- Official CFP date: **Friday, 2 October 2026, AoE (UTC-12)**.
- Submission site: **HotCRP**, https://fse2027.hotcrp.com/.
- The public HotCRP page currently displays `Friday Oct 2, 2026, 12 AM AoE`, while the CFP lists the date as an AoE deadline. Because `12 AM` is ambiguous in this context, use **1 October 2026 as the internal final-upload deadline** and confirm the countdown after signing in.
- No separate abstract-registration deadline is listed in the Research Track CFP.

## Page limit and document format

- Initial submission: **at most 18 pages for all text and figures, plus at most 4 pages for references**.
- A paper invited to major revision may use **20 pages for text and figures, plus 4 pages for references**.
- Use the official ACM proceedings template.
- LaTeX class required/recommended by the CFP:

  ```tex
  \documentclass[acmsmall,screen,review,anonymous]{acmart}
  ```

- Start from `sample-acmsmall-conf.tex` in the `acmart` package.
- The review layout is **single column**.
- Numeric and author-year citation styles are both allowed.
- Do not alter margins, font sizes, spacing, or other template parameters to fit more content.
- The limit covers all main-paper text and figures. Use the conservative interpretation that tables and appendices inside the main PDF also count toward the 18-page content limit.
- The required `Data Availability` statement after the conclusion does **not** count toward the page limit.
- A formatting violation can cause desk rejection without review.

## Required paper content

The paper must contain enough evidence in the main PDF to support its claims. For Hybrid-INoT, the compact FSE version should retain at least:

- the precise research questions and hypotheses;
- experimental factors, baselines, models, tasks, and sample sizes;
- exact definitions of success, executable verification, and cost;
- the primary statistical model or tests, effect sizes, uncertainty, and multiplicity handling;
- enough numerical results to establish the main positive, negative, and null findings;
- threats to validity and limits on generalization;
- an appropriate comparison with closely related code-generation, prompting, self-correction, agentic-workflow, and software-testing research;
- a reproducibility/data-availability statement after the conclusion.

Reviewers evaluate originality, importance, soundness, quality of evaluation, presentation, and comparison with related work.

## Double-anonymous review

FSE uses a **heavy double-anonymous** process that remains in force throughout review, discussion, author response, and any major revision.

The submission must:

- omit author names and affiliations;
- describe the authors' earlier work in the third person;
- avoid phrases such as `our previous work` when they reveal identity;
- exclude author-identifying URLs for repositories, tools, datasets, personal sites, or institutional storage;
- anonymize organization and institution names that could identify the authors while retaining the contextual facts needed to evaluate the study;
- omit acknowledgements at initial submission;
- anonymize the replication package and every file inside it, including metadata, paths, commit history, usernames, document properties, and generated outputs;
- keep the response letter and any major revision anonymous.

Preprints on arXiv or similar services are permitted, but the preprint should not state that the paper is submitted to FSE 2027. The submitted PDF must not link to an identity-revealing preprint or repository.

Noncompliance with double-anonymous review can cause desk rejection.

## Originality and simultaneous-submission rules

- The work must be original and unpublished.
- The same or substantially overlapping paper must not be under review at another refereed conference or journal during FSE review.
- The chairs may compare submissions with overlapping venues.
- An unrefereed preprint such as arXiv is allowed.
- Plagiarism, self-plagiarism, fabricated material, and unattributed reuse are prohibited under ACM policy.

The author list and title in the camera-ready version may not differ from the submitted version without explicit approval from the track chairs. Freeze the intended title, complete author list, and author order before submission.

## Open science and replication package

FSE asks authors to provide a replication package to the program committee, either as supplementary material or through an anonymous private/public link. If this is impossible or undesirable, the paper must explain why.

The paper must include a section named **Data Availability** after the conclusion that states:

- whether a replication package is available;
- how reviewers can access it anonymously;
- whether data and tools will be made public after acceptance;
- or why sharing is not possible.

For Hybrid-INoT, the replication package should include, after sanitization and anonymization:

- prompts and role definitions;
- task identifiers and benchmark versions;
- model/provider identifiers, versions, dates, and generation parameters;
- execution and verification scripts;
- raw or minimally processed result records where licensing permits;
- analysis scripts and environment lock files;
- scripts that reproduce every main table and figure;
- a manifest, README, and machine-readable provenance information;
- instructions for reproducing the primary statistical results without private credentials.

Accepted papers may later submit data and tools to the separate FSE 2027 artifact-evaluation committee.

## Generative-AI policy

- AI systems cannot be listed as authors.
- Every named author remains responsible for the entire submission.
- Any use of AI that materially affects the research—experimental design, data creation or selection, code generation, implementation, simulation, analysis, testing, validation, plots, or reproducibility artifacts—must be described in detail in the methods section.
- For Hybrid-INoT this disclosure is central to the method, not an optional acknowledgement. Record the provider, model name/version, access dates, parameters, prompts, sampling protocol, failure handling, and verification procedure.
- The FSE AI-policy section says that AI used only to assist writing does not require disclosure. The same CFP also quotes the broader ACM authorship policy recommending disclosure of substantive AI-generated content. The safe policy is to disclose substantive AI-generated text, code, tables, figures, data, or citations, while ordinary spelling, grammar, and translation assistance need not be disclosed.
- Fabricated or hallucinated results, references, or datasets are prohibited.
- Plagiarism, unattributed AI-generated content, and use of confidential material without authorization are prohibited.
- Hidden text or prompt injection intended to influence reviewers or automated review systems is prohibited and may cause desk rejection.
- Every reference must be authentic and manually verified; confirmed fabricated or unverifiable references cause desk rejection.

## Human-participant policy

Submission acknowledges ACM's policy on research involving human participants. If the final study includes a user study, annotators, interviews, surveys, or identifiable human-derived data, document consent, privacy protection, ethics/IRB status or the reason formal review was not required. A study based only on benchmark tasks and model executions should state its actual data sources clearly and should not imply human-subject approval that was not applicable.

## Review and revision process

- At least three program-committee members review each paper; additional reviews may be requested.
- Initial decisions are `accept`, `reject`, or `major revision`.
- A major revision may require new experiments, new analyses, substantial rewriting, clearer scope, or stronger motivation.
- A revised paper must include an anonymous response letter explaining how every concern was addressed.
- The same reviewers normally evaluate the revision.

Important dates:

| Milestone | Date |
|---|---:|
| Full-paper submission | 2 October 2026 AoE |
| Author-response period | 14–18 December 2026 |
| Initial notification | 22 January 2027 |
| Major-revision submission | 5 March 2027 |
| Final notification | 31 March 2027 |
| Conference in Shenzhen | 12–16 July 2027 |

The CFP does not yet list a camera-ready deadline.

## Publication, registration, and attendance

- Accepted papers are published open access in the ACM Digital Library.
- If at least one author is covered by an ACM Open participating institution, the institutional agreement can cover the APC.
- Otherwise the 2027 subsidized APC is **USD 500 for an ACM/SIG member** or **USD 750 for a non-member**, unless a waiver applies.
- Attendance is encouraged but **not mandatory for publication**.
- Authors may choose not to present. In that case, they do **not** need to register for the conference.
- All authors should obtain ORCID identifiers before the publication stage.
- The official publication date is the date on which the proceedings appear in the ACM Digital Library. It may be up to two weeks before the conference and can matter for patent-filing deadlines.

## Final pre-submission checklist

- [ ] Research Track selected in HotCRP.
- [ ] Main paper is no longer than 18 content pages.
- [ ] References are no longer than 4 pages.
- [ ] Official `acmsmall` review template used without layout modification.
- [ ] PDF is readable, fonts are embedded, and figures remain legible at normal zoom.
- [ ] Authors, affiliations, acknowledgements, metadata, URLs, repository history, and document properties are anonymized.
- [ ] Self-citations use third-person language.
- [ ] Title and complete author order are final.
- [ ] No simultaneous refereed submission exists.
- [ ] Every citation has been manually verified against the original source.
- [ ] Methods fully disclose the AI systems and their role in the research.
- [ ] No hidden text, prompt injection, unverifiable result, or unsupported claim remains.
- [ ] `Data Availability` appears after the conclusion.
- [ ] Anonymous replication package opens from a clean browser/account and reproduces the main results.
- [ ] Human-participant requirements are addressed if any human-derived data are present.
- [ ] All authors have or are obtaining ORCID identifiers.
- [ ] APC coverage, ACM/SIG membership, or waiver route has been checked.
- [ ] Final PDF and metadata are uploaded before the internal deadline on 1 October 2026.
- [ ] The exact HotCRP countdown has been checked after sign-in.
