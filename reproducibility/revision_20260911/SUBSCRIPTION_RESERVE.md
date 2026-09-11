# Author-requested subscription reserve

On 11 September 2026, while the main generation was running, the author required
work to stop when less than 55% of the subscription remained. The operational
guard stops at **55% remaining or below** (45% used or above), preserving the
boundary conservatively. This instruction takes priority over completing the
allocation without interruption. It is a spending constraint, not an
outcome-dependent stopping rule.

`subscription_guard.py` reads the documented
[Codex account rate-limit endpoint](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt)
through the same installed CLI (0.153.4) and subscription login. It sends only
initialization and `account/rateLimits/read`, with no thread or model turn,
reset-credit redemption, paid API call, or account change. Credentials and
account identifiers are not retained. The guard uses the authoritative `codex`
bucket and the smallest remaining percentage among its available primary and
secondary windows. The distinct, unused Spark quota is not the Luna quota.
Unknown or malformed main-quota readings close the gate.

The separate local watcher checks every 60 seconds. At the threshold it first
writes a persistent `PAUSED.json` in `reproducibility/runs/subscription_guard`,
then stops only the factorial or SCC dispatchers whose exact module and current
working directory match this checkout, together with their descendant
processes. It suspends each dispatcher before collecting descendants to prevent
new submissions during shutdown. It leaves independent native evaluators and
other Codex tasks alone. After a pause it checks for accidentally restarted
study generators every two seconds, without further quota requests.

This is a local polling guard, not a server-side reservation: it reacts to the
latest returned quota, and already transmitted work can have consumed quota
before a stop is observed. It cannot govern unrelated account usage.

Raw study files, submitted-attempt directories and frozen sources are never
edited by this guard. Forced termination may leave a frozen dispatch status or
lock stale and may interrupt at most the currently active assignments. Inspect
the actual processes and the separate pause record before any recovery; do not
infer liveness from a stale lock, invent completed rows, label the pause a
model-quality failure, or silently repeat submitted assignments. If a pause
actually occurs, disclose it and audit its affected records before analysis.
This operational amendment does not change task allocation, prompts, model,
reasoning setting, native tests, registered comparisons, or prior outcomes.

The author must explicitly authorize recovery from a latched pause. A quota
reset alone does not clear it. No automatic reset, model switch, paid fallback,
or fresh account can be used to evade the reserve. The existing thread heartbeat
contains the same rule, must stop model work and pause itself when the reserve
or latch is reached, and must not launch SCC while paused.

## Operation

Install `requirements-subscription-guard.txt` in the host Python environment.
Run the watcher once as a hidden local process from this checkout, retaining
its stdout and stderr. Do not launch a duplicate if `watch.lock` identifies a
live watcher. The initial deployed host uses Python 3.11 and psutil 7.1.3.

```text
python -m reproducibility.revision_20260911.subscription_guard watch
python -m reproducibility.revision_20260911.subscription_guard check
python -m reproducibility.revision_20260911.subscription_guard inventory
```

Before starting or resuming either study, confirm the actual watcher process,
its matching command and a recent `status.json`, then run `check`. A nonzero
exit forbids a launch. `check` alone is a read-only gate, not a process stopper.
Do not run new reviewer agents or continue model-driven editing at or below
the reserve. Local tests can finish without further model calls.

## Verification

Eighteen tests cover the correct quota bucket, both quota windows, missing and
invalid values, the exact threshold, failure-closed reads, the persistent pause,
and termination boundaries. The process integration test starts harmless
sleeping fixtures in two temporary checkouts and verifies that only the selected
parent and its child stop. It does not stop an experimental process. A separate
real read of the account endpoint agreed with the app's usage tool. No new model
request or experimental observation was made by these tests.

```text
python -m pytest reproducibility/revision_20260911/test_subscription_guard.py -q
```
