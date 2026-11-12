"""Small synthetic tests; no real geographic or observational data."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from toshkan_workflow.glacier import annual, aggregation, thermal
from toshkan_workflow.glacier.state import STATE_FIELDS

spec = importlib.util.spec_from_file_location(
    'annual_synthetic_example', Path(__file__).resolve().parents[1] / 'examples/glacier_annual_demo.py')
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


def equal_nested(a, b):
    if isinstance(a, np.ndarray):
        np.testing.assert_array_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            equal_nested(a[key], b[key])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for left, right in zip(a, b):
            equal_nested(left, right)
    elif isinstance(a, pd.DatetimeIndex):
        assert a.equals(b)
    else:
        assert a == b


class AnnualTests(unittest.TestCase):
    def test_full_year_and_input_preservation(self):
        kw = example.synthetic_inputs()
        saved = deepcopy(kw)
        result = annual.run_resumable_one_year_daily_cycle(**kw)
        equal_nested(kw, saved)
        d = result[3]
        self.assertEqual(d['day_count'], 365)
        self.assertTrue(d['calendar_year_complete'])
        self.assertEqual(len(d['annual_diagnostics']), 1)
        self.assertLess(d['maximum_relative_cycle_mass_closure'], 1e-10)
        self.assertEqual(result[2].shape, (2, 1))
        self.assertGreater(d['daily_sparse_grid_flux_m3']['total_release_mm'].sum(), 0.)

    def test_checkpoint_roundtrip_exact(self):
        kw = example.synthetic_inputs()
        left = annual.run_resumable_one_year_daily_cycle(**kw)
        right = annual.run_resumable_one_year_daily_cycle(**kw, checkpoint_roundtrip=True)
        equal_nested(left, right)
        checkpoint = annual.checkpoint_copy(left[3]['checkpoint_payload'])
        checkpoint['state__snow_mm_we'][0] += 1
        self.assertNotEqual(checkpoint['state__snow_mm_we'][0], left[3]['checkpoint_payload']['state__snow_mm_we'][0])

    def test_leap_year(self):
        result = annual.run_resumable_one_year_daily_cycle(**example.synthetic_inputs(2000))
        self.assertEqual(result[3]['day_count'], 366)
        self.assertEqual(result[3]['daily_sparse_grid_flux_m3']['total_release_mm'].shape, (366, 2))

    def test_explicit_partial_year_no_aging(self):
        kw = example.synthetic_inputs()
        kw['dates'] = kw['dates'][:120]
        kw['daily_forcing_by_support'] = {k: v[:120] for k,v in kw['daily_forcing_by_support'].items()}
        kw.update(expected_day_count=120, checkpoint_day_index=60, terminal_partial_year_end=kw['dates'][-1])
        result = annual.run_resumable_one_year_daily_cycle(**kw)
        self.assertTrue(result[3]['terminal_partial_year'])
        self.assertEqual(result[3]['annual_diagnostics'], [])
        self.assertEqual(result[2].shape, (2, 0))

    def test_calendar_rejects_gaps_and_undeclared_partial(self):
        dates = pd.date_range('2001-01-01', '2001-12-31')
        for invalid in (dates.delete(30), dates[:120], dates[::-1]):
            with self.assertRaises(ValueError):
                annual.validate_cycle_calendar(invalid, len(invalid), 60)

    def test_forcing_and_state_faults(self):
        for fault in ('negative_rain', 'nan_temperature', 'support_index', 'cold_mirror', 'missing_field'):
            kw = example.synthetic_inputs()
            if fault == 'negative_rain': kw['daily_forcing_by_support']['rain_input_mm'][0, 0] = -1
            if fault == 'nan_temperature': kw['daily_forcing_by_support']['mean_air_temperature_c'][0, 0] = np.nan
            if fault == 'support_index': kw['forcing_support_index'][0] = 2
            if fault == 'cold_mirror': kw['state']['cold_content_mm_we'][0] += 1
            if fault == 'missing_field': del kw['daily_forcing_by_support']['rain_input_mm']
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                annual.run_resumable_one_year_daily_cycle(**kw)

    def test_checkpoint_rejects_schema_and_negative_store(self):
        payload = annual.run_resumable_one_year_daily_cycle(**example.synthetic_inputs())[3]['checkpoint_payload']
        for fault in ('missing', 'negative'):
            broken = deepcopy(payload)
            if fault == 'missing': del broken['monthly_day_count']
            else: broken['state__ice_volume_m3'][0] = -1
            with self.assertRaises(ValueError): annual.checkpoint_npz_roundtrip(broken)

    def test_depth_volume_totals(self):
        kw = example.synthetic_inputs()
        d = annual.run_resumable_one_year_daily_cycle(**kw)[3]
        sparse = d['daily_sparse_grid_flux_m3']
        for field, depth in d['release_totals_mm'].items():
            np.testing.assert_allclose(sparse[field].sum(axis=0), depth * kw['area_m2'] / 1000., atol=1e-12)
        np.testing.assert_allclose(sparse['total_release_mm'], sum(sparse[k] for k in d['release_totals_mm']), atol=1e-12)

    def test_separate_alternatives_not_added(self):
        result = aggregation.aggregate_grid_flux_m3_day(
            np.array([1., 2.]), np.array([100., 100.]), np.array([0, 1]), np.array([0, 0]),
            trajectory_count=2, grid_count=1)
        np.testing.assert_array_equal(result, [[.1], [.2]])

    def test_sparse_exclusion_and_range(self):
        args = (np.array([1., 2.]), np.array([100., 100.]), np.array([0, -1]))
        np.testing.assert_array_equal(aggregation.aggregate_sparse_grid_flux_m3_day(*args, sparse_support_count=1), [.1])
        with self.assertRaises(ValueError):
            aggregation.aggregate_sparse_grid_flux_m3_day(args[0], args[1], np.array([0, 1]), sparse_support_count=1)

    def test_grid_ids_are_checked_before_conversion(self):
        for ids in ([0.9], [True], np.array([2**64 - 1], dtype=np.uint64)):
            with self.subTest(ids=ids):
                with self.assertRaises(ValueError):
                    aggregation.aggregate_sparse_grid_flux_m3_day([1.], [1000.], ids, sparse_support_count=1)
                for trajectory, grid in ((ids, [0]), ([0], ids)):
                    with self.assertRaises(ValueError):
                        aggregation.aggregate_grid_flux_m3_day([1.], [1000.], trajectory, grid,
                                                               trajectory_count=1, grid_count=1)

    def test_annual_entry_preserves_index_validation(self):
        for key in ("sparse_grid_support_index", "forcing_support_index",
                    "member_to_trajectory", "member_group_inverse"):
            inputs = example.synthetic_inputs()
            inputs[key] = inputs[key].astype(float) + 0.9
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "integer indices"):
                example.run_resumable_one_year_daily_cycle(**inputs)

    def test_thermal_debit_and_boundary(self):
        kw = example.synthetic_inputs()
        t, p = kw['thermal_temperature_c'], kw['thermal_parameters']
        capacity = thermal.thermal_capacity_mm_we(t, p)
        warmed, remaining = thermal.consume_refreezing_capacity_arrays(t, capacity / 2, p)
        np.testing.assert_allclose(warmed, t / 2)
        np.testing.assert_allclose(remaining, capacity / 2)
        with self.assertRaises(ValueError): thermal.consume_refreezing_capacity_arrays(t, capacity + 1, p)
        result, d = thermal.advance_monthly_conduction_arrays(
            t, np.array([-3., -3.]), 86400., kw['lower_boundary_mode'], kw['fixed_lower_temperature_c'], p)
        self.assertLessEqual(d['maximum_fourier_number'], .45)
        self.assertEqual(result[1, -1], -2.)
        with self.assertRaises(ValueError):
            thermal.advance_monthly_conduction_arrays(t, np.ones(2), 86400., kw['lower_boundary_mode'], kw['fixed_lower_temperature_c'], p)

    def test_nonwinter_does_not_conduct(self):
        kw = example.synthetic_inputs()
        t = kw['thermal_temperature_c']
        result, _, d = thermal.close_monthly_thermal_mass_arrays(
            t, np.zeros(2), np.full(2, 3.), np.full(2, -10.), 86400.,
            kw['lower_boundary_mode'], kw['fixed_lower_temperature_c'], kw['thermal_parameters'])
        np.testing.assert_array_equal(result, t)
        self.assertEqual(d['winter_state_count'], 0)

    def test_aging_both_registered_modes(self):
        for mode, fraction in [('AC01', None), ('AC02', .25)]:
            updated, diagnostic = thermal.apply_registered_balance_year_aging_arrays(
                np.array([4.]), np.array([8.]), np.array([100.]), np.array([1.]), np.ones((1, 4)),
                aging_candidate_id=mode, registered_firn_to_ice_fraction=fraction)
            self.assertEqual(updated['snow_mm_we'][0], 0.)
            self.assertEqual((updated['firn_mm_we'] + updated['ice_mm_we'])[0], 112.)
            self.assertEqual(diagnostic['maximum_absolute_mass_closure_mm_we'], 0.)
        with self.assertRaises(ValueError):
            thermal.apply_registered_balance_year_aging_arrays(
                np.ones(1), np.ones(1), np.ones(1), np.ones(1), np.zeros((1, 0)),
                aging_candidate_id='AC02', registered_firn_to_ice_fraction=.5)


if __name__ == '__main__':
    unittest.main()
