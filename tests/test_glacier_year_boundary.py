import unittest

import numpy as np

from toshkan_workflow.glacier import geometry as g
from toshkan_workflow.glacier.initialization import assemble_initial_state
from toshkan_workflow.glacier.state import STATE_FIELDS


class StartTests(unittest.TestCase):
    def setUp(self):
        self.endpoint = {"state__" + n: np.arange(6.).reshape(2, 3) for n in STATE_FIELDS}
        self.endpoint.update(thermal_temperature_c=-np.arange(60.).reshape(2, 3, 10),
                             five_year_balance_memory_mm_we=-np.arange(30.).reshape(2, 3, 5))
        self.ice = [21., 22., 23.]

    def test_order_and_no_alias(self):
        state, t, m = assemble_initial_state(self.endpoint, self.ice)
        for n in STATE_FIELDS:
            np.testing.assert_array_equal(state[n], self.ice * 2 if n == "ice_volume_m3" else np.arange(6.))
            self.assertFalse(np.shares_memory(state[n], self.endpoint["state__" + n]))
        for x, key, width in [(t, "thermal_temperature_c", 10), (m, "five_year_balance_memory_mm_we", 5)]:
            np.testing.assert_array_equal(x, self.endpoint[key].reshape(6, width))
            self.assertFalse(np.shares_memory(x, self.endpoint[key]))

    def test_invalid_inputs(self):
        for ice in [[], [1.], [1., -1., 2.], [np.nan] * 3]:
            with self.assertRaises(ValueError):
                assemble_initial_state(self.endpoint, ice)
        for k, x in [("thermal_temperature_c", np.zeros((3, 2, 10))),
                     ("state__snow_mm_we", -np.ones((2, 3))),
                     ("five_year_balance_memory_mm_we", np.full((2, 3, 5), np.inf))]:
            with self.assertRaises(ValueError):
                assemble_initial_state(dict(self.endpoint, **{k: x}), self.ice)


class AnnualGeometryTests(unittest.TestCase):
    def check(self, beds, thickness, target, route, c=1., allow=False):
        geo = g.GeometryState((1.,) * len(beds), tuple(beds),
                              tuple(a + b for a, b in zip(beds, thickness)))
        curve = g.RegisteredDeltaHCoefficients("small", 0., 1., 0., 0., c, 1.)
        out, d = g.synchronize_multiyear_geometry(geo, target, curve,
            allow_terminal_zero_weight_residual_local_mass_balance=allow)
        self.assertEqual(d["route"], route)
        self.assertEqual(out.band_area_m2, geo.band_area_m2)
        self.assertAlmostEqual(out.volume_m3, sum(target), places=5)
        self.assertFalse(d["unregistered_footprint_created"])
        self.assertTrue(all(h >= 0 for h in out.thickness_m))
        return out

    def test_regular(self):
        self.check([0, 10], [2, 2], [1, 2], g.RETREAT_ROUTE)
        self.check([0, 10], [2, 2], [2, 2], g.NEUTRAL_ROUTE)
        raised = self.check([0, 10], [2, 0], [2, 1], g.POSITIVE_ROUTE)
        self.assertEqual(raised.thickness_m, (2., 1.))

    def test_terminal_and_extinction(self):
        self.check([0], [2], [1], g.TERMINAL_ROUTE)
        self.check([0], [2], [0], g.EXTINCTION_ROUTE)

    def test_degenerate_elevation(self):
        with self.assertRaises(RuntimeError):
            self.check([0, 0], [2, 2], [1, 1], None)
        self.check([0, 0], [2, 2], [1, 1], g.TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE, allow=True)

    def test_zero_weight_hold(self):
        with self.assertRaises(RuntimeError):
            self.check([0, 10], [2, 2], [0, 1], None, c=0.)
        self.check([0, 10], [2, 2], [0, 1], g.TERMINAL_ZERO_WEIGHT_ROUTE, c=0., allow=True)

    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):
            self.check([0], [-1], [1], None)
        with self.assertRaises(ValueError):
            self.check([0], [1], [-1], None)
