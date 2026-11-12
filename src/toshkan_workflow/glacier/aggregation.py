"""Aggregate nonnegative glacier release depths to separate volume supports."""
from __future__ import annotations
import numpy as np


def _integer_indices(values: np.ndarray) -> np.ndarray:
    indices = np.asarray(values)
    if indices.dtype.kind not in "iu":
        raise ValueError("expected integer indices")
    if indices.dtype.kind == "u" and np.any(indices > np.uint64(np.iinfo(np.int64).max)):
        raise ValueError("indices exceed the signed 64-bit range")
    return indices.astype(np.int64, copy=False)


def aggregate_sparse_grid_flux_m3_day(
    values_mm: np.ndarray,
    area_m2: np.ndarray,
    sparse_support_index: np.ndarray,
    *,
    sparse_support_count: int,
) -> np.ndarray:
    """Aggregate unit fluxes directly onto registered sparse support rows."""
    values = np.asarray(values_mm, dtype=np.float64)
    area = np.asarray(area_m2, dtype=np.float64)
    support = _integer_indices(sparse_support_index)
    state_count = len(values)
    if (
        state_count == 0
        or area.shape != (state_count,) or support.shape != (state_count,)
        or not isinstance(sparse_support_count, int) or sparse_support_count <= 0
        or not np.isfinite(values).all() or (values < 0.0).any()
        or not np.isfinite(area).all() or (area <= 0.0).any()
        or support.min(initial=0) < -1
        or support.max(initial=-1) >= sparse_support_count
        or not (support >= 0).any()
    ):
        raise ValueError("sparse grid-resolved daily flux aggregation schema failed")
    included = support >= 0
    return np.bincount(
        support[included],
        weights=values[included] * area[included] / 1000.0,
        minlength=sparse_support_count,
    )


def aggregate_grid_flux_m3_day(
    values_mm: np.ndarray,
    area_m2: np.ndarray,
    trajectory_index: np.ndarray,
    grid_index: np.ndarray,
    *,
    trajectory_count: int,
    grid_count: int,
) -> np.ndarray:
    """Aggregate nonnegative unit fluxes to trajectory-grid volume fluxes."""
    values = np.asarray(values_mm, dtype=np.float64)
    area = np.asarray(area_m2, dtype=np.float64)
    trajectories = _integer_indices(trajectory_index)
    grids = _integer_indices(grid_index)
    state_count = len(values)
    if (
        state_count == 0
        or any(array.shape != (state_count,) for array in (area, trajectories, grids))
        or not isinstance(trajectory_count, int) or trajectory_count <= 0
        or not isinstance(grid_count, int) or grid_count <= 0
        or not np.isfinite(values).all() or (values < 0.0).any()
        or not np.isfinite(area).all() or (area <= 0.0).any()
        or trajectories.min(initial=0) < 0
        or trajectories.max(initial=-1) >= trajectory_count
        or grids.min(initial=0) < 0 or grids.max(initial=-1) >= grid_count
    ):
        raise ValueError("grid-resolved daily flux aggregation schema failed")
    flat_index = trajectories * grid_count + grids
    aggregated = np.bincount(
        flat_index,
        weights=values * area / 1000.0,
        minlength=trajectory_count * grid_count,
    )
    return aggregated.reshape(trajectory_count, grid_count)
