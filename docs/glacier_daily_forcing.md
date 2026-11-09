# Hourly grid weather to daily glacier inputs

One call represents one band. Supply hourly grid air temperature (degrees C)
and precipitation depth accumulated during each hour (mm, not a rate or a
running total). Supply the already selected band offset and precipitation
multiplier. Do not apply either adjustment before calling. The function
cannot detect weather already adjusted upstream. It does not derive parameter
values, match real grids, or remap bands as a glacier changes shape.

Grid weather -> apply band adjustments once -> split hourly precipitation
into rain and snow -> aggregate complete days -> daily glacier process input.

| Daily output | Unit | Meaning |
|---|---|---|
| rain_input_mm | mm | Sum of hourly rain |
| snowfall_input_mm | mm water equivalent | Sum of hourly snowfall |
| positive_degree_days_c_day | degree C day | Sum of positive hourly temperature excess above the supplied melt threshold divided by 24 |
| mean_air_temperature_c | degrees C | Arithmetic mean of adjusted hourly temperatures |

The rain fraction is zero at or below the lower threshold, one at or above
the upper threshold, and linear between them. Snow is adjusted precipitation
minus rain. A mean temperature of zero does not imply zero positive degree
days. These are weather inputs, not melt amounts or discharge.

Public interface checks require consecutive complete days starting at midnight
on a fixed time basis. No timezone conversion, gap filling, or date sorting
is performed. Arrays are positional; pandas Series must already match the
supplied time index. Dates label the start of each day.

With the repository's source directory on PYTHONPATH, run
`python examples/glacier_daily_forcing_demo.py`. Both bands and all weather
and parameter values in that example are invented. Band A should produce
12 mm rain, 12 mm snowfall and 1 degree C day; band B should produce
12 mm rain, 36 mm snowfall and zero positive degree days.
