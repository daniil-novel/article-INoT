# Human/assistant task exposure beyond the development set

On 8 September 2026, after the 400-candidate development extension was frozen and started, the public BigCodeBench dataset card was opened to verify its license. The page renderer also returned abbreviated example rows for `BigCodeBench/0` through `/7`, including prompt, solution and test snippets. This incidental exposure is recorded rather than describing all 1,100 reserved tasks as completely unseen by the research assistant.

These eight IDs are outside the frozen 40-task development set. No card snippets were supplied to any experimental model call, and the running development allocation, prompts and tests were unchanged. No reserved task has been used for model generation in the current study. Before any future confirmatory allocation, account for these IDs explicitly in the exposure map and do not claim an outcome-blind author inspection of them. The original 40/1,100 split files remain intact; this note does not silently remove tasks or retrospectively change an assigned denominator.

Source: [BigCodeBench dataset card](https://huggingface.co/datasets/bigcode/bigcodebench), accessed 8 September 2026. It labels the dataset Apache-2.0; the accompanying source license is retained with redistributed development evidence.
