# Partial SCC diagnostic harness review

The diagnostic protocol is frozen before native execution: one candidate per each
of 396 SCC failure cells, all retained native outputs, and quality interpreted only
under the original frozen controls. No SCC method score or primary imputation is
assigned. The audit validates inventory cell/status/source hashes and string code
and report fields, then writes immutable artifacts. Setup validates and hashes the
actual frozen gate, dataset, prepared split, selection, and every source program.
It defines three groups (replicates 101, 102, 103), enforcing 396 unique
`(assignment_id, task_id, replicate_id)` identities. The runner rechecks sample
solutions and hashes, binds the Docker image to the gate image ID, and remains
preparation-only unless `--run` is explicitly supplied. Reports preserve pass,
fail, timeout, and unknown rows; missing reports stay unknown. Python compilation
and a fresh 396-cell audit passed, with group counts 140/145/111. Native execution
remains unstarted. Once the primary queue completes, run:

`python -m reproducibility.scc2000.partial_runner --setup tmp/revision/scc-partial-programs-20260913/setup.json --image bcb-scale1000:v2 --requirements reproducibility/scale1000/environment-v2/requirements.txt --dockerfile reproducibility/scale1000/environment-v2/Dockerfile --run`
