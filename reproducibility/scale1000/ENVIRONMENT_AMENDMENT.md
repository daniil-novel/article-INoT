# Pre-generation dependency amendment

The first full 1000-task gold run in bcb-segregation80:v3 returned 949 passes,
49 failures and two timeouts. It completed before any scale1000 model call.
Many failures were missing-library import errors. The complete first gold and
incorrect control runs remain under controls-v1 and are not rewritten.

The new image bcb-scale1000:v1 adds the missing libraries listed in
environment/requirements.txt, primarily using exact versions from the pinned
upstream Requirements/requirements-eval.txt. Related Flask extensions are
included because a missing initial Flask import can hide their absence.
scikit-image 0.21.0 is used instead of the upstream 0.18.0 pin to support the
existing Python 3.11 runtime. Existing NumPy 1.26.4, SciPy 1.10.1 and NLTK
3.8.1 contracts are retained. Tk and libsndfile runtime libraries are added.
The complete installed package freeze and container identity are recorded by
each native control attempt; the image build log is retained separately.

Both control programs must be rerun for all 1000 tasks in controls-v2 before
generation. Tests, reference code, task prompts and task IDs are unchanged.
Offline networking, upstream restrictions on subprocess execution and native
resource limits remain unchanged. Failures requiring external services or
changed assertions are not made successful by editing benchmark behavior.
The final eligibility count, not the intended 1000 allocation, determines
the available quality task clusters. Every assigned candidate remains scheduled.

The second complete gold attempt returned 986 passes, 12 failures and two
timeouts. Task /227 revealed the next missing dependency, librosa, after the
soundfile import was repaired. Before any model generation, the separate
environment-v2 layer adds upstream librosa 0.10.1 with compatible pinned
Numba/LLVM and audio dependencies. Its base is the unchanged bcb-scale1000:v1
image; the resulting bcb-scale1000:v2 image identity is
sha256:afeb8d78b76f6a7b1fbf427d78a55bd35dbfcf58387711b47f8a8ba00e16b580.
Offline imports confirm librosa 0.10.1, NumPy 1.26.4, SciPy 1.10.1,
soundfile 0.12.1 and Numba 0.58.1. Both full 1000-task controls are repeated
as controls-v3; earlier control attempts and environment sources remain
unchanged. No generated-model success rate informed either amendment.

The third gold control completed with 987 passes, 11 failures and two
timeouts. Task /227 now passes. The remaining gold non-pass IDs are /14,
/101, /111, /176, /205, /276, /314, /363, /459, /460, /590, /1012 and /1028;
none is a missing-library import failure. They remain in the full assignment
and raw native outcomes. Final quality eligibility additionally requires the
completed incorrect control to fail, as recorded in the final gate.

The final incorrect control returned 998 failures, one pass (/272) and one
timeout (/1038). The final gate therefore contains 985 quality-eligible
task clusters: 195 of the prior 200 and 790 of the fresh 800. All 1000 tasks
remain scheduled in all five conditions and all three new repeats.
