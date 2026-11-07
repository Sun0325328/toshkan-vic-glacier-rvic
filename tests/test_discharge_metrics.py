import math
import unittest

import numpy as np
from toshkan_workflow.evaluation import compute_accuracy_metrics as score


class DischargeMetricsTests(unittest.TestCase):
    def test_perfect_match(self):
        s = score([1, 2, 3], [1, 2, 3])
        for name in ("KGE_2012_modified", "KGE_2009", "NSE", "Pearson_r"):
            self.assertAlmostEqual(s[name], 1.)
        self.assertEqual(s["RMSE_m3s"], 0.)

    def test_double_flow(self):
        s = score([1, 2, 3], [2, 4, 6])
        self.assertAlmostEqual(s["KGE_2012_modified"], 0.)
        self.assertAlmostEqual(s["KGE_2009"], 1 - math.sqrt(2))
        self.assertAlmostEqual(s["NSE"], -6.)
        self.assertAlmostEqual(s["RMSE_m3s"], math.sqrt(14/3))
        self.assertEqual(s["MAE_m3s"], 2.)
        self.assertEqual(s["PBIAS_percent"], 100.)
        self.assertEqual(s["volume_bias_percent"], 100.)

    def test_pairwise_exclusion(self):
        s = score([1, np.nan, 2, 3, 4], [1, 99, 2, 3, np.inf])
        self.assertEqual(s["paired_count"], 3)
        self.assertEqual(s["MAE_m3s"], 0.)

    def test_small_sample(self):
        s = score([1, 2], [1, 2])
        self.assertEqual(s["paired_count"], 2)
        self.assertTrue(all(math.isnan(v) for k, v in s.items() if k != "paired_count"))

    def test_constant_and_zero_flow(self):
        s = score([0]*3, [1]*3)
        for name in ("NSE", "Pearson_r", "PBIAS_percent", "KGE_2009", "KGE_2012_modified"):
            self.assertTrue(math.isnan(s[name]))
        self.assertEqual(s["MAE_m3s"], 1.)

    def test_shape_mismatch(self):
        with self.assertRaises(RuntimeError): score([1, 2, 3], [1, 2])
