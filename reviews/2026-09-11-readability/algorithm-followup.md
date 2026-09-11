# Algorithm-semantics readability follow-up

Date: 2026-09-11
Scope: read-only follow-up after the algorithm and figure revisions. Checked the current EN/RU `hybrid_core`, `task_dependence`, `exact_prompts`, and `figures/inot_instruction` sources, plus the supplied Russian PDF pages 7, 8, 16, 34 and 38. No experiments or live-series outputs were read.

## Result

No substantive semantic error was found in the revised algorithm or figures. The measured boundary is now clear:

```text
task/context and assigned condition -> observed call path -> extraction
-> external native evaluation -> outcome/resource record
```

Figure 1 explicitly limits itself to the observed response path and points incomplete generation to Algorithm 1. The algorithm separately marks an incomplete call or unverifiable resource record as unavailable, keeps invalid-format output as an empty observed candidate, and states that native test results are not returned to the model (`sections/hybrid_core_en.tex:31-47`; RU counterpart lines 31-47). The PDF rendering makes this distinction readable.

The SR/MR drawing is a representative view rather than a claim that only two arms exist. Its caption states that D, SN and MN are among the five evaluated conditions and that they share external evaluation (`sections/hybrid_core_en.tex:16-19`, RU counterpart). The MR arrows and caption correctly indicate forwarding of complete preceding responses; the figure does not imply native feedback between calls.

Figure 2 is now semantically bounded by the dashed region and its caption: it depicts prescribed content in one model request, not a host-executed loop or measured internal agents. The decision has the correct agreement-or-ten-rounds stopping condition, and the common output box “latest solution A” is compatible with agreement because agreement means A and B have the same answer (`figures/inot_instruction_en.tex:5-16`; `sections/inot_method_en.tex:7-10`; `sections/exact_prompts_en.tex:25-49`). The appendix also preserves the literal non-whitespace instruction content and explicitly says that the rounds are unobserved.

The task-dependence section is also internally coherent for this audit: it states that only source instructions/reference programs enter the similarity screen, excludes generated answers and evaluation outcomes, and keeps the later outcome-based intervals pending for the Luna extension (`sections/task_dependence_en.tex:1-12,29-31`; RU counterpart). It does not turn source similarity into a claim of semantic independence.

## Minor points worth monitoring, not blocking defects

1. Algorithm 1 deliberately numbers the evaluation items 6--8 after generation items 1--5. This is readable as one continuous procedure and is not a semantic error; if the layout is later simplified, retaining either continuous numbering or explicitly restarting at 1 would avoid a purely presentational question.
2. Figure 1's input box names task and context but not the preassigned condition. The branch labels and Algorithm 1 input state supply that missing detail, so the figure is not misleading. A condition label in the input box would be optional clarification only.
3. The INoT figure's output box says “latest solution A” for both exits. The caption and appendix explain the agreement case (`A=B`) and the no-agreement fallback, so this is correct. Replacing it with “agreed A/B, otherwise latest A” would improve immediate readability but is not required for semantic correctness.

These are presentation observations only. No change is recommended by this follow-up unless the editor wants additional visual polish.
