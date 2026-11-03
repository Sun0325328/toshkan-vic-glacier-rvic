"""Synthetic baseline preparation and routing; no glacier replacement applied."""

from pathlib import Path
from tempfile import TemporaryDirectory
from toshkan_workflow.preprocessing import read_daily_depths, prepare_source_volumes
from toshkan_workflow.daily_routing import route_daily


def main():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "synthetic_daily.csv"
        path.write_text(
            "date,grid_id,depth_mm,units\n"
            "2000-02-28,synthetic_grid,1,mm/day\n"
            "2000-02-29,synthetic_grid,2,mm/day\n", encoding="utf-8")
        daily = read_daily_depths(path, start_date="2000-02-28",
            end_date="2000-02-29", expected_grid_ids=["synthetic_grid"])
    prepared = prepare_source_volumes(daily, [
        {"source_id": "synthetic_source", "grid_id": "synthetic_grid", "m3_per_mm": 100},
    ])
    routed = route_daily(**prepared, kernels={"synthetic_source": [0.5, 0.5]},
                         outlets={"synthetic_source": "synthetic_outlet"})
    print("SYNTHETIC BASELINE ONLY; NO GLACIER REPLACEMENT; NO MODEL EXECUTION")
    for day, amount in zip(routed["dates"], routed["volume_m3_per_day"]["synthetic_outlet"]):
        print(day, "m3 water per day:", amount)


if __name__ == "__main__":
    main()
