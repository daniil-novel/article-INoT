# Reusable workflow overview

[View the two-page layout preview](workflow_layout_preview.pdf); the figure is
on page 2. This is a preparation artifact, not an AAMAS submission. It contains no
experimental outcome and does not imply that the large studies are complete.

The overview places the three factorial call configurations beside the same
external evaluation boundary. A separate panel shows the adapted SCC controller
and its generated-test feedback. Model calls have solid borders; host execution
has dashed borders. Named roles in one prompt are explicitly described as
prescribed functions, without claiming observed internal agents.

The source is [workflow_overview.tex](workflow_overview.tex), a vector TikZ figure
for a full-width `figure*`. It uses no scaling or changes to the conference class.
Keep the caption and `Description` in
[workflow_layout_preview.tex](workflow_layout_preview.tex) when adapting it:
they explain the ordinary-path scope, failure/fallback rules, generated tests,
external evaluation and the absence of a second internal SCC test after repair.

To reproduce this preview, copy the unchanged files from `../official-template/`
and the two TeX files above into an empty build directory, then compile
`workflow_layout_preview.tex` with a normal PDF LaTeX/latexmk workflow. The preview
wrapper explicitly identifies itself as a layout check and uses no real author
or submission identifier. It is not the final main-paper source.

[Source review, decisions and PDF audit](../../../reviews/2026-09-12-workflow-layout/DECISIONS.md)
record the checks. The figure may be incorporated when the conference article is
written from the completed, reviewed research. Its position, caption and full
page layout must then be checked again in that actual document.
