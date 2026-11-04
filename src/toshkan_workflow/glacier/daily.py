#!/usr/bin/env python3
"""Mass-conserving daily glacier step using prepartitioned hourly forcing sums."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .state import (
    FLUX_FIELDS,
    STATE_FIELDS,
    total_storage_mm_we_arrays,
)


def _state_arrays(values: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {name: np.asarray(values[name], dtype=np.float64) for name in STATE_FIELDS}
    shape = result[STATE_FIELDS[0]].shape
    if not shape or any(value.shape != shape for value in result.values()):
        raise ValueError("daily glacier state arrays must share one nonempty shape")
    if any(not np.isfinite(value).all() or (value < 0.0).any() for value in result.values()):
        raise ValueError("daily glacier state values must be finite and nonnegative")
    return result


def step_glacier_prepartitioned_daily_arrays(
    state: Mapping[str, np.ndarray],
    *,
    rain_input_mm: np.ndarray,
    snowfall_input_mm: np.ndarray,
    positive_degree_days_c_day: np.ndarray,
    area_m2: np.ndarray,
    debris_fraction: np.ndarray,
    snow_ddf: float,
    firn_ddf: float,
    clean_ice_ddf: float,
    debris_ice_ddf: float,
    liquid_holding_fraction: float,
    rho_ice_kg_m3: float = 900.0,
    cold_content_gain_mm_we: float = 0.0,
    sublimation_demand_mm_we: float = 0.0,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Advance one day after hourly rain/snow partition and PDD aggregation.

    Rain, snowfall and positive-degree days must be calculated from the original
    hourly forcing. This function deliberately does not infer phase from a daily
    mean temperature.
    """
    current = _state_arrays(state)
    shape = current[STATE_FIELDS[0]].shape
    area = np.broadcast_to(np.asarray(area_m2, dtype=np.float64), shape)
    rain = np.broadcast_to(np.asarray(rain_input_mm, dtype=np.float64), shape)
    snowfall = np.broadcast_to(np.asarray(snowfall_input_mm, dtype=np.float64), shape)
    pdd = np.broadcast_to(np.asarray(positive_degree_days_c_day, dtype=np.float64), shape).copy()
    debris = np.broadcast_to(np.asarray(debris_fraction, dtype=np.float64), shape)
    scalar = np.asarray([
        snow_ddf, firn_ddf, clean_ice_ddf, debris_ice_ddf,
        liquid_holding_fraction, rho_ice_kg_m3, cold_content_gain_mm_we,
        sublimation_demand_mm_we,
    ], dtype=np.float64)
    if (
        not np.isfinite(scalar).all()
        or not np.isfinite(area).all()
        or not np.isfinite(rain).all()
        or not np.isfinite(snowfall).all()
        or not np.isfinite(pdd).all()
        or not np.isfinite(debris).all()
        or (area <= 0.0).any()
        or (rain < 0.0).any()
        or (snowfall < 0.0).any()
        or (pdd < 0.0).any()
        or (debris < 0.0).any()
        or (debris > 1.0).any()
        or min(snow_ddf, firn_ddf, clean_ice_ddf, debris_ice_ddf) <= 0.0
        or not 0.0 <= liquid_holding_fraction <= 0.2
        or rho_ice_kg_m3 <= 0.0
        or cold_content_gain_mm_we < 0.0
        or sublimation_demand_mm_we < 0.0
    ):
        raise ValueError("invalid prepartitioned daily glacier input or parameter")

    initial_storage = total_storage_mm_we_arrays(current, area, rho_ice_kg_m3)
    snow = current["snow_mm_we"] + snowfall
    firn = current["firn_mm_we"].copy()
    snow_loss = np.minimum(snow, sublimation_demand_mm_we)
    remaining_sublimation = sublimation_demand_mm_we - snow_loss
    firn_loss = np.minimum(firn, remaining_sublimation)
    snow -= snow_loss
    firn -= firn_loss
    sublimated = snow_loss + firn_loss

    snow_melt = np.minimum(snow, snow_ddf * pdd)
    snow -= snow_melt
    pdd -= snow_melt / snow_ddf
    firn_melt = np.minimum(firn, firn_ddf * np.maximum(pdd, 0.0))
    firn -= firn_melt
    pdd -= firn_melt / firn_ddf

    effective_ice_ddf = clean_ice_ddf * (1.0 - debris) + debris_ice_ddf * debris
    old_ice_we = current["ice_volume_m3"] * rho_ice_kg_m3 / area
    ice_melt = np.minimum(old_ice_we, effective_ice_ddf * np.maximum(pdd, 0.0))
    ice_volume_loss = ice_melt / 1000.0 * area * 1000.0 / rho_ice_kg_m3
    ice_volume = np.maximum(current["ice_volume_m3"] - ice_volume_loss, 0.0)

    liquid_components = np.stack((
        current["liquid_rain_mm_we"] + rain,
        current["liquid_snow_mm_we"] + snow_melt,
        current["liquid_firn_mm_we"] + firn_melt,
        current["liquid_ice_mm_we"] + ice_melt,
    ))
    liquid_total = liquid_components.sum(axis=0)
    cold_content = current["cold_content_mm_we"] + cold_content_gain_mm_we
    refrozen = np.minimum(liquid_total, cold_content)
    liquid_after_refreezing = liquid_total - refrozen
    cold_content -= refrozen
    firn += refrozen

    refreeze_factor = np.divide(
        liquid_after_refreezing,
        liquid_total,
        out=np.zeros_like(liquid_total),
        where=(liquid_total > 0.0) & (liquid_after_refreezing > 0.0),
    )
    after_refreeze = liquid_components * np.clip(refreeze_factor, 0.0, 1.0)
    holding_capacity = liquid_holding_fraction * (snow + firn)
    retained_total = np.minimum(liquid_after_refreezing, holding_capacity)
    retained_factor = np.divide(
        retained_total,
        liquid_after_refreezing,
        out=np.zeros_like(retained_total),
        where=(liquid_after_refreezing > 0.0) & (retained_total > 0.0),
    )
    retained = after_refreeze * np.clip(retained_factor, 0.0, 1.0)
    released = after_refreeze - retained

    updated = {
        "snow_mm_we": np.maximum(snow, 0.0),
        "firn_mm_we": np.maximum(firn, 0.0),
        "ice_volume_m3": ice_volume,
        "liquid_rain_mm_we": retained[0],
        "liquid_snow_mm_we": retained[1],
        "liquid_firn_mm_we": retained[2],
        "liquid_ice_mm_we": retained[3],
        "cold_content_mm_we": np.maximum(cold_content, 0.0),
    }
    final_storage = total_storage_mm_we_arrays(updated, area, rho_ice_kg_m3)
    closure = initial_storage + rain + snowfall - final_storage - released.sum(axis=0) - sublimated
    fluxes = {
        "rain_input_mm": rain,
        "snowfall_input_mm": snowfall,
        "snow_melt_mm": snow_melt,
        "firn_melt_mm": firn_melt,
        "ice_melt_mm": ice_melt,
        "refrozen_mm": refrozen,
        "sublimated_mm": sublimated,
        "rain_release_mm": released[0],
        "snow_release_mm": released[1],
        "firn_release_mm": released[2],
        "ice_release_mm": released[3],
        "mass_closure_error_mm": closure,
    }
    if set(fluxes) != set(FLUX_FIELDS):
        raise RuntimeError("daily glacier flux schema differs from hourly kernel")
    return updated, fluxes
