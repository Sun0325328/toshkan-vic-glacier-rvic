"""Entirely synthetic volumes and weights; no basin data or model launch."""

from toshkan_workflow.glacier_replacement import (
    GLACIER_COMPONENTS, LAND_COMPONENTS, replace_daily_water,
)
from toshkan_workflow.daily_routing import route_daily

water = replace_daily_water(
    100, dict.fromkeys(LAND_COMPONENTS, 5),
    dict.fromkeys(GLACIER_COMPONENTS, 5), units="m3 water per day",
)["combined"]
result = route_daily(
    ["2001-01-01"], {"synthetic_source": [water]},
    {"synthetic_source": [0.5, 0.3, 0.2]},
    {"synthetic_source": "synthetic_outlet"}, units="m3 water per day",
)
print("SYNTHETIC_ONLY: replacement =", water, "m3 water per day")
for day, volume, flow in zip(
    result["dates"], result["volume_m3_per_day"]["synthetic_outlet"],
    result["mean_flow_m3_per_second"]["synthetic_outlet"],
):
    print(day, "volume_m3_per_day=", volume, "mean_flow_m3_per_second=", flow)
