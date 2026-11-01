"""Synthetic single-day, single-support example; not research output."""

import json
from toshkan_workflow.glacier_replacement import replace_daily_water


def main():
    removed = dict(runoff_rain=10, baseflow_rain=5, runoff_snow=8,
                   baseflow_snow=4, runoff_initial=2, baseflow_initial=1)
    glacier = dict(rain_release=5, snow_release=10, firn_release=2, ice_release=3)
    result = replace_daily_water(100, removed, glacier, units="m3 water per day")
    print(json.dumps({"synthetic": True, "units": "m3 water per day", **result}, indent=2))


if __name__ == "__main__":
    main()
