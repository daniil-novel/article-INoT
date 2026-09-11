# Recorded request for the preparatory statistical reporting audit

Subsequent follow-up task (same reviewer, separate report):

```text
Please run a bounded follow-up on the revised sections/standalone_details_en.tex and sections/standalone_details_ru.tex. Verify the new resource-eligibility paragraph against both frozen analyzers: component contrasts require completed generations, whereas SCC full-resource metrics can retain an incomplete workflow if every submitted turn has known counters. Check the two ratio equations, zero-denominator subset, ratio-of-means versus mean-of-ratios intervals, random generators and seeds. Also check that the numerical-degeneracy wording remains conditional and does not pretend to amend or recompute frozen tests. Read local code only, do not inspect live outcomes or modify manuscript/analysis. Save a separate report as reviews/2026-09-12-decision-rules/RESOURCE_FOLLOWUP.md; give concrete corrections if needed. This remains the same preparatory reviewer, not a second independent critic.
```

Requested configuration: GPT-5.6 Luna, medium. This is the exact authored task
text supplied to the child reviewer, retained before dispatch. It does not
include system instructions, internal reasoning or a claim about backend weights.

```text
Perform a bounded, read-only statistical reporting audit of the large-study appendix. This is a preparatory check, not a final independent review of the completed paper. Read sections/standalone_details_en.tex, sections/standalone_details_ru.tex, reproducibility/scale1000/analyze.py, reproducibility/scale1000_luna/protocol.md and reproducibility/revision_20260911/scc_analyze.py plus scc_protocol.md. Do not read live study outcomes, run models or native tests, change frozen files, or edit manuscript files. Verify the exact primary test families, task/repeat unit, bootstrap generators, percentile interpolation, seeds and resource-ratio estimands. Check the edge case of constant nonzero paired differences: the frozen factorial code emits p=0 with a degeneracy flag and null t-statistic, whereas SCC reports the test as unestimable. Explain how to report this accurately without changing frozen analysis or falsely claiming that it occurred in real data. Suggest a short, readable clarification in EN and RU for a standalone paper, keeping routine operational status out of the table. Save your audit separately as reviews/2026-09-12-decision-rules/METHODS_REVIEW.md. Clearly distinguish actual code facts, any scientific concern, and the limited scope. Use only relevant local sources; browse primary sources only if needed for a statistical fact. Do not write tests that merely reproduce implementation. Return the report path and actionable findings. You are GPT-5.6 Luna with medium reasoning, requested for this bounded audit.
```

Follow-up context supplied during the same audit:

```text
Additional reporting point from local code inspection: primary resource contrasts explicitly require completed generations in all six task-condition-repeat rows. SCC full-resource metrics require known counters for every submitted turn, but _task_means does not require generation_complete; thus an incomplete workflow can still have a known consumed-resource total. Known-subtotal fields are separate again. Please verify and distinguish these scopes, and verify that the SCC ratio interval is for mean within-task ratios (dropping zero denominator pairs), while ratio_of_means is only a point estimate. This is a check of frozen code semantics, not an instruction to alter them.
```
