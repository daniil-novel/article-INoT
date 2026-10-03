# R5 — English writing, bibliography, and text integrity

Initial independent review, 3 October 2026. No manuscript edits made.

## Review (approximately 420 words)

**Coverage.** I read all 15 English and 26 Russian frozen-baseline PDF pages, including tables, references, and limitations, then every current English TeX component and all 35 bibliography records. Visual inspection covered EN pp. 4/8 and RU pp. 8/16. Current sources contain 31 cited keys, four unused entries, and no undefined keys. The rebuilt current PDF was not yet available during this review.

**Strengths.** The title is clear and worth retaining. The revised conclusion expresses the practical magnitude of the call-structure result without claiming a generic multi-agent penalty. The role-label text correctly separates failure to reject from equivalence; SCC statements consistently distinguish observed pairs from the assigned population. I found no prompt residue or evidence sufficient to infer improper authorship. Repeated scope qualifications are mostly scientifically necessary, rather than removable generic prose.

**Priority issues.**

1. **P2 — `body.tex:148` → “provider-independent token counts”.** The recorded counts come from provider events and depend on model tokenization. Calling them provider-independent overstates comparability. Replace with “provider-reported token counts, with the model/tokenizer and input, output, and cache components specified.” Verify agreement with the accounting definition and Russian discussion, which already asks for model/accounting disclosure.
2. **P2 — `references.bib:37,124` → “Lo, David and Hui, Binyuan” / “Step-by-Step”.** The published BigCodeBench PDF orders Hui, Muennighoff, then Lo; its printed name is Armel Zebaze. ACL’s LDB title ends “Step by Step”. These are transcription defects, not fabricated sources. Import camera-ready metadata, then inspect the rebuilt reference list against those primary records. MetaGPT has conflicting landing-page/PDF author ordering; do not automatically replace its current PDF-consistent order.
3. **P3 — `references.bib:149–150` → unversioned AdaCoder URL / “Version1, 5April2025”.** The six-model claim is supported specifically by v1, dated 5 April 2025, including its SCC quality/token tables. Pin `/abs/2504.04220v1` and repair the glued words. Keep the separate journal key. I could not access primary final-journal text to independently confirm its twelve-model expansion; this is an access limitation, not a demonstrated false claim. Verify against the final publisher PDF before finalizing that comparison.
4. **P3 — `main.tex:19`, `temporal_diagnostics.tex:2` → dense abstract / “task-bootstrap95%”.** The abstract has 286 whitespace-counted words and many secondary-study details. Compress pilot/direct/SCC detail while retaining primary denominators, effects, and uncertainty; this is editorial advice, not an alleged CFP word-limit breach. Insert the missing caption space and inspect final rendering.

**Fresh compliance/audit boundary.** The official FSE CFP supports the current `acmsmall,screen,review,anonymous` template and post-conclusion Data Availability section; it no longer mandates AI writing disclosure. I found no abstract word cap there. Bibliography audit: **35/35 attempted; 34/35 have primary-source existence support**, with field-level access gaps recorded below. No nonexistent reference was established.

## Evidence and access ledger

Primary-source checks used direct URLs plus exact title/DOI queries, including `10.1145/3672459`, `10.1145/3715754`, `10.1145/3359591.3359735`, `10.1016/j.jeconom.2022.04.001`, `10.1145/3691620.3695506`, `10.1145/3712003`, and `10.1109/TSE.2025.3642621`. Failed exact-DOI searches were followed by full-title searches. AdaCoder queries included `"10.1109/TSE.2025.3642621" AdaCoder twelve models` and `"AdaCoder" "twelve" Zhu Liu He`, restricted to IEEE/Computer Society/arXiv/GitHub; they returned no accessible primary final-journal text. No claim is based on a search snippet pretending to be a full-paper reading.

“Opened” means metadata/HTML or the indicated PDF portion was actually accessible; it does not imply reading every cited paper in full. “Indexed” means primary-source indexed text was accessible but opening failed. Publisher DOI pages often returned 403/internal errors; OpenReview returned a browser challenge. Software/documentation years are bibliography access-era labels, not independently established publication dates. Existing publication DOI values were cross-checked where exposed; Allamanis publisher DOI/pages and AdaCoder final fields remain incompletely verified here.

| Bibliography key | Primary source and actual depth | Result / boundary |
|---|---|---|
| dong2023selfcollaboration | [Author-hosted final PDF](https://ligechina.github.io/My%20Papers/2024%20-%20TOSEM%20-%20Self-collaboration%20Code%20Generation%20via%20ChatGPT.pdf), indexed first-page metadata; [arXiv](https://arxiv.org/abs/2304.07590) opened | Title/authors/2024 TOSEM/DOI supported; final PDF opening failed |
| scc2024source | [Pinned upstream tree](https://github.com/YihongDong/Self-collaboration-Code-Generation/tree/b471e12051190dbae2c71b429a3c87466df4b336), opened | Repository/author/pin exist; software publication year not independently dated |
| madaan2023selfrefine | [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html), opened | Title, complete authors, 2023 venue, DOI agree |
| shinn2023reflexion | [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html), opened | Title/authors/2023 venue/DOI agree |
| sun2025inot | [arXiv record](https://arxiv.org/abs/2507.08664), opened | Title/authors/2025; preprint distinguished |
| tran2026budget | [arXiv record](https://arxiv.org/abs/2604.02460), opened | Title/authors/2026; preprint distinguished |
| xia2025agentless | [Author-hosted publisher PDF](https://lingming.cs.illinois.edu/publications/fse2025.pdf), first-page metadata opened | Title/authors/PACMSE 2 FSE/2025/DOI agree; PDF uses article FSE037 and 24 pages |
| yang2024sweagent | [arXiv record](https://arxiv.org/abs/2405.15793), opened | Title/authors/2024 supported; separate proceedings metadata not fully audited |
| zhuo2024bigcodebench | [Published ICLR PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/a6a90bcc2aa470c3871b2d39a67d26e8-Paper-Conference.pdf), first page opened | 2025 publication/title supported; author order/name defects above |
| jimenez2023swebench | [ICLR record](https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html), opened | Title/authors/publication year 2024 agree; unused current key |
| swebenchdocs2026 | [Official evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/), opened | Guide exists; unused current key |
| openai54mini2026 | [Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini), opened | Official model page exists |
| openai56luna2026 | [Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), opened | Official model/rates exist; standard text rates checked |
| openaipricing2026 | [Official pricing](https://developers.openai.com/api/docs/pricing), opened | Official page/rate basis supported |
| codexexec2026 | [Official noninteractive documentation](https://developers.openai.com/codex/noninteractive), opened redirect | Official documentation exists; redirects to learn.chatgpt.com |
| zheng2024personas | [ACL record](https://aclanthology.org/2024.findings-emnlp.888/), opened | Title/authors/year/pages/DOI agree |
| araujo2025personas | [ACL record](https://aclanthology.org/2025.emnlp-main.1364/), opened | Title/authors/year/pages/DOI agree |
| choi2025debate | [NeurIPS record](https://papers.nips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html), opened | Title/authors/year/DOI agree; unused current key |
| wunderlich2026compute | [ACL record](https://aclanthology.org/2026.acl-srw.1/), opened | Title/authors/year/pages/DOI agree; unused current key |
| allamanis2019duplication | [arXiv record](https://arxiv.org/abs/1812.06469) and [PDF](https://arxiv.org/pdf/1812.06469), opened | Title/author/Onward! 2019 status supported; publisher DOI/pages not directly verified |
| mackinnon2023clusters | [Publisher DOI record](https://doi.org/10.1016/j.jeconom.2022.04.001), indexed publisher metadata | Title/authors/2023/232(2)/272–299/DOI supported; opening failed |
| qian2024chatdev | [ACL record](https://aclanthology.org/2024.acl-long.810/), opened | Title/complete authors/year/pages/DOI agree |
| hong2024metagpt | [ICLR record](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6507b115562bb0a305f1958ccc87355a-Abstract-Conference.html), opened; official PDF indexed | Title/2024 agree; author-order metadata conflict, current bibliography follows printed PDF |
| huang2023agentcoder | [arXiv record](https://arxiv.org/abs/2312.13010), opened | Title/authors/2023 v1/arXiv DOI agree; later revision is not itself a publication |
| islam2024mapcoder | [ACL record](https://aclanthology.org/2024.acl-long.269/), opened | Title/authors/year/pages/DOI agree |
| zhu2026adacoder | [Publisher DOI](https://doi.org/10.1109/TSE.2025.3642621), blocked | Final TSE record corroborated only by secondary indexing; primary title/authors/pages/12-model claim unresolved in this audit |
| chen2026paircoder | [ACL record](https://aclanthology.org/2026.findings-acl.149/), opened | Title/authors/year/pages/DOI agree; distinct from ASE PairCoder; abstract says 13 LLMs |
| xu2026oneflow | [arXiv record](https://arxiv.org/abs/2601.12307), opened | Title/complete authors/2026 agree; preprint |
| hong2026dats | [arXiv record](https://arxiv.org/abs/2609.13890), opened | Title/author/2026 agree; preprint |
| kapoor2025agents | [OpenReview published PDF](https://openreview.net/pdf?id=Zy4uFzMviZ), indexed first-page metadata | Title/authors/TMLR May 2025 supported; opening challenge |
| chen2023codet | [OpenReview published PDF](https://openreview.net/pdf?id=ktrw68Cmu9c), indexed first-page metadata | Title/authors/ICLR 2023 supported; opening challenge |
| zhong2024ldb | [ACL record](https://aclanthology.org/2024.findings-acl.49/), opened | Authors/year/pages/DOI agree; exact-title punctuation defect above |
| zhang2024paircoder | [Author deposited publisher-formatted PDF](https://arxiv.org/pdf/2409.05001), first page opened | Title/authors/ASE 2024/DOI agree; publisher page range not independently exposed in PDF |
| he2025lma | [Publisher DOI](https://doi.org/10.1145/3712003), indexed metadata; [author preprint PDF](https://arxiv.org/pdf/2404.04834), opened | Title/authors/2025 final venue/DOI supported; 2024 preprint kept distinct from 2025 publication |
| zhu2025adacoderpreprint | [Version-1 record](https://arxiv.org/abs/2504.04220v1) and [full HTML](https://arxiv.org/html/2504.04220v1), opened; sections III-D/E and tables I/II inspected | Seven authors, 5 April 2025, six models and SCC negative quality–resource pattern confirmed |

The source comparison for AdaCoder v1 concerns its reported aggregate HumanEval pass@1 and token results; relative percentage changes in that paper should not be relabeled as percentage-point effects.

## Fresh FSE check

[Official FSE 2027 Research Track CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers), full page opened on 3 October 2026: 18 text/figure pages plus up to four references, 20+4 for major revision; anonymous ACM Small format; Data Availability after Conclusion, exempt from page limit; substantive AI use in research must be documented, whereas AI writing disclosure is no longer mandatory. The current source options and section placement agree. The 15-page English baseline lies within the initial total limit, but the current rebuilt page count/layout and anonymization are not verified by this review.

## Source snapshot

- `main.tex` SHA-256: `939d2523d1512d9caa68e27495e47499248d180b4d35dcb0ba2ab95b5a67576b`
- `body.tex` SHA-256: `89ea34b866b1a8d1388089b71097549c86e2451c1e8e7db5a9f6686880f360e6`
- `references.bib` SHA-256: `5b1975c374582131366179800533dfefc7bd74b96ae13c83253dd3c63eb79c5c`
## Root follow-up source check, 3 October 2026

The author's own publication page (https://xiaoxuerens.github.io/, rendered browser Publications entry) lists AdaCoder as a TSE article with the same seven authors and links to arXiv 2504.04220. The official FSE 2026 Journal-First programme also lists the same article and authors (https://conf.researchr.org/track/fse-2026/fse-2026-journal-first). These primary pages support existence/status, raising existence support to 35/35 attempted records; they do not expose the final journal text or independently establish its model count. The arXiv record has only v1 and its accessible full text reports six models. The manuscript removes the unnecessary twelve-model numeral and bases the described controller on the inspected preprint/author implementation. Final journal text/field-level checking remains unavailable; it is not described as a completed full-text audit.