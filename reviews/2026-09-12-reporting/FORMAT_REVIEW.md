# Подготовительная проверка формата полного приложения

Дата: 2026-09-12. Это подготовительная проверка читаемости и аудируемости, а не финальная научная рецензия. Живые исходы в `reproducibility/runs` не читались и не анализировались; модельные и нативные запуски не выполнялись. Код, протоколы, статьи и работающие запуски не изменялись.

## Проверенные файлы

- `sections/heldout_tasks_en.tex`
- `sections/heldout_tasks_ru.tex`
- `reproducibility/scale1000_luna/collect.py`
- `reproducibility/revision_20260911/scc_export.py` (SCC-сборщик; отдельного `scc_collect.py` нет)
- Для уточнения итоговой классификации прочитан фрагмент `reproducibility/revision_20260911/scc_finish.py`.

## Что следует сохранить в полном приложении

Основная факторная матрица должна содержать все 15,000 назначений: 1,000 задач, 5 условий и 3 повтора. SCC должен быть отдельной матрицей из 9,000 назначений: 1,000 задач, 3 метода и 3 повтора. Идентификатор строки — составной ключ `task_id`, условие или метод и `replicate_id`; повтор следует хранить отдельным числом, а не кодировать набором значений в одной ячейке.

В каждой строке PDF и CSV рекомендуется сохранять как минимум:

`task_id`, `arm` или `method`, `replicate_id`, `availability`, `generation_complete`, `observed_candidate`, `format_extracted`, `native_status`, `control_eligible`, `quality`, `outcome_type`.

Дополнительный ресурсный файл может содержать `resource_usage` и стоимость. Полный текст кандидата и сырые доказательства должны оставаться в архиве и связываться с этой строкой через стабильный идентификатор и хеш.

Классификации должны оставаться раздельными:

- `native_status=pass`, `fail` или `timeout` — результат штатного теста, когда нативный отчёт действительно существует;
- `generation_unavailable`, `submitted_incomplete` или `infrastructure_failure` — назначение без полного кандидата либо с незавершённым сбором;
- `native_unavailable` — кандидат есть, но нативный отчёт отсутствует или не принят проверкой;
- `model_format_failure` — ответ получен, но формат кандидата не извлечён;
- `control_ineligible` — контрольная проверка не разрешает оценивать качество этой задачи.

Для всех перечисленных случаев `quality` должно быть `unknown` или пустым, то есть `null`, кроме явного форматного отказа и штатного `pass` или `fail` по определению протокола. В частности, отсутствие кандидата, отсутствие native-отчёта и контрольная непригодность нельзя автоматически превращать в `fail`. Список назначений сохраняется целиком, включая незавершённые и недоступные строки.

## Сравнение двух вариантов

| Вариант | Представление | Читаемость | Аудит и риск ошибки |
|---|---|---|---|
| A | В PDF одна строка на назначение (`task_id` плюс условие или метод и повтор), а полный CSV прикладывается к AAMAS | Хорошая для поиска отдельного назначения; 15,000 строк остаются длинным, но однородным приложением | Лучшая: каждая строка однозначна, неизвестное видно отдельно, CSV пригоден для фильтрации и пересчёта |
| B | В PDF одна строка на задачу; для каждой группы условий или методов три отдельные подколонки повторов 101, 102 и 103, плюс отдельная колонка `control_eligible`; полный CSV также прикладывается | Компактнее и удобно для обзора задачи целиком (около 15 ячеек исходов в факторной строке), но таблица становится широкой, а обозначения повторов нужно постоянно держать в легенде | Пригодно для обзорного PDF, но хуже для аудита: конечная ячейка качества может скрыть отсутствие кандидата, native-отчёта или форматную ошибку. Эти различия должны быть полностью восстановимы только из CSV |

## Выбор

Рекомендую вариант A: PDF с одной строкой на назначение и полный CSV как дополнительное приложение AAMAS. Он лучше показывает отдельно штатное качество, отсутствие полного кандидата, отсутствие native-отчёта, форматную ошибку и контрольную пригодность; `unknown` не маскируется пустой ячейкой и не превращается в `fail`. В PDF следует иметь две самостоятельные версии или две самостоятельные таблицы с одинаковой схемой: English и Русский. Вариант B можно использовать как короткую обзорную таблицу в основном тексте, но его итоговые ячейки не заменяют assignment-level ledger.

Для удобства чтения PDF можно разбить на последовательные страницы по диапазонам задач и повторять заголовок таблицы на каждой странице. Это разбивка отображения, а не удаление строк. В CSV порядок рекомендуется фиксировать как `task_id`, затем условие или метод, затем `replicate_id`.

## Искусственный образец строк

Строки ниже вымышлены и показывают только формат. Они не являются результатами исследования.

| task_id | arm or method | replicate_id | availability | generation_complete | observed_candidate | format_extracted | native_status | control_eligible | quality | outcome_type |
|---:|---|---:|---|---|---|---|---|---|---|---|
| 900001 | D | 101 | completed | true | true | true | pass | true | true | native_outcome |
| 900001 | D | 102 | completed | true | true | true | fail | true | false | native_outcome |
| 900001 | D | 103 | submitted_incomplete | false | false | false | unknown | true | unknown | submitted_incomplete |
| 900002 | SN | 101 | completed | true | true | true | unknown | true | unknown | native_unavailable |
| 900002 | SN | 102 | completed | true | true | false | unknown | true | false | model_format_failure |
| 900002 | SN | 103 | completed | true | true | true | pass | false | unknown | control_ineligible |

### English caption and legend

**Table A. Complete assignment ledger for the 1,000-task repeated study.** One row represents one task-condition-repeat assignment. `pass`, `fail`, and `timeout` are native benchmark statuses. `generation_unavailable` or `submitted_incomplete` means that no complete candidate was retained; `native_unavailable` means that a candidate exists but no accepted native report exists; `model_format_failure` means that the response was obtained but no candidate could be extracted; `control_ineligible` means that the control gate does not permit a quality endpoint. `quality=unknown` is retained for unavailable or ineligible endpoints and is not counted as failure.

### Русская подпись и легенда

**Таблица A. Полный реестр назначений для исследования 1,000 задач с повторами.** Одна строка соответствует одному назначению «задача — условие — повтор». `pass`, `fail` и `timeout` — статусы штатной проверки. `generation_unavailable` или `submitted_incomplete` означает отсутствие сохранённого полного кандидата; `native_unavailable` — наличие кандидата при отсутствии принятого нативного отчёта; `model_format_failure` — ответ получен, но кандидат не извлечён из-за формата; `control_ineligible` — контрольная проверка не разрешает оценивать качество. `quality=unknown` сохраняется для недоступных или непригодных конечных точек и не считается отказом.

Для SCC используется та же построчная схема, но заголовок явно называет метод: `method` вместо `arm`, 3 метода и 3 повтора, всего 9,000 назначений. Это поддерживает самостоятельные EN/RU приложения и не смешивает SCC с основной пятиусловной матрицей.
