"""Synthetic reference checks only; no research files or model execution."""

import copy
import math
import unittest
from toshkan_workflow.daily_routing import route_daily
from toshkan_workflow.glacier_replacement import (
    GLACIER_COMPONENTS, LAND_COMPONENTS, replace_daily_water,
)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.args = [["2000-02-28", "2000-02-29"], {"a": [10, 20]},
                     {"a": [0.5, 0.5]}, {"a": "out"}]

    def run_case(self):
        return route_daily(*self.args, units="m3 water per day")

    def test_overlap_tail_and_leap_day(self):
        r = self.run_case()
        self.assertEqual(r["dates"], ["2000-02-28", "2000-02-29", "2000-03-01"])
        self.assertEqual(r["volume_m3_per_day"]["out"], [5, 15, 10])

    def test_conversion(self):
        self.args[1]["a"] = [86400, 0]
        self.args[2]["a"] = [1]
        self.assertEqual(self.run_case()["mean_flow_m3_per_second"]["out"], [1, 0])

    def test_multiple_sources_and_outlets(self):
        self.args[1].update(b=[4, 8], c=[3, 0])
        self.args[2].update(b=[1], c=[0, 0, 1])
        self.args[3].update(b="out", c="other")
        r = self.run_case()["volume_m3_per_day"]
        self.assertEqual(r, {"out": [9, 23, 10, 0], "other": [0, 0, 3, 0]})
        self.assertEqual(sum(map(sum, r.values())), 45)

    def test_dates(self):
        for dates in ([], ["2001-02-29"], ["20000101"],
                      ["2000-01-01", "2000-01-01"],
                      ["2000-01-01", "2000-01-03"],
                      ["2000-01-02", "2000-01-01"]):
            self.args[0] = dates
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                self.run_case()

    def test_source_alignment(self):
        self.args[3] = {"wrong": "out"}
        with self.assertRaises(ValueError):
            self.run_case()

    def test_length_and_units(self):
        with self.assertRaises(ValueError):
            route_daily(*self.args, units="mm/day")
        self.args[1]["a"] = [1]
        with self.assertRaises(ValueError):
            self.run_case()

    def test_invalid_weights(self):
        for weights in ([], [0.2], [-1, 2], [True], [math.nan], [math.inf]):
            self.args[2]["a"] = weights
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                self.run_case()

    def test_invalid_volumes(self):
        for value in (-1, True, math.nan, math.inf):
            self.args[1]["a"] = [value, 0]
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_case()

    def test_overflow(self):
        self.args[1].update(a=[1e308, 0], b=[1e308, 0])
        self.args[2].update(a=[1], b=[1])
        self.args[3]["b"] = "out"
        with self.assertRaises(ValueError):
            self.run_case()

    def test_zero_and_separate_calls(self):
        before = copy.deepcopy(self.args)
        first = self.run_case()
        self.assertEqual(before, self.args)
        self.args[1]["a"] = [0, 0]
        self.assertEqual(sum(self.run_case()["volume_m3_per_day"]["out"]), 0)
        self.assertEqual(sum(first["volume_m3_per_day"]["out"]), 30)

    def test_replacement_chain(self):
        volume = replace_daily_water(100, dict.fromkeys(LAND_COMPONENTS, 5),
            dict.fromkeys(GLACIER_COMPONENTS, 5), units="m3 water per day")["combined"]
        self.args[1]["a"] = [volume, 0]
        self.assertEqual(self.run_case()["volume_m3_per_day"]["out"], [45, 45, 0])

    def test_identifiers_and_empty_sources(self):
        for sources, kernels, outlets in (({}, {}, {}),
                ({"": [0, 0]}, {"": [1]}, {"": "out"}),
                ({"a": [0, 0]}, {"a": [1]}, {"a": ""})):
            with self.assertRaises(ValueError):
                route_daily(self.args[0], sources, kernels, outlets,
                            units="m3 water per day")

    def test_weights_not_renormalized(self):
        self.args[1]["a"] = [1, 0]
        self.args[2]["a"] = [1 - 5e-11]
        self.assertEqual(self.run_case()["volume_m3_per_day"]["out"][0], 1 - 5e-11)

    def test_independent_arrival_day_reference(self):
        volumes = [0.1, 2.7]
        weights = [0.2, 0.3, 0.5]
        self.args[1]["a"] = volumes
        self.args[2]["a"] = weights
        expected = [math.fsum(volumes[i] * weights[t-i]
                    for i in range(len(volumes)) if 0 <= t-i < len(weights))
                    for t in range(4)]
        actual = self.run_case()["volume_m3_per_day"]["out"]
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=14)
        self.assertAlmostEqual(math.fsum(actual), math.fsum(volumes), places=14)


if __name__ == "__main__":
    unittest.main()
