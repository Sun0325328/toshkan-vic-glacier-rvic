"""State schema and water-equivalent storage accounting."""
from __future__ import annotations
from typing import Mapping
import numpy as np


STATE_FIELDS = (
    "snow_mm_we",
    "firn_mm_we",
    "ice_volume_m3",
    "liquid_rain_mm_we",
    "liquid_snow_mm_we",
    "liquid_firn_mm_we",
    "liquid_ice_mm_we",
    "cold_content_mm_we",
)


FLUX_FIELDS = (
    "rain_input_mm",
    "snowfall_input_mm",
    "snow_melt_mm",
    "firn_melt_mm",
    "ice_melt_mm",
    "refrozen_mm",
    "sublimated_mm",
    "rain_release_mm",
    "snow_release_mm",
    "firn_release_mm",
    "ice_release_mm",
    "mass_closure_error_mm",
)


def _arrays(values: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {name: np.asarray(values[name], dtype=np.float64) for name in STATE_FIELDS}
    shape = result[STATE_FIELDS[0]].shape
    if not shape or any(value.shape != shape for value in result.values()):
        raise ValueError("vector glacier state arrays must share one nonempty shape")
    if any(not np.isfinite(value).all() or (value < 0.0).any() for value in result.values()):
        raise ValueError("vector glacier state values must be finite and nonnegative")
    return result


def total_storage_mm_we_arrays(
    state: Mapping[str, np.ndarray], area_m2: np.ndarray, rho_ice_kg_m3: float
) -> np.ndarray:
    values = _arrays(state)
    area = np.broadcast_to(np.asarray(area_m2, dtype=np.float64), values[STATE_FIELDS[0]].shape)
    if not np.isfinite(area).all() or (area <= 0.0).any() or rho_ice_kg_m3 <= 0.0:
        raise ValueError("invalid vector glacier area or ice density")
    liquid = sum(values[name] for name in STATE_FIELDS[3:7])
    ice_mm = values["ice_volume_m3"] * float(rho_ice_kg_m3) / area
    return values["snow_mm_we"] + values["firn_mm_we"] + ice_mm + liquid
