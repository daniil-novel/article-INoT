import pytest
from reproducibility.heldout200.exploratory_inot import compare


def row(task, arm, status, tokens):
    return {'task_id': task, 'arm': arm, 'replicate_id': 5 if arm == 'inot_algorithm_replication' else 4,
            'analysis_status': status, 'total_tokens': tokens,
            'api_equivalent_usd': tokens/1e6, 'uncached_sensitivity_usd': tokens/1e5}


def test_missing_cells_are_excluded_pairwise_but_keep_allocation():
    primary = [row('a','direct','pass',10), row('b','direct','fail',40), row('c','direct',None,100)]
    baseline = [row('a','inot_algorithm_replication','fail',20), row('c','inot_algorithm_replication',None,50)]
    out = compare(primary,baseline,['a','b','c'])
    q = out['paired_contrasts']['inot_minus_direct']['quality']
    tokens = out['paired_contrasts']['inot_minus_direct']['total_tokens']
    assert out['task_clusters_assigned'] == 3
    assert q['complete_task_pairs'] == 1 and q['mean_paired_difference'] == -1
    assert q['inot_only_passes'] == 0 and q['comparator_only_passes'] == 1
    assert tokens['complete_task_pairs'] == 2
    assert tokens['ratio_of_paired_means'] == pytest.approx(70/110)
    assert out['paired_contrasts']['inot_minus_single_roles']['quality']['mean_paired_difference'] is None
    assert 'p_value' not in q


def test_duplicate_or_wrong_treatment_cannot_enter_exploratory_comparison():
    b = row('a','inot_algorithm_replication','pass',10)
    with pytest.raises(ValueError): compare([], [b,b], ['a'])
    with pytest.raises(ValueError): compare([], [row('a','direct','pass',10)], ['a'])
