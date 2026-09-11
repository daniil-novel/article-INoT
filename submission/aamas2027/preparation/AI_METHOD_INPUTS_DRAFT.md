# Selected author inputs for the AI-method disclosure (draft)

This is a preparation draft, not the final conference supplement. It records
selected original human inputs to the authoring assistant. The Russian wording
is retained; the English sentence before each input is a descriptive summary,
not a claimed verbatim translation. Quoted requests and reviewer criticisms
are historical inputs, not assertions that their requested outcomes were met.

Recorded coordinator configuration: OpenAI Codex, model identifier
`gpt-6-astra`, high/xhigh settings, CLI/runtime version 0.153.4. The runtime
version is not the desktop application version. Model aliases do not identify
immutable weights. Experimental model settings are reported separately.

The manuscript-hosting URL has been replaced with `[MANUSCRIPT HOSTING URL]`.
No other wording in the selected inputs has been edited. Earlier and later
conversation context, other inputs, attached documents and delegated messages
are not reproduced here. This selection does not establish preregistration.
The final disclosure must map assistance to the final methods and their checks,
report unavailable delegated-prompt text and incorporate later material changes.


## H01. Initial redesign request

The author requested an uncompressed, larger empirical evaluation and supplied concerns about confounding, ceiling effects, missing evaluations and comparison methods.

```text
Проанализируй, пожалуйста, данное замечание относительно моей научной статьи и переделай мою статью так, чтобы она стала гораздо более сильной как с точки зрения этих замечаний, так и в целом с точки зрения Q1 грейда. То есть эксперимент должен быть настоящим, большим, масштабным, с четкими, понятными результатами, без компрессии и так далее. Учти все эти замечания, исправь мою статью, можешь переделать гипотезу, переделать эксперимент. Если тебе нужно переделать эксперимент, то скажи, пожалуйста, какой ключ от OpenRouter тебе нужен. Также я напоминаю, что ты можешь использовать кодекс SEVAI с неограниченным количеством агентов, только учти, что они должны быть достаточно дешевыми. Я бы выбрал модель 5.3 Spark с high reasoning. Исправь, пожалуйста, статью, сделай необходимое количество коммитов, коммиты делай достаточно часто. Также не забывай обновлять LaTeX, PDF и описание само в GitHub. И также я скидываю тебе актуальные замечания.

ЗАмечания:
Сильные стороны (реально редкие):\
• Образцовая эпистемическая честность — сам объявляет H1 не доказанной, H2 не оценённой, H3 не поддержанной, роутер не идентифицирован, эффект — «пакета», а не оркестрации.\
• Аккуратная статистика (Wilcoxon+Holm, task-resampling, Clopper–Pearson, честный power-calc «нужно ≥149 пар»).\
• Воспроизводимость: репо на commit-хэше, SHA-256, evidence snapshot, проверка сетки 60/60 и 240/240.\
\
Критические проблемы (почему major):\
⚠️ Главный результат конфаундед by design. B2 = 3 вызова над несжатым контекстом, B3 = 1 вызов над сжатым. Экономия смешивает топологию вызовов и компрессию; плоский склон B3 выше 4096 даёт в основном cap компрессии — а сама заявленная новизна (внутренняя ролевая сегрегация) так и не изолирована. Нужен 2×2 факторный дизайн.\
⚠️ Всё качество на потолке (pass\@1=1.0 везде). Тезис «экономим токены без потери качества» непроверяем, когда качество не может двигаться. Единственный заход на сложное (SWE-bench Lite) — на заглушке check(), и там согласие малой модели падает до 0.30.\
⚠️ Мало данных, неслучайные first-k, один seed; baseline самодельный, нет сравнения с самим INoT / Agentless / SWE-agent.\
• runs.json не хранит полные ответы → pass/fail нельзя перепроверить (дыра в «reproducibility-first» статье). RouteMode (контрибуция C1) вообще не тестируется.\
\
Приоритетные правки: (1) 2×2 факторный, (2) не-потолочные задачи + официальный SWE-bench harness, (3) реальные бейзлайны включая INoT, (4) сохранять полные ответы, (5) оценить или убрать RouteMode.\
\
Резюме одной фразой: методологически честнейшая работа, но подтверждённый позитивный вклад пока тонкий — «один сжатый вызов дешевле трёх несжатых на лёгких задачах».

Статья [[MANUSCRIPT HOSTING URL]]([MANUSCRIPT HOSTING URL])

[@Deep Research](plugin://deep-research-work@openai-curated-remote)
```

## H02. Subscription transport and measured tokens

The author requested Codex CLI use and measurement of actual token counters before a separate cost calculation.

```text
Попробуй пока через codex cli. почитай пожалуйста документацию. По-моему там есть способы в запросах узнавать количество токенов, истраченных на запрос, поэтому лучше тогда использовать подписку и потом просто отдельно вычислять стоимость.
```

## H03. Documented model and price

The author requested an economical working GPT model with published pricing and an explicit experimental design. This was an early preference, not the identifier ultimately used in every study.

```text
Давай выберем не парк, а максимально дешевую GPT, но при этом достаточно рабочую, то есть 5.4, 5.3 и так далее, с high или medium reasoning, информация о цене которой имеется, чтобы не выдумывать. Нам нужна прозрачность и понятность эксперимента, причем эксперимент должен быть явным.
```

## H04. Statistical rules and evaluation failures

The author supplied methodological criticisms concerning multiplicity, the quality margin, monetary claims, close prior work and missing evaluator reports.

```text
Пять главных замечаний:

1. **Методы: правила статистического вывода ещё неоднозначны.** В §7 обещан основной двусторонний тест, но программа вычисляет поправку Холма только для теста смены знаков, названного анализом чувствительности. Также нужно обосновать допуск ухудшения качества **2 п.п.** и определить критерий денежного преимущества. Всё это следует зафиксировать до подтверждающих запусков.
2. **Новизна: пропущен особенно близкий предшественник.** *Self-Collaboration Code Generation* уже сравнивала ролевые инструкции с инструкциями без ролей и отдельно исследовала число взаимодействий. Это не делает новый дизайн тождественным старому, но требует объяснить его добавленную ценность. Нужны сопоставление методов и обоснованный выбор ближайшего baseline. [Предшествующая работа, §5.2–5.3](https://arxiv.org/html/2304.07590v2).
3. **Результаты: найдена ошибка обработки будущих оценок.** Отсутствующий отчёт SWE-bench автоматически превращается в пропуск. Однако причиной бывает пустой или неприменимый патч модели, который по самой статье должен считаться неуспехом. Исключение таких задач способно сместить будущие оценки. Ошибка подтверждена чтением кода; фактического смещения результатов пока нет, поскольку новая серия не выполнена. [Правила SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/).
4. **Готовность исследования: осуществимость протокола не показана.** Официальные контрольные проверки, новые генерации и внешние baseline ещё не выполнены. Для обычной эмпирической статьи нужны эти данные. Для статьи-протокола — окончательный выполнимый план, включая бюджет, мощность и рабочую процедуру оценки.
5. **Текст: остались фрагменты ответа рецензенту.** Формулировки «The reviewer’s…», «The author instead requires…» в §4.1 и ссылка на декларацию предыдущей рукописи следует заменить самостоятельной научной аргументацией. Повторные объяснения отсутствия результатов можно сократить. Это редакционные дефекты; надёжно определить «процент AI» по ним нельзя.
```

## H05. Preserve the original research question

The author asked for a coherent revision retaining the original architecture rather than replacing the work with a different paper.

```text
Но учти, что ты сейчас слишком сильно отошел от исходной версии статьи. Это, наверное, не очень правильно. То есть статья должна быть исходной, просто ты должен был ее доработать таким образом, чтобы все те замечания перестали быть актуальны, чтобы они не могли быть применимы к данной статье. Поэтому, пожалуйста, сделай гибрид того, что у тебя получилось сейчас, с тем, что было ранее. Причем абсолютно продуманный и сочетающийся, чтобы все было.
```

## H06. Isolate role segregation and evaluate every assignment

The author requested an additional isolated-segregation study and evaluation of previously unassessed candidates.

```text
Давай улучшим статью ещё. Можно дополнить эксперимент или провести ещё один с чисто изолированной сегрегацией (если это возможно) и посмотреть подтверждает он наш эксперимент или нет.&#x20;
Касаемо того, что проверены только **два полученных кандидата на одной задаче**, восемь назначений остались пропускам - так не пойдет. Надо всех проверить. Скажи как это сделать и что тебе для этого надо и давай сделаем
```

## H07. Scale and repeated observations

The author requested approximately 1,000 tasks and three to five repeats. The wording about independence is the original request, not evidence that the selected tasks are independent.

```text
То, что у нас 200 независимых единиц - это мало. Хорошо бы ближе к 1000. Также нужно сделать 3-5 повторов
```

## H08. Actual external comparison

The author asked for real external baselines rather than only locally designed controls.

```text
Касаемо того, что нет реальных внешних бейзлайнов - это плохо. Давай придумаем как их сделать, что мы можем для этого сделать и т д
```

## H09. Comparable SCC study and complete evaluation

The author requested a comparable SCC series with a documented model and test access, completion of the large series and correction of intervals.

```text
Прекрасно. Теперь запусти необходимых субагентов, можешь проверить всё, что тебе необходимо. Потом допиши, пожалуйста, статью или поправь статью таким образом, чтобы все нынешние рецензии были учтены. То есть ты можешь сделать сопоставимую серию SCC в документированной модели, доступ к тестам и так далее. Можешь завершить серию из тысячи задач и пяти условий и поправить доверительный интервал — то, что просит агент. Сделай всё это. А, кстати, рецензии агента сохраняй отдельные в Review или Review Change Log, давай его назовём, файл, и там будут рецензии агента после каждого запуска. В общем, исправь всё, что необходимо, сделай статью сильнее и опубликуй новую версию. Потом снова запусти агента-ревьюера и посмотри, что он выведет.
```

## H10. Subscription stopping constraint

The author specified a reserve near 55% remaining. The implemented study guard and its exact boundary are documented separately; this message alone is not an execution record.

```text
Если ты понимаешь, что истратил больше 50% подписки, то пожалуйста остановись. Я имею в виду, когда процент подписки стал меньше 55%.
```
