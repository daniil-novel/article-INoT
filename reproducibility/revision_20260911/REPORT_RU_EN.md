# Post-review statistics: missingness and batch sensitivity

Date: 2026-09-11  
Archive: `reproducibility/results/20260908_codex_mini_heldout200`  
Code: `stats_batch_missingness.py`

## Русский отчёт

Этот постфактум диагностический анализ использует только сохранённые записи и манифесты; новых вызовов модели нет. Единица анализа — задача BigCodeBench (в отчёте архива она также называется task cluster), а не отдельный CLI-turn. Привязка к партии восстановлена по `id` ячейки: ячейка относится к `continuation`, если её `id` есть в `heldout200_continuation_manifest.json:pending_cells`; иначе она относится к `original`. Получено 460 original assignments и 540 continuation assignments. Из 1000 назначений сохранены 996 candidate records; 4 submitted-incomplete cells отсутствуют в candidate table. В continuation присутствуют 539 сохранённых записей.

Для качества `pass` кодируется как 1, `fail` и наблюдаемый `timeout` — как 0, а unavailable остаётся неизвестным. Поэтому bounds — это sharp finite-sample identification ranges при независимом варьировании каждого неизвестного endpoint между 0 и 1. Они не являются доверительными интервалами и не доказывают значимость, эквивалентность или non-inferiority.

| Контраст | 193 control-eligible задач | Все 200 назначенных задач |
|---|---:|---:|
| SR−SN | [−1.554, −0.518] п.п. | [−5.0, +3.0] п.п. |
| MR−MN | [+1.036, +1.036] п.п. | [−2.5, +4.5] п.п. |
| MN−SN | [−4.663, −3.627] п.п. | [−8.0, 0.0] п.п. |
| MR−SR | [−2.073, −2.073] п.п. | [−5.5, +1.5] п.п. |

Парные batch-сопоставления рассчитаны только для задач, у которых оба endpoint принадлежат одному batch. В original complete pairs составляют 87–90 из 200 задач (43.5–45.0%); в continuation — 102–104 (51.0–52.0%). Поэтому это не восстановление единой full-original серии. Наблюдаемые quality differences (п.п.) таковы:

| Batch | SR−SN | MR−MN | MN−SN | MR−SR |
|---|---:|---:|---:|---:|
| Original | −2.30 (CI −8.05, +3.45) | +3.37 (−3.37, +11.24) | −2.30 (−9.20, +4.60) | +4.44 (−2.22, +11.11) |
| Continuation | 0.00 (−4.93, +4.90) | −0.97 (−5.83, +3.88) | −6.73 (−13.46, 0.00) | −7.84 (−13.73, −2.94) |

В скобках приведены 95% percentile intervals task-cluster bootstrap (10,000 resamples, seed 20260911). Это описательные интервалы вариации задач; они не включают provider/model sampling, повторные запуски, batch uncertainty или uncertainty от missingness. Узкий continuation MR−SR interval не превращает post hoc анализ в доказательство архитектурного эффекта.

Для контроля покрытия cross-batch complete pairs составили 2 (SR−SN), 1 (MR−MN), 0 (MN−SN) и 1 (MR−SR); остальные полные пары были original–original или continuation–continuation. Cost summaries в CSV содержат оба denominator: legacy-поле на quality-complete pairs и отдельное `resource_complete_pairs` на всех парах с двумя наблюдаемыми resource endpoints. Ни cross-batch counts, ни различия знаков между batch не идентифицируют provider drift или причинный batch effect.

### Предложение для русской статьи

Добавить в раздел Results/Limitations отдельный абзац: «В постфактум анализе чувствительности 540 из 1000 назначенных ячеек были выполнены административным continuation после остановки исходной партии; 460 относятся к original batch. Batch восстановлен по идентификаторам ячеек из continuation manifest. Внутри-batch complete-pair coverage составила 43.5–45.0% для original и 51.0–52.0% для continuation. Поэтому first-batch-only оценки не интерпретируются как unbiased counterfactual для полной исходной серии. Для пропущенных binary endpoints bounds по 193 control-eligible задачам составили SR−SN [−1.55, −0.52] п.п., MR−MN [+1.04, +1.04], MN−SN [−4.66, −3.63], MR−SR [−2.07, −2.07]; при включении всех 200 назначенных задач bounds расширились. Эти bounds являются identification ranges, а не confidence intervals; observed timeouts считаются failures только в операционном описании, тогда как unavailable endpoints остаются неизвестными в bounds. Выводы ограничены сохранённой серией и не являются доказательством качества или non-inferiority.»

Следует сохранить формулировку о том, что comparisons относятся к целым процедурам; не называть batch differences репликацией или provider effect и не превращать descriptive bootstrap CI в интервал для population/provider uncertainty.

## English report

This post-review diagnostic uses retained records and manifests only; no new model calls were made. The unit is the BigCodeBench task (called a task cluster in the archive), not an individual CLI turn. Batch is recovered from cell IDs: a cell is `continuation` iff its ID occurs in `heldout200_continuation_manifest.json:pending_cells`; all other assigned cells are `original`. This yields 460 original assignments and 540 continuation assignments. The archive retains 996 candidate records for 1,000 assignments; four submitted-incomplete cells are absent from the candidate table, while 539 continuation cells are retained.

For quality, `pass` is 1, observed `fail` and `timeout` are 0, and unavailable endpoints remain unknown. The bounds are sharp finite-sample identification ranges under independent 0/1 completion of each unknown endpoint. They are not confidence intervals and do not establish significance, equivalence, or non-inferiority.

| Contrast | 193 control-eligible tasks | All 200 assigned tasks |
|---|---:|---:|
| SR−SN | [−1.554, −0.518] pp | [−5.0, +3.0] pp |
| MR−MN | [+1.036, +1.036] pp | [−2.5, +4.5] pp |
| MN−SN | [−4.663, −3.627] pp | [−8.0, 0.0] pp |
| MR−SR | [−2.073, −2.073] pp | [−5.5, +1.5] pp |

Within-batch paired comparisons include only tasks whose two endpoints are in the same batch. Original complete-pair coverage is 87–90 of 200 tasks (43.5–45.0%); continuation coverage is 102–104 (51.0–52.0%). These are descriptive batch-stratified subsets, not a reconstruction of an all-original run. The observed quality differences (percentage points) are:

| Batch | SR−SN | MR−MN | MN−SN | MR−SR |
|---|---:|---:|---:|---:|
| Original | −2.30 (CI −8.05, +3.45) | +3.37 (−3.37, +11.24) | −2.30 (−9.20, +4.60) | +4.44 (−2.22, +11.11) |
| Continuation | 0.00 (−4.93, +4.90) | −0.97 (−5.83, +3.88) | −6.73 (−13.46, 0.00) | −7.84 (−13.73, −2.94) |

Parentheses are descriptive 95% task-cluster bootstrap percentile intervals (10,000 resamples; seed 20260911). They do not quantify provider/model sampling, repeated-run, batch-assignment, or missingness uncertainty. The narrow continuation MR−SR interval should not be presented as evidence of an architectural effect.

As a coverage check, cross-batch complete pairs number 2 (SR−SN), 1 (MR−MN), 0 (MN−SN), and 1 (MR−SR); the remaining complete pairs are original–original or continuation–continuation. The CSV reports both cost denominators: the legacy quality-complete-pair field and a separate `resource_complete_pairs` field for all pairs with two observed resource endpoints. Cross-batch counts and sign differences across batches are descriptive and do not identify provider drift or a causal batch effect.

### Suggested insertion for the English article

“In a post hoc sensitivity analysis, 540 of 1,000 assigned cells were executed administratively as a continuation after the original batch stopped; 460 cells belong to the original batch. Batch membership was recovered from cell IDs in the continuation manifest. Within-batch complete-pair coverage was 43.5–45.0% for original and 51.0–52.0% for continuation. We therefore do not interpret first-batch-only estimates as an unbiased counterfactual for the fully original series. For the 193 control-eligible tasks, identification bounds for SR−SN, MR−MN, MN−SN, and MR−SR were [−1.55, −0.52], [+1.04, +1.04], [−4.66, −3.63], and [−2.07, −2.07] percentage points, respectively; including all 200 assigned tasks widened the ranges. These are identification ranges, not confidence intervals. Observed timeouts are failures only in the operational description; unavailable endpoints remain unknown in the bounds. Claims remain limited to this retained execution and do not establish quality preservation or non-inferiority.”

Keep the estimand framed as the full procedures. Do not describe batch differences as a replication or provider effect, and do not present the descriptive task bootstrap intervals as population/provider uncertainty intervals.
