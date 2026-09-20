# Anonymous FSE 2027 analysis artifact

This package reproduces the numerical claims and tables in the paper from retained assignment-level outcome records. It contains no author identity, repository history, local absolute paths, account identifiers, credentials, or submission metadata.

## Contents

- `primary/`: the 15,000-row factorial outcome ledger, statistical summary, native-evaluation audit, source-dependence partition, protocols, and analysis sources.
- `scc/`: the amended 2,000-block Self-Collaboration outcome ledger, selection and control records, source-dependence audit, summary, per-task contrasts, amendment, protocol, and analysis source. Candidate source text is removed because it is unused by the analysis and can contain task-authored example identifiers.
- `paper_tables/`: the exact LaTeX table inputs used by the paper.
- `reproduce_tables.py`: performs a dependency-free check of every reported count/effect and writes `REPRODUCED_TABLES.md`.
- `reproduce_full_analysis.py`: reruns the primary and SCC statistical analyses from the anonymous assignment ledgers and compares the numerical summaries.
- `MANIFEST.json`: SHA-256 and byte count for every other file.

Run with Python 3.11 or later:

```text
python reproduce_tables.py
```

The quick table check uses only the Python standard library. It fails if a paper value differs from the retained summaries.

For an end-to-end statistical replay from the assignment ledgers, create a clean Python 3.11 environment and run:

```text
python -m pip install -r requirements.txt
python reproduce_full_analysis.py
```

This reruns the 10,000-draw task bootstrap for both studies and fails unless the primary summary matches byte-for-JSON and every non-provenance SCC result matches. The SCC input-file hash changes because the unused candidate source-text field is deliberately removed during anonymization.

## Scope and omissions

The anonymous submission artifact includes assignment-level outcomes, resource counters, hashes, protocols, task selections, control records, statistical summaries, source-dependence partitions, and analysis code. Full model response bodies, candidate source text from the SCC study, benchmark tests, and operational transport traces are omitted from the review package because they can contain incidental generated identifiers, benchmark-restricted material, or machine-local metadata. They are not needed to reproduce the reported statistical results. The complete research archive is retained and will be released after the double-anonymous review period, subject to benchmark and provider terms.

The package reruns the table-level audit without making new model calls or executing untrusted generated code. Native test execution requires the pinned container described in the retained environment files and is therefore outside this lightweight reviewer replay.
