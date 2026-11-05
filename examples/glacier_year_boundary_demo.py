"""Invented two-band geometry and two alternative starting states."""
import numpy as np

from toshkan_workflow.glacier.geometry import (
    GeometryState, RegisteredDeltaHCoefficients, synchronize_multiyear_geometry,
)
from toshkan_workflow.glacier.initialization import assemble_initial_state
from toshkan_workflow.glacier.state import STATE_FIELDS


def main():
    geometry = GeometryState((10., 20.), (0., 10.), (2., 12.))
    endpoint = {"state__" + name: np.zeros((2, 2)) for name in STATE_FIELDS}
    endpoint["state__snow_mm_we"][1] = [3., 4.]
    endpoint["thermal_temperature_c"] = np.full((2, 2, 10), -1.)
    endpoint["five_year_balance_memory_mm_we"] = np.zeros((2, 2, 5))
    ice = np.multiply(geometry.band_area_m2, geometry.thickness_m)
    state, _, _ = assemble_initial_state(endpoint, ice)
    print("Starting ice (m3) in each alternative:", state["ice_volume_m3"].reshape(2, 2))
    # Invented year-end targets, not the output of a simulated year.
    curve = RegisteredDeltaHCoefficients("small", 0., 1., 0., 0., 1., 1.)
    next_geometry, diagnostics = synchronize_multiyear_geometry(geometry, [15., 30.], curve)
    print("One scenario: initial and year-end volume (m3):", geometry.volume_m3,
          next_geometry.volume_m3, diagnostics["route"])


if __name__ == "__main__":
    main()
