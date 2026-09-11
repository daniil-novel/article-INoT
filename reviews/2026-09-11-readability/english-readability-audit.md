# English readability and scheme audit

Scope: `hybrid_core_en.tex`, `task_dependence_en.tex`, `inot_method_en.tex`, `exact_prompts_en.tex`, `segregation80_prompts_en.tex`, the current `hybrid_core_en.tex` and `inot_instruction_en.tex` diagrams, and PDF-QA pages 7, 14, 30, and 34. This is a preliminary language/readability pass; it is not a new scientific review.

The four inspected pages are generally readable. The Hybrid-INoT diagram clearly separates SR and MR, the external evaluation boundary is visible, and the INoT* diagram marks its dashed procedure as prescribed rather than observed. The task-similarity page explains the three criteria and the table numbering clearly. The prompt appendix is legible at the inspected scale.

## Material remaining fixes

1. **Avoid the orphaned continuation below the INoT* figure.** On PDF page 14, the final line of the paragraph from `sections/inot_method_en.tex:13` (“evidence about this disclosed adaptation ...”) appears below the figure caption, separated from the preceding paragraph. This makes the paragraph look like figure text. Ready fix: place the figure after that paragraph, or force the paragraph to remain together before the figure; no prose change is needed.

2. **Explain the intentionally identical branches in the literal INoT* listing.** `sections/exact_prompts_en.tex:45` contains `final_result=result_A if agreement else result_A (latest A fallback)`. As literal prompt text this is faithful, but a reader can mistake it for a transcription error. Add immediately after the listing: “Both branches name `result_A`: under agreement it is the common answer, whereas at the round limit it is the latest answer from A.” This preserves the executed prompt and makes the fallback explicit.

3. **Make the code-similarity thresholds grammatical and easier to scan.** `sections/task_dependence_en.tex:8` says “must have Jaccard similarity of at least 0.80 as sets and 0.70 as multisets”. Replace with: “The set Jaccard similarity must be at least 0.80 and the multiset Jaccard similarity at least 0.70; both measures use non-keyword identifiers and string or numeric literals.”

4. **Clarify what the similarity table counts.** `sections/task_dependence_en.tex:12` says “seven contain 15 tasks in total”. This is correct but easy to misread as seven groups of 15 tasks. Replace with: “It yields 992 groups: seven are non-singleton groups containing 15 tasks in total, and the remaining groups are singletons.”

5. **Make the figure’s MR context flow explicit at the call boxes.** The Hybrid-INoT diagram and caption are consistent, but the arrows between MR call 1, call 2, and call 3 visually show only sequencing; the full-context forwarding is stated only in the caption. If space permits, add a short line to the call-2 and call-3 boxes, such as “+ full previous responses”, or retain the caption sentence and add “full previous responses” next to the two vertical arrows. This is a comprehension improvement, not a numerical or methodological correction.

No additional problem was found in the inspected PDF pages with labels, numbers, pseudocode step order, or the distinction between generation-unavailable outcomes and native test failures. The already planned fixes to the first two algorithm steps, the AST wording, listing size, and A.2 page break address the other visible risks.
