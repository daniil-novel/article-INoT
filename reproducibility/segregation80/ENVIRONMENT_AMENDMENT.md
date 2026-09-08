# Pre-generation environment completion

8 September 2026, no Segregation-80 model calls have been submitted.
The first control run in bcb-heldout200:v3 has 68/80 passing gold programs;
all 80 deliberately incorrect programs fail. Nine gold failures name absent
libraries. Three further gold failures are assertion mismatches and require
diagnosis; they will not be fixed by modifying reference programs or tests.

Preserve the original control attempt, gate and unexecuted generation plan.
Add the nine missing libraries in a new image and rerun both complete 80-task
controls without replacing tasks. Use versions from the pinned BigCodeBench
requirements except TensorFlow: its upstream 2.11 build is incompatible with
Python 3.11, so use tensorflow-cpu 2.15.1 with NumPy 1.26.4. This is an explicit
environment adaptation, not the unchanged upstream environment. Limit TensorFlow
thread pools to one thread each inside the existing two-CPU evaluator budget.
Record the final image ID and full package freeze. Eligibility is derived from
the final pre-generation controls; all original failures remain public. Only
the final gate can authorize dispatch; the older draft plan is never executed.
