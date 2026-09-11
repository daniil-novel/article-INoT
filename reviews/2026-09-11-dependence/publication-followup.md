# Follow-up технического аудита publication package

Дата: 2026-09-11  
Статус: повторный ограниченный технический аудит после интеграции source-family package. Это не итоговый scientific review и не чтение реальных model outcomes.

## Проверки

Запущен только `python -m pytest -q reproducibility/tests/test_task_dependence_package.py`: `3 passed` (оба artificial ledger formats, factorial и SCC, плюс negative omission test). Реальные candidate records, generation traces и model outcomes не читались; основная серия не запускалась.

Параметризованный тест создаёт искусственные полные матрицы, вызывает `sensitivity.run()`, упаковывает их, удаляет `PYTHONPATH`, запускает `source_family_replay.py` из независимого рабочего каталога и проверяет успешный replay. Отдельно проверяются отказ на изменённом draw vector и на изменённом retained `PROTOCOL.md`. В выводе теста есть только 46 `DeprecationWarning` о неэкранированных regex escape в искусственно загружаемом source code; это предупреждения, не ошибки теста и не blocker упаковки.

## Подтверждённые результаты

1. `sensitivity.py` теперь принимает явные `selection_path`/`gate_path`, записывает hashes source-audit, selection, main analysis, script, NumPy и control gate (`reproducibility/task_dependence/sensitivity.py:80-123`). `verify_saved()` пересчитывает все draw vectors во временном каталоге и сравнивает полный набор сохранённых файлов (`sensitivity.py:126-135`).

2. `package.attach()` отказывается работать без завершённого supplementary output, повторяет `verify_saved()`, копирует source graph и source closure, фиксирует hashes и создаёт `source_family_replay.py` (`reproducibility/task_dependence/package.py:62-89`). Negative test подтверждает невозможность тихо опубликовать архив без дополнительного расчёта.

3. Portable source closure теперь включает код аудита/реплея, protocol, evidence manifest helper, полный source dataset 1,140 задач, license, data README, `prepare_manifest`, segregation selection и publication requirements (`package.py:16-28`). Эти файлы присутствуют в рабочем дереве и tracked Git paths.

4. Оба publisher-а вызывают `attach()` после основного raw/native replay и до общего `write_manifest()` (`publish_scale.py:398-402`; `publish_scc.py:188-196`). Поэтому supplementary package становится обязательной частью общего evidence manifest, а omission приводит к ошибке до успешного завершения публикации.

5. SCC portable layout согласован: package использует `inputs/` и `controls/` (`package.py:12-15`), ровно эти каталоги передаются в `attach()` и затем читаются `verify_archive()` (`package.py:34-58`). SCC verifier восстанавливает source context для основного replay и затем вызывает supplementary verifier (`publish_scc.py:120-132`). Искусственный SCC replay из каталога вне checkout прошёл.

## Итог

По проверенному scope конкретного blocker нет. Silent omission дополнительного расчёта закрыт требованием `attach()` и negative test; source graph, полные 1,140 исходных задач, зависимости, draw vectors и SCC portable paths включены в replay contract. Остаётся только косметическое предупреждение о неэкранированных regex escapes в искусственных тестовых source snippets; оно не влияет на pass/fail и не требует изменения исходников для данного аудита.
