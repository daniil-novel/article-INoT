# Аудит исходной библиографии

Аудит выполнен по состоянию на 2026-04-13. Критерии: приоритет у первичных академических публикаций, книг, стандартов и официальной документации. Vendor-блоги, маркетинговые страницы, форумы, discussion-треды, marketplace-записи и `Wikipedia` не используются как опорные научные источники.

| Key | Исходный источник | Тип | Надежность | Цитируемость | Решение | Замена / комментарий |
| --- | --- | --- | --- | --- | --- | --- |
| `ref1` | Sun, Zeng, *Introspection of Thought Helps AI Agents* | arXiv preprint | medium-high | strong | `retain` | Базовый источник по `INoT`; в тексте отмечать как препринт 2025 г. |
| `ref2` | Ko et al., *Information Needs in Collocated Software Development Teams* | conference paper | high | strong | `retain` | Остается для мотивации по информационным потребностям разработчиков. |
| `ref3` | Parnin, Rugaber, *Resumption Strategies for Interrupted Programming Tasks* | journal paper | high | strong | `retain` | Остается для аргумента про переключение контекста. |
| `ref4` | Goncalves et al., observational study of developers' work practices | journal paper | high | strong | `retain` | Остается как эмпирическое подкрепление. |
| `ref5` | OpenAI blog post on `GPT-5.2` | vendor blog | medium | conditional | `replace` | Для статьи не нужен; если упоминается OpenAI, использовать `ChatGPT agent` announcement, system card и `Agents SDK` docs. |
| `ref6` | OpenAI system card update for `GPT-5.2` | vendor safety note | medium | conditional | `remove` | Непосредственно не поддерживает тезисы статьи. |
| `ref7` | OpenRouter `State of AI 2025: 100T Token LLM Usage Study` | vendor research / marketing | low | weak | `remove` | Не использовать как научное основание для экономических выводов. |
| `ref8` | Aubakirova et al., empirical `100T Token Study` | unverified arXiv-style claim | low | weak | `unconfirmed-remove` | Не использовать: надежная первичная верификация не получена. |
| `ref9` | Cursor `Agents` docs | official product documentation | medium | conditional | `replace` | Для индустриального обзора допустимы только как контекст; оставить не более одной официальной product reference на систему. |
| `ref10` | Cursor `Subagents` docs | official product documentation | medium | conditional | `remove` | Дублирует `ref9`; не нужен в научном ядре. |
| `ref11` | Microsoft / VS Code blog on Copilot agent mode | official product announcement | medium | conditional | `replace` | При необходимости оставить одну ссылку на публично подтвержденные capabilities Copilot Agent Mode. |
| `ref12` | VS Code blog on agent mode and MCP | official product announcement | medium | conditional | `remove` | Избыточно относительно `ref11`. |
| `ref13` | GitHub docs on Copilot coding agent | official documentation | medium | conditional | `replace` | Можно заменить на одну официальную doc/blog citation для GitHub Copilot Agent. |
| `ref14` | Windsurf Cascade docs | official documentation | medium | conditional | `replace` | Если индустриальное сравнение сохраняется, оставить как product-level context без архитектурных claims. |
| `ref15` | AWS DevOps blog on Amazon Q Developer | vendor blog | medium | conditional | `replace` | При необходимости заменить на официальную документацию Amazon Q, а не на блог. |
| `ref16` | AWS blog on Amazon Q Developer | vendor blog | medium | conditional | `remove` | Дублирование и маркетинговый характер. |
| `ref17` | Cline GitHub discussion on single-agent architecture | forum / discussion | low | weak | `remove` | Форумные обсуждения не допускаются как научный источник. |
| `ref18` | Kilo Code marketplace page | marketplace listing | low | weak | `remove` | Неакадемический и ненадежный источник. |
| `ref19` | Anthropic announcement of MCP | official vendor announcement | medium | conditional | `remove` | Не является центральным для гипотезы статьи; при необходимости можно заменить на стандарт или peer-reviewed protocol work. |
| `ref20` | OpenAI Cookbook `agent orchestration & hand-offs` | official example documentation | medium | conditional | `replace` | Предпочтительнее `OpenAI Agents SDK` docs и `A Practical Guide to Building Agents` как более стабильные первичные источники. |
| `ref21` | GitLab Merge Requests API | API documentation | medium | weak | `remove` | Слишком низкий научный вклад для основной статьи. |
| `ref22` | GitLab Projects API | API documentation | medium | weak | `remove` | Не нужен в переработанной версии. |
| `ref23` | GitLab REST API auth docs | API documentation | medium | weak | `remove` | Не нужен в переработанной версии. |
| `ref24` | Git documentation | official documentation | medium | weak | `remove` | Общеизвестный инструмент, отдельная citation не нужна. |
| `ref25` | OWASP `LLM01: Prompt Injection` | security guidance | high | strong | `retain` | Допустим для раздела о безопасности агентных систем. |
| `ref26` | OWASP Top 10 for LLM Applications | security guidance | high | strong | `retain` | Остается как систематизированная рамка рисков. |
| `ref27` | ISO/IEC 25010 | international standard | high | strong | `retain` | Базовый источник для надежности и поддерживаемости ПО. |
| `ref28` | ISO/IEC/IEEE 12207 | international standard | high | strong | `remove` | В текущей версии не дает критически нужной поддержки тезисов статьи. |
| `ref29` | IEEE 1471-2000 | standard | high | strong | `replace` | Если нужен архитектурный стандарт, лучше использовать более современный `ISO/IEC/IEEE 42010`; иначе убрать. |
| `ref30` | Simon Brown `C4 model` website | reference website | medium | conditional | `remove` | В научном ядре не обязателен; можно не использовать при отказе от инженерных диаграмм. |
| `ref31` | PlantUML official site | software website | low | weak | `remove` | Инструмент сборки диаграмм не требует citation в основной статье. |
| `ref32` | Weiss, *Multiagent Systems* | academic book | high | strong | `retain` | Базовый теоретический источник по MAS. |
| `ref33` | Wooldridge, *An Introduction to MultiAgent Systems* | academic book | high | strong | `retain` | Базовый теоретический источник по MAS. |
| `ref34` | Guo et al., survey of LLM-based multi-agents | arXiv survey | medium-high | strong | `retain` | Полезен как обзорный источник. |
| `ref35` | Qian et al., *Scaling Large-Language-Model-based Multi-Agent Collaboration* | arXiv preprint | medium-high | strong | `retain` | Остается как современная работа по масштабированию multi-agent collaboration. |
| `ref36` | OpenRouter model card for Claude Opus 4.5 | aggregator model card | low | weak | `remove` | Заменить на первичный источник модели или полностью убрать модель-специфичную часть. |
| `ref37` | OpenRouter model card for Qwen3 Coder 30B A3B Instruct | aggregator model card | low | weak | `remove` | Заменить на первичный technical report модели или убрать. |
| `ref38` | `Wikipedia` article on J.A.R.V.I.S. | encyclopedia | low | none | `remove` | Полностью исключается. |

## Источники, которыми будут заменены слабые или неподходящие ссылки

1. Wei et al., *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models* (NeurIPS 2022).
2. Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023).
3. Madaan et al., *Self-Refine: Iterative Refinement with Self-Feedback* (2023).
4. Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning* (2023).
5. Turpin et al., *Language Models Don't Always Say What They Think* (2023) для ограничения интерпретации chain-of-thought.
6. Hong et al., *MetaGPT* (2023).
7. Qian et al., *ChatDev* (2023).
8. Jimenez et al., *SWE-bench* (2023).
9. Yang et al., *SWE-agent* (2024).
10. Chen et al., *Evaluating Large Language Models Trained on Code* (HumanEval, 2021).
11. Austin et al., *Program Synthesis with Large Language Models* (MBPP, 2021).
12. Jiang et al., *LongLLMLingua* (2023) и Pan et al., *LLMLingua-2* (2024) для компрессии контекста.
13. Jia et al., *Compressing Code Context for LLM-based Issue Resolution* (2026) для code-context compression.
14. Blyth et al., *Static Analysis as a Feedback Loop* (2025) и Bi et al., *CoCoGen* (2024) для самопроверки кода.
15. Sepidband et al., *Enhancing LLM-Based Code Generation with Complexity Metrics* (2025) для maintainability-aware feedback.
16. DeepSeek-AI, *DeepSeek-V3 Technical Report* (2024) и *DeepSeek-R1* (2025).
17. Z.ai, *GLM-4.5: Agentic, Reasoning, and Coding Foundation Models* (arXiv:2508.06471, 2025).
18. OpenAI `ChatGPT agent` announcement, `ChatGPT agent system card`, `Agents SDK` docs и `A Practical Guide to Building Agents` для подтверждаемых сведений об агентных паттернах OpenAI.

## Что принципиально не будет использоваться дальше

- `Wikipedia`, GitHub Discussions, marketplace pages, неакадемические агрегаторы.
- Утверждения о внутренних архитектурах `ChatGPT`, `DeepSeek` или других closed-source систем без первичного подтверждения.
- Любые конкретные claims о кварталах релиза, сравнительных качествах или процентах выигрыша, если они не поддержаны первичным источником и не маркированы как vendor-reported либо synthetic.
