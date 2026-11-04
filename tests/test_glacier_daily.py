import unittest
import numpy as np
from toshkan_workflow.glacier import step_glacier_prepartitioned_daily_arrays as step
from toshkan_workflow.glacier.state import STATE_FIELDS, total_storage_mm_we_arrays


class DailyGlacierTests(unittest.TestCase):
    def setUp(self):
        self.state = {name: np.zeros(2) for name in STATE_FIELDS}
        self.state['ice_volume_m3'][:] = 10.
        self.kw = dict(rain_input_mm=np.zeros(2), snowfall_input_mm=np.zeros(2),
                       positive_degree_days_c_day=np.zeros(2), area_m2=np.full(2, 100.),
                       debris_fraction=np.zeros(2), snow_ddf=3., firn_ddf=4.,
                       clean_ice_ddf=6., debris_ice_ddf=2., liquid_holding_fraction=0.)

    def test_dry_identity(self):
        state, flux = step(self.state, **self.kw)
        for name in STATE_FIELDS:
            np.testing.assert_array_equal(state[name], self.state[name])
        np.testing.assert_allclose(flux['mass_closure_error_mm'], 0., atol=1e-12)

    def test_melt_sequence(self):
        self.state['snow_mm_we'][:] = 6
        self.state['firn_mm_we'][:] = 4
        self.kw['positive_degree_days_c_day'][:] = 4
        _, f = step(self.state, **self.kw)
        for key, value in [('snow_melt_mm', 6), ('firn_melt_mm', 4), ('ice_melt_mm', 6)]:
            np.testing.assert_allclose(f[key], value)

    def test_ice_limited_and_debris(self):
        self.kw['positive_degree_days_c_day'][:] = 1
        self.kw['debris_fraction'][:] = [0, 1]
        _, f = step(self.state, **self.kw)
        np.testing.assert_allclose(f['ice_melt_mm'], [6, 2])
        self.kw['positive_degree_days_c_day'][:] = 1000
        state, f = step(self.state, **self.kw)
        np.testing.assert_allclose(f['ice_melt_mm'], 90)
        np.testing.assert_allclose(state['ice_volume_m3'], 0)

    def test_refreeze_retention_release(self):
        self.state['cold_content_mm_we'][:] = 2
        self.state['snow_mm_we'][:] = 8
        self.kw['rain_input_mm'][:] = 5
        self.kw['liquid_holding_fraction'] = .1
        state, f = step(self.state, **self.kw)
        np.testing.assert_allclose(f['refrozen_mm'], 2)
        np.testing.assert_allclose(state['liquid_rain_mm_we'], 1)
        np.testing.assert_allclose(f['rain_release_mm'], 2)
        np.testing.assert_allclose(f['mass_closure_error_mm'], 0, atol=1e-12)

    def test_sublimation_limited(self):
        self.state['snow_mm_we'][:] = 2
        self.state['firn_mm_we'][:] = 3
        self.kw['sublimation_demand_mm_we'] = 20
        _, f = step(self.state, **self.kw)
        np.testing.assert_allclose(f['sublimated_mm'], 5)
        np.testing.assert_allclose(f['mass_closure_error_mm'], 0, atol=1e-12)

    def test_cold_capacity_not_water(self):
        baseline = total_storage_mm_we_arrays(self.state, np.full(2, 100.), 900.)
        self.state['cold_content_mm_we'][:] = 100
        np.testing.assert_array_equal(baseline, total_storage_mm_we_arrays(self.state, np.full(2, 100.), 900.))

    def test_inputs_unchanged(self):
        original = {k: v.copy() for k, v in self.state.items()}
        inputs = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in self.kw.items()}
        step(self.state, **self.kw)
        for k in original:
            np.testing.assert_array_equal(self.state[k], original[k])
        for k in inputs:
            np.testing.assert_array_equal(self.kw[k], inputs[k])

    def test_invalid_inputs(self):
        for key, value in [('area_m2', 0.), ('rain_input_mm', -1.), ('debris_fraction', 2.),
                           ('snow_ddf', 0.), ('liquid_holding_fraction', .3), ('rho_ice_kg_m3', float('nan'))]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    step(self.state, **dict(self.kw, **{key: value}))

    def test_bad_state_shape(self):
        self.state['snow_mm_we'] = np.zeros(3)
        with self.assertRaises(ValueError):
            step(self.state, **self.kw)


if __name__ == '__main__':
    unittest.main()
