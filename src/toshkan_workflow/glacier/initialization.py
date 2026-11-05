"""Assemble already verified endpoint arrays; no reading of research files."""
import numpy as np

from .state import STATE_FIELDS


def assemble_initial_state(endpoint, initial_ice_volume_m3):
    """Return branch-major daily state, temperature profiles and balance memory.

    Input units and row order must already be verified by the caller.
    The two scenarios are alternatives, never additive.
    """
    ice = np.asarray(initial_ice_volume_m3, dtype=np.float64)
    if ice.ndim != 1 or not ice.size or not np.isfinite(ice).all() or (ice < 0).any():
        raise ValueError("expected a nonempty nonnegative volume vector in m3")
    count = ice.size
    state = {name: np.asarray(endpoint["state__" + name], dtype=np.float64).copy()
             for name in STATE_FIELDS}
    thermal = np.asarray(endpoint["thermal_temperature_c"], dtype=np.float64).copy()
    memory = np.asarray(endpoint["five_year_balance_memory_mm_we"], dtype=np.float64).copy()
    if (any(v.shape != (2, count) for v in state.values())
            or thermal.shape != (2, count, 10) or memory.shape != (2, count, 5)):
        raise ValueError("incompatible branch, band, temperature or history axes")
    state["ice_volume_m3"] = np.tile(ice, (2, 1))
    if (any(not np.isfinite(v).all() or (v < 0).any() for v in state.values())
            or not np.isfinite(thermal).all() or not np.isfinite(memory).all()):
        raise ValueError("invalid assembled state")
    return ({name: values.reshape(-1) for name, values in state.items()},
            thermal.reshape(2 * count, -1), memory.reshape(2 * count, 5))
