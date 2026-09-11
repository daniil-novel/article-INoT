# Retained BigCodeBench source

`bigcodebench-v0.1.4.jsonl` is the exact 1,140-row source snapshot used by the
frozen allocation and native controls. Its SHA-256 is
`f6704a124f4edcec9d12cc7912f41f3d4207f51b87f091d136e3436f7e25149f`.
The snapshot is distributed with its original instructions, reference programs,
and tests. It is not generated study output and must not be sent to the model:
the generation manifests separately identify the allowed prompt/context inputs.

Upstream: [BigCodeBench dataset](https://huggingface.co/datasets/bigcode/bigcodebench),
version v0.1.4, by the BigCodeBench authors. The dataset card declares Apache-2.0
(checked 11 September 2026); the license is retained in
[BIGCODEBENCH-LICENSE.txt](BIGCODEBENCH-LICENSE.txt).
See the [benchmark paper](https://arxiv.org/abs/2406.15877) for construction.

`bigcodebench-split/prepare_manifest.json` preserves the original source split
and byte hashes. Neither retained file has been regenerated or normalized for
this publication. They support complete offline source-overlap replay;
publication adds no tasks to the study and changes no evaluation contract.
