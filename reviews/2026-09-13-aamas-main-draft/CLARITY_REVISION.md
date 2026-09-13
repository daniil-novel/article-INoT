# Clarity revision record

Date: 2026-09-13

## Scope

Edited only `submission/aamas2027/paper/body.tex` and `submission/aamas2027/paper/primary_contrasts.tex`. No class, bibliography, statistics, code, prompts, model settings, protocol values, or SCC outcomes were changed. SCC remains method-only and pending.

## Changes

- Defined `Y_{tr}(a)` as the binary pass endpoint for repeat `r`, `\bar Y_t(a)` as the available per-generation task mean, and the complete-pair estimand conditional on three repeats in both compared conditions. Updated all four displayed estimands to use the task means.
- Moved the four source-group sensitivity intervals into a dedicated column in the Luna quality-contrasts table; the caption note now identifies the 992-group resampling basis.
- Condensed duplicated descriptions of the mini factorial, label-by-layout study, INoT* adaptation, stopping semantics, and robustness boundary while preserving all reported numbers and scope distinctions.
- Preserved the label-versus-independent-agent boundary, fixed-context controller scope, exposed `E_j` resource accounting, exact literal prompt strings, and all numerical results.

## Build and visual coverage

Compiled `submission/aamas2027/paper/main.tex` with local `latexmk -pdf -interaction=nonstopmode main.tex` from the paper directory. Build completed with PDFLaTeX/BibTeX and produced `main.pdf` with 7 physical pages (letter, 612 x 792 pt). The known official-class end-document `ifx` warning remains; no LaTeX error occurred.

Rendered pages 4--7 with Poppler at 120 dpi and inspected pages 4 and 5 visually, including the quality and resource tables. The added source-group column fits within the table width, remains legible, and has no overflow or clipping. Pages 6--7 were rendered and text-checked for the condensed earlier-studies discussion, pending SCC section, discussion, limitations, and conclusion. The paper remains within the 8-page content limit and leaves one physical page of space for later SCC results insertion.
