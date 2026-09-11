# Quality-figure audit: coordinator decisions

The [original technical report](quality-figure-audit.md) is retained unchanged.
It concerns the renderer introduced in `6e8b16b`, not a completed scientific
comparison. No live main-study outcomes were used to develop or validate the
figures. The reviewer used a separate context and did not edit the implementation.

1. **Strengthen contract checks — accepted.** The renderer now checks the exact
   factorial arm order, 10,000 resamples and seed 20260909, and Holm alpha 0.05;
   for SCC it checks the three methods, 1,000 assigned task clusters, Holm alpha
   0.05, and 10,000 resamples with seed 20260911. The test suite rejects conflicting
   method and resampling metadata. This remains a presentation gate: free-text
   method descriptions are not a substitute for the archive's full statistical
   replay, which remains a required preceding publication step.
2. **Unknown quality and conditional denominators — clarified and tested.** An
   unavailable outcome does not justify deleting its assignment or substituting
   zero. The plot uses each contrast's actual complete paired-task denominator,
   with three repetitions averaged within task. A new regression test retains
   nonzero unknown-outcome counts without inflating that denominator. The footer
   explicitly separates these conditional intervals from missingness bounds and
   source-group sensitivity. Requiring every quality outcome to be observed would
   wrongly prevent transparent publication of an otherwise complete ledger.
3. **Integrity checks versus statistical replay — retained boundary.** The
   renderer verifies retained bytes, terminal generation and summary structure;
   it does not claim to rerun evaluations or inference. The publication workflow
   already requires separate full replay. Both README and output provenance state
   this limitation.
4. **Presentation correction — adopted during visual QA.** Very small adjusted
   p-values now read `pH < 0.0001`, without an additional equals sign. Zero values
   remain exact in the exported CSV. Asymmetric intervals and unavailable
   estimates remain unchanged.

Validation after these edits: 13 targeted tests passed, and `git diff --check`
passed. Four EN/RU factorial/SCC PDF layouts were inspected using visibly marked
synthetic software fixtures; all were one page, with no out-of-page words in
Poppler bounding-box checks. These fixtures are not study results and are not
included in either manuscript. Actual figures await completed, replayed archives.

This is a technical review and adjudication. It does not replace the five fresh
scientific critics requested after the empirical manuscript is complete.
