# SCC method audit (pre-freeze)

This is a preparation audit of the author-code SCC comparison pipeline, not a
new manuscript review.

The pinned author controller remains the historical `Session.run_session`,
role prompts, histories, extraction, generated-test transition, and stopping
logic. Adaptations are the BigCodeBench self-contained task contract, Luna
medium transport bridge, serialized conversation JSON, and isolated Docker
execution. The protocol labels this as an author-code SCC transport/dataset
adaptation rather than an exact historical reproduction.

Cross-review findings fixed in the revision include randomized schedule RNG
reset, wrong SR/SN instruction policy, failed raw usage omission and double
counting, prior valuation reset, non-atomic lock cleanup, missing runtime and
instruction identity checks, transport failure misclassification, fabricated
empty SCC candidates, process-shared SCC globals, missing parent quota drain,
and generated-test concurrency control. The process path now uses spawned
workers, up to eight active assignments, and a shared two-container generated
test semaphore. The USD 15 in-flight amount is a planning reserve within the
shared USD 285 envelope.

Offline evidence: revision tests pass 10/10, the dev gate reports zero model
calls, the fixed 1000-task controls planner reports 9000 assignments and 985
quality-eligible IDs, and the three exposed development IDs (325, 322, 1036)
have a preparation-only smoke manifest with nine method assignments. The smoke
helper has an explicit execute mode that initializes the same runtime,
instruction policies, provenance capture, and spawned worker; it has not been
run. No main series or live smoke generation has been run. Native export,
finish, and analysis remain separate review surfaces and must pass their own
gates before final freeze.
