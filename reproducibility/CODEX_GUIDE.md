# Воспроизведение эксперимента через подписку

Модель — **GPT-5.4 mini, medium**; тариф — $0,75 / $0,075 / $4,50 за миллион входных / кешированных входных / выходных токенов. Это условная цена по официальному API-тарифу, а не счёт за подписку. [Протокол и отклонения](revision/CODEX_PROTOCOL.md) зафиксированы до новой матрицы. Spark не является экспериментальной моделью.

Матрица разработки: восемь задач × пять условий × один повтор = **40 решений и 72 отдельных хода CLI**. Четыре условия — один/три хода × нейтральные/ролевые этапы; пятое — прямой решатель. Все предоставленные данные и предшествующие ответы сохраняются без сокращений. Названия повторов не означают поддерживаемый моделью sampling seed. Общий жёсткий предел выхода не выравнивается: исследуется указанный протокол CLI с естественной остановкой.

## Подготовка

Сначала выполните скачивание и случайное разбиение набора по [основному руководству](REVISION_GUIDE.md). Полученные файлы должны совпасть с опубликованными хэшами и ID. Генератор получает только `prompt` и `context`; официальные тесты остаются отдельными входами проверки.

Установите отдельную копию официального CLI и используйте обычную авторизацию ChatGPT:

```powershell
npm install --prefix tmp/codex-runtime --no-audit --no-fund @openai/codex@0.153.4
$env:CODEX_STUDY_CLI_JS = (Resolve-Path tmp/codex-runtime/node_modules/@openai/codex/bin/codex.js).Path
node $env:CODEX_STUDY_CLI_JS login
```

Не копируйте файлы авторизации в репозиторий. Настройки пользователя и проектные инструкции игнорируются; общий каталог входа в аккаунт остаётся доступен CLI. Подписка ограничена квотами. Ни доступ к подписке, ни число запущенных процессов не означают неограниченный объём генераций.

## Генерация и аудит

Опубликованный `tasks.json` заменяющей серии содержит ровно восемь модельных входов. Для нового исполнения сохраните эти объекты построчно как JSONL. Не подменяйте их полной development-выборкой под прежним манифестом. В командах ниже `tasks-dev8.jsonl` — именно этот файл; папка нового запуска должна отсутствовать.

```powershell
python -m reproducibility.codex_subscription run --tasks tasks-dev8.jsonl --manifest reproducibility/revision/codex_dev8_v2_manifest.json --archive reproducibility/runs/new-dev8 --workers 2
python -m reproducibility.record_codex_runtime --archive reproducibility/runs/new-dev8 --npm-root tmp/codex-runtime
python -m reproducibility.audit_codex_pilot --archive reproducibility/runs/new-dev8 --output reproducibility/runs/new-dev8/audit.json
```

Фиксируются полные запросы, аргументы, stdout JSONL, stderr, ответы, счётчики, время и контрольные суммы. Любое обращение к инструменту, ошибка, сжатие истории или неподдержанный счётчик останавливает серию. Произвольного автоматического повтора нет. Аудит полного результата сверяет каждую ячейку, полный вход и промежуточную историю, все параметры CLI, инструкции, версию и исходники. Свидетельство установки фиксирует время своего сбора и не выдаётся за аттестацию внутренних серверных весов.

Первая остановленная попытка сохраняется отдельно. Её 12 готовых решений не дополняют заменяющую матрицу; расходы всех 21 отправленных ходов остаются в общем журнале. Неполный журнал нельзя выдавать за нулевой расход.

## Исполняемая проверка

Используется исходная функция `untrusted_check` закреплённого BigCodeBench и его оригинальные тесты в ограниченном контейнере. Это **пилот с upstream-кодом, а не полный официальный результат BigCodeBench CLI**. Сначала клонируйте BigCodeBench в `reproducibility/vendor/bigcodebench` и переключите на commit `09dd993f46c3fbf3a799465bb96d524edcb0b199`.

```powershell
docker --context default build -f reproducibility/pilot_env/Dockerfile -t bcb-pilot:dev .
python reproducibility/benchmark_bridge.py export --results reproducibility/runs/new-dev8/results.jsonl --benchmark bigcodebench --output-dir reproducibility/runs/new-dev8/predictions
```

Экспорт создаёт пять отдельных файлов, перечисленных в `export_manifest.json`. Каждый передайте в отдельный запуск:

```powershell
.\reproducibility\pilot_env\run_pilot.ps1 -Predictions <файл-режима.jsonl> -OutputDir <новая-папка-режима>
```

Угловые скобки обозначают путь из манифеста, а не буквальную команду. Сеть, запись в исходники и лишние разрешения отключены; контейнер видит только перечисленные входы. Для каждой задачи повторяются эталонный и заведомо неправильный контроли. Успех процесса Docker не равен успеху решения. У закреплённого upstream проверка имеет фактический тайм-аут около 241 секунды на задачу; параметры 0,1 секунды не отменяют этот внутренний минимум.

Результат задачи доступен лишь при успешном эталоне и проваленном отрицательном контроле. Для сетевой задачи /1005 контроль в этой среде не проходит; её не выбрасывают и не объявляют ошибкой модели. Качество показывается и среди оцениваемых задач, и диапазоном при всех восьми назначенных задачах.

Для объединения сохраните каталоги пяти оценок под именами `single_neutral`, `single_roles`, `multi_neutral`, `multi_roles`, `direct` внутри одной папки:

```powershell
python -m reproducibility.report_codex_pilot --archive reproducibility/runs/new-dev8 --evaluations <папка-оценок> --output <итог.json> --tables <папка-таблиц>
```

Скрипт повторно проверяет точное соответствие исполняемого кода полному ответу, исходные тестовые статусы, контроли и одинаковую среду. Он не вычисляет статистическую значимость по восьми задачам и не заменяет оригинальные INoT, Agentless или SWE-agent самодельными аналогами. Большая подтверждающая серия требует отдельной фиксации доступного объёма, рабочего официального evaluator и окончательной модели до просмотра её результатов.

## Сверка с нативным официальным CLI

Она также выполнена: все 40 исходных статусов совпали. Расширенный образ занимает около 1,02 GB; официальный исходник не изменялся. Это выборочный запуск `instruct` в собственной изолированной среде, а не полный образ релиза или результат всего набора.

```powershell
docker --context default build -t bcb-official-cli:dev reproducibility/pilot_env/official_cli
python reproducibility/pilot_env/official_cli/prepare_samples.py --dataset reproducibility/data/bigcodebench-v0.1.4.jsonl --kind gold --output reproducibility/runs/native-gold.jsonl
python reproducibility/pilot_env/official_cli/prepare_samples.py --dataset reproducibility/data/bigcodebench-v0.1.4.jsonl --kind incorrect --output reproducibility/runs/native-incorrect.jsonl
.\reproducibility\pilot_env\official_cli\run_official_cli.ps1 -Samples reproducibility/runs/native-gold.jsonl -OutputDir reproducibility/runs/native-controls/gold-run
.\reproducibility\pilot_env\official_cli\run_official_cli.ps1 -Samples reproducibility/runs/native-incorrect.jsonl -OutputDir reproducibility/runs/native-controls/incorrect-run
```

Затем тот же launcher используется для каждого из пяти исходных файлов predictions с отдельной папкой результата. Его `no_gt=True` отключает внутренний кеш эталонов; пригодность определяется показанными отдельными запусками gold/incorrect. `calibrated=False` сохраняет исходный знаменатель. Сеть отключена, входные решения доступны только для чтения, их хэши проверяются до и после исполнения.

Сверка отчётов выполняется `python -m reproducibility.audit_official_cli` с аргументами `--predictions`, `--native`, `--controls`, `--core`, `--dataset`, `--output`, соответствующими этим папкам и файлам. В опубликованном архиве ранние дополнительные метаданные используют культурно-зависимый порядок файлов для хэша исходников; пояснение и переносимый хэш сохранены в его README. Текущий launcher сортирует пути в ordinal-порядке.

После оценки выявлены ограничения самих задач: /1036 требует неуказанного заголовка, /45 противоречит себе в названиях, /322 зависит от конкретных подменённых API. Первичные оценки не исправлялись. До большой серии необходим независимый от результатов модели аудит соответствия условий тестам.
