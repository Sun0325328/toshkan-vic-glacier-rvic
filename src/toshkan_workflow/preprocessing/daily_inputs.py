"""Read a small, explicit CSV interface, not native VIC output files."""

import csv
from datetime import date, timedelta
import math
from pathlib import Path


def _iso_day(value):
    if not isinstance(value, str):
        raise ValueError("Dates must be YYYY-MM-DD strings")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("Dates must be YYYY-MM-DD strings")
    return result


def _identifier(value):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("Identifiers must be nonempty strings without outer whitespace")
    return value


def _number(value, *, positive=False):
    if isinstance(value, bool):
        raise ValueError("Boolean amounts are not accepted")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("A finite number is required") from exc
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError("Amount must be finite and nonnegative; factors must be positive")
    return result


def read_daily_depths(path, *, start_date, end_date, expected_grid_ids):
    """Return dates and per-grid nonnegative depths from an exact CSV schema.

    Columns: date,grid_id,depth_mm,units. Every units entry must be mm/day.
    Rows must be chronological within each grid; grids may be interleaved.
    The caller declares the inclusive expected range and exact grid set.
    No filling, cropping, sorting of dates, or physical unit inference occurs.
    """
    first, last = _iso_day(start_date), _iso_day(end_date)
    if first > last:
        raise ValueError("Start date must not follow end date")
    grids = list(expected_grid_ids)
    if not grids or any(_identifier(g) != g for g in grids) or len(set(grids)) != len(grids):
        raise ValueError("Expected grid identifiers must be nonempty and unique")
    dates = [(first + timedelta(days=i)).isoformat()
             for i in range((last - first).days + 1)]
    depths = {g: [] for g in grids}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = ["date", "grid_id", "depth_mm", "units"]
        if reader.fieldnames is None or len(reader.fieldnames) != 4 or set(reader.fieldnames) != set(fields):
            raise ValueError("CSV columns must be date,grid_id,depth_mm,units, without duplicates")
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed CSV row {line}")
            grid = _identifier(row["grid_id"])
            if grid not in depths:
                raise ValueError(f"Unexpected grid at row {line}")
            if row["units"] != "mm/day":
                raise ValueError(f"Expected explicit mm/day units at row {line}")
            _iso_day(row["date"])
            index = len(depths[grid])
            if index >= len(dates) or row["date"] != dates[index]:
                raise ValueError(f"Missing, duplicate, unordered or out-of-range date at row {line}")
            depths[grid].append(_number(row["depth_mm"]))
    if any(len(series) != len(dates) for series in depths.values()):
        raise ValueError("Incomplete expected date-grid coverage")
    return {"dates": dates, "depths_mm_per_day": depths, "units": "mm/day"}
