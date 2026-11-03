"""Convert declared daily depths with supplied, externally verified factors."""

from datetime import timedelta
import math
from .daily_inputs import _identifier, _iso_day, _number


def prepare_source_volumes(daily, mapping):
    """Return dates, source_volumes and units for one scenario.

    Each mapping record has source_id, grid_id, m3_per_mm. A grid may have
    several sources, but source IDs are unique and all input grids are used.
    Factors already include any required spatial weighting. This function
    cannot establish their geographic validity or determine glacier replacement.
    """
    if set(daily) != {"dates", "depths_mm_per_day", "units"} or daily["units"] != "mm/day":
        raise ValueError("Expected explicit daily-depth schema and mm/day units")
    dates = list(daily["dates"])
    parsed = [_iso_day(d) for d in dates]
    if not parsed or any(b-a != timedelta(days=1) for a, b in zip(parsed, parsed[1:])):
        raise ValueError("Dates must be nonempty and consecutive")
    depths = {}
    for grid, values in daily["depths_mm_per_day"].items():
        depths[_identifier(grid)] = [_number(v) for v in values]
        if len(depths[grid]) != len(dates):
            raise ValueError("Depth series length must match dates")
    if not depths:
        raise ValueError("No input grids")
    sources, used_grids = {}, set()
    for record in mapping:
        if set(record) != {"source_id", "grid_id", "m3_per_mm"}:
            raise ValueError("Mapping schema must be source_id,grid_id,m3_per_mm")
        source, grid = _identifier(record["source_id"]), _identifier(record["grid_id"])
        if source in sources or grid not in depths:
            raise ValueError("Duplicate source or missing input grid")
        factor = _number(record["m3_per_mm"], positive=True)
        values = [v * factor for v in depths[grid]]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Converted water volume overflow")
        sources[source] = values
        used_grids.add(grid)
    if used_grids != set(depths):
        raise ValueError("Mapping must cover every supplied grid")
    return {"dates": dates, "source_volumes": sources, "units": "m3 water per day"}
