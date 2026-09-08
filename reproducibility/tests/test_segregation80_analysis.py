from reproducibility.segregation80.analyze import summarize,holm


def test_holm_primary_family_and_missingness():
    assert holm({'a':.01,'b':.02})=={'a':.02,'b':.02}
    ids=[str(i) for i in range(80)]
    rows=[]
    for t in ids:
        for a in ('role_boundary','neutral_boundary','role_prose','neutral_prose'):
            rows.append({'task_id':t,'arm':a,'quality':None if t=='0' else a.startswith('role'),
                         'total_tokens':100,'api_equivalent_usd':.1,'uncached_sensitivity_usd':.12})
    result=summarize(rows,ids)
    contrast=result['contrasts']['role_boundary_minus_neutral_boundary']
    assert contrast['quality_pairs']==79
    assert contrast['wins']==79 and contrast['losses']==0
    assert contrast['holm_p']<.05
    assert contrast['total_tokens']['pairs']==80
    assert 'exact_two_sided_mcnemar_p' not in result['contrasts']['boundary_minus_prose_role']
    assert result['by_arm'][0]['assigned_rate_bounds']==[79/80,1]
