# Подготовительная техническая проверка рендера assignment tables

Дата: 2026-09-12. Это follow-up к подготовительной проверке формата, а не финальная научная рецензия и не проверка реальных больших результатов. Реальные outcomes в `reproducibility/runs` не читались. Генерации и нативные оценки не запускались; разрешённый офлайн-набор из 26 искусственных тестов выполнен.

## Проверенные исходники и результат

Проверены:

- `reproducibility/revision_20260911/render_assignment_tables.py`
- `reproducibility/tests/test_assignment_tables.py`
- схемы путей и контрактов в `reproducibility/revision_20260911/publish_scale.py` и `reproducibility/revision_20260911/publish_scc.py`.

Команда `python -m pytest -q reproducibility/tests/test_assignment_tables.py` завершилась результатом `26 passed in 0.48s`.

## Подтверждённое соответствие

Рендерер использует пути готовых архивов согласованно с публикационными скриптами:

- factorial: `analysis/candidate_records.jsonl`, `inputs/scale1000-v1/selection.json`, `controls/controls-v3/heldout200_control_gate.json`;
- SCC: корневой `candidate_records.jsonl`, `inputs/selection.json`, `controls/heldout200_control_gate.json`.

Перед построением таблиц проверяется `generation/status.json= generation_finished`, отсутствие `generation/DISPATCH.lock`, манифест доказательств и фиксированное распределение 1,000 задач с 985 пригодными по контролю. `project_rows` требует полный уникальный ключ task-condition-repeat: 15,000 строк для factorial и 9,000 для SCC. Пропуск строки, дубликат, неправильный task ID или повтор отвергаются до рендера.

Для каждого назначения source-поля корректно проецируются в самостоятельные поля `candidate_available`, `format_extracted_recorded`, `native_status`, `quality` и `outcome_type`. `null` остаётся `unknown` в CSV; он не преобразуется в `false` и не считается отказом. При отсутствии кандидата формат помечается как `not_assessed`, а явный исходный флаг `format_extracted=false` сохраняется в `format_extracted_recorded`.

Коды PDF разделяют состояния: G — нет полного кандидата, N — нативная конечная точка недоступна, U — качество непригодно по контролю, P — успех, F — штатный fail, T — штатный timeout, X — форматная ошибка. Контрольная непригодность сохраняет `quality=null`, даже если `native_status=pass`. Штатный timeout замораживается как наблюдаемый неуспех: при `quality=false`, `native_status=timeout` и корректном формате выводится T. Форматная ошибка выводится X и сохраняется как `quality=false` согласно замороженной схеме сборщиков. Для строки одновременно без кандидата и без контрольной пригодности приоритет G явно задокументирован; отдельная колонка `control_eligible` сохраняет второй факт.

Тесты также подтверждают отказ от незавершённого архива (`state=running`), отказ при попытке писать презентацию внутрь архива, полноту 1,000 строк задач в EN/RU PDF и отсутствие слешей в строках таблицы. Исходный `native_status` сохраняется даже у control-ineligible строк.

## Предел проверки

Факторный `scale1000_luna/collect.py` не добавляет отдельное поле `availability` для незавершённых строк; там доступность представлена через `generation_complete` и `outcome_type`. Поэтому рендерер выводит `availability_recorded=unknown`, если source-ledger не содержит такого ключа, и использует `generation_complete` для `candidate_available`. Это прозрачное ограничение входной схемы, а не превращение неизвестного в fail. SCC-экспорт, напротив, явно сохраняет `availability` (`never_started` или `submitted_incomplete`). Проверка не устанавливает, насколько фактические опубликованные архивы удовлетворяют этим контрактам: она покрывает только искусственные fixture-данные и защитные проверки загрузки.

Подтверждённых дефектов реализации в пределах этой офлайн-проверки не обнаружено. Изменений в реализации, протоколах, статьях и рабочих запусках не вносилось.
