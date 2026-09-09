"""Post-review identification bounds; no model calls or changes to frozen analyses."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'reproducibility/results/20260908_codex_mini_heldout200/analysis/candidate_records.jsonl'
raw = SOURCE.read_bytes()
records = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
lookup = {(r['task_id'], r['arm']): r for r in records}
assert len(lookup) == len(records) == 996
tasks = {r['task_id'] for r in records}
excluded = {r['task_id'] for r in records if r['analysis_status'] is None}
eligible = tasks - excluded
assert len(tasks) == 200 and len(eligible) == 193
assert all(r['analysis_status'] is None for r in records if r['task_id'] in excluded)

contrasts = {
    'SR-SN': ('single_roles', 'single_neutral'),
    'MR-MN': ('multi_roles', 'multi_neutral'),
    'MN-SN': ('multi_neutral', 'single_neutral'),
    'MR-SR': ('multi_roles', 'single_roles'),
}


def interval(task, arm):
    r = lookup.get((task, arm))
    if r is None or r['analysis_status'] is None:
        return (0, 1)
    assert r['analysis_status'] in ('pass', 'fail', 'timeout')
    value = int(r['analysis_status'] == 'pass')
    return (value, value)


def bounds(sample, a, b):
    lower = upper = missing = 0
    for task in sorted(sample):
        lo_a, hi_a = interval(task, a)
        lo_b, hi_b = interval(task, b)
        lower += lo_a - hi_b
        upper += hi_a - lo_b
        missing += int(lo_a != hi_a or lo_b != hi_b)
    n = len(sample)
    return {'task_count': n, 'tasks_with_unobserved_endpoint': missing,
            'lower_difference_pp': 100 * lower / n,
            'upper_difference_pp': 100 * upper / n}


results = {}
for name, (a, b) in contrasts.items():
    observed_successes = lambda arm: sum(interval(t, arm)[0] for t in eligible)
    results[name] = {
        'eligible_tasks': bounds(eligible, a, b),
        'all_assigned_tasks': bounds(tasks, a, b),
        'eligible_generation_unavailable_counted_as_failure_difference_pp':
            100 * (observed_successes(a) - observed_successes(b)) / len(eligible),
    }

payload = {
    'analysis_timing': 'Post hoc, after five scientific reviews; not predeclared and not in the reviewed PDF.',
    'source': str(SOURCE.relative_to(HERE.parents[1])).replace('\\', '/'),
    'source_sha256': hashlib.sha256(raw).hexdigest(),
    'interpretation': 'Finite-sample binary-outcome identification bounds, not confidence intervals or evidence of non-inferiority. Unknown endpoints range independently over {0,1}; no assumptions about missingness. The 200-task analysis also treats control-ineligible endpoints as unknown. Failure mapping is a separate operational estimand restricted to 193 control-eligible tasks, not retroactive ITT preregistration.',
    'contrasts': results,
}
(HERE / 'missingness-bounds.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results, indent=2))
