# Claim-to-source ledger

Accessed 8 September 2026. Primary sources only. A source's result is background, never an observation from this project.

| Claim / decision | Primary source and date | Evidence / limitation |
|---|---|---|
| Internal programmatic debate is prior art | Sun and Zeng, *Introspection of Thought Helps AI Agents*, arXiv v1, 11 July 2025: https://arxiv.org/html/2507.08664v1 | Sections 3.1/3.3 and Listings 1/3 describe PromptCode and two debating roles. Listing 3 has an OR condition inconsistent with a simple bounded-loop interpretation. No claim to invent internal role debate; no original baseline result is reproduced here. |
| Equal reasoning budgets can change multi-agent comparisons | Tran and Kiela, *Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets*, April 2026: https://arxiv.org/abs/2604.02460 | Different task domain; motivates budget controls, does not establish coding performance. |
| BigCodeBench has 1,140 library-rich programming tasks | Zhuo et al., *BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions*, 2024 / ICLR 2025: https://arxiv.org/abs/2406.15877 ; https://github.com/bigcode-project/bigcodebench | Current official evaluation and dataset repository; the downloaded v0.1.4 release has exactly 1,140 unique rows. Official tests required. Difficulty and no-ceiling outcome must be measured, not assumed from its name. |
| Dataset bytes and field separation | https://huggingface.co/datasets/bigcode/bigcodebench | Revision b74c0d0bf70d2c0bc459be537895cca163007f1a; v0.1.4 parquet downloaded, SHA256 in dataset_source.json. Model inputs use instruct_prompt/code_prompt; canonical_solution/test remain evaluator-only. |
| Repository repair must use real patch application and tests | Jimenez et al., SWE-bench; official evaluation documentation: https://www.swebench.com/SWE-bench/guides/evaluation/ | Predictions contain instance_id/model_name_or_path/model_patch; per-instance report.json, test_output.txt and patch.diff are required evidence. A zero process return code is not resolved=true. |
| Agentless is an upstream pipeline comparator | Xia et al., *Agentless: Demystifying LLM-based Software Engineering Agents*, 2024: https://arxiv.org/abs/2407.01489 ; https://github.com/OpenAutoCoder/Agentless | Localization, repair and validation; use upstream implementation and record overrides. A handwritten three-role pipeline is not Agentless. |
| SWE-agent is an upstream tool-using comparator | Yang et al., *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*, NeurIPS 2024: https://arxiv.org/abs/2405.15793 ; https://github.com/SWE-agent/SWE-agent | Native environment interactions differ from fixed-context generation. Current maintainers recommend mini-swe-agent for new deployments, but original SWE-agent remains the reviewer-requested comparator. Never silently substitute it. |
| Verified still has validity and contamination concerns | OpenAI, *Why SWE-bench Verified no longer measures frontier coding capabilities*, February 2026: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ | First-party audit concerns frontier evaluation. Does not invalidate every instance or establish our cheap-model outcomes. Use Verified for comparability with explicit limitations and require temporal replication before broad claims. |
| API price and model availability | https://openrouter.ai/api/v1/models ; https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key | Live model catalogue saved in model_catalog_2026-09-08.json. Key-status read confirmed exhausted local allowance; no secret saved. Advertised aliases and prices can drift. |

## Upstream source pins (git ls-remote HEAD, 8 September 2026)

- BigCodeBench: `09dd993f46c3fbf3a799465bb96d524edcb0b199`
- SWE-bench: `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`
- Agentless: `5ce5888b9f149beaace393957a55ea8ee46c9f71`
- SWE-agent: `3ea751c087f32b16e039a2233dd6eefecef325d5`

At the initial source-discovery stage these pins identified inspected public upstream heads, not installed versions. The later BigCodeBench pilot actually uses the pin above and records its source and image digests. The later one-task SWE demonstration also executes the pinned SWE-bench harness. Agentless and SWE-agent remain unexecuted.

## Gaps and stopping decision

Source discovery covered original INoT, official evaluation/baseline implementations, budget-comparison prior art, current benchmark validity concerns and model prices. Follow-up checked the actual dataset schema, current source revisions, the INoT termination ambiguity and the distinction between successful harness execution and a resolved task. These are sufficient to revise the study question and evidence gates. Further broad searching cannot supply missing API responses or official evaluation results; synthesis proceeds with these gaps explicit.

Unresolved at the initial eight-task development checkpoint: original INoT executable release/fidelity validation; installed upstream baseline environments; a frozen SWE repository retrieval packet and its gold-patch/negative controls; large confirmatory model generation and paired outcomes. The project does not claim systematic-review completeness or verified absence of all similar work.

## Evaluator preflight follow-up

The pinned BigCodeBench source was cloned and its HEAD verified locally. Its loader supports `BIGCODEBENCH_OVERRIDE_PATH` for the pinned local dataset. GitHub marks the repository archived since 20 July 2026. Registry metadata resolves the amd64 evaluator image to the digest in `evaluator_preflight.json`; its compressed layers total 9,273,490,980 bytes, exceeding the observed C: free space before unpacking. At that initial preflight checkpoint no image was pulled and no official control was executed; the later custom-image control archives supersede that execution status. The image's internal source version remains unverified.

## Subscription execution follow-up

- GPT-5.4 mini documentation: https://developers.openai.com/api/docs/models/gpt-5.4-mini . Coding-capable mini model, medium reasoning supported. This describes advertised capability, not measured quality on our tasks. The CLI alias is recorded; an immutable served snapshot is not independently proven.
- Standard API list prices: https://developers.openai.com/api/docs/pricing . Accessed 8 September 2026: USD 0.75/M input, 0.075/M cached input, 4.50/M output. Used only for counterfactual valuation of CLI tokens, never as a subscription invoice. Cheaper GPT models exist; this pilot is not an exhaustive model-price-quality optimization.
- Noninteractive CLI JSONL: https://developers.openai.com/codex/noninteractive . `turn.completed.usage` supplies observed token counters. Cached input and reasoning output are subsets, not additional totals. No verified CLI controls for provider sampling seed, temperature or equal hard output allowance were established.
- Tool registration: official https://github.com/openai/codex/releases/tag/rust-v0.152.0 and https://raw.githubusercontent.com/openai/codex/rust-v0.153.4/codex-rs/core/src/tools/spec_plan.rs . CLI 0.144.1 exposed the planning tool despite text-only instructions. Version 0.153.4 supports explicit `tools.update_plan.enabled=false`; remaining model-dependent tools are guarded by per-trace rejection.
- The development evaluator executes both the pinned BigCodeBench core and the unchanged official CLI in the documented smaller containers. All 40 raw test statuses agree. This is selective `instruct` evaluation of eight tasks in a custom environment, not a full benchmark score or the complete official release image. Reference-control failures remain missing for all treatments.

## Completed development and reserved-sample follow-up

- The unchanged BigCodeBench CLI evaluated 400 new development programs with 400 verified input/code/status joins. The 39/40 control eligibility is retained. These are 40 independent assigned task clusters and two labelled repeats, not 400 independent tasks. Full evidence: `results/20260908_codex_mini_dev40/`.
- The official SWE harness pin above actually evaluated two generated patches for one frozen development issue. One applies but fails the target test, one fails native application. Ten candidates were assigned; eight are missing after a transport deadline. Native logs establish these classifications, not an exit code alone. The custom NumPy 1.26.4 environment passes the gold control; earlier official-image failures remain archived.
- The SWE Lite source card https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite/raw/main/README.md does not supply a blanket repository-content license. Exact upstream source licenses at all included repo/commit pairs are recorded under the SWE evidence archive. The harness license does not replace them.
- The reserved 200-task allocation was selected before controls. Updated environment controls validate 193 references and reject all 200 deliberately incorrect programs. Original tasks and tests remain fixed. No model quality is inferred from controls.
- INoT Sections 3.1/3.3, Listings 1/3 support the two-debater PromptCode concept. Our separately frozen 86-word instruction is independently worded, omits image augmentation for text tasks, uses agreement-or-ten-round stopping from the prose, and declares a latest-Agent-A fallback when ten rounds end without agreement. This resolves ambiguities for this replication; it is not an author-validated exact implementation. No native author executable was identified in the inspected primary sources, which is not proof that none exists.

## Additional comparator and persona context (8 September 2026)

Final empirical checkpoint: the primary archive at commit `96be37745b7f727d790c324fc0d8670f8e7623f2` contains 996 observed programs from 1,000 assignments, all checked by the unchanged native evaluator. There are 963 eligible observations; all four predeclared quality contrasts have Holm-adjusted p above 0.05. Known primary usage is 8,585,185 tokens, USD 14.2048182 list-price valuation, with three unknown-usage calls. The separate 199-program INoT adaptation has 96/192 eligible passes. These are local experimental observations, not facts inferred from the literature. Full primary, development and INoT response/report/statistics replay passes in Linux CI and the isolated local analysis environment.

- Zheng et al., Findings EMNLP 2024, https://aclanthology.org/2024.findings-emnlp.888/: factual-question persona effects; motivates explicit label controls, not a coding result.
- Luz de Araujo et al., EMNLP 2025, https://aclanthology.org/2025.emnlp-main.1364/: separates performance, irrelevant-attribute robustness and fidelity. Broad persona claims are not justified by one fixed prompt.
- Choi, Zhu and Li, NeurIPS 2025, https://arxiv.org/abs/2508.17536v2: separates debate from majority voting; no voting baseline is silently imputed to our serial pipeline.
- Wunderlich et al., ACL Student Research Workshop 2026, https://aclanthology.org/2026.acl-srw.1/: reports configurations favorable to multi-agent inference under its compute comparison on MMLU-Pro/BBH. Included as a counterpoint; these external results do not establish code-generation performance.

## Closest predecessor and outcome-classification correction

- Dong, Jiang, Jin and Li, *Self-collaboration Code Generation via ChatGPT*, arXiv:2304.07590v2 (24 May 2023), https://arxiv.org/html/2304.07590v2. Sections 5.2–5.3 compare role-excised prompting and different maximum interactions; Appendix B.1 supplies role-removal detail. These are prior ablations. Our methodological inference is that SCC is the closest external role baseline; the joint fixed-call matrix, new dataset and evidence audit are an extension, not first introduction of role ablation. No SCC score is imported into our results.
- SWE-bench official evaluation guide, https://www.swebench.com/SWE-bench/guides/evaluation/, and the already pinned harness source `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`: empty predictions, evaluator errors and native test outcomes have different reporting paths. Report absence alone cannot establish either failure or evaluability. The collector additionally requires archived model-response provenance to distinguish invalid candidates from damaged exports. Synthetic regression fixtures verify code behavior and are not experimental observations.

## Hybrid-INoT manuscript integration

The original manuscript immediately preceding f8f7006 is retained in Git and supplies the author's engineering framing, internal/external responsibility split and resource-accounting questions. The integrated text treats the published 200-task protocol as authoritative about what was actually executed. Its conditional token balance and screening-cost identity are explicit algebraic models, not new empirical observations. The original INoT source (https://arxiv.org/html/2507.08664v1) and the closest role-ablation predecessor (https://arxiv.org/html/2304.07590v2) were checked again on 8 September 2026 to preserve the distinction between the proposed role-labelled core, PromptCode adaptation and unexecuted SCC baseline.


## 9 September: author-code SCC feasibility update

The external baseline is now implemented as a pinned original SCC session with a disclosed Codex subscription transport adaptation. All three exposed development tasks produced candidates and were checked by native BigCodeBench tests: one pass, two failures; all three gold and incorrect controls behaved as expected. Full traces and upstream-controller replay are in `reproducibility/results/20260909_scc_dev3`. This supersedes earlier statements that no SCC execution exists; a powered external comparison, SCC role ablation, native Agentless and SWE-agent runs remain outstanding. The pilot does not change historical primary estimates or establish superiority.
