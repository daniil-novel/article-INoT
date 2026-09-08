# Interpretation of the seven fixed gold-control failures

This note was written after INoT native outcomes were available and while the primary generation continuation was running. It corrects an earlier README interpretation that six gold failures had no diagnostic message. Their native `details` dictionaries contain per-test tracebacks/assertions, even when no `ALL` field is present. No control, task, test, environment or eligibility decision is changed by this later interpretation.

The primary evidence is `results/20260908_codex_mini_heldout200/controls/attempt3/gold/input/samples_eval_results.json`, indexed by `eval[task_id][0].details`. Exact task/reference/test source is retained in `controls/attempt2/input/evaluator_dataset.jsonl`; package versions are in `controls/attempt3/gold/pip-freeze.txt`.

| Task | Directly observed native evidence | Interpretation and limit |
|---|---|---|
| /101 | Four tests end with a DNS/name-resolution error during URL loading. | Reference requests the Boston Housing data URL; incompatible with this intentionally offline execution. |
| /590 | Three tests report URL/DNS errors while fetching the Wikibooks page. | The task/reference requires network access, which this environment disables. |
| /418 | `ALL` reports no module named `tensorflow`. | TensorFlow is absent. The assessed CPU TensorFlow dependency amendment conflicted with the environment's protobuf requirements and was not installed. |
| /686 | Five tests reject `OneHotEncoder(..., sparse=...)`. | The canonical solution uses an argument unsupported by the retained scikit-learn 1.5.2 environment. No reference program or dependency is changed after generation. |
| /276 | `test_case_4` and `test_case_5` fail the assertions requiring a non-NaN skewness. | These tests supply identical row maxima or a single observation; the canonical implementation calls SciPy moments on those degenerate samples. This is a reference/test discrepancy for the retained implementation. |
| /14 | `test_archive_content` cannot find `sample_file.txt` in the empty output of the test's external archive-listing command. | Test source invokes `unzip`. A later read-only inventory confirms that executable is absent in the identical image. The original report records the assertion rather than the command's exact exit diagnostic. |
| /1028 | `test_normal_operation` receives `None` instead of `logfile.log`. | Canonical code invokes `top` and catches `IOError`. The same later inventory confirms `top` is absent; this supports the explanation but the inner caught exception was not retained in the original report. |

The later inventory used the exact image ID `sha256:76d84f87bb98a10e358e19d58b84c2eed3dc24c1e8431582ae1dd9874faa7667`, offline/read-only/non-root, and only called `shutil.which` for `unzip` and `top`. Both returned null. Its command, output and hash are in the held-out archive's `environment/diagnostics/post_generation/`. It did not run a reference/model program or rescore a task. An absent executable plus a corresponding source call supports a diagnosis; it does not turn the original assertion into a separately observed process exit code.

All seven assigned tasks remain quality-unavailable for every treatment. Raw candidate/native outcomes are retained, and generation tokens remain counted. Repairing the environment now would require a separate evaluation version and would not retrospectively change the frozen main estimand.
