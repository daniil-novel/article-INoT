# Editorial board and scientific review, 9 September 2026

The author requested immediate editing and review of the current Hybrid-INoT manuscript. The previously scheduled review was paused. This is an internal AI-assisted editorial and scientific review, not a journal decision or an external human referee report.

**Completed:** five Russian editors, five English editors and five separate scientific critics. Read the [Russian synthesis](REVIEW_RU.md), [coordinator decisions and corrected reviewer errors](DECISIONS.md), and [snapshot manifest](review-manifest.json). Individual scientific opinions are preserved in R1–R5.md; they must be read with the adjudication. The outcome is a clearer bounded empirical paper, with remaining replication, batch-sensitivity and external-comparison work. No unconditional Q1-readiness verdict was issued.

The English manuscript reviewed is commit `823ac21d1517c9e4967b47aee82485c743e0eb75` (39 PDF pages); the Russian edition has 44 pages. PDF hashes are in `pdf-audit.json`. The report includes a new, explicitly post-review [missingness diagnostic](missingness-bounds.json), reproducible with `python reviews/2026-09-09-editorial/check_missingness.py`. It does not change the reviewed manuscript or frozen primary analysis. See [journal source access details](JOURNAL_SOURCES.md).

## Scope and sequence

- Field: empirical software engineering and LLM code generation.
- Article type: empirical component evaluation with an architectural model and separate feasibility studies.
- Languages: Russian editing first, followed by an English edition checked against the revised Russian text.
- Target journal: not specified; journal fit is evaluated separately from language quality.
- Intervention: moderate prose editing. Preserve the original Hybrid-INoT architecture, experimental facts, uncertainty, formulas, citations, and exact executed prompts.
- Starting commit: `5f4a64faaeb4c9c62fc1b591e3485e177e46361a`.

Five Russian editors and five English editors worked in separate fresh contexts, in waves because at most three child agents could run at once. They submitted proposed changes rather than modifying the manuscript concurrently. The coordinating editor selected changes and resolved overlap using the source text. A subsequent Scientific Reviewer run used five further fresh critics. Separation of contexts does not establish independence between model families or replace human peer review.

The editorial instructions supplied by the author define the requested workflow. Their embedded citation placeholders are not references and are not copied into the manuscript. The installed Scientific Reviewer 1.0.0 skill and its references match the supplied reviewer kit after line-ending normalization.

## Preservation and review records

The working snapshot covers 89 TeX files. `preservation-audit.json` compares numerical tokens, mathematical expressions, citation commands, labels, references, included files, and verbatim blocks before and after editing. This is a mechanical safeguard; semantic equivalence still requires editorial review. The frozen experimental source and evidence archives are outside the editing scope.

Each editor's report identifies actual reading coverage and sources. Scientific critics receive the final revised manuscript and a neutral material map, without earlier editorial verdicts or each other's reports. Any unresolved empirical limitations remain visible in the final synthesis.

## Editorial reference points

The coordinating editor opened the following sources on 9 September 2026:

- [Nature editors' advice on scientific writing](https://blogs.nature.com/blog/editors_advice_on_writing_scie_1/) (2010, full page): state the research question, distinguish data from interpretation, and use clear sentences. This is general guidance, not a requirement to imitate Nature's article format.
- [LLM-based Interactive Code Generation: Empirical Evaluation](https://www.ispras.ru/proceedings/docs/2025/37/5/isp_37_2025_5_123.pdf), Proceedings of ISP RAS 37(5), 2025 (full Russian article PDF): a topical Russian-language reference for concrete descriptions of code generation, external checks, and empirical questions. No distinctive wording is borrowed. Its journal indexing or quartile is not inferred from this article.

Additional independent source checks are recorded in the individual reports. The Nature formatting-guide page failed to open through its authentication redirect; it is not counted as a verified source.
