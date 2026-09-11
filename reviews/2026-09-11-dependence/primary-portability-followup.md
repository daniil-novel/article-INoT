# Follow-up технического аудита portable replay основной Luna серии

Дата: 2026-09-11  
Статус: ограниченная проверка реализации полного portable `collect -> analyze` replay. Это не full journal review; реальные outcomes основной серии не читались.

## Проверенный результат

По исходникам проверены `reproducibility/revision_20260911/scale_replay.py`, его интеграция в `publish_scale.py` и artificial fixture test `test_scale_portable_replay.py`. Заявленный тестовый результат — `7 passed` на искусственных 15,000 assignment rows, 30 synthetic completed cells/54 turns, native report fixtures, 3 repeats и 5 arms; повторно его не запускал, поскольку новых оснований для повторного выполнения не было.

Исправленная portable layout-схема согласована: generation source files действительно лежат как относительные пути без префикса `reproducibility`; `install()` создаёт `replay-sources/reproducibility` и копирует туда retained source bytes (`scale_replay.py:21-31`). Luna `PROTOCOL.md`, отсутствующий в `dispatch.DEPENDENCIES`, копируется отдельно и проверяется по `protocol_sha256_lf` (`scale_replay.py:32-35`).

## Закрытые прежние риски

- `verify()` добавляет `replay-sources` в `sys.path`, импортирует collector/dispatch/analyze/evidence modules и отказывает, если любой `module.__file__` находится вне retained tree (`scale_replay.py:43-56`). Это устраняет риск случайного использования локального checkout и соответствует тому, как `dispatch.ROOT` вычисляется от пути импортированного `dispatch.py`.
- Verifier использует archive-local `generation`, `inputs/scale1000-v1`, `controls/controls-v3`, `predictions`, `native` и frozen generation manifest (`scale_replay.py:58-79`), а не cwd-relative defaults.
- Перед replay проверяются общий `EVIDENCE_MANIFEST`, retained source bytes против `source_sha256_lf` и protocol hash (`scale_replay.py:57,64-71`). LF normalization применяется только там, где этого требует frozen manifest; сохранённые bytes дополнительно сравниваются побайтно.
- Полный replay пересобирает collector artifacts (`candidate_records.jsonl`, `turn_usage.json`, `native_audit.json`) и повторно вычисляет весь statistical summary (`scale_replay.py:76-87`). Таким образом, прежний primary-only `replay_verify.py` теперь явно обозначен как меньший diagnostic (`publish_scale.py:405-408`), а publisher запускает отдельный full verifier в новом subprocess вне cwd и с удалённым `PYTHONPATH` (`publish_scale.py:420-429`).

## Остаточные ограничения

### P2 — `install()` получает два вспомогательных файла из checkout до упаковки

`install()` копирует `evidence_manifest.py` и `requirements-publication.txt` из переданного `repository` (`scale_replay.py:36-37`). После установки их bytes входят в общий evidence manifest, поэтому portable verification после публикации не требует checkout. Однако эти два файла не входят в `generation/manifest.json` source hash closure и их provenance привязана к текущему repository в момент `install()`, а не к frozen generation source manifest.

Это не блокирует переносимость текущего archive flow, потому что `publish_scale.py` вызывает install до `write_evidence_manifest()` (`publish_scale.py:403-410`) и затем запускает subprocess verification. Для более строгой provenance можно копировать requirements/helper из уже собранного archive source closure либо добавить их exact hashes в отдельную replay metadata запись.

### P2 — Искусственный тест не доказывает clean-environment dependency installation

Тест удаляет `PYTHONPATH` и меняет cwd, но запускает subprocess на текущем Python environment. Он проверяет import isolation и replay logic, но не устанавливает отдельное чистое окружение и не подтверждает фактическое соответствие pinned NumPy/SciPy версиям из `requirements-publication.txt`. README/publisher теперь явно требуют установить этот файл перед full replay (`publish_scale.py:406-408`); это остаётся операционным prerequisite.

## Границы подтверждения и итог

Подтверждены по исходникам: archive-local import resolution, ROOT/protocol path behavior, LF-normalized source binding, full collector artifact comparison, complete summary recomputation, native/control path usage и refusal to use checkout modules. Реальная 15,000-cell series не читалась, а заявленный искусственный тест повторно не запускался.

Конкретного blocker для portable full replay в проверенной реализации не обнаружено. Остались только P2 provenance и clean-environment validation limitations, которые не нарушают заявленный replay contract при установке сохранённых publication requirements.
