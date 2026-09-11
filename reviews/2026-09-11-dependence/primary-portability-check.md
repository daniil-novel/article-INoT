# Ограниченный аудит portable replay основной Luna серии

Дата: 2026-09-11  
Статус: технический аудит требований к переносимому `collect -> analyze` replay. Это не full journal review. Run-root основной серии, raw/native traces и model outcomes не читались; живые процессы не затрагивались.

## Что подтверждено по исходникам

`scale1000_luna/collect.py` импортирует `codex_luna_subscription`, `benchmark_bridge`, `heldout200.evidence`, `scale_env.validate_native` и соседний `dispatch` (`collect.py:6-10`). `dispatch.py` дополнительно использует `record_codex_runtime` и объявляет source dependencies для всех этих модулей, `scale1000` collector/analyzer support, gate/evaluator sources и оба environment-v2 файла (`dispatch.py:12-24`). Это даёт достаточную основу для source closure collector-а, если verifier импортирует её из архивированного source tree.

Collector выполняет существенные проверки: frozen plan через `dispatch.plan`, generation manifest/status, exact tasks/instructions, turn inventory, event usage, response hashes, prediction export hashes, native reports и строит `candidate_records.jsonl`, `turn_usage.json`, `native_audit.json` (`collect.py:37-89,92-128`). Локальный publisher вызывает этот collector и затем `scale1000.analyze.summarize`, сравнивая три collector artifacts и основной summary (`publish_scale.py:178-195`).

Publisher сохраняет `generation/sources`, generation manifest/tasks/instructions, inputs, controls, predictions, native, analysis и source hashes (`publish_scale.py:330-379`). Generation sources записываются dispatch-ом в LF-normalized виде, а manifest хранит соответствующие `source_sha256_lf` (`dispatch.py:58-62,103-105`); publisher проверяет эти hashes после LF normalization (`publish_scale.py:198-215`).

## Подтверждённые риски и требования к новому `scale_replay.py`

### P1 — Текущий `replay_verify.py` не является полным collect→analyze replay

Генерируемый verifier читает только `analysis/candidate_records.jsonl` и `analysis/summary.json`, проверяет 15,000 строк, уникальность assignment keys, 1,000 task IDs и четыре primary mean/count контраста (`publish_scale.py:263-307`). Он не вызывает archived `collect`, не проверяет raw turns, `generation/sources`, source hashes, predictions, native reports, `turn_usage.json` или реконструкцию основного summary.

Новый verifier должен запускать archived collector в temporary output, используя только archive paths, побайтно сравнивать `candidate_records.jsonl`, `turn_usage.json`, `native_audit.json`, затем повторно вызывать archived `scale1000.analyze.summarize` и сравнивать `analysis/summary.json`. Primary-only verifier можно оставить как быстрый smoke check, но его нельзя описывать как полный replay.

### P1 — `dispatch.plan()` должен выполняться из archive source tree, а не из checkout

`dispatch.ROOT` вычисляется от расположения импортированного `dispatch.py` (`dispatch.py:16`), а `plan()` читает и hashes `ROOT/reproducibility/...` (`dispatch.py:50-66`). Поэтому portable verifier обязан prepend именно `archive/generation/sources` к `sys.path` и импортировать оттуда `reproducibility.scale1000_luna.collect/dispatch`; затем `plan()` должен видеть `archive/generation/sources/reproducibility/...`. Если импорт останется из локального checkout, replay будет проверять локальные исходники вместо сохранённых и перестанет быть переносимым.

Verifier также должен передавать `archive/generation`, `archive/inputs/scale1000-v1`, `archive/controls/controls-v3` и `archive/generation/manifest.json`; нельзя восстанавливать protocol, selection или gate через cwd/repository-relative defaults.

### P1 — Для analyze нужны pinned host dependencies, которых нет в текущем core source copy

`scale1000/analyze.py` импортирует NumPy и SciPy (`analyze.py:16-17`). Текущий publisher копирует environment-v2 evaluator requirements (`publish_scale.py:374-375`), но этот файл содержит только дополнительные evaluator/audio pins; NumPy/SciPy host pins находятся в `reproducibility/requirements-publication.txt`. Следовательно, новый full replay должен либо явно использовать и архивировать `requirements-publication.txt` с pinned Python/NumPy/SciPy, либо честно ограничить replay средой, где эти версии уже установлены. Наличие native Docker requirements само по себе не делает host `collect -> analyze` replay воспроизводимым.

### P2 — Byte/hash contract должен быть сохранён явно

Generation manifest сравнивает LF-normalized hashes, тогда как portable evidence manifest хэширует фактически сохранённые bytes (`dispatch.py:58-62,103-105`; `publish_scale.py:200-215`). Новый verifier должен повторять именно LF-normalized comparison против `generation/manifest.json`, а затем отдельно проверять общий `EVIDENCE_MANIFEST`. Нельзя заменять source files локальными копиями с другими окончаниями строк или считать совпадение только по имени/path.

### P2 — Native validation требует полного archived controls tree

`heldout200.evidence.environment_from_gate()` проверяет gate, gold/incorrect control metadata, reports, samples и их hashes (`heldout200/evidence.py:7-35`), а `validate_native()` требует staged samples, evaluator metadata, package/resource hashes и exact container argv (`scale_env/validate_native.py:48-100`). Portable verifier должен передавать полный `archive/controls/controls-v3`, включая gold/incorrect subtrees, а не только `heldout200_control_gate.json`; иначе archived collector не сможет доказать environment/native join.

## Итог

Source closure, который dispatch сохраняет в `generation/sources`, покрывает runtime imports collector-а и plan-а. Однако текущий generated verifier проверяет только primary summary, а полноценный portable replay требует отдельного `scale_replay.py` с archive-local imports, explicit archive paths, pinned publication dependencies, LF-normalized source hash checks и полным collect/native/analyze byte comparison. До добавления и проверки такого verifier это остаётся существенным portability gap; данный отзыв фиксирует требования и риски, не читая реальные исходы основной серии.
