"""Full-tail daily routing for sources draining to one outlet."""
import numpy as np
import pandas as pd


def route_replacement(baseline, delta, weights, *, loss_per_day):
    """Route aligned daily water volumes (m3/day); kernel rows are day lags."""
    if not all(isinstance(x, pd.DataFrame) for x in (baseline, delta, weights)):
        raise ValueError("expected three labeled tables")
    dates = baseline.index
    if (baseline.empty or not isinstance(dates, pd.DatetimeIndex)
            or dates.tz is not None or dates.hasnans
            or not dates.equals(dates.normalize())
            or not dates.equals(pd.date_range(dates[0], periods=len(dates), freq="D"))
            or not dates.equals(delta.index)):
        raise ValueError("expected matching consecutive midnight dates")
    keys = baseline.columns
    if (not keys.is_unique or not all(isinstance(k, str) and k for k in keys)
            or not keys.equals(delta.columns) or not keys.equals(weights.columns)):
        raise ValueError("source labels and order must match")
    if weights.empty or not weights.index.equals(pd.RangeIndex(len(weights))):
        raise ValueError("kernel rows must be ordered lags starting at zero")
    v, d, w = (x.to_numpy(dtype=float) for x in (baseline, delta, weights))
    rate = float(loss_per_day)
    if (not all(np.isfinite(x).all() for x in (v, d, w))
            or (v < 0).any() or (w < 0).any() or not np.isfinite(rate) or rate < 0
            or not np.allclose(w.sum(axis=0), 1, atol=1e-10, rtol=0)):
        raise ValueError("invalid volumes, original weights or loss rate")
    kernel = w * np.exp(-rate * np.arange(len(w), dtype=float))[:, None]
    def route(values):
        return sum(np.convolve(values[:, j], kernel[:, j]) for j in range(len(keys)))
    base, correction = route(v), route(d)
    total = base + correction
    if not all(np.isfinite(x).all() for x in (base, correction, total)):
        raise ValueError("nonfinite routed result")
    return pd.DataFrame({"baseline_m3_day": base, "delta_m3_day": correction,
                         "total_m3_day": total, "mean_flow_m3_s": total / 86400},
                        index=pd.date_range(dates[0], periods=len(total), freq="D"))
