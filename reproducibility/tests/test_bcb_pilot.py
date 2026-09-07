import unittest
from reproducibility.bcb_pilot_evaluator import analysis_outcome, quality_summary


class PilotQualityTests(unittest.TestCase):
    def test_reference_or_negative_control_failure_is_missing(self):
        for gold, negative in [('fail', 'fail'), ('timeout', 'fail'), ('pass', 'pass')]:
            controls = {'gold': {'status': gold}, 'incorrect': {'status': negative}}
            self.assertIsNone(analysis_outcome('pass', controls))

    def test_unknown_prediction_is_not_an_observed_failure(self):
        controls = {'gold': {'status': 'pass'}, 'incorrect': {'status': 'fail'}}
        for value in [None, 'unknown', 'evaluator_error', 'new-status']:
            self.assertIsNone(analysis_outcome(value, controls))
        self.assertEqual(analysis_outcome('timeout', controls), 'timeout')

    def test_bounds_preserve_missing_and_assigned_denominator(self):
        records = [{'task_id': str(i), 'control': 'prediction', 'analysis_status': s}
                   for i, s in enumerate(['pass', 'fail', None])]
        result = quality_summary(records, ['0', '1', '2'])
        self.assertEqual(result['denominator'], 3)
        self.assertEqual(result['evaluable_tasks'], 2)
        self.assertEqual(result['evaluable_only_rate'], .5)
        self.assertEqual(result['pessimistic_lower_bound'], 1/3)
        self.assertEqual(result['optimistic_upper_bound'], 2/3)
        with self.assertRaises(ValueError): quality_summary(records[:-1], ['0', '1', '2'])
        with self.assertRaises(ValueError): quality_summary([records[0]] * 3, ['0', '1', '2'])


if __name__ == '__main__': unittest.main()
