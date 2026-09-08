import unittest

from reproducibility.analyze_scale import ARMS, REPLICATES, summarize


def observations():
    return [{'task_id': task, 'arm': arm, 'replicate_id': rep,
             'analysis_status': 'pass' if task == 'a' else 'fail',
             'total_tokens': 100, 'api_equivalent_usd': .001,
             'uncached_sensitivity_usd': .002, 'format_extracted': True}
            for task in ('a', 'b') for arm in ARMS for rep in REPLICATES]


class RepeatedAnalysisTests(unittest.TestCase):
    def test_repeated_attempts_do_not_inflate_independent_sample(self):
        result = summarize(observations(), ['a', 'b'])
        contrast = result['paired_contrasts']['roles_minus_neutral_single']['quality']
        self.assertEqual(contrast['complete_task_clusters'], 2)
        self.assertEqual(contrast['descriptive_task_bootstrap_95_interval'], [0., 0.])
        self.assertEqual(result['by_arm'][0]['evaluable_only_rate'], .5)

    def test_one_missing_repeat_retains_denominator_but_removes_paired_cluster(self):
        rows = observations()
        next(r for r in rows if r['task_id'] == 'a' and r['arm'] == 'single_roles')['analysis_status'] = None
        result = summarize(rows, ['a', 'b'])
        role = next(g for g in result['by_arm'] if g['arm'] == 'single_roles')
        self.assertEqual(role['assigned_attempts'], 4)
        self.assertEqual((role['pessimistic_lower_bound'], role['optimistic_upper_bound']), (.25, .5))
        quality = result['paired_contrasts']['roles_minus_neutral_single']['quality']
        self.assertEqual(quality['complete_task_clusters'], 1)
        self.assertIsNone(quality['descriptive_task_bootstrap_95_interval'])

    def test_duplicate_candidate_is_not_an_extra_replicate(self):
        rows = observations()
        with self.assertRaises(ValueError):
            summarize(rows + [rows[0]], ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
