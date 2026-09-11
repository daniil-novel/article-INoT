# Follow-up: SCC feedback-method wording and related-work note

Дата: 2026-09-11. Повторная техническая проверка после правок. Первый отчёт не изменялся; модели и эксперименты не запускались.

## Что теперь сформулировано корректно

1. `sections/closest_predecessor_en.tex:16` и `closest_predecessor_ru.tex:16` явно разделяют paper SCC и pinned author-code implementation, называют реальные arms (SCC, fresh SR, fresh SN), говорят, что в frozen comparison нет role-excised SCC, и ограничивают SCC-vs-SR/SN сравнением полных workflow. Это соответствует `reproducibility/revision_20260911/scc_protocol.md:10-18,31-38` и manifest (`methods` содержит только `single_roles`, `single_neutral`, `scc_author_2024_codex_transport`). Обещанных role-excised arm или powered superiority claim нет.

2. `sections/scc_feasibility_en.tex:5` и RU-версия теперь правильно указывают: paper (2023) описывает simulated tester report; pinned author code исполняет model-generated report/examples; controller logic сохранена, но configured cap отличается. Формула “max_round=2, одна initial coder generation плюс не более одного repair, до четырёх model calls включая analyst/tester” согласуется с `external_baselines/vendor/scc_2024/session.py:8-12,19-57`, adapter `external_baselines/scc.py:69-80` и dispatcher `revision_20260911/scc_dispatch.py:95-96`. При `max_round=2` второй coder call является последним раундом, поэтому после него tester не вызывается; верхняя граница действительно 4 calls: analyst + coder + tester + coder.

3. Это корректно отделяет author-code constructor default `max_round=4` от paper's experimental maximum interaction (`SCC paper v2`, §3, HTML lines 136--138; §4, line 145; §5.3, lines 196--205). Новый текст не называет `max_round=2` репликацией paper MI=4 и прямо ограничивает вывод данной конфигурацией.

4. `sections/related_extended_en.tex:1` и RU-версия не обещают Self-Refine/Reflexion as arms. Self-Refine primary paper states that the same LLM generates, gives feedback, and refines iteratively (NeurIPS abstract; arXiv v2 lines 98--110, 167--221). Reflexion primary paper states that verbal reflection is stored in episodic/long-term memory and reused in later trials (NeurIPS paper lines 17--30, 312--350); its programming implementation generates, filters and executes self-generated unit tests (lines 497--515). Thus the new summary (“same model”; “verbal reflections”; “self-generated executable tests”) is supportable and the explicit “neither has been run as an experimental arm” is accurate.

## One concrete defect in the new reproducibility note

`reproducibility/revision_20260911/FEEDBACK_METHOD_COMPARISON.md:11` says “Present factorial components ... Five conditions; 1000 tasks × three repeats in the running Luna study.” This row conflates the factorial component study with the separate SCC comparison. The factorial component study has five conditions over the 200-task held-out allocation, with 1,000 candidates (5 × 200), as stated in `sections/heldout_methods_en.tex:30,32`; the 1,000 tasks × three repetitions / 9,000 assignments belong to the separate SCC/SR/SN comparison (`scc_protocol.md:21-27`, `scc_manifest.json`).

Recommended exact replacement for note line 11:

> Present factorial components | Fixed sequence; no execution feedback during generation | Five conditions on the 200-task factorial allocation (1,000 candidate assignments); separate SCC comparison uses 1,000 tasks × three repetitions and is not a role-excised arm

The same distinction should be preserved in any Russian rendering of this table. This is a documentation defect only; it does not imply a data or experiment defect.

## No other blockers found

`FEEDBACK_METHOD_COMPARISON.md:15,22-24` correctly records cap=2, at most four calls, no role-excised SCC, complete-workflow estimand, lack of equal-token-budget matching, and separation of internal exception-based execution from benchmark quality. The related-work paragraph correctly says component conditions do not receive execution feedback during generation; author-code SCC is the separately scoped exception. No nonexistent Self-Refine, Reflexion, role-excised, or other promised arm is claimed.
