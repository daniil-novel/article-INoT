# Methods synchronization report

Date: 2026-09-13

Evidence read:

- `reproducibility/scc2000/AMENDMENT.md` for the fixed 2,000-block SCC prefix, estimands, Holm family, bootstrap and resource rules, paused unknowns, and completion gates.
- `reproducibility/scc2000/analyze.py` for the implemented selected-cell validation, PCG64 bootstrap, linear percentiles, task-level pairing, missingness bounds, and complete-resource eligibility.
- `reproducibility/results/20260912_scale1000_luna_full/analysis/summary.json` for the completed Luna counts and primary contrast outputs.
- `sections/scale1000_results_en.tex` and `_ru.tex` for the already integrated completed-study results and terminology.

Files edited: the requested bilingual standalone details, held-out limitations, task-dependence, and held-out-methods sections only. No protocols, analyzers, code, or pinned files were changed.

Changes synchronize the manuscript with the completed 1,000-task Luna evidence (15,000 assigned; 14,961 complete; 985 control-eligible) while keeping the initial 200-task mini study as a separate estimator and inference family. SCC is described as an ongoing amended comparison restricted to 6,000 selected prefix assignments over 956 tasks, with 941 control-eligible tasks; native outcomes are explicitly uninspected and no SCC results are stated.

Uncertainties retained: SCC generation and native evaluation are incomplete; eight previously submitted interrupted attempts remain paused unknowns; source similarity does not establish independence; the reused initial 200 tasks are not newly held out; equivalence, non-inferiority, matched token allowances, agent independence, and training contamination remain unsupported.
