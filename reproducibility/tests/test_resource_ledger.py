import pytest
from reproducibility.heldout200.resource_ledger import summarize_turns


def test_subsets_and_unknown_usage_are_not_double_counted():
    out=summarize_turns([{'observed_usage':{'input_tokens':1000,'cached_input_tokens':600,'output_tokens':100,'reasoning_output_tokens':40}}, {'observed_usage':None}])
    assert out['known_total_tokens']==1100
    assert out['known_api_equivalent_usd']==pytest.approx((400*.75+600*.075+100*4.5)/1e6)
    assert out['known_uncached_sensitivity_usd']==pytest.approx(.0012)
    assert out['turns_without_usage']==1 and out['turns_with_reasoning_subset']==1


def test_unsupported_cache_write_keeps_tokens_but_withholds_valuation():
    out=summarize_turns([{'observed_usage':{'input_tokens':100,'cached_input_tokens':0,'output_tokens':10,'cache_write_input_tokens':20}}])
    assert out['known_total_tokens']==110
    assert out['turns_without_usage']==0
    assert out['turns_without_supported_valuation']==1
    assert out['known_api_equivalent_usd']==0
