# Preparation review decisions

13 September2026. These are bounded protocol/software reviews before resumed
calls and SCC quality evaluation, not final independent manuscript reviews.

Accepted: fixed first2000 randomized blocks; matched-repeat, equal-task quality
and resource estimands; explicit eligible-task masking; assignment-denominator
bounds; source-family sensitivity; original three-complete-repeat analysis
separately; no submitted retries or success-based replacement.

Reviewer wording correction: FOLLOWUP_REVIEW.md calls the administratively
unselected remainder "3000 blocks". It is **1000 blocks / 3000 method
assignments**. AMENDMENT.md and the actual selection use those correct units.
The original review's initial eligibility concern was narrowed on source
inspection: the record builder already nulls control-ineligible quality, so
no observed outcome bias was demonstrated. The amended analyzer will still
require an explicit control mask and reject inconsistent records.

The first continuation implementation has not passed root review: inventory
basename collisions, insufficient fresh-guard/source/commit validation,
post-mutation process checking, and missing generate CLI were identified.
CONTINUATION_CORRECTIONS_REQUEST.md records required fixes. No real recovery
or resumed generation occurred before these findings. Resolution remains
pending corrected code, counterexample tests, and root verification.

Root corrections now retain full relative file inventories, bind actual ordered
cells and source hashes, verify fresh strict-65 quota plus watcher identity, and
require a valid heartbeat before every submission. Eighteen continuation tests
and nineteen reserve tests pass. Actual recovery preserved the eight raw copies;
all 3857 old assignments were compared and only the eight recorded status changes
were accepted. A Windows venv launcher was initially mistaken for a generator;
the command verb is now checked and that preflight failure caused no mutation.

LAUNCH_REVIEW.md raised two race concerns. The first does not account for the
existing exclusive DISPATCH.lock, which remains throughout recovery and prevents
another frozen dispatcher from acquiring the study. The second prompted the
per-submission heartbeat check with a 75-second maximum age and 30-second watcher
interval. freeze-v3 is the final pre-call binding after those changes; earlier
preparation drafts did not launch any model call. The old inventory and selected
cells remain byte-identical as JSON values. The old 55-percent latch remains in
its original directory; a separate, live reserve65 watcher enforces continuation.
The review addendum records the critic's independent reassessment.
