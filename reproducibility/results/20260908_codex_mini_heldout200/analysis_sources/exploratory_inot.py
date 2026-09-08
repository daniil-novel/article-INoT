"""Descriptive paired INoT contrasts, kept outside the four primary tests."""
import argparse
import json
from pathlib import Path
import numpy as np
from .. import codex_subscription as c
from .analyze import bootstrap_mean


def compare(primary, baseline, assigned):
    ids = set(assigned)
    if len(ids) != len(assigned):
        raise ValueError('Duplicate task allocation')
    p = {}; b = {}
    for r in primary:
        key = (r['task_id'], r['arm'])
        if key in p or r['task_id'] not in ids or r['arm'] not in c.ARMS or r['replicate_id'] != 4:
            raise ValueError('Unexpected primary record')
        p[key] = r
    for r in baseline:
        if r['task_id'] in b or r['task_id'] not in ids or r['arm'] != 'inot_algorithm_replication' or r['replicate_id'] != 5:
            raise ValueError('Unexpected INoT record')
        b[r['task_id']] = r
    results = {}
    for arm in ('direct', 'single_roles'):
        contrasts = {}
        for metric in ('quality', 'total_tokens', 'api_equivalent_usd', 'uncached_sensitivity_usd'):
            pairs = []
            for task in assigned:
                a, z = b.get(task), p.get((task, arm))
                if a is None or z is None:
                    continue
                if metric == 'quality':
                    if a['analysis_status'] is None or z['analysis_status'] is None:
                        continue
                    pair = (int(a['analysis_status'] == 'pass'), int(z['analysis_status'] == 'pass'))
                else:
                    if a.get(metric) is None or z.get(metric) is None:
                        continue
                    pair = (a[metric], z[metric])
                pairs.append(pair)
            differences = [a-z for a, z in pairs]
            result = {'complete_task_pairs': len(pairs),
                      'mean_paired_difference': float(np.mean(differences)) if pairs else None,
                      'descriptive_task_bootstrap_95_interval': bootstrap_mean(differences)}
            if metric == 'quality':
                result.update(inot_only_passes=sum(a == 1 and z == 0 for a, z in pairs),
                              comparator_only_passes=sum(a == 0 and z == 1 for a, z in pairs))
            else:
                denominator = sum(z for _, z in pairs)
                result['ratio_of_paired_means'] = sum(a for a, _ in pairs)/denominator if denominator else None
            contrasts[metric] = result
        results['inot_minus_'+arm] = contrasts
    return {'scope': 'Exploratory cross-batch comparisons, outside the four primary tests; no confirmatory p-values or non-inferiority inference',
            'timing_and_cache_confounding': True, 'task_clusters_assigned': len(assigned),
            'paired_contrasts': results, 'bootstrap_resamples': 10000, 'analysis_seed': 20260908}


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('primary', 'inot', 'selection', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists(): raise ValueError('Refuse to overwrite analysis')
    c.save(a.out, compare(read_rows(a.primary), read_rows(a.inot), c.read(a.selection)['assigned_task_ids']))
