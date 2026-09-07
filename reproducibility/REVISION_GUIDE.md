# Новый эксперимент без компрессии

Статус: **подготовка и тестирование ПО выполнены; подтверждающие LLM-запуски и официальная оценка не выполнены**. См. [протокол](revision/PROTOCOL.md), [ответ рецензенту](revision/REVIEW_RESPONSE.md), [источники](revision/SOURCE_LEDGER.md). Фактические новые результаты этой ревизии — арифметический аудит сохранённого E3, а не новые ответы моделей.

## Что доступно

- `factorial_runner.py`: четыре режима, все task × seed × arm, случайный порядок, одинаковый полный контекст, полная история, фиксированный провайдер, общий журнал расходов.
- `benchmark_bridge.py`: независимые выборки настройки и подтверждения; экспорт официальных predictions и аргументов evaluator.
- `collect_outcomes.py`: связывает ответы с реальными отчётами, проверяет код/патч, сохраняет пропуски.
- `analyze_factorial.py`: парные эффекты и взаимодействие, bootstrap задач, Holm, границы при пропусках, консервативная проверка неухудшения.
- `audit_legacy.py`: независимый пересчёт 240 исторических записей и таблицы B0/B2/B3.

Это ещё не готовая репликация оригинального INoT, Agentless или SWE-agent. Для них зафиксированы источники и требования к воспроизведению, но нет выполненных траекторий. Поиск файлов SWE-bench и официальные изолированные среды также требуют реализации/настройки и контрольных запусков.

## Окружение и бесплатные проверки

Нужен Python 3.11+. Генератор и экспорт используют стандартную библиотеку. Для чтения Parquet и анализа нужны зависимости из `requirements-revision.txt` (версии, проверенные в локальном исследовательском окружении).

```powershell
python -m pip install -r reproducibility/requirements-revision.txt
python -m unittest discover -s reproducibility/tests -v
python reproducibility/audit_legacy.py
python reproducibility/download_benchmark.py
python reproducibility/benchmark_bridge.py prepare --dataset reproducibility/data/bigcodebench-v0.1.4.jsonl --output-dir reproducibility/data/bigcodebench-split --dev-size 40
```

Скачивание фиксирует официальный Parquet SHA-256. В `prepared.jsonl` находятся **40 development-задач**, в `confirmatory.jsonl` — **1100 остальных задач**. Полные идентификаторы и хэши записаны в `prepare_manifest.json`; опубликованная копия — `revision/task_split_manifest.json`. Поля `test` и `canonical_solution` не передаются генератору. Данные и будущие API-трассы не добавляются в Git автоматически.

```powershell
python reproducibility/factorial_runner.py plan --config reproducibility/revision/qwen.json --tasks reproducibility/data/bigcodebench-split/confirmatory.jsonl --out reproducibility/revision/qwen_manifest.json
python reproducibility/factorial_runner.py plan --config reproducibility/revision/gemini.json --tasks reproducibility/data/bigcodebench-split/confirmatory.jsonl --out reproducibility/revision/gemini_manifest.json
```

Каждый манифест содержит 13200 генераций и 26400 вызовов: 1100 задач × 3 seed × 4 режима; многовызовный режим делает три вызова. Суммарная цель — 26400 генераций. **Манифест не означает выполненный запуск.** Максимальная консервативная оценка двух матриц — около $404.42, выше общего лимита $300 и выделения $190 на основную серию. Фактический расход может быть меньше, но обещать полное выполнение нельзя: сначала нужна development-калибровка и фиксация доступного объёма до просмотра подтверждающих исходов.

## API и общий бюджет

Разрешённый автором максимум — **$300 суммарно**, а не на модель или попытку. Начальный найденный ключ был валиден, но имел нулевой остаток. Нужен обычный OpenRouter API key с доступным балансом и соответствующим лимитом; секрет хранится в локальном `.env` или переменной окружения `OPENROUTER_API_KEY`. В публичные артефакты ключ не включается.

Конфигурации пока являются кандидатами для настройки: Qwen через `novita/fp8`, Gemini через `google-vertex`; поддержка seed и цены проверены по каталогу endpoints. Настоящий capability-canary ещё не выполнен. Fallback отключён; `max_price` запрещает более дорогие endpoints и отдельную плату за запрос. Не менять модель, провайдера, промпт или бюджет после просмотра подтверждающих ответов без явного отклонения от протокола.

Сначала создать конфигурацию и манифест development-серии, затем использовать её с единым журналом `reproducibility/private/campaign_budget.json`. **Все модели, canary и повторы этой работы должны использовать один и тот же файл**. Параллельный процесс остановится на блокировке журнала. Не удалять журнал для обнуления расходов.

```powershell
python reproducibility/factorial_runner.py run --config <development-config.json> --tasks reproducibility/data/bigcodebench-split/prepared.jsonl --manifest <development-manifest.json> --archive reproducibility/runs/development-qwen --budget-ledger reproducibility/private/campaign_budget.json --budget-usd 5
```

Угловые скобки — места для предварительно созданных файлов; команда не является готовым запуском подтверждающей серии. Ключ должен быть загружен в окружение процесса без вывода значения. Для возобновления используются те же аргументы и тот же архив; проверяются исходники, конфигурация, задачи и манифест.

Перед вызовом программа проверяет полный вход, резервирует расходы и сохраняет запрос. Тело ответа сохраняется до разбора. При неопределённом списании, отсутствующем cost, HTTP/сетевой ошибке или незавершённом запросе повтор автоматически не выполняется. Нужна сверка с провайдером; полный резерв остаётся занят. После аварийного завершения может сохраниться `.lock`: сначала убедиться, что процесс завершён, и проверить несверенные запросы; не удалять блокировку у работающего процесса. Более дорогой ответ, чем разрешённый конверт, сохраняется и останавливает серию. Локальный контроль дополняется лимитом самого API-ключа.

## Экспорт и официальная оценка

```powershell
python reproducibility/factorial_runner.py audit --archive reproducibility/runs/development-qwen
python reproducibility/benchmark_bridge.py export --results reproducibility/runs/development-qwen/results.jsonl --benchmark bigcodebench --output-dir reproducibility/runs/development-qwen/export
```

В `export_manifest.json` сохраняются отдельные файлы для каждой модели/режима/seed, контрольные суммы и `evaluation_argv` — список аргументов официального evaluator. Передавать аргументы как список; не склеивать их в командную строку. BigCodeBench использует `selective_evaluate` для точного набора ID и `calibrated=False`, чтобы evaluator не дописывал код к предоставленному решению. Для SWE-bench применяется отдельный `run_id`, зависящий от байтов predictions каждой группы: разные режимы не должны переиспользовать результаты кэша.

**Команды официальной оценки запускаются только в подготовленной изолированной среде**, без API-ключа и личных каталогов. Экспорт ничего не исполняет. На локальной машине Linux Docker доступен через `--context default`; `desktop-linux` при проверке был недоступен. Свободное место на системном диске ограничено, поэтому полный образ и кеш сотен репозиториев требуют отдельного расчёта размещения. Не переносить диски Docker автоматически.

Точные upstream-heads приведены в `revision/SOURCE_LEDGER.md`. Это проверенные публичные версии, но не утверждение об их установке. Сначала нужно зафиксировать реально установленный commit и digest образа, выполнить gold/reference и отрицательный контроль. Только после этого официальные отчёты могут служить доказательством.

## Сбор и анализ исходов

`collect_outcomes.py` требует полного аудированного архива генерации. Для BigCodeBench ожидает `_eval_results.json` рядом в указанном каталоге reports; для SWE-bench — дерево `run_id/model/instance_id/report.json` с `patch.diff`. Проверяется совпадение оценённого кода/патча с экспортом. Отсутствующие отчёты остаются пропусками. Неизвестные статусы не превращаются в успехи.

```powershell
python reproducibility/collect_outcomes.py --archive <archive> --export-manifest <export/export_manifest.json> --reports <official-reports> --output <outcomes.jsonl>
python reproducibility/analyze_factorial.py --outcomes <outcomes.jsonl> --manifest <archive/manifest.json> --output <analysis.json>
```

Каждая модель анализируется отдельно. Нужна ровно замороженная матрица; повторы или пропущенные строки отклоняются. Поле `resolved=null` представляет инфраструктурный пропуск и сохраняет назначенный знаменатель. Точный дополнительный gate использует заранее выбранный первый seed: нижняя граница вероятности улучшения минус верхняя граница вероятности вреда с Bonferroni-разделением ошибки. Для заявления о неухудшении должны пройти и этот консервативный gate, и bootstrap среднего по seed. Это строже одного bootstrap-интервала и должно быть сохранено при регистрации окончательного протокола.

Отчёты исходов и анализа не созданы для текущей новой серии, поскольку реальной официальной оценки ещё нет. Unit tests используют явно искусственные фикстуры и не являются результатами бенчмарков.

## Исторические материалы

`results/20260726_flash_lite`, прежний `evidence_snapshot.json` и `build_article_evidence.py` относятся к старой версии статьи и зафиксированному исследовательскому commit. Старый snapshot содержит хэши тогдашних LaTeX-файлов, а не этой ревизии. Не переписывать его так, будто новые полные ответы когда-либо существовали. Новый `revision/legacy_audit.json` проверяет арифметику и явно фиксирует отсутствие полных исторических решений.
