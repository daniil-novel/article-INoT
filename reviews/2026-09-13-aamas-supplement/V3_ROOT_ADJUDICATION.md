# V3 anonymous-primary candidate: unresolved portability

13 September 2026. The packaging agent reported a rebuilt candidate of
17,745,787 bytes, with 98,240 TAR members. Its latest rebuild had not been
moved-extracted and fully replayed when that report was delivered. Do not
release the candidate or label it a complete portable research archive.

The preceding moved extraction at `E:/Temp/aamas-v3-final/decoded` passed its
own byte inventory. Full replay then rejected the pricing sidecar, and the
source-family verifier reported a missing nested evidence manifest. A later
rebuild added that manifest; the older successful byte check does not verify
the later rebuilt ZIP.

Coordinator inspection found a deeper cause of the pricing failure: the
generation index reconstructs 26,968 prompts and 26,936 result JSON files,
but zero raw `events.jsonl` streams. The original verified primary archive
contains 26,968 event files. Its registered collector also requires argv,
status and standard-error records. Adding a pricing sidecar alone therefore
cannot make this candidate pass the full frozen raw reconstruction.

The candidate retains full response texts, but that fact is narrower than
complete raw transport evidence. Neither its basic four-contrast calculation
nor its byte check establishes the full raw/native/resource/source replay.
The broad redaction helper also requires an explicit preservation audit;
its claim of field-specific transformation is not accepted as demonstrated.

The original complete primary research archive and its earlier full replay
remain valid. This failure is in the proposed anonymous packaging, not evidence
of changed primary experimental results. Further packaging work must preserve
the validation scope and disclose its exact contents rather than removing
checks to obtain a passing message.
