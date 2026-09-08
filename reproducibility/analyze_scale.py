"""Descriptive task-cluster analysis for a predeclared repeated development matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np

from .codex_subscription import ARMS, read, save

REPLICATES = (2, 3)
CONTRASTS = {
    'roles_minus_neutral_single': ('single_roles', 'single_neutral'),
    'roles_minus_neutral_multi': ('multi_roles', 'multi_neutral'),
    'multi_minus_single_neutral': ('multi_neutral', 'single_neutral'),
    'multi_minus_single_roles': ('multi_roles', 'single_roles'),
    'single_neutral_minus_direct': ('single_neutral', 'direct'),
    'multi_roles_minus_direct': ('multi_roles', 'direct'),
}


def bootstrap_mean(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return None
    rng = np.random.default_rng(20260908)
    means = values[rng.integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
    return np.quantile(means, [.025, .975]).tolist()


def summarize(records, ids):
    """Inputs must already be reconciled with full traces and native test reports."""
    expected = {(task, arm, rep) for task in ids for arm in ARMS for rep in REPLICATES}
    indexed = {}
    for r in records:
        key = (r['task_id'], r['arm'], r['replicate_id'])
        if key not in expected or key in indexed:
            raise ValueError('Unexpected or duplicate assignment')
        if r['analysis_status'] not in ('pass', 'fail', 'timeout', None):
            raise ValueError('Unrecognized quality status must be classified upstream')
        indexed[key] = r
    n = len(ids) * len(REPLICATES)
    groups = []
    for arm in ARMS:
        rows = [r for key, r in indexed.items() if key[1] == arm]
        observed = [r for r in rows if r['analysis_status'] is not None]
        passed = sum(r['analysis_status'] == 'pass' for r in observed)
        valued = [r for r in rows if r.get('total_tokens') is not None]
        groups.append({'arm': arm, 'assigned_attempts': n, 'recorded_attempts': len(rows),
                       'evaluable_attempts': len(observed), 'passes': passed,
                       'evaluable_only_rate': passed / len(observed) if observed else None,
                       'pessimistic_lower_bound': passed / n,
                       'optimistic_upper_bound': (passed + n - len(observed)) / n,
                       'format_extraction_failures': sum(r.get('format_extracted') is False for r in rows),
                       'resource_observed_attempts': len(valued),
                       **{f'mean_{metric}': float(np.mean([r[metric] for r in valued])) if valued else None
                          for metric in ('total_tokens', 'api_equivalent_usd', 'uncached_sensitivity_usd')}})

    def complete_task_values(task, arms, metric):
        result = {}
        for arm in arms:
            values = []
            for rep in REPLICATES:
                r = indexed.get((task, arm, rep))
                if r is None:
                    return None
                if metric == 'quality':
                    if r['analysis_status'] is None:
                        return None
                    values.append(float(r['analysis_status'] == 'pass'))
                else:
                    if r.get(metric) is None:
                        return None
                    values.append(r[metric])
            result[arm] = float(np.mean(values))
        return result

    contrasts = {}
    for name, (a, b) in CONTRASTS.items():
        outcome = {}
        for metric in ('quality', 'total_tokens', 'api_equivalent_usd', 'uncached_sensitivity_usd'):
            pairs = [v for task in ids if (v := complete_task_values(task, (a, b), metric)) is not None]
            differences = [v[a] - v[b] for v in pairs]
            entry = {'complete_task_clusters': len(pairs),
                     'mean_paired_difference': float(np.mean(differences)) if pairs else None,
                     'descriptive_task_bootstrap_95_interval': bootstrap_mean(differences)}
            if metric != 'quality':
                denominator = sum(v[b] for v in pairs)
                entry['ratio_of_paired_means'] = sum(v[a] for v in pairs) / denominator if denominator else None
            outcome[metric] = entry
        contrasts[name] = outcome
    factorial = ('single_neutral', 'single_roles', 'multi_neutral', 'multi_roles')
    interactions = [v['multi_roles'] - v['multi_neutral'] - v['single_roles'] + v['single_neutral']
                    for task in ids if (v := complete_task_values(task, factorial, 'quality')) is not None]
    return {'scope': 'descriptive development extension; no confirmatory significance or non-inferiority claim',
            'task_clusters_assigned': len(ids), 'replicate_ids': list(REPLICATES),
            'assigned_attempts': len(expected), 'recorded_attempts': len(records), 'by_arm': groups,
            'paired_contrasts': contrasts,
            'quality_interaction': {'complete_task_clusters': len(interactions),
                                    'mean_difference_of_differences': float(np.mean(interactions)) if interactions else None,
                                    'descriptive_task_bootstrap_95_interval': bootstrap_mean(interactions)},
            'uncertainty': '10000 task-cluster percentile bootstrap resamples, seed 20260908; exploratory intervals',
            'missingness_bounds': 'assignment-denominator ranges, not confidence intervals',
            'resource_totals_for_recorded_candidates': {
                metric: sum(r[metric] for r in records if r.get(metric) is not None)
                for metric in ('total_tokens', 'api_equivalent_usd', 'uncached_sensitivity_usd')},
            'incomplete_attempt_usage': 'Accounted separately in the complete submitted-turn inventory; candidate totals alone omit unfinished cells'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records', required=True, type=Path)
    p.add_argument('--manifest', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    records = [json.loads(line) for line in a.records.read_text(encoding='utf-8').splitlines()]
    save(a.out, summarize(records, read(a.manifest)['assigned_task_ids']))
