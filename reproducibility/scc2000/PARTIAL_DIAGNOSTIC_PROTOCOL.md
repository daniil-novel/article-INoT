# Retained SCC developer-program diagnostic

Frozen 13 September 2026 after generation ended and before executing or inspecting
native quality of these retained programs. This is an additional feasibility
diagnostic; it does not amend the primary SCC estimand or replace missing outcomes.

Include exactly the 396 selected SCC workflow cells whose first generated-test
execution failed because the Docker daemon was unavailable. The later network
stream failure and eight historical pauses are outside this diagnostic. Source
programs are the exact UTF-8 `code` strings in the frozen generated-test input,
not tester-response fences, reconstructed programs or newly requested responses.
Retain their associated generated-check text and all source hashes. No model
request, repair, manual patch or generated-check rerun is permitted.

Evaluate each retained program once against the same original BigCodeBench native
tests and verified control environment as the completed primary SCC candidates.
The 396 assignment identities are grouped by repeat label: 140 for 101, 145 for
102, and 111 for 103. A task can occur in more than one group. Within each group,
the sample order follows the original 1,000-task allocation. The official runner
and its process limits remain unchanged. Start these groups sequentially only
after the main SCC native queue releases the local evaluator resources.

Validate each native group against its exact programs, original test identities,
image, dependencies, control evidence, command and before/after sample hashes.
Retain native pass, ordinary failure and timeout separately. A missing report,
identity mismatch or invalid enclosing evaluation record leaves diagnostic
quality unknown; it does not become a program failure. Control-ineligible
programs can have native statuses but have no eligible diagnostic quality.
Publish a row for every one of the 396 assignments, including unknown values.

Report counts and observed rates descriptively with their explicit eligible
denominators. No new hypothesis test, SCC--SR/SN contrast, workflow-completion
claim or primary imputation is made from these partial programs. The diagnostic
cannot recover the unexecuted generated-test feedback or the counterfactual
repaired program. Original 396 infrastructure-failure statuses remain intact.

The v2 setup and inventory are retained under
`reproducibility/runs/scc-partial-programs-20260913`. Earlier draft helpers and
preparations did not execute native programs. The working preflight reconciles
all 396 rows as unknown before native execution; nine focused tests exercise
retained-code selection, tampering, allocation order, repeated identities,
missing reports and native timeouts.
