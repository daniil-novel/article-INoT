import unittest
from reproducibility.analyze_factorial import analyze, holm, ARMS


def rows(n=20):
    return [{'task_id':str(i),'arm':a,'seed':s,'resolved':True,'cost_usd':.01}
            for i in range(n) for a in ARMS for s in [17,43,101]]


class AnalysisTests(unittest.TestCase):
    def test_ceiling_bootstrap_cannot_establish_noninferiority(self):
        r=analyze(rows(),1000)
        self.assertEqual(r['quality_preservation']['decision'],'not_assessed')
        self.assertEqual(r['complete_tasks'],20)
        self.assertEqual(r['contrasts']['roles_single']['quality_ci95'],[0,0])
        self.assertIsNone(r['quality_preservation']['margin'])

    def test_missing_case_is_not_silently_removed(self):
        data=rows();data[0]['resolved']=None
        r=analyze(data,1000)
        self.assertEqual(r['status'],'incomplete')
        self.assertEqual(r['complete_tasks'],19)
        self.assertEqual(r['assigned_tasks'],20)
        self.assertEqual(r['missing_outcomes'],1)
        self.assertEqual(r['quality_preservation']['decision'],'not_assessed')

    def test_favorable_large_sample_cannot_invent_quality_or_money_criterion(self):
        data=rows(160)
        for x in data:
            x['resolved']=x['arm']=='single_roles'
            x['cost_usd']=.001 if x['arm']=='single_roles' else .01
        r=analyze(data,1000)
        self.assertEqual(r['quality_preservation']['decision'],'not_assessed')
        self.assertIsNone(r['quality_preservation']['margin'])
        self.assertEqual(r['monetary_superiority']['decision'],'not_assessed')
        self.assertEqual(r['analysis_role'],'legacy_exploratory_only')
        expected=holm([v['sign_flip_p'] for v in r['contrasts'].values()])
        self.assertEqual([v['holm_sign_flip_sensitivity_p'] for v in r['contrasts'].values()],expected)
        self.assertTrue(all('holm_p' not in v for v in r['contrasts'].values()))

    def test_factorial_interaction_is_difference_of_differences(self):
        data=rows()
        for x in data:x['resolved']=x['arm']=='single_roles'
        r=analyze(data,1000)
        self.assertEqual(r['contrasts']['interaction']['quality_difference'],1)
        self.assertEqual(r['cells']['single_neutral']['cost_per_resolved_task'],None)

    def test_holm_family(self):
        self.assertEqual(holm([.01,.04,.03]),[.03,.06,.06])


if __name__=='__main__':unittest.main()
