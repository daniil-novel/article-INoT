# Export final-newline sensitivity: all ten original patches

A post-observation diagnostic, specified before the new evaluations in commit
9233028. Each of the ten original canonical predictions receives exactly one
final LF. No model call, hunk repair, program edit or selection is performed.

All ten transformed patches were evaluated through the same pinned native
SWE-bench harness/image with fresh run IDs. Every classification remains
unchanged: eight native application rejections and two applied patches that
fail the target regression. No issue is resolved. Removing the final newline
therefore does not explain the original negative results under this diagnostic.

plan.json links every immutable original prediction to its transformed copy
and SHA-256. Complete native artifacts are retained. These ten evaluations
are sensitivity rechecks of existing candidates, not ten new model candidates.
