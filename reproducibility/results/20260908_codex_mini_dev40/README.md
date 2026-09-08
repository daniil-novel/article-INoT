# GPT-5.4 mini development extension

This directory initially publishes the complete pre-generation control evidence. The frozen model matrix has 40 tasks × five conditions × two repeat labels: 400 candidates and 720 fresh CLI turns. Model generation is in progress; these control reports are not model-performance results.

- `controls/attempt1`: original environment diagnostic; missing Faker and an offline network-dependent task; CLI `dev` mode was not the intended `instruct` mode.
- `controls/attempt2`: Faker added; still the wrong CLI mode. Retained as a diagnostic, not the final control gate.
- `controls/attempt3`: final `instruct full` selective development controls. Gold passes 39/40, all 40 negative controls fail; `/1005` remains unavailable offline. The gate, raw metadata, exact solutions, full reports and independent pre-generation audit are retained.
- `controls/attempt1/inputs/official_dev40.jsonl`: the exact 40 selected original dataset records, including evaluator-only tests and canonical solutions. They were not model inputs.
- `evaluator-software-checks`: a successful gold round trip through the prediction launcher and an intentionally forced one-second deadline with verification that its own container was removed. These are evaluator software checks, not model responses.
- `BIGCODEBENCH-LICENSE.txt`: Apache-2.0 license accompanying the [upstream code](https://github.com/bigcode-project/bigcodebench); the [dataset card](https://huggingface.co/datasets/bigcode/bigcodebench) also declares Apache-2.0. Original benchmark work: Zhuo et al., *BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions*, ICLR 2025.

The original byte sequences and historical absolute paths are preserved. Runtime paths in recorded commands are evidence of the original execution, not portable installation instructions. See [the fixed extension protocol](../../revision/DEV40_PROTOCOL.md), [the assignment manifest](../../revision/codex_dev40_manifest.json), and [the exposure log](../../revision/DATA_EXPOSURE_LOG.md).
