"""Annual ice geometry within a registered band footprint."""

from __future__ import annotations

from dataclasses import dataclass

import math

from typing import Sequence

import numpy as np



@dataclass(frozen=True)
class GeometryState:
    band_area_m2: tuple[float, ...]
    bed_elevation_m: tuple[float, ...]
    surface_elevation_m: tuple[float, ...]

    @property
    def thickness_m(self) -> tuple[float, ...]:
        return tuple(
            max(surface - bed, 0.0)
            for surface, bed in zip(self.surface_elevation_m, self.bed_elevation_m)
        )

    @property
    def volume_m3(self) -> float:
        return sum(
            area * thickness
            for area, thickness in zip(self.band_area_m2, self.thickness_m)
        )

    @property
    def active_area_m2(self) -> float:
        return sum(
            area
            for area, thickness in zip(self.band_area_m2, self.thickness_m)
            if thickness > 0.0
        )

    def validate(self) -> None:
        n = len(self.band_area_m2)
        if n == 0 or len(self.bed_elevation_m) != n or len(self.surface_elevation_m) != n:
            raise ValueError("geometry arrays must have equal nonzero length")
        if not all(math.isfinite(value) for values in (
            self.band_area_m2, self.bed_elevation_m, self.surface_elevation_m
        ) for value in values):
            raise ValueError("geometry values must be finite")
        if any(area <= 0.0 for area in self.band_area_m2):
            raise ValueError("band areas must be positive")
        if any(surface < bed for surface, bed in zip(
            self.surface_elevation_m, self.bed_elevation_m
        )):
            raise ValueError("surface elevation cannot be below bed elevation")

def update_geometry_delta_h(
    geometry: GeometryState,
    target_volume_m3: float,
    delta_h_weights: Sequence[float],
    tolerance_m3: float = 1e-5,
) -> tuple[GeometryState, float]:
    """Redistribute a target volume over fixed bands using nonnegative delta-h weights."""
    geometry.validate()
    if not math.isfinite(target_volume_m3) or target_volume_m3 < 0.0:
        raise ValueError("target volume must be finite and nonnegative")
    if len(delta_h_weights) != len(geometry.band_area_m2):
        raise ValueError("delta-h weights must match geometry bands")
    if not all(math.isfinite(value) and value >= 0.0 for value in delta_h_weights):
        raise ValueError("delta-h weights must be finite and nonnegative")
    if not any(value > 0.0 for value in delta_h_weights):
        raise ValueError("at least one delta-h weight must be positive")
    if target_volume_m3 == 0.0:
        result = GeometryState(
            geometry.band_area_m2,
            geometry.bed_elevation_m,
            geometry.bed_elevation_m,
        )
        return result, 0.0

    thickness = geometry.thickness_m

    def volume(scale: float) -> float:
        return sum(
            area * (
                old if weight == 0.0 else max(old + scale * weight, 0.0)
            )
            for area, old, weight in zip(
                geometry.band_area_m2, thickness, delta_h_weights
            )
        )

    current = geometry.volume_m3
    if target_volume_m3 < current:
        immutable = sum(
            area * old
            for area, old, weight in zip(
                geometry.band_area_m2, thickness, delta_h_weights
            )
            if weight == 0.0
        )
        allowed = max(tolerance_m3, target_volume_m3 * 1e-12)
        if immutable > target_volume_m3 + allowed:
            raise RuntimeError(
                "delta-h target is below the zero-weight residual volume"
            )
        removal_scales = [
            -old / weight
            for old, weight in zip(thickness, delta_h_weights)
            if weight > 0.0 and old > 0.0
        ]
        if not removal_scales:
            raise RuntimeError("delta-h retreat has no reducible active volume")
        lower = min(removal_scales)
        if not math.isfinite(lower) or volume(lower) > target_volume_m3 + allowed:
            raise RuntimeError("delta-h retreat finite bracket failed")
        upper = 0.0
    else:
        lower = 0.0
        upper = 1.0
        for _ in range(1024):
            if volume(upper) >= target_volume_m3:
                break
            upper *= 2.0
            if not math.isfinite(upper):
                raise RuntimeError("delta-h advance finite bracket failed")
        else:
            raise RuntimeError("delta-h advance bracket iteration limit failed")
    for _ in range(200):
        middle = 0.5 * (lower + upper)
        if volume(middle) < target_volume_m3:
            lower = middle
        else:
            upper = middle
    scale = 0.5 * (lower + upper)
    new_thickness = tuple(
        old if weight == 0.0 else max(old + scale * weight, 0.0)
        for old, weight in zip(thickness, delta_h_weights)
    )
    result = GeometryState(
        geometry.band_area_m2,
        geometry.bed_elevation_m,
        tuple(
            bed + thick
            for bed, thick in zip(geometry.bed_elevation_m, new_thickness)
        ),
    )
    error = result.volume_m3 - target_volume_m3
    allowed = max(tolerance_m3, target_volume_m3 * 1e-12)
    if abs(error) > allowed:
        raise RuntimeError("delta-h geometry volume closure failed")
    return result, error

@dataclass(frozen=True)
class RegisteredDeltaHCoefficients:
    size_class: str
    minimum_area_km2_inclusive: float
    maximum_area_km2_exclusive: float
    a: float
    b: float
    c: float
    gamma: float

    def validate(self) -> None:
        if self.size_class not in {"small", "medium", "large"}:
            raise ValueError("delta-h size class is not registered")
        finite = (
            self.minimum_area_km2_inclusive, self.a, self.b, self.c, self.gamma,
        )
        if not all(math.isfinite(value) for value in finite):
            raise ValueError("delta-h coefficients must be finite")
        if not (
            self.minimum_area_km2_inclusive >= 0.0
            and self.maximum_area_km2_exclusive > self.minimum_area_km2_inclusive
        ):
            raise ValueError("delta-h area interval is invalid")
        if self.gamma <= 0.0 or not float(self.gamma).is_integer():
            raise ValueError("delta-h gamma must be a positive registered integer")


def registered_delta_h_weights(
    geometry: GeometryState,
    coefficients: RegisteredDeltaHCoefficients,
) -> tuple[float, ...]:
    """Evaluate the registered retreat curve on active band surfaces."""
    geometry.validate()
    coefficients.validate()
    thickness = np.asarray(geometry.thickness_m, dtype=np.float64)
    surface = np.asarray(geometry.surface_elevation_m, dtype=np.float64)
    active = thickness > 0.0
    if int(active.sum()) < 2:
        raise ValueError("delta-h retreat requires at least two active elevation bands")
    minimum = float(surface[active].min())
    maximum = float(surface[active].max())
    if not maximum > minimum:
        raise ValueError("delta-h active elevation range must be positive")
    normalized = np.zeros(len(surface), dtype=np.float64)
    normalized[active] = (maximum - surface[active]) / (maximum - minimum)
    shifted = normalized + coefficients.a
    raw = (
        np.power(shifted, int(coefficients.gamma))
        + coefficients.b * shifted
        + coefficients.c
    )
    weights = np.where(active, np.maximum(raw, 0.0), 0.0)
    if not np.isfinite(weights).all() or not (weights > 0.0).any():
        raise RuntimeError("registered delta-h curve has no finite positive support")
    return tuple(float(value) for value in weights)

RETREAT_ROUTE = "RETREAT_WITH_REGISTERED_NONNEGATIVE_DELTA_H"
TERMINAL_ROUTE = "TERMINAL_SINGLE_ACTIVE_BAND_FIXED_AREA_THINNING"
TERMINAL_ZERO_WEIGHT_ROUTE = (
    "TERMINAL_ZERO_WEIGHT_RESIDUAL_LOCAL_MASS_BALANCE_SYNCHRONIZATION"
)
TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE = (
    "TERMINAL_SINGLE_ACTIVE_ELEVATION_CLASS_FIXED_AREA_THINNING"
)
EXTINCTION_ROUTE = "ZERO_VOLUME_REGISTERED_FOOTPRINT_EXTINCTION"
NEUTRAL_ROUTE = "NUMERIC_NEUTRAL_GEOMETRY_HOLD"
POSITIVE_ROUTE = "POSITIVE_BALANCE_REGISTERED_FOOTPRINT_BAND_STATE_SYNCHRONIZATION"


def _target_vector(values: Sequence[float], count: int) -> np.ndarray:
    target = np.asarray(values, dtype=np.float64)
    if (
        target.shape != (count,)
        or not np.isfinite(target).all()
        or (target < 0.0).any()
    ):
        raise ValueError("band target ice volumes must be finite and nonnegative")
    return target


def synchronize_multiyear_geometry(
    geometry: GeometryState,
    target_band_ice_volume_m3: Sequence[float],
    coefficients: RegisteredDeltaHCoefficients,
    *,
    tolerance_m3: float = 1.0e-5,
    allow_terminal_zero_weight_residual_local_mass_balance: bool = False,
) -> tuple[GeometryState, dict[str, float | int | str | bool]]:
    """Synchronize annual geometry without reversing a retreat delta-h curve.

    Annual loss uses the registered nonnegative delta-h curve. An explicitly
    authorized terminal route may preserve local band mass balance when that
    curve is mathematically infeasible on at most three active bands. Positive
    total balance uses the simulated band ice-volume state inside the fixed
    registered footprint; no route creates an unregistered band or cell.
    """
    geometry.validate()
    coefficients.validate()
    if not math.isfinite(tolerance_m3) or tolerance_m3 <= 0.0:
        raise ValueError("geometry tolerance must be finite and positive")
    target_by_band = _target_vector(
        target_band_ice_volume_m3, len(geometry.band_area_m2)
    )
    current = float(geometry.volume_m3)
    target = float(target_by_band.sum(dtype=np.float64))
    allowed = max(float(tolerance_m3), current * 1.0e-12, target * 1.0e-12)
    old_active = np.asarray(geometry.thickness_m, dtype=np.float64) > 0.0
    terminal_residual_previous_volume = 0.0
    terminal_residual_target_volume = 0.0
    terminal_residual_volume_ratio = 1.0
    terminal_zero_weight_band_count = 0
    terminal_single_elevation_class_band_count = 0
    terminal_single_elevation_class_surface_range = 0.0
    terminal_single_elevation_class_bed_range = 0.0
    terminal_single_elevation_class_target_thickness_range = 0.0

    if target <= allowed:
        updated = GeometryState(
            geometry.band_area_m2,
            geometry.bed_elevation_m,
            geometry.bed_elevation_m,
        )
        route = EXTINCTION_ROUTE
    elif target < current - allowed:
        active_count = int(old_active.sum())
        if active_count >= 2:
            thickness = np.asarray(geometry.thickness_m, dtype=np.float64)
            surface = np.asarray(geometry.surface_elevation_m, dtype=np.float64)
            bed = np.asarray(geometry.bed_elevation_m, dtype=np.float64)
            area = np.asarray(geometry.band_area_m2, dtype=np.float64)
            active_surface = surface[old_active]
            active_bed = bed[old_active]
            terminal_single_elevation_class_surface_range = float(
                np.ptp(active_surface)
            )
            terminal_single_elevation_class_bed_range = float(np.ptp(active_bed))
            elevation_tolerance = max(
                1.0e-9,
                float(np.max(np.abs(active_surface))) * 1.0e-12,
            )
            single_elevation_class = (
                terminal_single_elevation_class_surface_range <= elevation_tolerance
                and terminal_single_elevation_class_bed_range <= elevation_tolerance
            )
            if single_elevation_class:
                if not allow_terminal_zero_weight_residual_local_mass_balance:
                    raise RuntimeError(
                        "delta-h retreat has one degenerate active elevation class"
                    )
                if active_count > 3:
                    raise RuntimeError(
                        "terminal single-elevation route requires at most three active bands"
                    )
                if np.any(target_by_band[~old_active] > 0.0):
                    raise RuntimeError(
                        "terminal single-elevation route cannot reactivate an inactive band"
                    )
                target_thickness = target_by_band[old_active] / area[old_active]
                terminal_single_elevation_class_target_thickness_range = float(
                    np.ptp(target_thickness)
                )
                target_thickness_tolerance = max(
                    1.0e-9,
                    float(np.max(np.abs(target_thickness))) * 1.0e-12,
                )
                if (
                    terminal_single_elevation_class_target_thickness_range
                    > target_thickness_tolerance
                ):
                    raise RuntimeError(
                        "terminal single-elevation target thickness is not uniform"
                    )
                new_thickness = target_by_band / area
                updated = GeometryState(
                    geometry.band_area_m2,
                    geometry.bed_elevation_m,
                    tuple(
                        float(bed + value)
                        for bed, value in zip(
                            geometry.bed_elevation_m, new_thickness
                        )
                    ),
                )
                terminal_single_elevation_class_band_count = active_count
                route = TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE
            else:
                weights = registered_delta_h_weights(geometry, coefficients)
                weight_array = np.asarray(weights, dtype=np.float64)
                zero_weight_active = old_active & (weight_array == 0.0)
                terminal_residual_previous_volume = float(
                    np.sum(area[zero_weight_active] * thickness[zero_weight_active])
                )
                if target < terminal_residual_previous_volume - allowed:
                    if not allow_terminal_zero_weight_residual_local_mass_balance:
                        raise RuntimeError(
                            "delta-h target is below the zero-weight residual volume"
                        )
                    terminal_zero_weight_band_count = int(zero_weight_active.sum())
                    if terminal_zero_weight_band_count == 0:
                        raise RuntimeError(
                            "terminal zero-weight residual route has no active support"
                        )
                    if active_count > 3:
                        raise RuntimeError(
                            "terminal local-mass-balance route requires at most three active bands"
                        )
                    if np.any(target_by_band[~old_active] > allowed):
                        raise RuntimeError(
                            "terminal local-mass-balance route cannot reactivate an inactive band"
                        )
                    terminal_residual_target_volume = float(
                        target_by_band[zero_weight_active].sum(dtype=np.float64)
                    )
                    terminal_residual_volume_ratio = (
                        terminal_residual_target_volume
                        / terminal_residual_previous_volume
                    )
                    new_thickness = target_by_band / area
                    updated = GeometryState(
                        geometry.band_area_m2,
                        geometry.bed_elevation_m,
                        tuple(
                            float(bed_value + value)
                            for bed_value, value in zip(
                                geometry.bed_elevation_m, new_thickness
                            )
                        ),
                    )
                    route = TERMINAL_ZERO_WEIGHT_ROUTE
                else:
                    updated, _ = update_geometry_delta_h(
                        geometry, target, weights, tolerance_m3=tolerance_m3
                    )
                    route = RETREAT_ROUTE
        elif active_count == 1:
            index = int(np.flatnonzero(old_active)[0])
            thickness = np.zeros(len(old_active), dtype=np.float64)
            thickness[index] = target / float(geometry.band_area_m2[index])
            updated = GeometryState(
                geometry.band_area_m2,
                geometry.bed_elevation_m,
                tuple(
                    float(bed + value)
                    for bed, value in zip(geometry.bed_elevation_m, thickness)
                ),
            )
            route = TERMINAL_ROUTE
        else:
            raise RuntimeError("positive target is inconsistent with extinct geometry")
    elif target > current + allowed:
        thickness = target_by_band / np.asarray(
            geometry.band_area_m2, dtype=np.float64
        )
        updated = GeometryState(
            geometry.band_area_m2,
            geometry.bed_elevation_m,
            tuple(
                float(bed + value)
                for bed, value in zip(geometry.bed_elevation_m, thickness)
            ),
        )
        route = POSITIVE_ROUTE
    else:
        updated = geometry
        route = NEUTRAL_ROUTE

    updated.validate()
    closure = float(updated.volume_m3 - target)
    closure_limit = max(float(tolerance_m3), target * 1.0e-12)
    if abs(closure) > closure_limit:
        raise RuntimeError("multiyear geometry volume closure failed")
    new_active = np.asarray(updated.thickness_m, dtype=np.float64) > 0.0
    registered_area = float(sum(geometry.band_area_m2))
    if (
        geometry.band_area_m2 != updated.band_area_m2
        or float(updated.active_area_m2) > registered_area + 1.0e-8
    ):
        raise RuntimeError("multiyear geometry exceeded the registered footprint")
    return updated, {
        "route": route,
        "previous_geometry_volume_m3": current,
        "target_ice_volume_m3": target,
        "updated_geometry_volume_m3": float(updated.volume_m3),
        "volume_closure_error_m3": closure,
        "previous_active_area_m2": float(geometry.active_area_m2),
        "updated_active_area_m2": float(updated.active_area_m2),
        "registered_footprint_area_m2": registered_area,
        "previous_active_band_count": int(old_active.sum()),
        "updated_active_band_count": int(new_active.sum()),
        "positive_balance_route_used": route == POSITIVE_ROUTE,
        "terminal_zero_weight_residual_route_used": (
            route == TERMINAL_ZERO_WEIGHT_ROUTE
        ),
        "terminal_zero_weight_residual_previous_volume_m3": (
            terminal_residual_previous_volume
        ),
        "terminal_zero_weight_residual_target_volume_m3": (
            terminal_residual_target_volume
            if route == TERMINAL_ZERO_WEIGHT_ROUTE else 0.0
        ),
        "terminal_zero_weight_residual_volume_ratio": (
            terminal_residual_volume_ratio
        ),
        "terminal_zero_weight_active_band_count": terminal_zero_weight_band_count,
        "terminal_single_elevation_class_route_used": (
            route == TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE
        ),
        "terminal_single_elevation_class_active_band_count": (
            terminal_single_elevation_class_band_count
        ),
        "terminal_single_elevation_class_surface_range_m": (
            terminal_single_elevation_class_surface_range
        ),
        "terminal_single_elevation_class_bed_range_m": (
            terminal_single_elevation_class_bed_range
        ),
        "terminal_single_elevation_class_target_thickness_range_m": (
            terminal_single_elevation_class_target_thickness_range
        ),
        "terminal_local_mass_balance_band_state_used": (
            route in {
                TERMINAL_ZERO_WEIGHT_ROUTE,
                TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE,
            }
        ),
        "terminal_route_maximum_active_band_count": 3,
        "terminal_route_structural_sensitivity_required": (
            route in {
                TERMINAL_ZERO_WEIGHT_ROUTE,
                TERMINAL_SINGLE_ELEVATION_CLASS_ROUTE,
            }
        ),
        "registered_footprint_reactivation_used": bool((new_active & ~old_active).any()),
        "reverse_delta_h_used": False,
        "unregistered_footprint_created": False,
    }
