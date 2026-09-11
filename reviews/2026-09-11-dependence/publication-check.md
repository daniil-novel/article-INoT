# Технический аудит публикационного пакета source-family sensitivity

Дата: 2026-09-11  
Статус: ограниченный технический аудит переносимости и воспроизводимости. Это не итоговый scientific review и не оценка научной валидности результатов.

## Объём и выполненные проверки

Проверены `reproducibility/task_dependence/{PROTOCOL.md,README.md,audit.py,sensitivity.py}`, все четыре файла `source-audit-v2`, а также `publish_scale.py`, `publish_scc.py` и фактические коллекторы factorial/SCC. Model outcomes, candidate records и generation traces не читались; основная серия не запускалась; frozen dependencies и манифесты не изменялись.

Команда `python -m reproducibility.evidence_manifest verify reproducibility/task_dependence/source-audit-v2` прошла (`4` файла, `636067` байт). Тесты `reproducibility/tests/test_task_dependence.py` прошли `8 passed`. Схемы совместимы: factorial collector формирует `task_id/arm/replicate_id/quality`, SCC collector — `task_id/method/replicate_id/quality`; `paired_means()` выбирает соответствующее поле и требует полный frozen assignment matrix.

## Подтверждённые риски

### P1 — Дополнительные интервалы не входят автоматически в переносимый архив

`sensitivity.py` записывает `summary.json` и draw vectors только в переданный каталог `run-root/source-family-sensitivity` (`reproducibility/task_dependence/sensitivity.py:79-116`). В factorial publisher копируются только `pipeline`, `predictions`, `native`, `analysis` и фиксированные inputs (`reproducibility/revision_20260911/publish_scale.py:361-379`); SCC publisher аналогично копирует основной run tree и `candidate_records.jsonl/resource_usage.jsonl/native_audit.json`, но не source-family каталог (`reproducibility/revision_20260911/publish_scc.py:157-183`). Ни один publisher не принимает путь к sensitivity output и не добавляет его в `EVIDENCE_MANIFEST`.

Следствие: после завершения основной серии команду из README можно выполнить успешно, но получившиеся интервалы останутся рядом с run-root и не попадут в переносимый publication archive. Минимальное исправление: добавить явный optional/required publication input для каждого завершённого study, проверить его schema/hash и скопировать `summary.json`, все draw vectors, source-audit snapshot, protocol/script и replay verifier в архив до вызова `write_manifest()`.

### P1 — Для supplementary sensitivity нет замкнутого replay

Основные publisher-ы имеют replay-проверки исходного collector и основного `summary.json` (`publish_scale.py:178-195`; `publish_scc.py:107-117`). Для source-family sensitivity есть только расчёт bootstrap и сохранение массива draws (`sensitivity.py:24-49,100-116`): отдельного verifier, который заново прочитает сохранённый ledger/partitions, проверит seed/draw count и побайтно сравнит пересчитанные интервалы, нет. `EVIDENCE_MANIFEST` source-audit-v2 покрывает только четыре уже сохранённых source-only файла (`source-audit-v2/EVIDENCE_MANIFEST.json:1`), а не sensitivity output.

Минимальное исправление: добавить offline `replay_source_family.py` либо эквивалентную функцию publisher-а, которая пересчитывает все четыре графа и все контрасты из архивированных records/partitions, сравнивает `summary.json` и каждый draw vector, после чего включает эти файлы в evidence manifest.

### P2 — Sensitivity доверяет готовому analysis ledger без проверки основного raw/native replay

Перед чтением records код проверяет terminal generation, отсутствие lock, наличие `analysis/summary.json` и manifest source-audit (`sensitivity.py:79-98`), затем сразу загружает `analysis/candidate_records.jsonl` (`sensitivity.py:96-98`). Он проверяет ключи, quality-типы, eligibility и полноту matrix, но не вызывает factorial/SCC collector и не сверяет ledger с raw turns, predictions, native audits или основным summary. Поэтому корректный по форме, но вручную изменённый candidate ledger может породить supplementary intervals, если запускать sensitivity до publisher replay.

Минимальное исправление: сделать входом только уже проверенный publication root либо перед sensitivity выполнять и сохранять успешный collector replay; зафиксировать hash raw/native-derived ledger и основного summary в sensitivity metadata и проверять их перед расчётом.

### P2 — Provenance дополнительного расчёта неполна для переносимого результата

`summary.json` sensitivity сохраняет hashes records, partitions и control gate (`sensitivity.py:112-115`), но не hash `source-audit-v2/summary.json`, `EVIDENCE_MANIFEST.json`, `PROTOCOL.md`, `audit.py`, `sensitivity.py` или NumPy/runtime dependencies. README лишь сообщает, что NumPy должен быть зафиксирован (`reproducibility/task_dependence/README.md:50-55`); код это не проверяет. Сам source-audit manifest также перечисляет только `edges.jsonl`, `fingerprints.jsonl`, `partitions.json`, `summary.json`, не protocol или scripts.

Минимальное исправление: при создании supplementary artifact сохранять exact hashes protocol/script/audit summary/manifest, Python/NumPy versions и dependency lock; в portable archive хранить эти bytes и включать их в manifest.

### P1 — CLI sensitivity не является самодостаточным для portable archive

Хотя CLI принимает `--run-root` и `--audit`, selection и control gate разрешаются через фиксированные пути от `audit.ROOT` внутри исходного репозитория (`sensitivity.py:87-95`): `reproducibility/scale1000/inputs-v1/selection.json` и `reproducibility/results/20260908_scale1000_preflight/controls-v3/heldout200_control_gate.json`. Эти файлы не находятся внутри каталога `source-family-sensitivity`, а текущие publisher-ы не обязуются помещать их рядом с supplementary output. Поэтому replay из одного перенесённого архива зависит от внешнего checkout и может использовать другой selection/gate, если окружение изменено.

Минимальное исправление: принимать `--selection` и `--control-gate` явно, копировать их в archive вместе с sensitivity output и проверять их hashes против сохранённого metadata; `ROOT` оставить только как default для запуска из репозитория.

## Итог

Схемы ledger-ов и статусы коллекторов совместимы с `sensitivity.py`, а source-only audit v2 имеет рабочую внутреннюю byte-level проверку. Однако будущие source-family интервалы сейчас не являются частью переносимого publication package и не имеют собственного замкнутого replay. До публикации их следует присоединять к обоим publisher-ам, проверять после упаковки и фиксировать полную provenance цепочку. Это технический аудит упаковки и воспроизводимости, не итоговый scientific review.
