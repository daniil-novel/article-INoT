# English-language audit for the standalone article

## Scope and coverage

This is a focused editorial audit of the English manuscript rooted at `converted_article_springer.tex` and `sections/revision_en.tex`. The inclusion trace resolves 36 TeX files:

- `converted_article_springer.tex`; `sections/revision_en.tex`.
- Main text and methods: `sections/heldout_context_en.tex`, `closest_predecessor_en.tex`, `related_extended_en.tex`, `hybrid_core_en.tex`, `hybrid_accounting_en.tex`, `heldout_methods_en.tex`, `inot_method_en.tex`, `development_calibration_en.tex`, `heldout_cases_en.tex`, `segregation80_methods_en.tex`, `segregation80_results_en.tex`, `swe_demonstration_en.tex`, `hybrid_implications_en.tex`, `scc_feasibility_en.tex`, `task_dependence_en.tex`, `heldout_limitations_en.tex`, and `historical_evidence_en.tex`.
- Tables, figures, captions, and complete outcomes: `figures/hybrid_core_en.tex`, `heldout_quality_en.tex`, `heldout_tests_en.tex`, `heldout_resources_en.tex`, `heldout_resource_contrasts_en.tex`, `heldout_sensitivity_en.tex`, `heldout_exploratory_en.tex`, `dev40_table_en.tex`, `dev40_contrasts_en.tex`, `figures/segregation80/groups_en.tex`, `figures/segregation80/tests_en.tex`, `heldout_tasks_en.tex`, `dev40_tasks_en.tex`, and `figures/segregation80/tasks_en.tex`.
- Exact executed prompts and references: `sections/exact_prompts_en.tex`, `sections/segregation80_prompts_en.tex`, and `sections/revision_references.tex`.

The numerical results, limitations, original Hybrid-INoT contribution, exact prompts, and scholarly citations should be preserved. The recommendations below target clarity, idiomatic scientific English, and a self-contained reading experience. They do not assess scientific validity or assign an AI-authorship score.

## Highest-value language edits (12)

1. **Define the factorial arms directly.** Location: `sections/revision_en.tex:5`, “A factorial design crosses neutral or role-based stage labels with one or three calls”. The phrase is compact but makes the treatment structure harder to parse and “stage labels” is less precise than the later arm names. Replace with: “The factorial design crosses role-labelled versus neutral stage instructions with one-call versus three-call execution; a direct solver provides an additional comparison.”

2. **Clarify the acceptance-count sentence.** Location: `sections/revision_en.tex:5`, “GPT-5.4 mini with medium reasoning produces 996 of 1,000 assigned programs”. “Produces” can imply that all assignments generated a program before later exclusions. Replace with: “Under the disclosed amended execution protocol, GPT-5.4 mini with medium reasoning yielded 996 observed programs from 1,000 assigned cells.”

3. **Use “conditions” consistently and make the denominator explicit.** Location: `sections/revision_en.tex:23`, “The main five conditions span 44.56--48.70\% test success”. “Span” is acceptable, but the sentence mixes condition, arm, cell, and row terminology throughout the manuscript. Replace with: “Across the five primary conditions, observed test-success rates range from 44.56\% to 48.70\%.” Use *condition* for an experimental treatment, *assignment* for a task-by-condition allocation, and *call* for a model turn throughout.

4. **Repair the quality/resource conclusion.** Location: `sections/revision_en.tex:29`, “The resource reduction therefore does not establish savings with preserved quality.” The noun phrase “savings with preserved quality” is compressed and slightly unnatural. Replace with: “Thus, lower observed resource use cannot be interpreted as savings at preserved quality.”

5. **Make the interaction sentence grammatical and interpretable.** Location: `sections/revision_en.tex:27`, “The descriptive four-condition interaction is +2.09 percentage points, with interval ...”. A reader has to infer which interaction is meant. Replace with: “The descriptive difference-in-differences between the one-call and three-call role contrasts is +2.09 percentage points (95\% descriptive interval [−4.19,+8.38]) on the common 191-task subset.” Preserve the manuscript’s established interval convention if the minus sign is typeset in LaTeX.

6. **Replace an awkward adaptation description.** Location: `sections/revision_en.tex:54`, “The independent INoT* adaptation completes 199 of 200 assigned programs, with one original deadline and no final-format extraction error.” Replace with: “The independently dispatched INoT* adaptation yielded 199 complete programs from 200 assignments; one assignment reached the original deadline, and none failed final-format extraction.”

7. **Remove an idiom that obscures the replication status.** Location: `sections/closest_predecessor_en.tex:2`, “Removing roles or varying interaction is therefore not a novelty claim of the present study.” Replace with: “Therefore, removing role instructions or varying the interaction count is not claimed as a new intervention here.”

8. **Clarify what is being replicated.** Location: `sections/inot_method_en.tex:3`, “The four constructed factorial cells do not stand in for a published method.” Replace with: “The four factorial conditions are component interventions, not a replication of a published method.” This also removes the vague idiom “stand in for”.

9. **Use a concrete verb for archive reconciliation.** Location: `sections/development_calibration_en.tex:3`, “The full 400 native records reconcile to the exact exported programs.” Replace with: “All 400 native records match the exported programs exactly.” If byte identity is intended, say “match byte for byte”; otherwise retain “exactly” without implying a stronger check than was performed.

10. **Make the independent-extension limitation less abstract.** Location: `sections/segregation80_results_en.tex:20`, “The new estimates limit generalization of the earlier resource finding to role names alone.” Replace with: “The new estimates therefore do not support generalizing the earlier resource difference to role names alone.” This states the inferential consequence directly and matches the surrounding cautious claims.

11. **Shorten the dense repository-demonstration sentence.** Location: `sections/swe_demonstration_en.tex:8`, from “A prospective completion protocol ... restarts the interrupted MR assignment ...”. The sentence combines amendment timing, untouched assignments, recovery, and deadlines. Replace with two sentences: “Before the additional generation, a prospective completion protocol was published. It submitted each of the seven untouched assignments once and restarted the interrupted MR assignment from its first stage as a separately labelled recovery; each additional turn had a 600-second deadline.”

12. **Remove generic framing from the final contribution claim.** Location: `sections/revision_en.tex:84`, “The contribution is therefore an operational architecture supported by component-level evidence, not validation of every Hybrid-INoT extension or of a hidden internal role mechanism.” Replace with: “The evidence supports the operational single-pass architecture evaluated here; it does not validate the other Hybrid-INoT extensions or establish hidden internal role mechanisms.” This is shorter, concrete, and keeps the important scope limitation.

## Repetition groups to consolidate

- The manuscript repeats the same quality caveat in `revision_en.tex:29`, `revision_en.tex:68`, `revision_en.tex:70`, `revision_en.tex:84`, and `heldout_limitations_en.tex:5`: failure to reject is not equivalence or non-inferiority. Keep the full statistical explanation in the primary-results paragraph and use one short pointer in the Discussion and Conclusion.
- The external-verification boundary is stated in `heldout_context_en.tex:5,9`, `hybrid_core_en.tex:5,10--14,48`, `hybrid_implications_en.tex:4`, and `heldout_limitations_en.tex:7,9`. Retain the formal definition in `hybrid_core_en.tex`; elsewhere state only the implication for interpretation.
- Separate-batch and exploratory status is repeated for INoT* in `revision_en.tex:54`, `inot_method_en.tex:7`, `heldout_sensitivity_en.tex:2`, and `heldout_limitations_en.tex:11`. Keep the exact execution distinction in Methods and use “exploratory, separately dispatched batch” in results/discussion.
- Resource valuation is explained in `hybrid_accounting_en.tex`, `heldout_methods_en.tex:53--59`, `revision_en.tex:37,39,41`, and the captions of `heldout_resources_en.tex`, `heldout_resource_contrasts_en.tex`, and `figures/segregation80/groups_en.tex`. Define “API-equivalent valuation” once in Methods, then report values without repeating that they are not invoices in every nearby paragraph.
- The manuscript uses a recurring template of “does not establish”, “does not convincingly”, “does not support”, and “does not claim”. These are scientifically appropriate, but several adjacent paragraphs stack them. Keep the strongest limitation once per result and replace neighboring instances with direct descriptions of what the data show.

## Terminology and consistency checks

- Standardize *condition* for SR, SN, MR, MN, and D; reserve *arm* for a table column when needed; use *assignment* for one task-condition allocation; use *task* for the benchmark unit; use *call* or *turn* consistently (prefer *call* in the article, with *turn* only when referring to the CLI ledger).
- Standardize *role-labelled* and *neutral-label* (or *neutral-stage*) wording. The current text alternates among “role-based”, “role-labelled”, “roles”, “neutral stages”, and “label substitution”. Define the pair once as “role-labelled versus neutral stage labels” and retain that wording.
- Distinguish *one-call/three-call topology* from *heading/prose layout*. The independent 80-task experiment changes label wording and layout; it does not change topology. Avoid calling both dimensions “architecture” or “configuration” without a modifier.
- Use *quality* for native test success, *resource use* for tokens, and *valuation* for the counterfactual USD calculation. “Cost”, “price”, “spending”, and “valuation” currently appear close together and can imply different quantities.
- Use *reference control* for the gold-program check and *incorrect control* for the deliberately incorrect program check. “Reference gate”, “eligibility gate”, and “control gate” are all used; define “eligibility gate” once as the joint reference-pass/incorrect-fail rule.
- Keep *INoT* for the published method and *INoT*\* for the disclosed adaptation. Avoid calling the latter a “replication” without the qualifier “prompt-level” or “adaptation”.

## Standalone readability and artifact-dependent details

The article contains enough prose to explain the core intervention, task allocation, conditions, prompts, outcome definitions, missingness rules, statistical tests, and numerical results. The following details still make a reader dependent on external software artifacts and should be either summarized in the article or clearly labelled as supplementary verification rather than required for understanding:

- `sections/revision_en.tex:87` depends on a repository, a commit, named archive directories, SHA-256 inventories, Git-blob checks, public-archive replay, and automated Linux checks. These are reproducibility evidence, but they conflict with a standalone article with no repository or commit references. Replace this paragraph with an in-article data-availability statement that names the retained materials generically and gives the archive as supplementary material only, if permitted by the target journal.
- `sections/heldout_methods_en.tex:30--46` relies on a frozen permutation, source hashes, a model alias, CLI version, container image, package versions, exact source tree, and native reports. The article describes the protocol, but the identity and verification of these artifacts cannot be independently checked from the prose. Include the essential model, benchmark, evaluator, deadline, byte guard, and eligibility facts in the main text; move hashes and software identities to supplementary material.
- `sections/segregation80_methods_en.tex:10,12` refers to recorded container builds, image identities, and a dispatch commit. The control logic and final denominators are described; the build identity and commit are external provenance only and should not be prerequisites for interpreting the result.
- `sections/swe_demonstration_en.tex:4,6,8,27,29,33` depends on a base commit, selected repository packet, pinned harness, task image, archived traces, exact patch bytes, and replay auditor. The article can state the packet size, controls, deadlines, observed outcomes, and single-issue limitation without requiring access to those artifacts.
- `sections/scc_feasibility_en.tex:3,11,13` depends on author-code commits, isolated-container execution, raw-response replay, and named archives. Retain the scholarly citation and the procedural description, but remove commit/archive identifiers from the standalone narrative or place them in supplementary provenance.
- `sections/task_dependence_en.tex:6` points to a repository path for fingerprints and partitions and says that outcome-based sensitivity intervals await a future series. This is a pending-analysis statement, not a result needed to understand the article; move it to a supplement or rewrite it as a limitation.
- The exact prompt appendix is a strong standalone feature. Preserve it, including the final-output contract and the distinction between model-read conceptual guidance and executable host code. The appendix should not refer readers to hashes or byte strings as the only way to recover the treatment.

No missing language issue identified above requires changing a numerical result, citation, exact prompt, task outcome, or stated limitation.
