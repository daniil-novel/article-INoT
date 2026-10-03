# Anonymous July 2026 replication package

This package contains the code, configurations, saved metrics and usage records underpinning the July 2026 manuscript. It is an evidence-replay package: its default verification makes no model calls and disables network connections in the analysis builder.

## Contents

- `research/src/`, `research/config.yaml`, `research/pyproject.toml`: the frozen experimental harness and declared dependency constraints.
- `research/results/`: retained Pro E2/E3 and controlled Pro/Flash-Lite E6 records and original summaries.
- `article/reproducibility/results/20260726_flash_lite/`: retained Flash-Lite E3 and small-model profitability E4 records.
- `article/reproducibility/evidence_snapshot.json`: anonymized archived July aggregate snapshot and nine packaged-input checksums.
- `article/figures/`: archived original article diagrams and all six localized quantitative figures.
- `tables/`: machine-readable exports of the empirical table values and paired statistics; complete E2 aggregate objects are retained separately.
- `MANIFEST.json`: checksums of every review payload file except the manifest itself.

## Offline verification

Use an existing Python 3.10+ environment with NumPy, SciPy, Matplotlib and Pillow. The exact versions used to validate this package are in `ENVIRONMENT.json`; `requirements-offline-verified.txt` pins that validation environment. Package installation is a separate setup step and is not performed by the verification command.

From this directory:

```text
python verify_offline.py --output-dir reproduced
```

This checks every packaged checksum, reruns the archived statistical formulas and figure generation, compares all evidence fields with the preserved snapshot, and exports the empirical tables. It reports numerical comparisons with tight floating-point tolerances. Figure file/pixel identity is reported separately because fonts and renderer versions can differ; regenerated plots use the same archived numerical arrays. Output files are placed only in the chosen output directory.

The evidence builder has narrow adaptations: repository-history validation is replaced by packaged-file checksum validation; identifying source metadata is omitted; file paths become relative; the already archived HumanEval context profile is retained. The statistical formulas and original figure functions are unchanged. `scripts/export_tables.py` only exports the resulting data.

## Scope and limitations

The saved runs contain task identifiers, metrics, role usage, costs and latencies, but not full generated solutions. This package cannot retrospectively reconstruct or independently regrade those missing responses. HumanEval benchmark data and tokenizer caches are not bundled, so the archived context-input profile is preserved, not newly reconstructed during offline verification. The original task/context loader is included for inspection.

The Pro E3 pilot has five tasks per context; Flash-Lite E3 has twenty tasks per context with one seed (42). Controlled E6 covers ten base cases from three task families and has ceiling pass@1. The original approximate SWE-bench Lite check is not the official repository/container harness. The E5 figure is an API-cost extrapolation from E3, not a new measured E5 run or full TCO. Incomplete seed-123 E3 and separate E5 attempts were excluded. API model names are aliases rather than immutable weight snapshots; no new API evaluation was performed for this package.

## Source and data integrity

All research and article inputs come from the selected historical July sources. Two article JSON inputs were stored with LF line endings while the archived evidence recorded their original CRLF checksums; their parsed numerical records are unchanged. The review manifest uses packaged-byte checksums. Identifying provenance is deliberately outside this review payload. No credentials, account identifiers, personal repository links or author commit identifiers are included.
