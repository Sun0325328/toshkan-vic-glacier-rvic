"""Discharge accuracy metrics for pre-aligned pairs."""
from __future__ import annotations
import math
import numpy as np


def compute_accuracy_metrics(observed: object, simulated: object) -> dict[str, float | int]:
    """Compute the frozen metric set after finite pairwise selection."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    if obs.ndim != 1 or sim.ndim != 1:
        raise RuntimeError("expected one-dimensional observed and simulated discharge series")
    if obs.shape != sim.shape:
        raise RuntimeError("observed and simulated arrays have different shapes")
    # Lists and arrays are positional. Check labeled pairs before filtering.
    obs_index = getattr(observed, "index", None)
    sim_index = getattr(simulated, "index", None)
    if hasattr(obs_index, "equals") and hasattr(sim_index, "equals"):
        if not obs_index.equals(sim_index):
            raise ValueError("observed and simulated index labels or order differ")
        if len(obs_index.dropna()) != len(obs_index):
            raise ValueError("missing discharge index label")
        if not obs_index.is_unique:
            raise ValueError("expected a unique label for each discharge pair")
    valid = np.isfinite(obs) & np.isfinite(sim)
    obs = obs[valid]
    sim = sim[valid]
    result: dict[str, float | int] = {
        "paired_count": int(len(obs)),
        "KGE_2012_modified": np.nan,
        "KGE_2009": np.nan,
        "NSE": np.nan,
        "RMSE_m3s": np.nan,
        "MAE_m3s": np.nan,
        "PBIAS_percent": np.nan,
        "Pearson_r": np.nan,
        "volume_bias_percent": np.nan,
        "alpha_sd_ratio": np.nan,
        "beta_mean_ratio": np.nan,
        "gamma_cv_ratio": np.nan,
    }
    if len(obs) < 3:
        return result
    obs_mean = float(np.mean(obs))
    sim_mean = float(np.mean(sim))
    obs_sd = float(np.std(obs, ddof=1))
    sim_sd = float(np.std(sim, ddof=1))
    errors = sim - obs
    result["RMSE_m3s"] = float(np.sqrt(np.mean(errors ** 2)))
    result["MAE_m3s"] = float(np.mean(np.abs(errors)))
    obs_sum = float(np.sum(obs))
    if obs_sum != 0:
        bias = 100.0 * float(np.sum(errors)) / obs_sum
        result["PBIAS_percent"] = bias
        result["volume_bias_percent"] = bias
    nse_denominator = float(np.sum((obs - obs_mean) ** 2))
    if nse_denominator > 0:
        result["NSE"] = 1.0 - float(np.sum(errors ** 2)) / nse_denominator
    if obs_mean == 0 or sim_mean == 0 or obs_sd == 0 or sim_sd == 0:
        return result
    correlation = float(np.corrcoef(obs, sim)[0, 1])
    alpha = sim_sd / obs_sd
    beta = sim_mean / obs_mean
    gamma = (sim_sd / sim_mean) / (obs_sd / obs_mean)
    result.update({
        "Pearson_r": correlation,
        "alpha_sd_ratio": alpha,
        "beta_mean_ratio": beta,
        "gamma_cv_ratio": gamma,
        "KGE_2012_modified": 1.0 - math.sqrt(
            (correlation - 1.0) ** 2 + (gamma - 1.0) ** 2 + (beta - 1.0) ** 2
        ),
        "KGE_2009": 1.0 - math.sqrt(
            (correlation - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2
        ),
    })
    return result
