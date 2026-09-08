"""Component-wise usage inventory without zero-filling missing turn counters."""
from .. import codex_subscription as c


def summarize_turns(inventory, usage_key='observed_usage'):
    usages=[r[usage_key] for r in inventory if r.get(usage_key) is not None]
    for u in usages:
        for key in ('input_tokens','cached_input_tokens','output_tokens'):
            if type(u.get(key)) is not int or u[key]<0:raise ValueError('Invalid usage component')
        if u['cached_input_tokens']>u['input_tokens']:raise ValueError('Cached input exceeds input')
    valued=[u for u in usages if u.get('cache_write_input_tokens',0)==0]
    components={key:sum(u[key] for u in usages) for key in ('input_tokens','cached_input_tokens','output_tokens')}
    reasoning=[u['reasoning_output_tokens'] for u in usages if u.get('reasoning_output_tokens') is not None]
    return {'submitted_turns':len(inventory),'turns_with_usage':len(usages),'turns_without_usage':len(inventory)-len(usages),
            'turns_without_supported_valuation':len(inventory)-len(valued),**components,
            'known_total_tokens':components['input_tokens']+components['output_tokens'],
            'turns_with_reasoning_subset':len(reasoning),'known_reasoning_output_subset':sum(reasoning),
            'known_api_equivalent_usd':sum(c.value_usage(u) for u in valued),
            'known_uncached_sensitivity_usd':sum((u['input_tokens']*.75+u['output_tokens']*4.5)/1e6 for u in valued),
            'interpretation':'Observed usage only; cached input and reasoning output are subsets; unknown usage is not zero; valuation is not a subscription invoice'}
