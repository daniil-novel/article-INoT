# Workflow figure source review

**Scope.** Source-level review of `submission/aamas2027/preparation/workflow_overview.tex` against the frozen factorial treatment construction and the pinned SCC author implementation/adapter. No model, live outcome, or native evaluation was run.

## Disposition

The depicted workflow is substantively faithful for this reusable figure preview. I found no source-level error requiring a figure change. The solid/dashed legend, the common post-generation evaluation boundary, and the explicit separation of generated tests from benchmark tests are all supported by the inspected sources.

## Evidence checks

- The factorial rows match the frozen prompt construction: D is a one-call direct request; SN/SR are one call containing plan, implementation, and review operations; MN/MR are three calls in plan, implement, review order. Later factorial calls receive the complete earlier response history (`factorial_runner.py`, `ARMS`, `STEPS`, `payload`); role labels are prompt text, not separately observed agents. This supports lines 12--30 of the figure.
- The figure's top note is appropriately scoped as benchmark-test feedback: factorial generation has no test feedback, while SCC's internal feedback is from model-generated tests. The SCC protocol says generated-test reports are transition evidence only and never the benchmark quality label (SCC protocol, lines 47--49).
- The SCC sequence is accurate. `Session.run_session` calls Analyst once, then Coder; after a valid first code it calls Tester and host `unsafe_execute`, and at most makes the second Coder call (`session.py`, lines 19--56). With adapter `max_round=2`, this is at most four model calls: analyst, coder, tester, coder repair. The figure's “two coder iterations at most” and “Coder repair, if required” therefore match the configured controller.
- The execution box correctly represents host-side execution of the candidate plus the tester's generated `check` code. The adapter runs this in a network-disabled, read-only, non-root Docker container and does not provide hidden tests or reference programs (`external_baselines/scc.py`, `docker_execute`; SCC protocol, lines 17--19). The tester prompt itself asks for a `def check(candidate)` test program, so “generated tests” cannot be confused with benchmark tests.
- The stopping/repair branch is accurate for ordinary paths: an exact `Code Test Passed.` report stops the loop; another execution result reaches the next coder iteration, whose last-round output is final without another tester (`session.py`, lines 40--56). The caption's statement that a repaired program is not retested is correct for this controller. Transport aborts, extraction failures, and malformed outputs are separately categorized by the adapter/protocol, consistent with the figure's caveat.
- The final dashed node is correctly a shared external evaluation boundary: SCC's extracted candidate is sent to the unchanged native BigCodeBench evaluator, with common eligibility controls; internal exception-free execution does not establish benchmark correctness (adapter audit, “Self-contained program contract” and “Native algorithm”; SCC protocol, lines 42--49).

## Minor wording watchpoint

The heading “SCC: author controller” and named Analyst/Coder/Tester boxes are acceptable because the legend identifies solid boxes as model calls and the source explicitly preserves role prompts and role-specific histories. In the final paper prose, retain the protocol's qualification “pinned 2024 author implementation adapted to BigCodeBench” and call this a complete-method comparison, so the drawing is not read as an isolated causal test of role labels or as evidence of hidden independent agents.

The description's “execution without an exception stops” is a compact rendering of the actual exact-string stop rule: the controller stops on `Code Test Passed.`; any other returned execution report can trigger repair. The caption already states the exception-free run does not prove benchmark correctness, so this does not constitute a figure defect.

**Conclusion:** source check passes for the stated preview purpose. This is a figure-preparation disposition only and does not assess paper, submission, or scientific readiness.
