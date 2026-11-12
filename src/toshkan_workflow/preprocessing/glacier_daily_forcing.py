"""Aggregate unadjusted hourly grid weather for one elevation band at a time."""

import numpy as np
import pandas as pd


def daily_forcing(hours, temperature_c, precipitation_mm, *, offset_c,
                  precipitation_multiplier, rain_start_c, rain_full_c,
                  melt_threshold_c):
    """Return daily rain, snow, positive degree days and mean air temperature."""
    if not isinstance(hours, pd.DatetimeIndex) or hours.empty or hours.hasnans:
        raise ValueError("expected a nonempty DatetimeIndex without missing times")
    if hours.tz is not None:
        raise ValueError("supply timezone-naive hours on a single fixed time basis")
    if (hours[0] != hours[0].normalize() or len(hours) % 24
            or not hours.equals(pd.date_range(hours[0], periods=len(hours), freq="h"))):
        raise ValueError("expected consecutive complete midnight-to-midnight days")

    def vector(values):
        if isinstance(values, pd.Series) and not values.index.equals(hours):
            raise ValueError("series timestamps do not match hours")
        array = np.asarray(values, dtype=float)
        if array.shape != (len(hours),) or not np.isfinite(array).all():
            raise ValueError("invalid hourly vector")
        return array

    params = np.asarray([offset_c, precipitation_multiplier, rain_start_c,
                         rain_full_c, melt_threshold_c], dtype=float)
    if params.shape != (5,) or not np.isfinite(params).all():
        raise ValueError("expected five finite scalar parameters")
    offset, multiplier, lower, upper, threshold = params
    t = vector(temperature_c)
    p = vector(precipitation_mm)
    if multiplier <= 0:
        raise ValueError("precipitation multiplier must be positive")
    if upper <= lower or (p < 0).any():
        raise ValueError("invalid precipitation or phase thresholds")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        t = (t + offset).reshape(-1, 24)
        p = (p * multiplier).reshape(-1, 24)
        fraction = np.where(t <= lower, 0., np.where(t >= upper, 1.,
                            (t - lower) / (upper - lower)))
        rain = p * fraction
        return pd.DataFrame({
            "rain_input_mm": rain.sum(axis=1),
            "snowfall_input_mm": (p - rain).sum(axis=1),
            "positive_degree_days_c_day": np.maximum(t - threshold, 0.).sum(axis=1) / 24.,
            "mean_air_temperature_c": t.mean(axis=1),
        }, index=hours[::24])
