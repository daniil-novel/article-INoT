# Критик 4: соответствие AAMAS 2027

**Покрытие.** Полностью просмотрены 7 страниц `submission/aamas2027/paper/main.pdf` (текст, таблицы, рисунок, подписи и библиография), `paper/main.tex`, `body.tex`, все подключаемые таблицы/рисунок и `references.bib`. Проверены материалы формы и подготовки: `REQUIREMENTS.md`, `SUBMISSION_GUIDE_RU.md`, `AUTHOR_FORM_DRAFT_RU.md`, `AI_ASSISTANCE_PREPARATION.md`, `preparation/AI_METHOD_DISCLOSURE.md`, `preparation/AI_METHOD_INPUTS_DRAFT.md`, `SUPPLEMENT_SIZE_PREFLIGHT.md`, `TEMPLATE_PREFLIGHT.md`, `paper/README.md`, `anonymous_command_check.json`. Другие рецензии не читались. Проверка выполнена 13.09.2026; это внутренняя AI-проверка, не официальный отзыв AAMAS.

**Фит.** Наиболее естественна область GAAI: CFP прямо включает orchestration/workflows, runtime engineering, interaction protocols, verification, benchmarks и evaluation для generative-agent systems. Рукопись содержит контролируемое сравнение workflow, внешнюю исполнимую верификацию и явные границы причинных выводов. Однако соответствие хрупкое: эксперимент использует фиксированные prompt-операции для генерации кода, не демонстрирует независимых агентов, памяти, инструментов или автономного взаимодействия. Поэтому связь с агентной проблематикой нужно сделать центральной уже в abstract/introduction и явно объяснить, какую общую для agentic workflows границу устанавливает SCC-сравнение; иначе возможен desk rejection как generic prompt engineering/code generation.

**Формальные критерии.** PDF англоязычный, собран обязательным LaTeX-шаблоном, использует `anonymous`, содержит `Anonymous Author(s)` и не раскрывает автора; визуально проверены первая и последняя страницы. Объём 7 страниц при лимите максимум 8 страниц плюс библиография, поэтому лимит соблюдён. В логе есть один небольшой overfull box (3.49 pt) и несколько underfull vbox; это стоит перепроверить перед upload, хотя явного выхода текста за поля не видно. В `main.tex` остаётся `\acmSubmissionID{Pending registration}`: это допустимый черновой placeholder, но не готовый финальный PDF.

**AI и supplementary.** Раскрытие AI-помощи присутствует в основной статье и отдельно описывает инструменты/версии, применение к гипотезам и методологии, ответственность автора и provenance gaps. Это соответствует политике AAMAS только при включении в анонимный supplement фактически использованных prompt’ов и tool/version; текущая подготовка содержит выбранные H01–H11, но не является финальным архивом и сама отмечает неполную историю. Финального `supplementary.zip` в каталоге нет; измеренный raw-поднабор уже превышает 25 MB при обычном ZIP, а полная анонимная упаковка, extraction/round-trip, anonymity и replay checks не завершены.

**До 4 действий до подачи.**

1. Зарегистрировать abstract, получить реальный OpenReview submission ID и пересобрать/визуально проверить PDF с этим номером.
2. Уточнить positioning под GAAI (workflow/evaluation/verification of generative agents), не оставляя впечатления общего prompt-engineering benchmark.
3. Сформировать один анонимный ZIP ≤25 MB с prompt disclosure, кодом/данными и инструкцией воспроизведения; завершить проверку путей, метаданных, извлечения и replay.
4. Заполнить OpenReview author profiles, area/topics, Findings choice и reciprocal-reviewer declaration; перепроверить отсутствие существенной архивной dual submission.

**Вердикт готовности:** основной manuscript близок к формальной готовности и проходит 8-page/anonymity gate; submission package сейчас **не готов**.

**Официальные источники:** [AAMAS 2027 Call for Main Track](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/call-for-main-track/), [Submission Instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/guidelines-and-policies/instructions/), [Reviewer Guidelines](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/reviewer-guidelines/), [Findings policy](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/findings/).
