"""Small synthetic checks; no model execution or research data access."""

import unittest
from toshkan_workflow.glacier_replacement import (
    GLACIER_COMPONENTS, LAND_COMPONENTS, replace_daily_water,
)


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.removed = dict.fromkeys(LAND_COMPONENTS, 5)
        self.glacier = dict.fromkeys(GLACIER_COMPONENTS, 5)

    def run_case(self, baseline=100, units="m3 water per day"):
        return replace_daily_water(baseline, self.removed, self.glacier, units=units)

    def test_negative_increment_is_valid(self):
        result = self.run_case()
        self.assertEqual(result["replacement_increment"], -10)
        self.assertEqual(result["combined"], 90)
        self.assertEqual(result["combined"] + result["removed"], 120)

    def test_component_sum_reference(self):
        for scale in (0, 0.1, 1, 1000):
            self.glacier = dict.fromkeys(GLACIER_COMPONENTS, scale)
            values = list(self.glacier.values()) + list(self.removed.values())
            expected = sum(values[:4]) - sum(values[4:])
            self.assertEqual(self.run_case()["replacement_increment"], expected)

    def test_small_release_after_full_removal(self):
        self.removed = dict.fromkeys(LAND_COMPONENTS, 0)
        self.removed["runoff_rain"] = 1e16
        self.glacier = dict.fromkeys(GLACIER_COMPONENTS, 0)
        self.glacier["ice_release"] = 1
        self.assertEqual(self.run_case(1e16)["combined"], 1)

    def test_units(self):
        with self.assertRaises(ValueError):
            self.run_case(units="mm/day")

    def test_schema(self):
        self.removed["extra"] = 0
        with self.assertRaises(ValueError):
            self.run_case()

    def test_invalid_values(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_case(baseline=value)

    def test_removed_exceeds_baseline(self):
        with self.assertRaises(ValueError):
            self.run_case(baseline=29)

    def test_missing_component(self):
        del self.glacier["ice_release"]
        with self.assertRaises(ValueError):
            self.run_case()

    def test_component_values_and_overflow(self):
        for value in (-1, float("nan"), float("inf"), True):
            self.glacier["ice_release"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_case()
        self.glacier = dict.fromkeys(GLACIER_COMPONENTS, 1e308)
        with self.assertRaises(ValueError):
            self.run_case()

    def test_zero_and_complete_replacement(self):
        self.removed = dict.fromkeys(LAND_COMPONENTS, 0)
        self.glacier = dict.fromkeys(GLACIER_COMPONENTS, 0)
        self.assertEqual(self.run_case(0)["combined"], 0)
        self.removed["runoff_rain"] = 100
        self.assertEqual(self.run_case()["combined"], 0)

    def test_independent_calls_and_input_immutability(self):
        before = (self.removed.copy(), self.glacier.copy())
        first = self.run_case()
        second = replace_daily_water(200, self.removed, self.glacier,
                                     units="m3 water per day")
        self.assertEqual(first["combined"], 90)
        self.assertEqual(second["combined"], 190)
        self.assertEqual(before, (self.removed, self.glacier))


if __name__ == "__main__":
    unittest.main()
