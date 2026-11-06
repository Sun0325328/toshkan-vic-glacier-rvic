"""Thermal capacity, monthly conduction and registered annual aging."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


WINTER_MONTHLY_MELT_LIMIT_MM_WE = 2.0


MAXIMUM_FOURIER_NUMBER = 0.45


MASS_TOLERANCE_MM_WE = 1.0e-10


@dataclass(frozen=True)
class ThermalArrayParameters:
    density_kg_m3: tuple[float, ...]
    thickness_m: tuple[float, ...]
    specific_heat_j_kg_k: float
    latent_heat_j_kg: float
    conductivity_w_m_k: float

    def validate(self) -> None:
        density = np.asarray(self.density_kg_m3, dtype=np.float64)
        thickness = np.asarray(self.thickness_m, dtype=np.float64)
        scalars = np.asarray([
            self.specific_heat_j_kg_k,
            self.latent_heat_j_kg,
            self.conductivity_w_m_k,
        ], dtype=np.float64)
        if (
            density.ndim != 1
            or len(density) < 3
            or thickness.shape != density.shape
            or not np.isfinite(density).all()
            or not np.isfinite(thickness).all()
            or not np.isfinite(scalars).all()
            or (density <= 0.0).any()
            or (thickness <= 0.0).any()
            or (scalars <= 0.0).any()
            or not np.allclose(thickness, thickness[0], rtol=0.0, atol=1.0e-12)
        ):
            raise ValueError("invalid thermal array parameters")


def _profiles(values: np.ndarray, layer_count: int) -> np.ndarray:
    profiles = np.asarray(values, dtype=np.float64)
    if (
        profiles.ndim != 2
        or profiles.shape[1] != layer_count
        or profiles.shape[0] == 0
        or not np.isfinite(profiles).all()
        or (profiles > 1.0e-12).any()
    ):
        raise ValueError("thermal profiles must be finite subfreezing 2-D arrays")
    return np.minimum(profiles, 0.0)


def thermal_capacity_mm_we(
    temperature_c: np.ndarray,
    parameters: ThermalArrayParameters,
) -> np.ndarray:
    parameters.validate()
    density = np.asarray(parameters.density_kg_m3, dtype=np.float64)
    thickness = np.asarray(parameters.thickness_m, dtype=np.float64)
    profiles = _profiles(temperature_c, len(density))
    return (
        -profiles
        * density[None, :]
        * thickness[None, :]
        * parameters.specific_heat_j_kg_k
    ).sum(axis=1) / parameters.latent_heat_j_kg


def consume_refreezing_capacity_arrays(
    temperature_c: np.ndarray,
    refrozen_mm_we: np.ndarray,
    parameters: ThermalArrayParameters,
) -> tuple[np.ndarray, np.ndarray]:
    capacity = thermal_capacity_mm_we(temperature_c, parameters)
    refrozen = np.asarray(refrozen_mm_we, dtype=np.float64)
    if (
        refrozen.shape != capacity.shape
        or not np.isfinite(refrozen).all()
        or (refrozen < 0.0).any()
        or (refrozen > capacity + MASS_TOLERANCE_MM_WE).any()
    ):
        raise ValueError("monthly refreezing debit exceeds thermal capacity")
    remaining = np.maximum(capacity - refrozen, 0.0)
    factor = np.divide(
        remaining,
        capacity,
        out=np.zeros_like(remaining),
        where=capacity > 0.0,
    )
    warmed = np.minimum(np.asarray(temperature_c, dtype=np.float64), 0.0)
    warmed = warmed * factor[:, None]
    recalculated = thermal_capacity_mm_we(warmed, parameters)
    if not np.allclose(
        recalculated, remaining, rtol=1.0e-12, atol=MASS_TOLERANCE_MM_WE
    ):
        raise RuntimeError("vector thermal capacity debit is inconsistent")
    return warmed, remaining


def advance_monthly_conduction_arrays(
    temperature_c: np.ndarray,
    surface_temperature_c: np.ndarray,
    month_seconds: float,
    lower_boundary_mode: np.ndarray,
    fixed_lower_temperature_c: np.ndarray,
    parameters: ThermalArrayParameters,
    maximum_fourier_number: float = MAXIMUM_FOURIER_NUMBER,
) -> tuple[np.ndarray, dict[str, float]]:
    parameters.validate()
    density = np.asarray(parameters.density_kg_m3, dtype=np.float64)
    thickness = np.asarray(parameters.thickness_m, dtype=np.float64)
    profiles = _profiles(temperature_c, len(density)).copy()
    surface = np.asarray(surface_temperature_c, dtype=np.float64)
    modes = np.asarray(lower_boundary_mode, dtype=str)
    fixed = np.asarray(fixed_lower_temperature_c, dtype=np.float64)
    if (
        surface.shape != (len(profiles),)
        or modes.shape != surface.shape
        or fixed.shape != surface.shape
        or not np.isfinite(surface).all()
        or (surface > 0.0).any()
        or not math.isfinite(month_seconds)
        or month_seconds <= 0.0
        or not 0.0 < maximum_fourier_number <= 0.5
        or not np.isin(modes, ["ZERO_FLUX", "FIXED_TEMPERATURE"]).all()
        or (
            (modes == "FIXED_TEMPERATURE")
            & (~np.isfinite(fixed) | (fixed > 0.0))
        ).any()
        or ((modes == "ZERO_FLUX") & np.isfinite(fixed)).any()
    ):
        raise ValueError("invalid monthly conduction input or boundary")
    diffusivity = (
        parameters.conductivity_w_m_k
        / (density * parameters.specific_heat_j_kg_k)
    )
    unconstrained = float(diffusivity.max()) * month_seconds / thickness[0] ** 2
    substeps = max(1, math.ceil(unconstrained / maximum_fourier_number))
    fourier = diffusivity * (month_seconds / substeps) / thickness[0] ** 2
    if fourier.max() > maximum_fourier_number + 1.0e-12:
        raise RuntimeError("adaptive monthly conduction stability failed")
    zero_flux = modes == "ZERO_FLUX"
    fixed_boundary = ~zero_flux
    for _ in range(substeps):
        old = profiles
        new = old.copy()
        new[:, 0] = surface
        new[:, 1:-1] = old[:, 1:-1] + fourier[None, 1:-1] * (
            old[:, :-2] - 2.0 * old[:, 1:-1] + old[:, 2:]
        )
        new[zero_flux, -1] = old[zero_flux, -1] + fourier[-1] * (
            old[zero_flux, -2] - old[zero_flux, -1]
        )
        new[fixed_boundary, -1] = fixed[fixed_boundary]
        profiles = np.minimum(new, 0.0)
    return profiles, {
        "substeps": float(substeps),
        "maximum_fourier_number": float(fourier.max()),
    }


def close_monthly_thermal_mass_arrays(
    temperature_c: np.ndarray,
    monthly_refrozen_mm_we: np.ndarray,
    monthly_total_melt_mm_we: np.ndarray,
    monthly_mean_air_temperature_c: np.ndarray,
    month_seconds: float,
    lower_boundary_mode: np.ndarray,
    fixed_lower_temperature_c: np.ndarray,
    parameters: ThermalArrayParameters,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Debit daily refreezing, then conduct only in admitted winter months."""
    warmed, _remaining = consume_refreezing_capacity_arrays(
        temperature_c, monthly_refrozen_mm_we, parameters
    )
    melt = np.asarray(monthly_total_melt_mm_we, dtype=np.float64)
    mean_temperature = np.asarray(monthly_mean_air_temperature_c, dtype=np.float64)
    if (
        melt.shape != (len(warmed),)
        or mean_temperature.shape != melt.shape
        or not np.isfinite(melt).all()
        or not np.isfinite(mean_temperature).all()
        or (melt < 0.0).any()
    ):
        raise ValueError("invalid monthly thermal-mass diagnostics")
    winter = melt <= WINTER_MONTHLY_MELT_LIMIT_MM_WE
    updated = warmed.copy()
    maximum_fourier = 0.0
    substeps = 0.0
    if winter.any():
        winter_profiles, numerical = advance_monthly_conduction_arrays(
            warmed[winter],
            np.minimum(mean_temperature[winter], 0.0),
            month_seconds,
            np.asarray(lower_boundary_mode)[winter],
            np.asarray(fixed_lower_temperature_c, dtype=np.float64)[winter],
            parameters,
        )
        updated[winter] = winter_profiles
        maximum_fourier = numerical["maximum_fourier_number"]
        substeps = numerical["substeps"]
    capacity = thermal_capacity_mm_we(updated, parameters)
    return updated, capacity, {
        "winter_state_count": float(winter.sum()),
        "nonwinter_state_count": float((~winter).sum()),
        "substeps": substeps,
        "maximum_fourier_number": maximum_fourier,
    }


def apply_registered_balance_year_aging_arrays(
    snow_mm_we: np.ndarray,
    firn_mm_we: np.ndarray,
    ice_mm_we: np.ndarray,
    annual_balance_mm_we: np.ndarray,
    five_year_balance_memory_mm_we: np.ndarray,
    *,
    aging_candidate_id: str,
    registered_firn_to_ice_fraction: float | None,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    snow = np.asarray(snow_mm_we, dtype=np.float64)
    firn = np.asarray(firn_mm_we, dtype=np.float64)
    ice = np.asarray(ice_mm_we, dtype=np.float64)
    balance = np.asarray(annual_balance_mm_we, dtype=np.float64)
    memory = np.asarray(five_year_balance_memory_mm_we, dtype=np.float64)
    if (
        snow.shape != firn.shape
        or snow.shape != ice.shape
        or snow.shape != balance.shape
        or snow.ndim != 1
        or memory.ndim != 2
        or memory.shape[0] != len(snow)
        or memory.shape[1] > 5
        or not np.isfinite(np.concatenate((snow, firn, ice, balance))).all()
        or not np.isfinite(memory).all()
        or (snow < 0.0).any()
        or (firn < 0.0).any()
        or (ice < 0.0).any()
    ):
        raise ValueError("invalid balance-year aging arrays")
    before = snow + firn + ice
    firn_after_snow = firn + snow
    if aging_candidate_id == "AC01":
        if registered_firn_to_ice_fraction is not None:
            raise ValueError("AC01 prohibits a fixed firn-to-ice fraction")
        fraction = 0.0
        next_memory = np.concatenate((memory, balance[:, None]), axis=1)[:, -5:]
        surface_class = np.full(len(snow), "UNRESOLVED_LT5_YEARS", dtype=object)
        if next_memory.shape[1] == 5:
            surface_class = np.where(
                next_memory.mean(axis=1) > 0.0, "FIRN", "ICE"
            ).astype(object)
    elif aging_candidate_id == "AC02":
        if (
            registered_firn_to_ice_fraction is None
            or not math.isclose(
                float(registered_firn_to_ice_fraction), 0.25,
                rel_tol=0.0, abs_tol=1.0e-12,
            )
        ):
            raise ValueError("AC02 requires its registered 0.25 sensitivity fraction")
        fraction = 0.25
        next_memory = memory.copy()
        surface_class = np.full(len(snow), "NOT_APPLICABLE_AC02", dtype=object)
    else:
        raise ValueError("unregistered aging candidate: " + str(aging_candidate_id))
    transferred = firn_after_snow * fraction
    updated = {
        "snow_mm_we": np.zeros_like(snow),
        "firn_mm_we": firn_after_snow - transferred,
        "ice_mm_we": ice + transferred,
        "five_year_balance_memory_mm_we": next_memory,
    }
    after = updated["snow_mm_we"] + updated["firn_mm_we"] + updated["ice_mm_we"]
    closure = after - before
    if np.max(np.abs(closure)) > MASS_TOLERANCE_MM_WE:
        raise RuntimeError("registered annual aging violates mass conservation")
    return updated, {
        "firn_to_ice_fraction": fraction,
        "firn_to_ice_transfer_mm_we": transferred,
        "surface_class": surface_class,
        "maximum_absolute_mass_closure_mm_we": float(np.max(np.abs(closure))),
    }
