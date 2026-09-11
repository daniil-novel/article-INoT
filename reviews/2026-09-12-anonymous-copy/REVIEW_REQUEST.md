# Metadata-copy technical review request

Date: 2026-09-12. Requested model: GPT-5.6 Luna, medium.
Exact authored request, saved before dispatch:

```text
Review the new reproducibility/revision_20260911/prepare_primary_metadata_copy.py and reproducibility/tests/test_primary_metadata_copy.py against the frozen primary collector and command builder. This is a bounded technical review, not a final scientific critic. The tool must create a separate metadata-neutral generation copy, preserve all prompts/full scientific response text, candidates, failures and counters, retain malformed event fragments, rebuild changed per-turn hash references and leave original evidence untouched. Check file/path safety, accidental scientific-text redaction, command validation and the scope of its report. Read code only; do not inspect live candidate quality outcomes or SCC, modify source/evidence, invoke models/native tests or spawn agents. The coordinator will run a complete original-versus-copy raw reconstruction independently while you review. Save findings separately as reviews/2026-09-12-anonymous-copy/CODE_REVIEW.md. Distinguish demonstrated bugs from missing final whole-package anonymity/replay checks. Use GPT-5.6 Luna medium as approved for bounded preparation. Return concrete findings, not a broad acceptance verdict.
```

