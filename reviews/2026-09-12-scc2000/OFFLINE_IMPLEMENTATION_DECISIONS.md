# Offline analysis and evaluation implementation review

Root reviewed the generated implementations before their use on SCC outcomes.
The initial finisher omitted native evaluation and the initial analyzer used
guessed metadata fields, incomplete workflow resource eligibility and object
serialization for draw vectors. These were implementation defects in preparation
code, not demonstrated biases in observed SCC results. No SCC native outcome
analysis had run while the corrections were made.

The corrected finisher calls every required frozen native stage, verifies its
environment and reports, reconstructs the full 9000-row ledger and writes the
selected 6000-row view outside the immutable prediction export. It invokes both
the original and amended analysis. Stage failures retain their outputs and stop.

The corrected analyzer binds exact selected cell identities and actual control
and source metadata. It implements matched-repeat task means, fixed-family Holm,
fixed-denominator identification bounds, complete-workflow resource pairs, known
partial subtotals and before/after/spanning-restart descriptions. Numeric draw
arrays and task records are saved for direct reconstruction; source sensitivity
uses the four previously specified partitions. No new significance family or
outcome-based exclusions were introduced.

The independent test draft initially substituted a synthetic allocation for the
actual prefix, lacked completed workflow status fields and searched only the top
draw directory. Root corrected those tests to use the exact frozen allocation and
reference-control metadata, with explicitly synthetic model outcomes. A deliberate
same-repeat counterexample and a numerical bound-width check now test the paired
estimand rather than a count alone. Original reports remain in task history.

Validation: 16 finisher/analysis/contract tests passed; two queue process-identity
tests passed. The preceding 18 continuation and 19 quota tests are separate.
The queue waits for the exact existing generator and then evaluates and analyzes;
it makes no model calls and does not declare paper or publication readiness.

The first publisher implementation remains unaccepted: it did not perform full
native/raw/statistical verification despite its completion report. It must be
replaced or completed before any SCC archive is issued. The already verified
primary-study archive is separate from that pending publisher.
