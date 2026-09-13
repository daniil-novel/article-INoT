# AAMAS 2027 bibliography verification (2026-09-13)

The prepared BibTeX is `submission/aamas2027/preparation/references.bib`. Keys are preserved from `sections/revision_references.tex`; author lists are expanded where the primary record supplies them.

| Key | Primary source checked | Access / metadata result |
|---|---|---|
| `dong2023selfcollaboration` | arXiv:2304.07590; ACM DOI 10.1145/3672459 | Verified authors, title, and 2024 TOSEM 33(7), pp. 1--38; arXiv is the preprint. |
| `scc2024source` | Dong paper's documented accompanying implementation description | No independently archived software record or stable public URL located; BibTeX identifies the documented author implementation and reports this limitation. |
| `madaan2023selfrefine` | NeurIPS 2023 proceedings page | Verified all 16 authors, NeurIPS 36, DOI 10.52202/075280-2019. |
| `shinn2023reflexion` | NeurIPS 2023 proceedings page | Verified 5 authors, NeurIPS 36, DOI 10.52202/075280-0377. |
| `sun2025inot` | arXiv:2507.08664 | Verified 2 authors, title, arXiv identifier, 2025. |
| `tran2026budget` | arXiv:2604.02460 | Verified 2 authors, title, arXiv identifier, 2026. |
| `xia2024agentless` | arXiv:2407.01489 | Verified 4 authors, title, arXiv identifier, 2024. |
| `yang2024sweagent` | arXiv:2405.15793; NeurIPS record | Verified 7 authors and arXiv identifier; publication venue is recorded as NeurIPS 2024 without invented pages/DOI. |
| `zhuo2024bigcodebench` | ICLR/OpenReview record and arXiv:2406.15877 | Verified full 33-author list and ICLR 2025 venue. No DOI or page range added because the primary record checked did not supply one. |
| `jimenez2023swebench` | ICLR 2024 proceedings and arXiv:2310.06770 | Verified 7 authors and ICLR 2024 venue; no DOI/pages added. |
| `swebenchdocs2026` | SWE-bench official evaluation guide URL | URL retained; access date follows source manuscript. This is a living web guide, with no author person or DOI supplied. |
| `openai54mini2026` | OpenAI developer documentation URL | Citation is an online documentation record. Model-page metadata and pricing should be rechecked immediately before submission; no DOI added. |
| `openai56luna2026` | OpenAI developer documentation URL | Citation is an online documentation record. The named model/page was not independently corroborated in a second primary record; no prices or other metadata were invented. |
| `openaipricing2026` | OpenAI official API pricing URL | URL and document-level metadata retained; rates are intentionally not duplicated in the BibTeX. Recheck live rates before submission. |
| `codexexec2026` | OpenAI official Codex non-interactive documentation URL | URL and document-level metadata retained; no DOI or version string supplied. |
| `zheng2024personas` | ACL Anthology 2024.findings-emnlp.888 | Verified 5 authors, venue, pp. 15126--15154, DOI 10.18653/v1/2024.findings-emnlp.888. |
| `araujo2025personas` | ACL Anthology 2025.emnlp-main.1364 | Verified full names including “Pedro Henrique Luz de Araujo” and “Paul Röttger”, venue, pp. 26857--26886, DOI 10.18653/v1/2025.emnlp-main.1364. |
| `choi2025debate` | NeurIPS 2025 proceedings page | Verified 3 authors, NeurIPS 38, DOI 10.52202/085713-3405. |
| `wunderlich2026compute` | ACL Anthology 2026.acl-srw.1 | Verified 5 authors, proceedings title, pp. 1--14, DOI 10.18653/v1/2026.acl-srw.1. |
| `allamanis2019duplication` | ACM DOI record; arXiv:1812.06469 | Verified Miltiadis Allamanis, Onward!/SPLASH 2019 proceedings, pp. 143--153, DOI 10.1145/3359591.3359735. |
| `mackinnon2023clusters` | ScienceDirect/Elsevier DOI record | Verified 3 authors, Journal of Econometrics 232(2), pp. 272--299, DOI 10.1016/j.jeconom.2022.04.001. |

## Unsupported-claim check requested for the manuscript

The SCC arXiv record (2304.07590) supports the existence of an analyst/coder/tester role workflow and reports relative Pass@1 improvements of 29.9%--47.1% over a base LLM agent. It does not support the manuscript's current pending SCC pilot counts, controller-specific stopping semantics, or the ongoing 2,000-block comparison; those are project-generated claims and should remain explicitly marked as pending or feasibility evidence.

The INoT arXiv record (2507.08664) supports the proposed INoT framework, LLM-read code/programmatic dialogue reasoning, six-benchmark evaluation, and 58.3% lower average token cost than the best baseline method. Its abstract reports an average 7.95% improvement, while the body contribution statement reports 11.6%; this internal discrepancy is unresolved and should not be silently normalized. The record does not support the manuscript's local INoT* adaptation counts (199 complete programs, 96/192 passes), paired interval, valuation ratio, or exact identity-context/no-rerun protocol; these should be presented as the project's own study results and not attributed to Sun and Zeng.

For SCC arXiv:2304.07590v2 sections 5.2--5.3, the primary paper reports role-ablation relative improvements of 40.8% (HumanEval) and 47.1% (HumanEval-ET) for analyst+coder+tester, and 36.7%/39.4% for coder+tester on MBPP/MBPP-ET. The interaction experiment reports MI=0,1,2,4; the largest improvement occurs from 0 to 1 and later gains diminish. These are benchmark results from the original ChatGPT study, not evidence for the manuscript's native SCC pilot counts or ongoing prefix outcomes. The paper's tester is described as simulating tests and writing reports; this differs from the manuscript's generated `check(candidate)` execution controller and should be kept distinct.

No manuscript or study files were changed by this verification.
