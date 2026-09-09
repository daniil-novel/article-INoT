# SCC integration audit disposition

9 September 2026, after the preserved three-task pilot.

- **Host dependencies:** unchanged SCC imports OpenAI and tqdm before the
  replacement call boundary is installed. They were installed in the isolated
  `tmp/external-baseline-deps` environment used for generation and local tests.
  Exact installed versions are in the public pilot archive. CI installs
  `external_baselines/requirements.txt`; Linux CI passed on `bc13b47`, including
  the full raw/native replay. Testing without those declared dependencies is
  not the experiment environment.
- **Self-contained program contract:** the pilot passes full context as task
  text and leaves historical `before_func` empty. In the actual native harness,
  `--calibrated False` is explicit. In pinned BigCodeBench `evaluate.py`, lines
  300--306, a `solution` record is therefore evaluated without prepending
  `code_prompt`. Both internal SCC checking and final native evaluation consume
  the returned self-contained code. The claim that the final evaluator silently
  supplies missing imports does not apply to this configuration. The difference
  from SCC's historical HumanEval preamble remains a disclosed dataset adaptation.
- **Infrastructure failures:** structured assignment errors, per-container
  terminal states and cleanup records were added after generation. Tests cover
  missing Docker, timeout cleanup and an unexpected session exception. Old
  trajectories are unchanged; their archived adapter hash is explicitly accepted
  and their successful upstream transitions replay exactly.
- **Native algorithm:** tests preserve the first-fence extractor, last-function
  selection, retention of a prior valid program after an invalid repair, the
  final-round no-tester rule and print-only early stopping. The historical
  evaluation helper is not used to assign benchmark quality; original
  BigCodeBench supplies the separate outcome.
- **Transport boundary:** serializing conversation JSON into a CLI turn is a
  documented adaptation, not native API message semantics. Original requested
  sampling controls are archived but not enforced. This limits interpretation
  and must appear in every large-series protocol and method description.
- **Remaining scale work:** the pilot runner is not yet a resumable four-method
  confirmatory dispatcher. Freeze the common transport for SR/SN/SCC/INoT, complete
  the INoT fidelity specification, and validate the new allocation, missingness,
  inference family and resource ledger before the proposed 12000 assignments.
  No outcome from the three exposed pilot tasks enters that comparison.
