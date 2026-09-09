# Coordinator adjudication

The five reports are preserved as independent initial opinions, including errors and disputed interpretations. They are not five votes for a verdict. The reviewed manuscript is commit `823ac21`; the later README-only commit is `1e5f0de`. The primary evidence snapshot cited by the paper is `96be37745b7f`, a different, deliberately frozen object.

## Scientific decisions

| Review point | Coordinator finding and disposition |
|---|---|
| R1/R3: selection from missing cells and continuation | Accept as a sensitivity-analysis need, not proof of observed bias. The archive has 996 completed candidates and four submitted incomplete assignments; two missing SN generations are on control-eligible tasks. The original stopping rule does not make a first-batch-only analysis an unbiased counterfactual. Any batch analysis must report changed task composition and paired coverage. |
| R1/R3: paired missingness bounds absent | Confirmed in the reviewed PDF. Added a separately labelled post-review diagnostic, `check_missingness.py` and `missingness-bounds.json`, using the frozen candidate records. This supplements this review, not the preregistered family or the reviewed PDF. Bounds are identification ranges, not sampling intervals. |
| R1: unavailable = failure / ITT | An operational pipeline-failure endpoint is legitimate if defined, but infrastructure unavailability and invalid reference controls must not silently become model failures. The supplemental analysis maps missing generations to failure only on the 193 control-eligible tasks and labels this as a different, post hoc estimand. It does not retrospectively create an ITT preregistration. |
| R1/R3: provider drift and replication | Accept as a limitation. Lack of repeated observations does not by itself prove confounding or invalidate task-paired inference for this execution; it limits precision and generalization. The pending large series supplies neither completed outcomes nor confirmed replication yet. |
| R2 point 2: SR/SN −18.45% attributed to one-versus-three calls | Reject this example as a reviewer error. SR and SN both use one call. The reported −18.45% is the label contrast. The call-topology contrasts are MN/SN and MR/SR; they include intermediate information flow and repeated inference, as already stated in Methods. A budget-matched comparison would answer another estimand, not automatically repair the label contrast. |
| R3 point 4: “MR/SN contrast” | This cross-factor wording does not identify a predeclared isolated contrast. The likely intended multi-call label comparison is MR/MN, whose valuation interval includes zero. No inference is based on the ambiguous reviewer wording. |
| R2/R4: architectural framing | Retain the author's original Hybrid-INoT architecture and bounded component framing. The abstract and conclusion explicitly deny a general role advantage and quality non-inferiority. A null result does not eliminate scientific novelty. The empirical added value should remain the controlled intervention, native evaluation and auditable evidence, not priority over SCC for role collaboration. |
| R2/R4: latent agents, unrestricted correctness, SWE effectiveness | These limitations are already explicit. Results state that the endpoint is the retained executable contract, not unrestricted correctness; the conclusion reports no resolved SWE patch and no hidden-role mechanism. Keep these qualifications; do not present them as newly discovered undisclosed claims. |
| R1/R2/R3: a non-inferiority margin is needed | Needed only for a quality-preservation claim. The existing refusal to invent an application-specific margin is scientifically appropriate. Do not select 2 pp or another threshold after seeing outcomes, or demand a positive result for publication. |
| R2/R4: faithful external comparison | Accept as needed for broad comparative claims. SCC author-code dev3 is feasibility evidence; INoT* is an explicitly resolved adaptation, not endorsement or replication by the original INoT authors. The exact SCC primary text §§5.2–5.3 confirms prior role/instruction and interaction experiments. |
| R5: archive commit versus manuscript commit | Different hashes are intentional; current text already says “primary evidence snapshot.” Both identities are recorded in the review manifest. Do not replace the evidence hash with the editorial hash or insert a recursively changing self-commit reference. |
| R5: missing codexrelease2026 key | No active-manuscript error. The preliminary observation came from excluded historical TeX. Final active bibliography has 17 entries, all cited, with no missing key. The final R5 report corrects this. |
| R5: repetition and bibliography conventions | Minor editorial points, not evidence of fabricated sources or detectable authorship. Preserve methodological caveats where needed for interpretation. Historical source versions can be intentional. Source verification was largely metadata/abstract level. |
| R4: quartiles and abstract length | Journal fit is not an article quartile or acceptance prediction. Only a secondary Scopus/CiteScore 2024 Q1 transcription for JSS is reported with its access limitation. Other current category/year quartiles remain unverified. A target-specific 150–250-word abstract is a submission-format task, not a universal scientific validity requirement. |

## Post-review missingness diagnostic

Each missing or control-ineligible binary endpoint ranges independently over 0 and 1. For each task the contrast interval is `[a_min-b_max, a_max-b_min]`; summing and dividing by the number of tasks gives sharp finite-sample bounds under these unrestricted assumptions. Native timeout is an observed failure, not a missing endpoint.

| Contrast | 193 control-eligible tasks, pp | All 200 assigned tasks, pp |
|---|---:|---:|
| SR−SN | [−1.5544, −0.5181] | [−5.0, +3.0] |
| MR−MN | [+1.0363, +1.0363] | [−2.5, +4.5] |
| MN−SN | [−4.6632, −3.6269] | [−8.0, 0.0] |
| MR−SR | [−2.0725, −2.0725] | [−5.5, +1.5] |

These are not confidence intervals: a singleton still has sampling uncertainty. Their signs cannot establish population-level significance, equivalence or non-inferiority. No new model generations were used; the 200-task bounds also incorporate uncertainty from seven control-ineligible tasks. Batch/provider sensitivity remains open.

## Editorial decisions and checks

Five Russian and five English agents submitted proposals in separate contexts. The coordinator selected and adapted them; rejected proposals remain visible as proposals, not accepted changes. In particular, replacing “assignments” with “runs” obscured the distinction between scheduled cells and completed generations and was rejected. Categorical claims that an effect was disproved or not reproduced were softened to the supported uncertainty statement. Stage labels and exact executed prompts were not rewritten. The architecture was preserved at the author's request.

`accepted-ru.json` contains 45 selected changes. `accepted-en-and-alignment.json` records the subsequent English proposal selections and bilingual clarifications; it does not enumerate every coordinating-editor translation. Git diffs are the authoritative complete change record. The preservation audit covers all 89 original TeX files, including unchanged files; it checks numeric tokens, formulas, citations, cross-references, includes and verbatim blocks. Such a check complements, rather than replaces, semantic reading. Both PDFs were compiled; representative pages were visually inspected and all page word boxes checked for overflow.

GitHub audit run [34380871709](https://github.com/daniil-novel/article-INoT/actions/runs/34380871709) succeeded on `1e5f0de`, including software tests, byte integrity checks and replay of recorded primary, independent, SCC and SWE outcomes. Replay is not fresh inference or a fresh Docker evaluation. Frozen experiment artifacts and pending scale-study dependencies were not edited.
