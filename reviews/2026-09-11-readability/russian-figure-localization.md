# Russian figure localization

Created four new Russian-labelled PDF figures without changing the original English figures, TeX files, source archives, or numerical data:

- `figures/heldout_quality_effects_ru.pdf`
- `figures/heldout_token_components_ru.pdf`
- `figures/heldout_cost_quality_ru.pdf`
- `figures/segregation80/effects_ru.pdf`

The compact generator is `reproducibility/revision_20260911/render_russian_figures.py`. It uses DejaVu Sans and reads only completed-study summaries, candidate-record files for source identity/count checks, and `reproducibility/revision/heldout_rendered_values.json`. It does not read live-series outputs. Source hashes and checks are recorded in `reproducibility/revision_20260911/russian_figure_audit.json`.

Verified:

- primary allocation: 1,000 assignments and 996 recorded candidates;
- primary group counts: D 199, SN 197, SR 200, MN 200, MR 200, INoT* 199;
- independent extension: 320 assigned candidates;
- all plotted means, intervals, points, contrast labels, ranges, and units are taken from the same completed-study values as the English figures;
- Russian axis labels, panel titles, and token legend are embedded in the PDFs; the long token-axis label is split across two lines for readability.

No common Russian or English article PDF was compiled in this step.
