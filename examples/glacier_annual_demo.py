"""Invented two-band annual example; no research inputs or external models."""
import numpy as np
import pandas as pd

from toshkan_workflow.glacier.annual import run_resumable_one_year_daily_cycle
from toshkan_workflow.glacier.geometry import (
    GeometryState, RegisteredDeltaHCoefficients, synchronize_multiyear_geometry,
)
from toshkan_workflow.glacier.state import STATE_FIELDS
from toshkan_workflow.glacier.thermal import ThermalArrayParameters, thermal_capacity_mm_we


def synthetic_inputs(year=2001, aging='AC01'):
    """All areas, weather and state values below are invented for this example."""
    dates = pd.date_range(f'{year}-01-01', f'{year}-12-31', freq='D')
    parameters = ThermalArrayParameters((500., 600., 700.), (10., 10., 10.), 2000., 334000., .3)
    thermal = np.full((2, 3), -2.)
    state = {name: np.zeros(2) for name in STATE_FIELDS}
    state['ice_volume_m3'] = np.array([200., 400.])
    state['snow_mm_we'][:] = 5.
    state['cold_content_mm_we'] = thermal_capacity_mm_we(thermal, parameters)
    summer = (dates.month >= 6) & (dates.month <= 8)
    rain = np.broadcast_to(np.where(summer, .4, 0.)[:, None], (len(dates), 2)).copy()
    snow = np.broadcast_to(np.where(summer, 0., .2)[:, None], rain.shape).copy()
    pdd = np.broadcast_to(np.where(summer, 1., 0.)[:, None], rain.shape).copy()
    temperature = np.broadcast_to(np.where(summer, 1., -3.)[:, None], rain.shape).copy()
    # PDD and phase are invented independently here, not derived from daily mean temperature.
    return dict(
        state=state, thermal_temperature_c=thermal,
        five_year_balance_memory_mm_we=np.zeros((2, 0)), dates=dates,
        daily_forcing_by_support=dict(rain_input_mm=rain, snowfall_input_mm=snow,
                                     positive_degree_days_c_day=pdd, mean_air_temperature_c=temperature),
        forcing_support_index=np.array([0, 1], dtype=np.int64),
        area_m2=np.array([100., 200.]), debris_fraction=np.array([0., .2]),
        member_group_inverse=np.array([0, 0], dtype=np.int64),
        member_to_trajectory=np.array([0], dtype=np.int64), trajectory_count=1,
        snow_ddf=3., firn_ddf=4., clean_ice_ddf=6., debris_ice_ddf=2.,
        liquid_holding_fraction=.05, sublimation_demand_mm_we=0.,
        lower_boundary_mode=np.array(['ZERO_FLUX', 'FIXED_TEMPERATURE']),
        fixed_lower_temperature_c=np.array([np.nan, -2.]), thermal_parameters=parameters,
        aging_candidate_id=aging, registered_firn_to_ice_fraction=None if aging == 'AC01' else .25,
        expected_day_count=len(dates), sparse_grid_support_index=np.array([0, 1], dtype=np.int64),
        sparse_grid_support_count=2,
    )


def main():
    inputs = synthetic_inputs()
    continuous = run_resumable_one_year_daily_cycle(**inputs)
    roundtrip = run_resumable_one_year_daily_cycle(**inputs, checkpoint_roundtrip=True)
    for name in STATE_FIELDS:
        np.testing.assert_array_equal(continuous[0][name], roundtrip[0][name])
    for index in (1, 2):
        np.testing.assert_array_equal(continuous[index], roundtrip[index])
    geometry = GeometryState((100., 200.), (0., 10.), (2., 12.))
    coefficients = RegisteredDeltaHCoefficients('small', 0., 1., 0., 0., 1., 1.)
    updated, _ = synchronize_multiyear_geometry(geometry, continuous[0]['ice_volume_m3'], coefficients)
    daily = continuous[3]['daily_sparse_grid_flux_m3']['total_release_mm']
    np.testing.assert_array_equal(daily, roundtrip[3]['daily_sparse_grid_flux_m3']['total_release_mm'])
    print(f'Synthetic annual calculation: {len(inputs["dates"])} days; {daily.shape[1]} separate grid supports')
    print('Checkpoint serialization roundtrip: identical states and daily releases')
    print(f'Synthetic total release: {daily.sum():.6f} m3 water')
    print(f'Updated synthetic surfaces: {updated.surface_elevation_m}')
    print('No external restart, multiyear remapping, VIC or RVIC execution is demonstrated.')


if __name__ == '__main__':
    main()
