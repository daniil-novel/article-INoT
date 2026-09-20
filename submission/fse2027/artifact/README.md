# Anonymous FSE 2027 analysis artifact

This package reproduces the numerical claims and tables in the paper from retained assignment-level outcome records. It contains no author identity, repository history, local absolute paths, account identifiers, credentials, or submission metadata.

## Contents

- `primary/`: the 15,000-row factorial outcome ledger, statistical summary, source-dependence partition, protocols, analysis sources, and an `evaluation/` evidence tree. The latter contains all 14,961 candidate programs, staged native-evaluator inputs, native reports, reference/incorrect controls, pinned environment files, and the exact evaluator source and benchmark data under the included license.
- `mini/`: the earlier 1,000-assignment GPT-5.4-mini corroboration, including its anonymous outcome ledger, fixed task selection, protocol, amendment, prompt material, summary, and analyzer.
- `scc/`: the amended 2,000-block Self-Collaboration outcome ledger, selection and control records, source-dependence audit, summary, per-task contrasts, amendment, protocol, and analysis source. Candidate source text is removed because it is unused by the analysis and can contain task-authored example identifiers.
- `paper_tables/`: the exact LaTeX table inputs used by the paper.
- `reproduce_tables.py`: performs a dependency-free checkpoint of the reported assignment counts and headline effects and writes `REPRODUCED_TABLES.md`; the manifest separately seals every exact LaTeX table input.
- `reproduce_full_analysis.py`: reruns the primary and SCC statistical analyses from the anonymous assignment ledgers and compares the numerical summaries.
- `reproduce_source_sensitivity.py`: exactly regenerates all 16 source-component bootstrap draw vectors and their intervals.
- `verify_native_evidence.py`: verifies every primary candidate byte-for-byte against the staged evaluator input, every native status against the outcome ledger, all report hashes, and the control-gate hashes.
- `MANIFEST.json`: SHA-256 and byte count for every other file.

Run with Python 3.11 or later:

```text
python reproduce_tables.py
python verify_native_evidence.py
```

The quick table check uses only the Python standard library. It fails if a paper value differs from the retained summaries.

For an end-to-end statistical replay from the assignment ledgers, create a clean Python 3.11 environment and run:

```text
python -m pip install -r requirements.txt
python reproduce_full_analysis.py
python reproduce_source_sensitivity.py
```

This reruns the 10,000-draw task bootstrap for the primary, mini, and SCC studies and separately regenerates the source-component sensitivity distributions. It fails unless the primary summary matches byte-for-JSON, the mini analyzer's numerical output matches the corresponding retained fields, every non-provenance SCC result matches, and every source-component draw is identical. The SCC input-file hash changes because the unused candidate source-text field is deliberately removed during anonymization.

## Scope and omissions

The anonymous submission artifact includes assignment-level outcomes, resource counters, hashes, protocols, task selections, all primary candidate programs and native reports, control records, pinned evaluator source and data, statistical summaries, source-dependence partitions, and analysis code. Full conversational response bodies, candidate source text from the SCC study, and operational transport traces are omitted because they are unnecessary for the checks above and can contain incidental generated identifiers or machine-local metadata. The complete research archive is retained and will be released after the double-anonymous review period, subject to benchmark and provider terms.

The package reruns the table-level audit and verifies the entire primary candidate-to-report chain without making model calls or executing generated code. A reviewer may also rebuild the included container and rerun the native tests; that optional operation executes untrusted generated programs and therefore remains separate from the safe default checks.
