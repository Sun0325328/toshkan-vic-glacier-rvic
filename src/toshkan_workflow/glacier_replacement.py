"""Daily water-volume replacement for one already aligned scenario.

This release adaptation implements the component sum used in the research
workflow, not its glacier solver, area allocation, or routing-source mapping.
"""

import math

GLACIER_COMPONENTS = (
    "rain_release", "snow_release", "firn_release", "ice_release",
)
LAND_COMPONENTS = (
    "runoff_rain", "baseflow_rain", "runoff_snow", "baseflow_snow",
    "runoff_initial", "baseflow_initial",
)


def _amount(value):
    if isinstance(value, bool):
        raise ValueError("Water volume must be numeric, not boolean")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Water volume must be finite and nonnegative")
    return value


def _components(values, names):
    if set(values) != set(names):
        raise ValueError("Component names must match the documented schema")
    return _amount(sum(_amount(values[name]) for name in names))


def replace_daily_water(baseline, removed, glacier, *, units):
    """Combine aligned daily volumes, in m3 of water per day.

    Inputs must describe the same date, spatial support, and scenario. The
    caller must establish that alignment before calling this scalar function.
    Separate scenarios must be evaluated separately, never added together.
    """
    if units != "m3 water per day":
        raise ValueError("Convert inputs to m3 water per day before replacement")
    baseline = _amount(baseline)
    removed_total = _components(removed, LAND_COMPONENTS)
    glacier_total = _components(glacier, GLACIER_COMPONENTS)
    if removed_total > baseline:
        raise ValueError("Removed contribution exceeds the corresponding baseline")
    increment = glacier_total - removed_total
    combined = _amount((baseline - removed_total) + glacier_total)
    return {
        "removed": removed_total,
        "glacier_release": glacier_total,
        "replacement_increment": increment,
        "combined": combined,
    }
