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

The first augmented image could not import the evaluator: TensorFlow 2.15.1
requires protobuf below 5, whereas the installed e2b 1.4.0 generated module
imports protobuf.runtime_version. Preserve both failed control launches.
Pin e2b 1.0.5, whose package allows protobuf 3.20--5 and whose generated module
does not import runtime_version. The local evaluator still executes no e2b
cloud calls. Verify the actual imports and rerun complete controls in a second
augmented image before finalizing any generation gate.

The three assertion failures expose older library contracts: task 157 expects
a flattened Matplotlib heatmap array, 221 indexes the array-shaped pre-1.11
SciPy mode result, and 699 assumes the older scikit-learn KMeans initialization
default and label order. Restore the upstream Matplotlib 3.7.0 and scikit-learn
1.3.1 pins, and use SciPy 1.10.1 (supports Python 3.11 and the older mode
contract). Preserve the intermediate augmented control runs as diagnostics.
These adjustments concern reference controls only and precede every candidate.
No reference code, test, task selection or model prompt is changed. The KMeans
test remains label-permutation fragile and reference checks do not repair its
semantic limitation.
