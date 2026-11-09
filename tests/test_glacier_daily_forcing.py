import unittest

import numpy as np
import pandas as pd
from toshkan_workflow.preprocessing.glacier_daily_forcing import daily_forcing


class DailyForcingTests(unittest.TestCase):
    def setUp(self):
        self.hours = pd.date_range("2000-02-28", periods=72, freq="h")

    def run_case(self, t, p=None, hours=None, **changes):
        h = self.hours if hours is None else hours
        args = dict(offset_c=0, precipitation_multiplier=1, rain_start_c=-1,
                    rain_full_c=1, melt_threshold_c=0)
        return daily_forcing(h, t, np.ones(len(h)) if p is None else p,
                             **{**args, **changes})

    def test_phase_and_leap_day(self):
        result = self.run_case(np.repeat([-1, 0, 1], 24))
        self.assertEqual(result.index.day.tolist(), [28, 29, 1])
        np.testing.assert_equal(result.rain_input_mm.to_numpy(), [0, 12, 24])
        np.testing.assert_equal(result.snowfall_input_mm.to_numpy(), [24, 12, 0])

    def test_crossing_and_band_adjustment(self):
        t = np.tile([-2]*12 + [2]*12, 3)
        for offset, multiplier, expected in [(0, 1, [12, 12, 1, 0]),
                                             (-2, 2, [12, 36, 0, -2])]:
            r = self.run_case(t, offset_c=offset, precipitation_multiplier=multiplier)
            np.testing.assert_equal(r.to_numpy(), np.tile(expected, (3, 1)))

    def test_nonzero_melt_threshold(self):
        r = self.run_case(np.full(72, 4), melt_threshold_c=3)
        np.testing.assert_equal(r.positive_degree_days_c_day.to_numpy(), np.ones(3))

    def test_calendar_faults(self):
        for h in (self.hours.delete(12), self.hours[:12].append(self.hours[11:71]),
                  self.hours[1:25], self.hours.tz_localize("UTC")):
            with self.assertRaises(ValueError):
                self.run_case(np.ones(len(h)), hours=h)

    def test_invalid_inputs(self):
        for p, changes in [(np.full(72, -1), {}), (np.full(72, np.nan), {}),
                           (np.ones(72), {"rain_full_c": -1}),
                           (np.ones(72), {"precipitation_multiplier": -1}),
                           (np.ones(71), {})]:
            with self.assertRaises(ValueError):
                self.run_case(np.ones(72), p, **changes)
        with self.assertRaises(ValueError):
            self.run_case(pd.Series(np.ones(72), index=self.hours[::-1]))
