# Ограниченный аудит SCC: feedback, tester и author-code adaptation

Дата: 2026-09-11. Scope: только чтение кода/текста и сверка с первичной статьёй; модели и новые эксперименты не запускались.

## Первичный источник

Проверен Dong et al., *Self-collaboration Code Generation via ChatGPT*, arXiv v2, 24 May 2023: <https://arxiv.org/html/2304.07590v2>, §3 (HTML lines 129--138), а также §4 (145) и §5.3 (196--205).

В §3 прямо сказано, что tester получает code и составляет test report; вместо генерации test cases с последующим ручным запуском авторы предлагают модели **симулировать testing** и выдавать report (источник, строки 131--138). В том же разделе coder получает plan или test report, а workflow возвращается к предыдущей стадии при найденных проблемах (130--138). В §4 maximum interaction в основной настройке равен 4 (145); §5.3 определяет MI=0 как отсутствие feedback и отдельно варьирует MI 0, 1, 2, 4 (196--205).

## Что фактически делает pinned author code

* `reproducibility/external_baselines/vendor/scc_2024/session.py:19-63`: `Session.run_session()` сохраняет analyst/coder/tester роли, передаёт coder-у `report`, вызывает `tester.test(code)` на не-финальных раундах, затем формирует `answer_report` и останавливается при `"Code Test Passed."` или при достижении `max_round`. Это соответствует классу controller transitions из paper.
* `session.py:33-46,138-169`: tester возвращает модельный текст; этот текст конкатенируется с candidate code и исполняется через `unsafe_execute`. Исполнение означает `exec(code + report)` в изолированной среде; success — отсутствие исключения, а не проверка напечатанного значения против ожидаемого ответа. Следовательно, внутренняя SCC feedback — это (а) модельный test report и (б) exception/no-exception от выполнения этого report вместе с code.
* `reproducibility/external_baselines/scc.py:69-83,86-136`: execution вынесен в pinned network-disabled, non-root Docker-контейнер; `scc.py:91-109` загружает только хвост проверенного `session.py`, а `scc.py:107-108` монтирует vendor source и input read-only.
* `scc.py:160-180`: transport сериализует role messages как text-only JSON и передаёт задачу/контекст; generated-test folder получает code/report. В `scc_protocol.md:14-19` зафиксировано, что historical prompts, role histories, extraction, tester transition и stopping сохраняются, но API sampling controls (`max_tokens`, temperature, top_p) не воспроизводятся и лишь записываются; generated tests не видят hidden tests или reference programs.

## Реальный дефект/необходимая оговорка

1. **Умеренный методический дефект формулировки (исправить текст, не код): `max_round`.** Upstream constructor имеет default `max_round=4` (`vendor/scc_2024/session.py:8-12`), тогда как adapter `scc.run_session` задаёт `max_round=2` (`external_baselines/scc.py:69-79`), и revision dispatcher передаёт это же значение (`revision_20260911/scc_dispatch.py:95-96`). Поэтому утверждение `scc_feasibility_en.tex:5` о сохранении controller/stopping behavior без оговорки слишком широкое: сохранена логика переходов, но interaction cap адаптирован (две coder iterations, до четырёх model calls вместе с analyst). Это уже честно отражено в `scc_protocol.md:21-25,31-38` как adaptation и в `closest_predecessor_en.tex:16` как непроведённое powered external comparison, но должно быть явно сказано и в feasibility paragraph.

2. **Ограничение, не дефект:** adapter не reproduces original API sampling controls (`scc_protocol.md:16-18`; `scc_feasibility_en.tex:5`). Это disclosed transport/model adaptation и не является claim об exact paper reproduction.

3. **Ограничение, не дефект:** execution of generated report is not equivalent to author paper's purely simulated testing. The paper describes model-simulated reports (primary source §3), while pinned code executes `code + report` and uses exception/no-exception as internal signal. The manuscript already discloses this at `scc_feasibility_en.tex:5`; formulation should retain “author-code execution semantics” and avoid saying that it reproduces paper's evaluator.

## Frozen9000 и роль-excised baseline

`revision_20260911/scc_protocol.md:10-13,21-35` и `scc_manifest.json` define exactly three contemporaneous arms: `single_roles`, `single_neutral`, `scc_author_2024_codex_transport`, 1000 tasks × 3 repeats = 9000 assignments. `single_neutral` is the present neutral-stage control; it is **not** the paper's role-excised Self-collaboration baseline. The role-excised baseline is discussed as nearest predecessor in `sections/closest_predecessor_en.tex:7-16`, and the text correctly says it remains unexecuted (`closest_predecessor_en.tex:16`). `sections/heldout_limitations_en.tex:11` independently states that the role-excised variant and planned 1,000-task external comparison remain unexecuted.

Permissible wording: “The frozen 9000-assignment SCC/SR/SN comparison contains an author-code SCC arm, fresh role-labelled SR, and fresh neutral-stage SN. It does not contain the paper's role-excised Self-collaboration arm; the latter remains an unexecuted external baseline.” Avoid “SCC role ablation,” “role-excised SCC result,” or any claim that SN/MN are author-code role-excised conditions. `closest_predecessor_en.tex:8-10` already makes the intervention distinction correctly.

## Feedback and test-access wording

Permissible: “SCC receives feedback from the model-generated tester report and from the pinned execution of `candidate + report`; native BigCodeBench evaluation is a separate post-generation quality endpoint.” The generated-test workflow does not receive hidden tests or reference programs (`scc_protocol.md:18-19`); the main factorial generation likewise does not expose benchmark tests, reference solutions, or test feedback (`sections/heldout_methods_en.tex:32`). Native reference/incorrect controls are evaluator controls, not feedback supplied to model calls. The paper's claim should therefore distinguish internal SCC feedback from native BigCodeBench evaluation and should not call the latter tester feedback.

## Suggested minimal replacement for feasibility sentence

“The adapter preserves the pinned author controller, prompts, extraction, role histories, tester transition, and exception-based stopping logic, while explicitly adapting the model transport, task interface, and interaction cap (`max_round=2`, versus the upstream default 4). The tester remains a model-simulated report; the author-code execution helper then runs candidate code concatenated with that report in an isolated container and treats no exception as its internal pass signal. Hidden tests and reference programs are withheld from this workflow; native BigCodeBench evaluation is reported separately.”

This wording separates paper semantics, author-code behavior, and the current adaptation without changing experiments, data, or LaTeX.

## Итог

No evidence of a data or execution-integrity defect was found in the inspected paths. The one material issue is overbroad “controller preserved” wording unless the `max_round=2` adaptation is named. The role-excised baseline is correctly excluded from frozen9000, and the inspected protocol already records the transport, hidden-test access, and separate native evaluation limits.
