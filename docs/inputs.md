# Inputs and Outputs

`replace_daily_water` handles one date, one spatial support, and one selected
scenario at a time. It accepts numerical values rather than research files.
The caller is responsible for date, grid, area, and scenario alignment. This
function cannot infer or verify alignment from scalar numbers.

All amounts are cubic metres of water per day. Pass `units="m3 water per day"`.
The function does not convert millimetres, ice volume, or cubic metres per second.

| Argument | Meaning |
| --- | --- |
| `baseline` | Original total land-surface water for the selected support |
| `removed` | Dictionary containing the six land-surface contributions to remove |
| `glacier` | Dictionary containing four external glacier-area release components |

The exact keys for `removed` are `runoff_rain`, `baseflow_rain`, `runoff_snow`,
`baseflow_snow`, `runoff_initial`, and `baseflow_initial`. The last two refer to
water originating from initial storage, not the current amount of stored water.

The exact keys for `glacier` are `rain_release`, `snow_release`, `firn_release`,
and `ice_release`. These are water releases, not melt production before storage
or refreezing. All six and four keys are required, including zero contributions.
Missing components must not silently be interpreted as zero.

The returned dictionary contains `removed`, `glacier_release`,
`replacement_increment`, and `combined`. The first two are component sums;
the increment equals release minus removal, and combined equals baseline plus
increment. A negative increment is valid.

Inputs must be finite and nonnegative; the removed total must not exceed the
baseline. These example guards are strict: they do not apply clipping, filling,
or a rounding tolerance. Real inputs with uncertain units or inconsistent
coverage require review before use, not relaxed guards.

There is no data download, model execution, or automatic scenario selection.
