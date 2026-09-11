# Algorithm-semantics readability audit

Date: 2026-09-11
Scope: read-only technical audit of the current EN/RU descriptions and figures. No experiments, live-series outputs, or model calls were inspected. This is a readability and semantic-consistency check, not a scientific review.

## Assessment

The prose is methodologically careful, but the displayed algorithm and the figure still make the measured boundary harder to see than necessary. The central distinction should be rendered as a short observable pipeline:

```text
task x + fixed supplied context C0 + assigned condition a
        -> one fresh call (D/SR/SN) OR three fresh calls with full history (MR/MN)
        -> exposed response(s) and one extracted candidate
        -> original native tests + common control gate
        -> pass / failure / unavailable + resource record
```

The decisive visual rule is that no arrow returns from native tests to the model. The model receives task/context and, in MR/MN, prior exposed responses; it does not receive test outcomes. This is already stated in `sections/hybrid_core_en.tex:5,12-14,48` and `sections/exact_prompts_en.tex:5,14,20-22`, but the proposed short diagram should make it the dominant reading path.

## Proposed simple observable scheme

Use one common input box labelled “Task `x` + fixed supplied context `C0` + frozen condition `a`”. Split only by call structure:

1. **D:** one fresh call with the direct implementation instruction.
2. **SR/SN:** one fresh call containing the three operation sentences in order. SR uses role labels; SN uses neutral stage labels. The operations are instructions in one response, not three observed agents.
3. **MR/MN:** call 1, call 2, call 3; each is fresh, and every complete earlier exposed response is forwarded. MR uses role labels and MN neutral labels.

All branches then join at “extract the sole final program”. Show the extraction guard explicitly: a valid single Python fence (or the repository-repair diff form) yields the candidate; an observed response with invalid format yields an empty candidate. A failed completion/usage contract is a **generation unavailable** record and must not be drawn as an empty program. This distinction follows `sections/hybrid_core_en.tex:33-44` and the final-output contract in `sections/exact_prompts_en.tex:18-22`.

The next box should read “External native evaluation (after generation): original tests + common control gate”. Its output should be a small status ledger rather than one generic “outcome” box:

```text
generation: observed | unavailable
candidate: valid | empty (only if an observed response failed extraction)
native evaluation: pass | failure | unavailable
record: exact candidate bytes, test evidence, control-gate status, known resources
```

Do not collapse generation unavailability, an empty extracted candidate, native test failure, and unavailable evaluation into the same failure category. The formal section explicitly warns against turning unavailable generation/evaluation into a fabricated test failure (`sections/hybrid_core_en.tex:5-7`), and the algorithm records these outcomes separately (`:35-44`). “Exact program/report join” in `figures/hybrid_core_en.tex:11` is technically accurate but cryptic; “join candidate bytes with native test evidence and the control gate” is easier to read.

The figure currently shows only SR and MR (`figures/hybrid_core_en.tex:6-12`). That is acceptable as a representative core/comparator illustration only if the caption or a small side note says that D, SN and MN use the same evaluator and are defined by the design table. The current caption does this in prose (`sections/hybrid_core_en.tex:18`), but a visible label such as “representative call structures; all five conditions share the evaluator” would prevent readers from mistaking the drawing for the complete factorial.

For the algorithm caption, “Evaluated single-pass generation and subsequent external audit” is semantically defensible but “audit” suggests a human or security audit. A clearer caption is **“Visible generation, extraction, and external evaluation”**. Russian equivalent: **«Наблюдаемая генерация, извлечение и внешняя оценка»**. This names the actually measured stages without implying convergence, internal-agent traces, or feedback-driven retries. The stopping and no-retry qualifications must remain (`sections/hybrid_core_en.tex:48`).

## Separate conceptual INoT scheme

The INoT block should be separated from the measured pipeline with a dashed boundary and a label such as “Conceptual instruction read by the model; not host-executed and not separately measured”. A readable version is:

```text
Prompt-level INoT instruction + task/context
        -> virtual answer A and virtual answer B
        -> repeat for at most 10 conceptual rounds:
             arguments -> cross-critiques -> rebuttals -> updates
             if answers agree: stop
        -> final answer = agreed answer, otherwise latest A
        -> requested output format
```

The loop cap is **at most 10 internal/conceptual rounds**. It must not be described as ten host calls, ten logged agents, or a measured number of internal steps. The current appendix correctly says “conceptual guidance read by the model, not executable host code” (`sections/exact_prompts_en.tex:23-27`), and the method section correctly says that the actual INoT* condition uses one fresh call/task and that hidden interactions are unverified (`sections/inot_method_en.tex:3-5`). Those qualifications belong directly beside the conceptual block, not only in surrounding prose.

The fallback must remain explicit: if agreement is not reached by the cap, return the latest virtual-A result. The current PromptCode contains this rule, and the method section explains why it was made explicit (`sections/exact_prompts_en.tex:25; sections/inot_method_en.tex:5`). The block should also show that native tests happen only after the final answer is returned; no test feedback is sent into the conceptual loop.

For naming, “Exploratory prompt-level INoT adaptation” / «Поисковая промптовая адаптация INoT» is more precise than “algorithm replication” for this setup. The current text already limits the claim to a disclosed adaptation and states that no verified author implementation or author validation is claimed (`sections/inot_method_en.tex:3-5`). The figure and caption should use the same qualified wording.

## Details that cannot be lost when simplifying

- `C0` is the fixed supplied/retrieved context, not an assertion that the full repository was supplied (`sections/hybrid_core_en.tex:5`).
- Generation has no tools, file reading, browsing, test execution, delegation, benchmark tests, test outcomes, or reference-solution access; the common prompt makes this explicit (`sections/exact_prompts_en.tex:5`).
- SR/SN are one fresh model call; MR/MN are three fresh calls with the complete earlier exposed responses forwarded (`sections/hybrid_core_en.tex:12-14,23`; `sections/exact_prompts_en.tex:14,22`).
- SR versus SN changes only role labels; MR versus MN preserves the corresponding operation sentences. D is a direct-instruction control. All five conditions use the same subsequent native evaluator (`sections/hybrid_core_en.tex:14`).
- There is one final candidate per assignment, strict final-format extraction, and no automatic retry after a rejected completion. Continuation is only for cells where no call had started (`sections/hybrid_core_en.tex:34-44,48`; `sections/exact_prompts_en.tex:18-22`).
- External tests are a later evaluator, not a model tool, and no native result is returned to the generating model (`sections/hybrid_core_en.tex:18,48`).
- The record must preserve prompt/events/terminal status, exact candidate bytes, native evidence, control-gate status, and known resource counters (`sections/hybrid_core_en.tex:34,43-44`).
- INoT* is a separate exploratory prompt-level adaptation on the stated primary task setup, not one of the four factorial conditions and not an exact reproduction of paper scores (`sections/inot_method_en.tex:3,7`).
- The INoT conceptual loop has two virtual workers, agreement-or-cap stopping, a latest-A fallback, and no claim that internal rounds or hidden agents were observed (`sections/exact_prompts_en.tex:25-27`; `sections/inot_method_en.tex:3-5`).

## Findings to relay to the editor

There is no substantive methodological contradiction in the current EN text or its RU counterpart. The main issue is presentation: the measured outer pipeline and the unmeasured conceptual INoT loop are visually adjacent and the current one-line PromptCode forces readers to reconstruct the control flow. A two-part figure, with the observable pipeline as the primary panel and the conceptual INoT loop as a dashed explanatory inset, would resolve this without changing the experiment or claiming additional measurements. The only wording risks worth correcting are “external audit” (too broad), “one final program” without showing extraction status, and any label that could make an invalid observed response look identical to unavailable generation.
