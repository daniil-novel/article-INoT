# Root language R1 decisions

Applied the bounded R1 language edits to the English and Russian section sources on 2026-09-13. No compilation or commit was performed.

## Adjudications

- EN#1: use “Neither comparison remains statistically significant after Holm adjustment across the four prespecified tests.”
- EN#2: describe the preliminary intervention as changing context selection, rerun policy, and call topology together; this keeps the statement broad while retaining the documented selective-rerun context.
- EN#7: remove the duplicated Luna resource-accounting paragraph. Keep the Luna-specific rates and point the extension to the appendix’s complete-task accounting rules. Do not import the initial one-repeat complete-pair scope into the three-repeat extension.
- EN#10: preserve the executed prompt line `final_result=result_A if agreement else result_A (latest A fallback).` exactly. Clarify the surrounding explanation only.
- RU#1: state that 15,000 generations were assigned; retain the separate count of 14,961 completed programs.
- RU#4: retain the interaction estimand explicitly as the interaction of labels and call topology.

## Exact changed files

- `sections/closest_predecessor_en.tex`
- `sections/closest_predecessor_ru.tex`
- `sections/exact_prompts_en.tex`
- `sections/heldout_cases_en.tex`
- `sections/heldout_context_en.tex`
- `sections/heldout_context_ru.tex`
- `sections/heldout_methods_en.tex`
- `sections/heldout_methods_ru.tex`
- `sections/hybrid_core_en.tex`
- `sections/hybrid_core_ru.tex`
- `sections/revision_en.tex`
- `sections/revision_ru.tex`
- `sections/scale1000_results_ru.tex`
- `sections/swe_demonstration_ru.tex`
- `reviews/2026-09-13-language-full/ROOT_LANGUAGE_DECISIONS.md`

`converted_article_springer.tex` and `converted_article_springer_ru.tex` were inspected and required no changes because they contain the document wrapper and section inputs rather than duplicate target prose.

## Root verification after the agent pass

The applied EN#1 still used "remains", despite the requested adjudication. Root corrected it to "is statistically significant", preserving that only the three-call raw interval excludes zero. Root also restored the explicit label-by-topology interaction in the English predecessor paragraph and retained numeric ordering in the case-selection rule. The literal INoT instruction was unchanged.
