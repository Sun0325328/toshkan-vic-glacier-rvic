"""Small full-convolution reference for aligned, nonnegative daily volumes.

Not the production RVIC runner, parameter generator, or static-loss model.
"""

from datetime import date, timedelta
import math


def _nonnegative(value):
    if isinstance(value, bool):
        raise ValueError("Boolean amounts are not supported")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Values must be finite and nonnegative")
    return value


def route_daily(dates, source_volumes, kernels, outlets, *, units):
    """Route one scenario, retaining the complete convolution tail.

    dates: consecutive ISO Gregorian dates; lag zero arrives on the same date.
    The three mappings must have identical nonempty string source identifiers.
    Each source has one volume per date, a nonempty lag-weight sequence, and
    one nonempty string outlet identifier. Weights must sum to one within
    1e-10; they are never renormalized. No preceding inflow is assumed.
    """
    if units != "m3 water per day":
        raise ValueError("Expected m3 water per day")
    dates = list(dates)
    if not dates:
        raise ValueError("Dates cannot be empty")
    parsed = []
    for item in dates:
        if not isinstance(item, str):
            raise ValueError("Dates must be ISO strings")
        day = date.fromisoformat(item)
        if day.isoformat() != item:
            raise ValueError("Use YYYY-MM-DD dates")
        parsed.append(day)
    if any(b - a != timedelta(days=1) for a, b in zip(parsed, parsed[1:])):
        raise ValueError("Dates must be unique, ordered and consecutive")
    keys = list(source_volumes)
    if not keys or any(not isinstance(k, str) or not k for k in keys):
        raise ValueError("Nonempty string source identifiers required")
    if set(keys) != set(kernels) or set(keys) != set(outlets):
        raise ValueError("Source identifiers must match exactly")
    volumes, weights = {}, {}
    for key in keys:
        volumes[key] = [_nonnegative(v) for v in source_volumes[key]]
        weights[key] = [_nonnegative(v) for v in kernels[key]]
        if len(volumes[key]) != len(dates):
            raise ValueError("Each source must have one amount per date")
        if not weights[key] or not math.isclose(
            math.fsum(weights[key]), 1.0, rel_tol=0, abs_tol=1e-10
        ):
            raise ValueError("Routing weights must sum to one")
        if not isinstance(outlets[key], str) or not outlets[key]:
            raise ValueError("Nonempty string outlet identifiers required")
    size = len(dates) + max(map(len, weights.values())) - 1
    output_dates = [(parsed[0] + timedelta(days=i)).isoformat() for i in range(size)]
    result = {outlet: [0.0] * size for outlet in sorted(set(outlets.values()))}
    for key in keys:
        target = result[outlets[key]]
        for i, volume in enumerate(volumes[key]):
            for lag, weight in enumerate(weights[key]):
                target[i + lag] += volume * weight
                if not math.isfinite(target[i + lag]):
                    raise ValueError("Routed volume overflow")
    return {
        "dates": output_dates,
        "volume_m3_per_day": result,
        "mean_flow_m3_per_second": {
            outlet: [v / 86400.0 for v in values] for outlet, values in result.items()
        },
    }
