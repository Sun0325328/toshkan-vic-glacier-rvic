"""Entirely synthetic: one grid day shared by two imaginary elevation bands."""
import pandas as pd
from toshkan_workflow.preprocessing.glacier_daily_forcing import daily_forcing


def main():
    hours = pd.date_range("2000-02-29", periods=24, freq="h")
    for label, offset, multiplier in [("A", 0, 1), ("B", -2, 2)]:
        result = daily_forcing(hours, [-2]*12 + [2]*12, [1]*24,
                               offset_c=offset, precipitation_multiplier=multiplier,
                               rain_start_c=-1, rain_full_c=1, melt_threshold_c=0)
        print(label, result.to_string())


if __name__ == "__main__":
    main()
