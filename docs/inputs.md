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

## Daily Routing

`route_daily(dates, source_volumes, kernels, outlets, units=...)` processes one
scenario per call. Pass `units="m3 water per day"`. This interface accepts
nonnegative total volumes after replacement, not signed replacement increments.

- `dates`: nonempty, consecutive, ordered ISO dates (`YYYY-MM-DD`), Gregorian
  calendar. Leap days must be included. Each value covers that full day.
- `source_volumes`: mapping from source identifiers to daily water volumes.
- `kernels`: mapping from the same identifiers to nonnegative lag weights;
  index zero means arrival on the same date. Weight sequences may differ in
  length. Each must sum to one within an absolute tolerance of `1e-10`.
- `outlets`: mapping from the same identifiers to outlet identifiers. Both
  source and outlet identifiers must be nonempty strings. Many sources may
  share an outlet, but each source has exactly one destination in this example.

Source identifiers must match exactly across all three mappings; mapping order
does not define correspondence. Values must be finite and nonnegative. Weights
are checked, never renormalized. Source area conversion and geographic mapping
remain the caller's responsibility; identifiers alone cannot validate geography.

The result contains `dates`, `volume_m3_per_day`, and
`mean_flow_m3_per_second`. The last two are outlet-to-series mappings. Output
starts on the first input date and has `number_of_days + longest_kernel - 1`
records, including the full routing tail. Divide daily volume by 86,400 to obtain
daily mean flow in cubic metres per second. These are not instantaneous flows.

No inflow before the first date is represented. Real simulations require an
appropriate preceding history or routing state. No automatic warm-up, time-zone
conversion, output-date shift, evaluation-window crop, or gap filling is applied.
Separate scenarios must be routed separately and must not be added together.
