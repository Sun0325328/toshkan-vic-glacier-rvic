"""Synthetic source conversion and routing compatibility checks."""

import copy
import unittest
from toshkan_workflow.preprocessing import prepare_source_volumes
from toshkan_workflow.daily_routing import route_daily


class SourceMappingTests(unittest.TestCase):
    def setUp(self):
        self.daily = {"dates": ["2000-02-28", "2000-02-29"],
                      "depths_mm_per_day": {"g": [1, 2]}, "units": "mm/day"}
        self.mapping = [{"source_id": "s", "grid_id": "g", "m3_per_mm": 100}]

    def test_conversion_and_independent_calls(self):
        before = copy.deepcopy((self.daily, self.mapping))
        self.assertEqual(prepare_source_volumes(self.daily, self.mapping)["source_volumes"], {"s": [100, 200]})
        self.assertEqual(before, (self.daily, self.mapping))
        self.mapping[0]["m3_per_mm"] = 50
        self.assertEqual(prepare_source_volumes(self.daily, self.mapping)["source_volumes"], {"s": [50, 100]})

    def test_split_grid(self):
        self.mapping = [{"source_id": s, "grid_id": "g", "m3_per_mm": factor}
                        for s, factor in [("left", 40), ("right", 60)]]
        values = prepare_source_volumes(self.daily, self.mapping)["source_volumes"]
        self.assertEqual(values, {"left": [40, 80], "right": [60, 120]})
        self.assertEqual(sum(map(sum, values.values())), 300)

    def test_mapping_integrity(self):
        for mapping in ([], self.mapping*2, [{"source_id": "s", "grid_id": "missing", "m3_per_mm": 100}],
                        [{"source_id": "", "grid_id": "g", "m3_per_mm": 100}],
                        [{"source_id": "s", "grid_id": "g", "area": 100}]):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                prepare_source_volumes(self.daily, mapping)
        self.daily["depths_mm_per_day"]["unused"] = [1, 2]
        with self.assertRaises(ValueError):
            prepare_source_volumes(self.daily, self.mapping)

    def test_factors(self):
        for value in (0, -1, True, float("nan"), float("inf")):
            self.mapping[0]["m3_per_mm"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare_source_volumes(self.daily, self.mapping)
        self.mapping[0]["m3_per_mm"] = 1e308
        with self.assertRaises(ValueError):
            prepare_source_volumes(self.daily, self.mapping)

    def test_revalidate_daily(self):
        for change in ({"units": "mm"}, {"dates": ["2000-02-28", "2000-03-01"]},
                       {"depths_mm_per_day": {"g": [1]}}, {"depths_mm_per_day": {"g": [-1, 2]}},
                       {"depths_mm_per_day": {}}, {"dates": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_source_volumes(dict(self.daily, **change), self.mapping)

    def test_routing_chain_and_source_match(self):
        prepared = prepare_source_volumes(self.daily, self.mapping)
        routed = route_daily(**prepared, kernels={"s": [0.5, 0.5]}, outlets={"s": "out"})
        self.assertEqual(routed["volume_m3_per_day"]["out"], [50, 150, 100])
        self.assertEqual(routed["dates"][-1], "2000-03-01")
        self.assertAlmostEqual(sum(routed["mean_flow_m3_per_second"]["out"])*86400, 300)
        with self.assertRaises(ValueError):
            route_daily(**prepared, kernels={"wrong": [1]}, outlets={"s": "out"})


if __name__ == "__main__":
    unittest.main()
