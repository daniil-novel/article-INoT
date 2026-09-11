# Feedback methods: source and implementation distinctions

Checked 11 September 2026 while the primary Luna generation was running and before the main SCC comparison. This is a literature and implementation clarification, not a change to either frozen experiment or an outcome analysis.

| Method/version | Feedback and continuation | Status in this study |
|---|---|---|
| [SCC paper, v2](https://arxiv.org/html/2304.07590v2), §3 and §5.2–5.3 | Simulated tester reports; separate role and interaction ablations | Closest conceptual antecedent |
| [SCC author revision b471e1](https://github.com/YihongDong/Self-collaboration-Code-Generation/blob/b471e12051190dbae2c71b429a3c87466df4b336/session.py) | Executes generated code and tester output; exception-free execution can stop the session | Actual external implementation, with the disclosed transport/dataset adaptation |
| [Self-Refine, NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/91edff07232fb1b55a505a9e9f6c0ff3-Paper-Conference.pdf), §2 | The same model produces feedback and refinements | Related work; no executed arm |
| [Reflexion, NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf), §3 and §4.3 | Verbal reflection retained across trials; generated executable tests in programming | Related work; no executed arm |
| Present factorial components | Fixed sequence; no execution feedback during generation | [Running Luna extension](../scale1000_luna/PROTOCOL.md): 1000 tasks × five conditions × three repeats = 15000 assignments |

## Exact SCC configuration

The source constructor defaults to `max_round=4`. The adapter and frozen main dispatcher explicitly use `max_round=2`: analyst, initial coder, tester, and at most one coder repair. This is at most four model calls, and is not a reproduction of the paper's maximum-interaction setting. The early-stop rule and transition logic are retained; the configured iteration limit is adapted. Compare:

- `external_baselines/vendor/scc_2024/session.py`, constructor and `run_session`;
- `external_baselines/scc.py`, `run_session`;
- `revision_20260911/scc_dispatch.py`, SCC invocation;
- `revision_20260911/scc_protocol.md`, scope and estimand.

The frozen SCC comparison has SCC, fresh SR and fresh SN, totalling 9000 assignments. It has no role-excised SCC condition. SR–SN and MR–MN estimate the specified label effects within the factorial experiment. SCC versus SR/SN compares complete workflows under the chosen resource policy, including generated-test feedback, extraction and stopping. It is not an equal-token-budget comparison or a label-only effect. No main SCC outcome is available at this audit.

Generated SCC tests receive neither benchmark evaluation tests nor reference programs. Benchmark evaluation runs after generation and determines the separate quality endpoint. Exception-free internal execution is not proof of benchmark correctness.

## Editorial resolution

Both manuscripts now identify the SCC paper and author code separately, disclose the configured iteration cap, name the actual external arms, and include Self-Refine and Reflexion as methodological context. The bibliographic Reflexion entry follows the five-author NeurIPS proceedings record; the later arXiv v4 has a different author list. No historical scores are compared across those methods or imported into our experiment.

The independent technical review is retained in `reviews/2026-09-11-dependence/feedback-methods-audit.md`. It does not replace the final scientific review after the large studies complete.
