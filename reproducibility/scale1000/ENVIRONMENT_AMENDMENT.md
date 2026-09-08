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
