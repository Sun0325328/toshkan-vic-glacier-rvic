"""One-year daily execution with monthly thermal and year-end aging updates."""
from __future__ import annotations
from io import BytesIO
from typing import Mapping
import numpy as np
import pandas as pd
from .daily import step_glacier_prepartitioned_daily_arrays
from .thermal import (MASS_TOLERANCE_MM_WE, ThermalArrayParameters,
    apply_registered_balance_year_aging_arrays, close_monthly_thermal_mass_arrays, thermal_capacity_mm_we)
from .state import STATE_FIELDS, total_storage_mm_we_arrays
from .aggregation import _integer_indices, aggregate_sparse_grid_flux_m3_day


CHECKPOINT_DAY_COUNT = 365


CHECKPOINT_ARRAY_FIELDS = (
    *("state__" + name for name in STATE_FIELDS),
    "thermal_temperature_c",
    "five_year_balance_memory_mm_we",
    "monthly_refrozen_mm_we",
    "monthly_melt_mm_we",
    "monthly_temperature_sum_c",
    "release_rain_mm",
    "release_snow_mm",
    "release_firn_mm",
    "release_ice_mm",
    "precipitation_total_mm",
    "sublimation_total_mm",
    "cycle_initial_storage_mm_we",
    "year_start_storage_mm_we",
)


def validate_checkpoint_payload(payload: Mapping[str, np.ndarray]) -> int:
    """Validate the exact day-183 resumable-array checkpoint contract."""
    required = {"day_index", "monthly_day_count", *CHECKPOINT_ARRAY_FIELDS}
    if set(payload) != required:
        raise ValueError("canary checkpoint schema mismatch")
    day = np.asarray(payload["day_index"])
    month_days = np.asarray(payload["monthly_day_count"])
    if day.shape != (1,) or month_days.shape != (1,):
        raise ValueError("checkpoint scalar arrays must have shape (1,)")
    day_index = int(day[0])
    monthly_day_count = int(month_days[0])
    if not 1 <= day_index < CHECKPOINT_DAY_COUNT:
        raise ValueError("checkpoint day index is outside the one-year window")
    if not 0 <= monthly_day_count <= 31:
        raise ValueError("checkpoint monthly day count is invalid")

    state_arrays = {
        name: np.asarray(payload["state__" + name], dtype=np.float64)
        for name in STATE_FIELDS
    }
    state_count = len(state_arrays[STATE_FIELDS[0]])
    if state_count == 0 or any(values.shape != (state_count,) for values in state_arrays.values()):
        raise ValueError("checkpoint mass-state shape mismatch")
    if any(not np.isfinite(values).all() or (values < 0.0).any() for values in state_arrays.values()):
        raise ValueError("checkpoint mass state must be finite and nonnegative")

    profiles = np.asarray(payload["thermal_temperature_c"], dtype=np.float64)
    memory = np.asarray(payload["five_year_balance_memory_mm_we"], dtype=np.float64)
    if (
        profiles.ndim != 2 or profiles.shape[0] != state_count
        or profiles.shape[1] < 3 or not np.isfinite(profiles).all()
        or (profiles > 1.0e-12).any()
        or memory.ndim != 2 or memory.shape[0] != state_count
        or memory.shape[1] > 5 or not np.isfinite(memory).all()
    ):
        raise ValueError("checkpoint thermal or aging-memory shape failed")

    vector_fields = set(CHECKPOINT_ARRAY_FIELDS) - {
        *("state__" + name for name in STATE_FIELDS),
        "thermal_temperature_c", "five_year_balance_memory_mm_we",
    }
    for name in vector_fields:
        values = np.asarray(payload[name], dtype=np.float64)
        if values.shape != (state_count,) or not np.isfinite(values).all():
            raise ValueError("checkpoint accumulator shape failed: " + name)
        if name != "monthly_temperature_sum_c" and (values < 0.0).any():
            raise ValueError("checkpoint accumulator is negative: " + name)
    return state_count


def checkpoint_copy(payload: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Return a validated deep copy suitable for atomic NPZ materialization."""
    validate_checkpoint_payload(payload)
    copied = {name: np.asarray(values).copy() for name, values in payload.items()}
    validate_checkpoint_payload(copied)
    return copied


def checkpoint_npz_roundtrip(
    payload: Mapping[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Round-trip a checkpoint through the same compressed NPZ representation."""
    validate_checkpoint_payload(payload)
    buffer = BytesIO()
    np.savez_compressed(buffer, **payload)
    buffer.seek(0)
    with np.load(buffer, allow_pickle=False) as source:
        restored = {name: np.asarray(source[name]).copy() for name in source.files}
    validate_checkpoint_payload(restored)
    return restored


def _member_envelope(
    values_mm: np.ndarray,
    area_m2: np.ndarray,
    member_group_inverse: np.ndarray,
    member_to_trajectory: np.ndarray,
    trajectory_count: int,
) -> np.ndarray:
    group_count = len(member_to_trajectory)
    grouped = np.bincount(
        member_group_inverse,
        weights=np.asarray(values_mm, dtype=np.float64) * area_m2 / 1000.0,
        minlength=group_count,
    )
    result = np.empty((trajectory_count, 3), dtype=np.float64)
    for trajectory in range(trajectory_count):
        selected = grouped[member_to_trajectory == trajectory]
        if len(selected) == 0:
            raise RuntimeError("daily member envelope has an empty trajectory")
        result[trajectory] = (
            float(selected.min()), float(np.median(selected)), float(selected.max())
        )
    return result


def validate_cycle_calendar(
    dates: pd.DatetimeIndex,
    expected_day_count: int,
    checkpoint_day_index: int,
    terminal_partial_year_end: pd.Timestamp | str | None = None,
) -> bool:
    """Validate a full calendar year or one explicitly registered terminal year."""
    if not isinstance(dates, pd.DatetimeIndex) or len(dates) == 0:
        raise ValueError("one-year dates or checkpoint index failed")
    if dates.tz is not None or dates.hasnans or not dates.equals(dates.normalize()):
        raise ValueError("expected timezone-naive midnight dates without missing values")
    contiguous = dates.equals(pd.date_range(dates[0], periods=len(dates), freq="D"))
    starts_on_january_first = dates[0].month == 1 and dates[0].day == 1
    single_year = dates[0].year == dates[-1].year
    full_calendar_year = (
        expected_day_count in {365, 366}
        and dates[-1].month == 12 and dates[-1].day == 31
    )
    terminal_partial_year = False
    if terminal_partial_year_end is not None:
        declared_end = pd.Timestamp(terminal_partial_year_end)
        terminal_partial_year = (
            declared_end.tzinfo is None
            and declared_end == dates[-1]
            and declared_end.year == dates[0].year
            and declared_end < pd.Timestamp(declared_end.year, 12, 31)
            and dates.equals(pd.date_range(
                pd.Timestamp(declared_end.year, 1, 1), declared_end, freq="D"
            ))
        )
    if (
        len(dates) != expected_day_count or not contiguous
        or not starts_on_january_first or not single_year
        or not (full_calendar_year or terminal_partial_year)
        or not 1 <= checkpoint_day_index < len(dates)
    ):
        raise ValueError("one-year dates or checkpoint index failed")
    return terminal_partial_year


def run_resumable_one_year_daily_cycle(
    state: dict[str, np.ndarray],
    thermal_temperature_c: np.ndarray,
    five_year_balance_memory_mm_we: np.ndarray,
    dates: pd.DatetimeIndex,
    daily_forcing_by_support: dict[str, np.ndarray],
    forcing_support_index: np.ndarray,
    *,
    area_m2: np.ndarray,
    debris_fraction: np.ndarray,
    member_group_inverse: np.ndarray,
    member_to_trajectory: np.ndarray,
    trajectory_count: int,
    snow_ddf: float,
    firn_ddf: float,
    clean_ice_ddf: float,
    debris_ice_ddf: float,
    liquid_holding_fraction: float,
    sublimation_demand_mm_we: float,
    lower_boundary_mode: np.ndarray,
    fixed_lower_temperature_c: np.ndarray,
    thermal_parameters: ThermalArrayParameters,
    aging_candidate_id: str,
    registered_firn_to_ice_fraction: float | None,
    checkpoint_day_index: int = 183,
    checkpoint_roundtrip: bool = False,
    expected_day_count: int = CHECKPOINT_DAY_COUNT,
    terminal_partial_year_end: pd.Timestamp | str | None = None,
    rho_ice_kg_m3: float = 900.0,
    sparse_grid_support_index: np.ndarray | None = None,
    sparse_grid_support_count: int | None = None,
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, dict[str, object]]:
    """Run a full year or an explicitly registered terminal partial year."""
    terminal_partial_year = validate_cycle_calendar(
        dates, expected_day_count, checkpoint_day_index, terminal_partial_year_end
    )
    current = {
        name: np.asarray(state[name], dtype=np.float64).copy() for name in STATE_FIELDS
    }
    state_count = len(current[STATE_FIELDS[0]])
    if (
        set(current) != set(STATE_FIELDS) or state_count == 0
        or any(values.shape != (state_count,) for values in current.values())
        or any(not np.isfinite(values).all() or (values < 0.0).any() for values in current.values())
    ):
        raise ValueError("one-year mass-state schema failed")
    area = np.asarray(area_m2, dtype=np.float64)
    debris = np.asarray(debris_fraction, dtype=np.float64)
    support_index = _integer_indices(forcing_support_index)
    modes = np.asarray(lower_boundary_mode, dtype=str)
    fixed = np.asarray(fixed_lower_temperature_c, dtype=np.float64)
    group_inverse = _integer_indices(member_group_inverse)
    group_to_trajectory = _integer_indices(member_to_trajectory)
    if (
        any(values.shape != (state_count,) for values in (
            area, debris, support_index, modes, fixed, group_inverse,
        ))
        or not np.isfinite(area).all() or (area <= 0.0).any()
        or not np.isfinite(debris).all() or ((debris < 0.0) | (debris > 1.0)).any()
        or group_inverse.min(initial=0) < 0
        or group_inverse.max(initial=-1) >= len(group_to_trajectory)
        or group_to_trajectory.shape == (0,)
        or group_to_trajectory.min(initial=0) < 0
        or group_to_trajectory.max(initial=-1) >= trajectory_count
    ):
        raise ValueError("one-year state metadata failed")
    required_forcing = {
        "rain_input_mm", "snowfall_input_mm", "positive_degree_days_c_day",
        "mean_air_temperature_c",
    }
    forcing = {
        name: np.asarray(values, dtype=np.float64)
        for name, values in daily_forcing_by_support.items()
    }
    if set(forcing) != required_forcing:
        raise ValueError("one-year forcing schema failed")
    support_count = forcing["rain_input_mm"].shape[1]
    if (
        any(values.shape != (len(dates), support_count) for values in forcing.values())
        or not all(np.isfinite(values).all() for values in forcing.values())
        or support_index.min(initial=0) < 0
        or support_index.max(initial=-1) >= support_count
    ):
        raise ValueError("one-year forcing support failed")
    thermal = np.asarray(thermal_temperature_c, dtype=np.float64).copy()
    memory = np.asarray(five_year_balance_memory_mm_we, dtype=np.float64).copy()
    if (
        thermal.ndim != 2 or thermal.shape[0] != state_count
        or thermal.shape[1] != len(thermal_parameters.density_kg_m3)
        or not np.isfinite(thermal).all() or (thermal > 1.0e-12).any()
        or memory.ndim != 2 or memory.shape[0] != state_count
        or memory.shape[1] > 5 or not np.isfinite(memory).all()
    ):
        raise ValueError("one-year thermal or aging-memory state failed")
    initial_capacity = thermal_capacity_mm_we(thermal, thermal_parameters)
    initial_mirror = float(np.max(np.abs(current["cold_content_mm_we"] - initial_capacity)))
    if initial_mirror > MASS_TOLERANCE_MM_WE:
        raise ValueError("one-year initial cold-capacity mirror failed")

    monthly_refrozen = np.zeros(state_count, dtype=np.float64)
    monthly_melt = np.zeros(state_count, dtype=np.float64)
    monthly_temperature = np.zeros(state_count, dtype=np.float64)
    monthly_day_count = 0
    maximum_daily_closure = 0.0
    maximum_mirror_error = initial_mirror
    maximum_aging_closure = 0.0
    release_totals = {
        name: np.zeros(state_count, dtype=np.float64)
        for name in ("rain_release_mm", "snow_release_mm", "firn_release_mm", "ice_release_mm")
    }
    cycle_initial_storage = total_storage_mm_we_arrays(current, area, rho_ice_kg_m3)
    year_start_storage = cycle_initial_storage.copy()
    precipitation_totals = np.zeros(state_count, dtype=np.float64)
    sublimation_totals = np.zeros(state_count, dtype=np.float64)
    daily_fields = (
        "rain_input_mm", "snowfall_input_mm", "rain_release_mm",
        "snow_release_mm", "firn_release_mm", "ice_release_mm",
        "sublimated_mm", "total_release_mm",
    )
    envelopes = {
        name: np.empty((len(dates), trajectory_count, 3), dtype=np.float64)
        for name in daily_fields
    }
    sparse_fluxes: dict[str, np.ndarray] | None = None
    sparse_index: np.ndarray | None = None
    if sparse_grid_support_index is not None or sparse_grid_support_count is not None:
        if sparse_grid_support_index is None or sparse_grid_support_count is None:
            raise ValueError("sparse grid support metadata must be supplied together")
        sparse_index = _integer_indices(sparse_grid_support_index)
        if (
            sparse_index.shape != (state_count,)
            or not isinstance(sparse_grid_support_count, int)
            or sparse_grid_support_count <= 0
            or sparse_index.min(initial=0) < -1
            or sparse_index.max(initial=-1) >= sparse_grid_support_count
            or not (sparse_index >= 0).any()
        ):
            raise ValueError("sparse grid support metadata failed")
        sparse_fluxes = {
            name: np.empty((len(dates), sparse_grid_support_count), dtype=np.float64)
            for name in daily_fields
        }
    checkpoint: dict[str, np.ndarray] | None = None
    annual_rows: list[dict[str, object]] = []

    for day, timestamp in enumerate(dates):
        index = support_index
        current, fluxes = step_glacier_prepartitioned_daily_arrays(
            current,
            rain_input_mm=forcing["rain_input_mm"][day, index],
            snowfall_input_mm=forcing["snowfall_input_mm"][day, index],
            positive_degree_days_c_day=forcing["positive_degree_days_c_day"][day, index],
            area_m2=area, debris_fraction=debris,
            snow_ddf=snow_ddf, firn_ddf=firn_ddf,
            clean_ice_ddf=clean_ice_ddf, debris_ice_ddf=debris_ice_ddf,
            liquid_holding_fraction=liquid_holding_fraction,
            rho_ice_kg_m3=rho_ice_kg_m3,
            cold_content_gain_mm_we=0.0,
            sublimation_demand_mm_we=sublimation_demand_mm_we,
        )
        fluxes["total_release_mm"] = sum(
            fluxes[name] for name in release_totals
        )
        for name in daily_fields:
            envelopes[name][day] = _member_envelope(
                fluxes[name], area, group_inverse, group_to_trajectory,
                trajectory_count,
            )
            if sparse_fluxes is not None and sparse_index is not None:
                sparse_fluxes[name][day] = aggregate_sparse_grid_flux_m3_day(
                    fluxes[name], area, sparse_index,
                    sparse_support_count=int(sparse_grid_support_count),
                )
        maximum_daily_closure = max(
            maximum_daily_closure,
            float(np.max(np.abs(fluxes["mass_closure_error_mm"]))),
        )
        monthly_refrozen += fluxes["refrozen_mm"]
        monthly_melt += fluxes["snow_melt_mm"] + fluxes["firn_melt_mm"] + fluxes["ice_melt_mm"]
        monthly_temperature += forcing["mean_air_temperature_c"][day, index]
        monthly_day_count += 1
        for name in release_totals:
            release_totals[name] += fluxes[name]
        precipitation_totals += fluxes["rain_input_mm"] + fluxes["snowfall_input_mm"]
        sublimation_totals += fluxes["sublimated_mm"]

        month_end = day == len(dates) - 1 or dates[day + 1].month != timestamp.month
        if month_end:
            expected = np.maximum(
                thermal_capacity_mm_we(thermal, thermal_parameters) - monthly_refrozen,
                0.0,
            )
            maximum_mirror_error = max(
                maximum_mirror_error,
                float(np.max(np.abs(current["cold_content_mm_we"] - expected))),
            )
            thermal, capacity, _diagnostic = close_monthly_thermal_mass_arrays(
                thermal, monthly_refrozen, monthly_melt,
                monthly_temperature / monthly_day_count,
                float(monthly_day_count * 86400), modes, fixed, thermal_parameters,
            )
            current["cold_content_mm_we"] = capacity
            monthly_refrozen.fill(0.0)
            monthly_melt.fill(0.0)
            monthly_temperature.fill(0.0)
            monthly_day_count = 0

        if day + 1 == checkpoint_day_index:
            checkpoint = {
                "day_index": np.asarray([checkpoint_day_index], dtype=np.int64),
                "monthly_day_count": np.asarray([monthly_day_count], dtype=np.int64),
                **{"state__" + name: values for name, values in current.items()},
                "thermal_temperature_c": thermal,
                "five_year_balance_memory_mm_we": memory,
                "monthly_refrozen_mm_we": monthly_refrozen,
                "monthly_melt_mm_we": monthly_melt,
                "monthly_temperature_sum_c": monthly_temperature,
                "release_rain_mm": release_totals["rain_release_mm"],
                "release_snow_mm": release_totals["snow_release_mm"],
                "release_firn_mm": release_totals["firn_release_mm"],
                "release_ice_mm": release_totals["ice_release_mm"],
                "precipitation_total_mm": precipitation_totals,
                "sublimation_total_mm": sublimation_totals,
                "cycle_initial_storage_mm_we": cycle_initial_storage,
                "year_start_storage_mm_we": year_start_storage,
            }
            checkpoint = checkpoint_copy(checkpoint)
            if checkpoint_roundtrip:
                checkpoint = checkpoint_npz_roundtrip(checkpoint)
                current = {
                    name: checkpoint["state__" + name].copy() for name in STATE_FIELDS
                }
                thermal = checkpoint["thermal_temperature_c"].copy()
                memory = checkpoint["five_year_balance_memory_mm_we"].copy()
                monthly_refrozen = checkpoint["monthly_refrozen_mm_we"].copy()
                monthly_melt = checkpoint["monthly_melt_mm_we"].copy()
                monthly_temperature = checkpoint["monthly_temperature_sum_c"].copy()
                monthly_day_count = int(checkpoint["monthly_day_count"][0])
                release_totals = {
                    "rain_release_mm": checkpoint["release_rain_mm"].copy(),
                    "snow_release_mm": checkpoint["release_snow_mm"].copy(),
                    "firn_release_mm": checkpoint["release_firn_mm"].copy(),
                    "ice_release_mm": checkpoint["release_ice_mm"].copy(),
                }
                precipitation_totals = checkpoint["precipitation_total_mm"].copy()
                sublimation_totals = checkpoint["sublimation_total_mm"].copy()
                cycle_initial_storage = checkpoint["cycle_initial_storage_mm_we"].copy()
                year_start_storage = checkpoint["year_start_storage_mm_we"].copy()

        if timestamp.month == 12 and timestamp.day == 31:
            before_aging = total_storage_mm_we_arrays(current, area, rho_ice_kg_m3)
            annual_balance = before_aging - year_start_storage
            ice_mm_we = current["ice_volume_m3"] * rho_ice_kg_m3 / area
            aged, diagnostic = apply_registered_balance_year_aging_arrays(
                current["snow_mm_we"], current["firn_mm_we"], ice_mm_we,
                annual_balance, memory,
                aging_candidate_id=aging_candidate_id,
                registered_firn_to_ice_fraction=registered_firn_to_ice_fraction,
            )
            current["snow_mm_we"] = aged["snow_mm_we"]
            current["firn_mm_we"] = aged["firn_mm_we"]
            current["ice_volume_m3"] = aged["ice_mm_we"] * area / rho_ice_kg_m3
            memory = aged["five_year_balance_memory_mm_we"]
            maximum_aging_closure = max(
                maximum_aging_closure,
                float(diagnostic["maximum_absolute_mass_closure_mm_we"]),
            )
            year_start_storage = total_storage_mm_we_arrays(current, area, rho_ice_kg_m3)
            annual_rows.append({
                "year": int(timestamp.year),
                "aging_candidate_id": aging_candidate_id,
                "memory_year_count": int(memory.shape[1]),
                "maximum_absolute_aging_closure_mm_we": float(
                    diagnostic["maximum_absolute_mass_closure_mm_we"]
                ),
            })

    if checkpoint is None:
        raise RuntimeError("one-year checkpoint was not captured")
    final_capacity = thermal_capacity_mm_we(thermal, thermal_parameters)
    maximum_mirror_error = max(
        maximum_mirror_error,
        float(np.max(np.abs(current["cold_content_mm_we"] - final_capacity))),
    )
    cycle_final_storage = total_storage_mm_we_arrays(current, area, rho_ice_kg_m3)
    cycle_release = sum(release_totals.values())
    cycle_closure = (
        cycle_initial_storage + precipitation_totals - cycle_final_storage
        - cycle_release - sublimation_totals
    )
    cycle_scale = np.maximum.reduce((
        np.abs(cycle_initial_storage) + precipitation_totals,
        np.abs(cycle_final_storage) + cycle_release + sublimation_totals,
        np.full(state_count, 1.0e-12, dtype=np.float64),
    ))
    maximum_cycle_closure = float(np.max(np.abs(cycle_closure)))
    maximum_relative_cycle_closure = float(np.max(np.abs(cycle_closure) / cycle_scale))
    if (
        maximum_daily_closure > 1.0e-8
        or maximum_aging_closure > MASS_TOLERANCE_MM_WE
        or maximum_mirror_error > MASS_TOLERANCE_MM_WE
        or maximum_relative_cycle_closure > 1.0e-10
    ):
        raise RuntimeError("one-year mass, aging or thermal closure failed")
    return current, thermal, memory, {
        "day_count": len(dates),
        "calendar_year_complete": not terminal_partial_year,
        "terminal_partial_year": terminal_partial_year,
        "annual_diagnostics": annual_rows,
        "maximum_absolute_daily_mass_closure_mm": maximum_daily_closure,
        "maximum_absolute_cycle_mass_closure_mm": maximum_cycle_closure,
        "maximum_relative_cycle_mass_closure": maximum_relative_cycle_closure,
        "maximum_absolute_aging_closure_mm_we": maximum_aging_closure,
        "maximum_cold_capacity_mirror_error_mm_we": maximum_mirror_error,
        "release_totals_mm": release_totals,
        "daily_member_envelopes_m3": envelopes,
        "daily_sparse_grid_flux_m3": sparse_fluxes,
        "checkpoint_payload": checkpoint,
    }
