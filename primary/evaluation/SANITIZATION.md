# Anonymous metadata transformation

Machine-local repository and user-profile prefixes in JSON string fields were replaced with `<ANON_REPOSITORY>` and `<ANON_USER>`. Candidate programs, staged inputs, native test reports, status values, environment identifiers, and report hashes were not changed. The control gate's two metadata-file hashes were recomputed over the anonymous copies.

Transformed files:
- `primary/evaluation/controls/gold/run-metadata.json`
- `primary/evaluation/controls/gold.argv.json`
- `primary/evaluation/controls/incorrect/run-metadata.json`
- `primary/evaluation/controls/incorrect.argv.json`
- `primary/evaluation/native/direct-r101/run-metadata.json`
- `primary/evaluation/native/direct-r102/run-metadata.json`
- `primary/evaluation/native/direct-r103/run-metadata.json`
- `primary/evaluation/native/multi_neutral-r101/run-metadata.json`
- `primary/evaluation/native/multi_neutral-r102/run-metadata.json`
- `primary/evaluation/native/multi_neutral-r103/run-metadata.json`
- `primary/evaluation/native/multi_roles-r101/run-metadata.json`
- `primary/evaluation/native/multi_roles-r102/run-metadata.json`
- `primary/evaluation/native/multi_roles-r103/run-metadata.json`
- `primary/evaluation/native/single_neutral-r101/run-metadata.json`
- `primary/evaluation/native/single_neutral-r102/run-metadata.json`
- `primary/evaluation/native/single_neutral-r103/run-metadata.json`
- `primary/evaluation/native/single_roles-r101/run-metadata.json`
- `primary/evaluation/native/single_roles-r102/run-metadata.json`
- `primary/evaluation/native/single_roles-r103/run-metadata.json`
