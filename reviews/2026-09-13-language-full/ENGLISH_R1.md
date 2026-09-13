# English readability review R1

## Scope and coverage

This is a language, readability, terminology, repetition, and self-containment pass over the English snapshot `input/en.pdf` / `input/en.txt`. The extracted text was read sequentially from the title through page 82, including the main text, figures and captions as represented in the extraction, tables, appendices, complete outcome tables, and references. The snapshot manifest identifies `en.txt` by SHA-256 `d51f9a7d4301697e9273e2f6244cba02bfb02b45d7e9d0592630492f2ff41871` and `en.pdf` by SHA-256 `c4a3db213ff8a426f92c4ee77c0199faff56bf616f49f7e2f91d296c6a430334`. I did not perform page-by-page visual inspection of the PDF, so this report does not assess visual layout or figure legibility. The review is limited to English expression and reader orientation; it does not evaluate the scientific design or numerical correctness.

The manuscript is unusually careful about scope, missingness, controls, and the distinction between instructed roles and observed agents. The main readability cost is density: long sentences repeatedly carry design, estimand, and limitation qualifications at once. Most wording is professional and consistent. The ten edits below are prioritized for concrete reader benefit; they do not change numbers, definitions, or claims.

## Prioritized edits

1. **P1 — Abstract, p. 1, sentence ending “neither rejects after the four-test Holm correction.”**

   “Neither rejects” is grammatically strained because the subject is an implicit pair of comparisons, and “after” leaves the statistical operation vague.

   **Replace with:** “Neither comparison remains statistically significant after Holm adjustment across the four prespecified tests.”

2. **P1 — Section 1, p. 2, paragraph beginning “The original Hybrid-INoT implementation also included context selection…”**

   The sentence “The preliminary comparison of complete configurations changed these mechanisms together with call topology” makes the reader parse several abstractions before learning the practical point.

   **Replace with:** “The preliminary comparison changed context selection, selective reruns, and call topology at the same time, so it cannot identify the contribution of internal roles.”

3. **P2 — Section 2.1, p. 3, sentence “This is a new empirical setting and evidence record, not a new principle…”**

   “Evidence record” is abstract and sounds self promotional. The surrounding paragraph already explains the concrete extension.

   **Replace with:** “The study therefore extends the comparison to a fixed call interface and records the evaluated programs, native outcomes, and token components; it does not claim a new principle of role collaboration.”

4. **P1 — Section 3.3, p. 8, sentence “Call deadlines and a finite $n_a$ bound generation attempts.”**

   The wording suggests that the number of calls is a number of attempts, although the preceding algorithm distinguishes calls within one assignment from retries.

   **Replace with:** “The call deadline and the fixed call count bound the generation procedure.”

5. **P1 — Section 5.2, p. 11, sentence “At most, the latter represent 200 independent sampling units…”**

   “The latter” forces the reader to look back across two different sample descriptions, and “sampling units” is less direct than the task-level unit used later.

   **Replace with:** “The 1,000 assignments therefore represent at most 200 independent task units, not 1,000 independent tasks.”

6. **P1 — Section 5.3, p. 12, sentence “unexpected tool, retry or compaction events invalidate the fixed text-only treatment.”**

   The plural subject and singular event concept make the rule harder to scan.

   **Replace with:** “An unexpected tool call, retry, or compaction event invalidates that text-only treatment.”

7. **P1 — Section 5.6, pp. 14–15, repeated resource-accounting paragraph beginning “$V$ is a counterfactual API list-price valuation…”**

   The paragraph repeats the resource definition and exclusions already stated almost verbatim in Section 5.5. Repetition is especially costly here because the reader has just encountered the same caveats. Keep the Luna-specific rate sentence in Section 5.6 and replace the repeated paragraph with a cross-reference.

   **Replace the repeated paragraph with:** “Resource accounting follows the definitions and complete-pair rules in Section 5.5; the Luna extension applies the rates stated above. Interrupted workflows and unknown usage remain reported separately and are never zero-imputed.”

8. **P2 — Section 11, p. 27, sentence beginning “The following four examples were selected…”**

   The selection rule is reproducible but syntactically overloaded (“in each direction in which…”).

   **Replace with:** “For each label contrast, we selected the lowest task ID with an observed, eligibility-gated discordance in each direction. Thus, the four examples contain one role-labelled–neutral discordance favouring each condition for each contrast.”

9. **P1 — Appendix A.1, p. 40, paragraph beginning “INoT* defines two virtual positions…”**

   This contains a clear local wording error: “result denotes a solution, thought its rationale, and agreement agreement between solutions.” It is also the one place where a reader may mistake pseudocode variable definitions for prose.

   **Replace with:** “INoT* defines two virtual positions, A and B, that propose solutions to the same task. `result` denotes a solution, `thought` its rationale, and `agreement` whether the two solutions match.”

10. **P2 — Appendix A.1, p. 40, pseudocode line `final_result=result_A if agreement else result_A (latest A fallback).`**

   The two branches are textually identical, so the intended distinction is easy to miss even though the following prose explains it.

   **Replace with:** “`final_result = common_result` if `agreement`; otherwise `final_result = result_A` (the latest answer from A).”

## Additional observations

The paper consistently labels the Luna SCC comparison as ongoing and avoids using it as completed evidence; that is appropriate for this language-only pass. I found no need to flag stock AI-like phrasing as a standalone defect, and I do not infer authorship or any AI percentage from the prose. The complete outcome tables are repetitive by design and were read as tabular records; their repetition is not an editorial defect requiring removal because the manuscript explicitly presents them as complete audit tables.
