# SCC-2000 presentation preparation

`reproducibility/scc2000/presentation.py` is prepared as a downstream renderer
for the completed, verified SCC-2000 archive. It reads
`amended-analysis/summary.json` as the final amended analysis,
the amendment selection manifest, the selected 6,000-row view, and the archive
manifests; it refuses an incomplete generation or missing final analysis and
manifest. It preserves raw availability, format, native status, quality, and
outcome fields in `selected_6000_rows.csv`, and emits separate EN/RU summary
and 956-task appendix tables.

The appendix uses P/F/T/X/G/U/N consistently with the existing assignment
renderer. Unknown remains unknown; an em dash denotes an assignment outside
the frozen selected prefix. The original 9,000-row ledger's 3,000
administratively unselected cells therefore are not described as missing.
Summary values are passed through from the frozen analyzer, including
SCC-minus-SR/SN task differences, bootstrap and Holm values, fixed-denominator
bounds, paired-resource ratio-of-means versus mean-task-ratio, and restart
diagnostics. No native quality or interim live source was inspected.

Focused synthetic tests:

```text
python -m pytest reproducibility/tests/test_scc2000_presentation.py
```

When the published archive is available, render it with:

```text
python reproducibility/scc2000/presentation.py --archive <verified-archive> --output <presentation-output>
```
