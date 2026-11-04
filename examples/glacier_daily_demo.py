"""Synthetic single-day example, not a basin simulation."""
import numpy as np
from toshkan_workflow.glacier import step_glacier_prepartitioned_daily_arrays
from toshkan_workflow.glacier.state import STATE_FIELDS

state = {name: np.zeros(1) for name in STATE_FIELDS}
state['snow_mm_we'][:] = 6
state['firn_mm_we'][:] = 4
state['ice_volume_m3'][:] = 10
updated, flux = step_glacier_prepartitioned_daily_arrays(
    state, rain_input_mm=np.array([2.]), snowfall_input_mm=np.array([0.]),
    positive_degree_days_c_day=np.array([4.]), area_m2=np.array([100.]),
    debris_fraction=np.array([0.]), snow_ddf=3., firn_ddf=4.,
    clean_ice_ddf=6., debris_ice_ddf=2., liquid_holding_fraction=0.,
)
release_mm = sum(flux[name + '_release_mm'] for name in ('rain', 'snow', 'firn', 'ice'))
release_m3 = release_mm * 100. / 1000.
np.testing.assert_allclose(release_m3, [1.8])
print('Synthetic release (m3 water per day):', release_m3.tolist())
print('Mass residual (mm water equivalent):', flux['mass_closure_error_mm'].tolist())
