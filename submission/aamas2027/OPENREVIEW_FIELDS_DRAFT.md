# Fields for the AAMAS 2027 submission form

Preparation record, 13 September 2026. This file contains author-identifying
information and must stay outside the anonymous PDF and supplementary ZIP.
No form has been submitted. The title and abstract below match the current
completed-data conference manuscript. Final editorial review remains a separate gate.

| Field | Prepared value |
|---|---|
| Paper title | Hybrid-INoT: Isolating Role Labels and Call Structure in Verified Code Generation |
| Author | Daniil Privezentsev |
| Author email | daprivezentsev@edu.hse.ru |
| Affiliation | HSE University, Faculty of Computer Science |
| Current position | Master's student, second year |
| Primary author is a student | Yes |
| Primary subject area | Generative and Agentic AI (GAAI) |
| Secondary area, optional | Engineering and Analysis of Multiagent Systems (EMAS) |
| External funding | None, as confirmed by the author |
| Conflict of interest | None, as declared by the author |

The author's supplied program description is «FKN SPI; системное
программирование». The institutional affiliation above is sufficient for the
prepared author entry; an unverified English program title is not substituted.
The previous bachelor's qualification was awarded by MIREA in program
09.03.04. It is background information, not a second current affiliation.

The following three topic labels appear in the recorded submission invitation:

- GAAI: Orchestration and workflows of agents and tools
- GAAI: Modeling and analysis of generative AI agents
- GAAI: Benchmarks, evaluation, and metrics for generative and agentic AI systems

These choices describe the intended workflow-evaluation contribution. They do
not establish that the area chairs will find the paper in scope. The manuscript
must keep the distinction between instructed role labels and independently
acting agents explicit.

Optional working TL;DR (under 250 characters):

> A matched code-generation study separates role labels from call structure and measures native correctness and full-context resource use, with an external Self-Collaboration workflow comparison.

## Abstract for the current conference manuscript

Hybrid-INoT combines planning, implementation, and critique in one model response while leaving correctness verification to an external executable evaluator. We isolate this single-pass core by crossing role labels (neutral versus planner–implementer–reviewer) with call structure (one versus three calls), holding the operations and full supplied task context fixed. A direct solver is the fifth condition. GPT-5.6 Luna with medium reasoning receives 15,000 assignments on 1,000 BigCodeBench tasks with three repeats per condition; 14,961 candidates complete and 985 tasks pass reference controls. Neither role-label quality contrast is significant after Holm adjustment. On complete eligible task pairs, three-call execution lowers success by 4.17 percentage points for neutral instructions and 2.13 points for role-labelled instructions. Its API-equivalent valuation is 2.67 and 2.78 times that of the corresponding single-call workflows. A separate 2,000-block comparison assigns 6,000 fresh single-call and Self-Collaboration workflows across 956 tasks. Self-Collaboration has lower observed-pair success by 2.48–2.68 points and approximately three times the valuation, but substantial infrastructure missingness leaves the full-population quality difference unidentified. The results provide a controlled evaluation of role labels and interaction structure, with explicit boundaries on quality and resource claims. They do not establish that named roles act as independent agents or that one topology dominates all agent workflows.

## Author decisions or platform-generated fields

| Field | Required action |
|---|---|
| OpenReview author ID | Create/activate the author's profile and use its actual ID; none is invented here. |
| Final author list | Confirm that the listed author is the complete author list. |
| Submission number | Use the number assigned after abstract registration. |
| Findings of AAMAS 2027 | Author's Yes/No choice is pending. |
| Reciprocal reviewer nomination | Confirm actual eligibility against the official reviewer criteria; student status alone is not the rule. |
| Policy acknowledgement | The author must attest to originality, authorship, and absence of a prohibited parallel archival submission. |
| Workshop outreach, if offered | Optional author choice; no permission to forward the paper is presumed. |

ORCID, DBLP and exact study start/end dates are not invented. Provide them only
when available and requested by the live profile or form. No cover letter,
copyright transfer or acceptance declaration is required by the recorded
initial main-track form; later camera-ready requirements are a separate stage.

Sources: [official AAMAS instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/guidelines-and-policies/instructions/)
and the locally retained public OpenReview invitation snapshot. Recheck the live
form before upload. Author registration is due 17 September, the abstract
1 October and the paper 8 October 2026, all at end of day AoE.
