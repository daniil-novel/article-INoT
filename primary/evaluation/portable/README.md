# Native evaluator reconstruction

This archive retains the historical `scale1000-v2-Dockerfile` as evidence. Its private local base tag and repository-relative COPY path are not build inputs for this recipe. `portable/Dockerfile` supplies an archive-local build context, the complete final pip freeze, exact evaluator source, the prepared 1,000-task override dataset (SHA-256 `b7a414c732e7a131d5e76122613dff012470fa73fd2017a606223814428cbb8a`), the upstream 1,140-task dataset for provenance, and the recorded NLTK resource hashes.

From the archive root:

```text
docker build -f primary/evaluation/portable/Dockerfile -t fse2027-native-replay .
```

The public base tag is mutable. A successful build verifies the retained Python package versions and NLTK bytes, but does not imply byte-identical OS layers or equality to historical image `sha256:afeb8d78b76f6a7b1fbf427d78a55bd35dbfcf58387711b47f8a8ba00e16b580`. Downloaded NLTK data are checked against the retained hashes: unavailable or changed resources fail the build instead of silently being substituted. The frozen list is copied byte-for-byte from the completed reference-control environment. None of its versions is inferred from a current dependency resolver.

## Historical native replay command

For an existing staged input, run the helper from the archive root. Start with both controls:

```text
python primary/evaluation/portable/run_native.py --run-dir primary/evaluation/controls/gold
python primary/evaluation/portable/run_native.py --run-dir primary/evaluation/controls/incorrect
```

It prints a complete Docker command without launching it. Add `--execute` to run that command; outputs go into a fresh temporary directory and never overwrite retained reports. Use `--run-dir primary/evaluation/native/single_neutral-r101` for a candidate batch. The helper derives selective task IDs and execution settings from the original run metadata and uses the packaged data/source through the image. Generated code is isolated with the original network, privilege, user, memory, CPU, PID and filesystem restrictions. The fresh image name defaults to `fse2027-native-replay`.

Compare the two control reports task by task before interpreting candidate replay. The historical gold controls passed 987 tasks, failed 11 and timed out on 2; incorrect controls failed 998, passed 1 and timed out on 1. Their intersection defines 985 eligible tasks. Counts alone are insufficient to establish identical control-task membership. If reconstructed controls differ, report the task identities and environment difference; do not alter the original ledger or replace failed programs with canonical solutions.

## Verification boundary for the 3 October revision

All Dockerfile COPY sources exist in this package and the historical package/resource provenance is preserved. A fresh Docker build and new native execution were **not performed**: the Docker Desktop engine was unavailable. Statistical replay and candidate/report hash checks passed separately. Native equivalence, current availability of every historical dependency, OS-layer reproducibility, and hosted-model rerun remain unverified.
