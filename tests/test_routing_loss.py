import unittest
from math import log
import numpy as np
import pandas as pd
from toshkan_workflow.glacier_replacement import (
    GLACIER_COMPONENTS, LAND_COMPONENTS, replace_daily_water,
)
from toshkan_workflow.routing_loss import route_replacement


class RoutingTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2000-02-28", periods=2)
        self.b = pd.DataFrame({"A": [100., 0.], "B": [0., 8.]}, index=dates)
        self.d = pd.DataFrame({"A": [-10., 0.], "B": [0., 4.]}, index=dates)
        self.w = pd.DataFrame({"A": [.5, .5], "B": [0., 1.]})

    def run_case(self, rate=log(2)):
        return route_replacement(self.b, self.d, self.w, loss_per_day=rate)

    def test_signed_budget_tail_and_units(self):
        r = self.run_case()
        np.testing.assert_allclose(r.delta_m3_day, [-5, -2.5, 2])
        np.testing.assert_allclose(r.total_m3_day, [45, 22.5, 6])
        np.testing.assert_allclose(r.mean_flow_m3_s, r.total_m3_day / 86400)
        self.assertEqual(r.index[-1], pd.Timestamp("2000-03-01"))
        self.assertAlmostEqual(102 - r.total_m3_day.sum(), 28.5)

    def test_direct_combination(self):
        expected = route_replacement(self.b + self.d, self.d * 0,
                                     self.w, loss_per_day=log(2))
        np.testing.assert_allclose(self.run_case().total_m3_day, expected.total_m3_day)

    def test_route_combined_when_signed_change_loses_small_residual(self):
        removed = dict.fromkeys(LAND_COMPONENTS, 0.)
        glacier = dict.fromkeys(GLACIER_COMPONENTS, 0.)
        removed["runoff_rain"] = 1e16
        glacier["rain_release"] = 1.
        volumes = replace_daily_water(1e16, removed, glacier, units="m3 water per day")
        self.assertEqual(1e16 + volumes["replacement_increment"], 0.)
        combined = pd.DataFrame({"A": [volumes["combined"]]}, index=self.b.index[:1])
        routed = route_replacement(combined, combined * 0, self.w[["A"]], loss_per_day=log(2))
        np.testing.assert_allclose(routed.total_m3_day, [.5, .25])

    def test_no_attenuation(self):
        np.testing.assert_allclose(self.run_case(0).total_m3_day, [45, 45, 12])

    def test_negative_total_rejected_in_arrival_tail(self):
        self.d.loc[self.d.index[-1], "B"] = -9.
        with self.assertRaisesRegex(ValueError, "negative total volume"):
            self.run_case(0)

    def test_exact_cancellation_is_valid(self):
        self.d = -self.b
        np.testing.assert_array_equal(self.run_case().total_m3_day, [0., 0., 0.])

    def test_alignment(self):
        for d in (self.d.iloc[::-1], self.d.iloc[:, ::-1]):
            with self.assertRaises(ValueError):
                route_replacement(self.b, d, self.w, loss_per_day=1)

    def test_bad_weights_and_rates(self):
        for w, rate in [(self.w * .5, 1), (self.w, -1), (self.w, np.nan),
                        (self.w.iloc[::-1], 1)]:
            with self.assertRaises(ValueError):
                route_replacement(self.b, self.d, w, loss_per_day=rate)
