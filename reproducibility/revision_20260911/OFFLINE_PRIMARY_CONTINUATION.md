# Offline continuation after primary native evaluation

Prepared on 12 September 2026 while the existing primary finisher and SCC
dispatcher are running. No unfinished candidate-quality results were inspected
to choose this sequence. This is operational scheduling of previously defined
calculations, not a change to hypotheses, source groups, bootstrap rules,
assignment eligibility or frozen generation/evaluation software.

`finalize_primary_offline.py` attaches to the already running primary finisher by
PID, creation time, exact module and checkout. It waits without a timeout-based
restart. It then requires terminal generation without a dispatch lock and all
18 successful stage records: export, the 15 native groups, collection and the
registered analysis. The existing publication tool independently validates full
records, responses, native joins and statistical results; stage exits alone do
not certify an archive.

The three sequential steps are the existing source-family sensitivity,
`publish_scale` (including full portable replay in a separate interpreter outside
the checkout), and the complete EN/RU assignment-table renderer. Each study's
fixed supplementary calculation can run after that entire study is complete.
This clarifies the earlier combined workflow wording in the task-dependence
README; its statistical protocol and implementations are unchanged. Integration
into the article and the five final scientific critiques remain after both
studies are complete.

The wrapper records its exact source and tracked processing-code/protocol hashes,
requires fresh nonoverlapping destinations, and takes one exclusive study lock.
Before every processing step it checks that those sources have not changed. It
holds a temporary system-sleep request until it exits. Any failed gate or stage
stops without retry, retaining logs and partial outputs for inspection. It never
starts a model, executes generated programs, reruns native evaluation, edits
frozen evidence, uploads files or pushes a commit. It produces no PDF; later
figure rendering and visual review still require an active review pass.

These local computations do not consume the Codex subscription. They can finish
alongside the already-running native evaluator if the separate subscription
guard stops model generation. The 55% reserve and its persistent pause continue
to forbid model work and automatic recovery; this wrapper does not read, clear
or override that pause.

Use the host publication dependencies and the existing operational dependency
file `requirements-subscription-guard.txt` (psutil 7.1.3). CI installs that separate
file to exercise PID-validation tests. The benchmark container requirements and
recorded analysis-library versions are unchanged.

Eight focused tests passed, including missing native output, failed/ambiguous
analysis return codes, an active dispatch lock and an unrelated PID. A real
read-only preflight recognized the existing finisher and created no output.
The continuation is not itself evidence that the main study or final archive
has completed. Inspect its actual process and `status.json` before acting; do
not launch a second copy or rerun completed stages.
