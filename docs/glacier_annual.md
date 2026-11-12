# Annual glacier execution

This addition connects the existing daily mass kernel to monthly thermal updates
and year-end aging. It also exposes grid-volume aggregation. These are project
operators extracted from the research workflow. Imports refer to the public
package. The annual and aggregation interfaces also validate integer indices
before conversion. Examples and tests are specific to this release.

## Place in the workflow

1. Prepare and independently justify forcing, parameters, spatial links and initial states.
2. Run `glacier.annual.run_resumable_one_year_daily_cycle` for one calendar year.
3. Apply the separate `glacier.geometry` update to the resulting ice volumes.
4. Before another year, consistently update forcing supports, surface elevations
   and any required state remapping. The annual function does not do this step.
5. Align separately exported glacier releases with the baseline before replacement
   and routing. Neither coupling nor outlet discharge is computed here.

The example demonstrates steps 2 and 3 only. Initialization assembly from the
previous module is not historical ice-mass reconstruction or spin-up convergence.
This is not a complete multiyear simulation launcher or a paper reproduction.

## Physical sequence

Daily rain, snowfall and positive degree days drive the existing daily kernel.
Monthly refreezing is debited from the thermal profile's cold capacity. Heat
conduction is applied when monthly melt is at most the original method's 2 mm
water-equivalent limit, with adaptive substeps and the retained Fourier bound.
The caller supplies layer properties and either a zero-flux or fixed-temperature
lower boundary. For zero-flux rows, the fixed-temperature value must be NaN.

On December 31, retained snow enters firn. The original AC01 and AC02 method
branches are preserved, not automatically selected: AC01 updates a five-year
balance memory without a fixed firn-to-ice fraction; AC02 requires the explicitly
registered 0.25 sensitivity fraction. These method constants are not a calibrated
parameter table. An explicitly declared terminal partial year has no December 31
aging step. No spin-up length or calibrated thermal/degree-day factors are provided.

## Array and unit contract

- Use aligned, nonempty one-dimensional mass states and positive areas in m2.
  Snow, firn and liquid stores are mm water equivalent; ice volume is m3 of ice.
  Cold capacity is not additional water mass.
- Forcing arrays have shape `(days, forcing_supports)`: rain/snow in mm per day,
  positive degree days in degrees Celsius times days, and mean air temperature in
  degrees Celsius. PDD and rain/snow phase must be prepared at the required source
  resolution; do not replace hourly positive-temperature accumulation with the
  positive part of daily mean temperature.
- Dates must represent contiguous midnight, timezone-naive daily steps within one
  year, beginning January 1. Explicitly pass 365 or 366 as `expected_day_count`,
  or the declared terminal partial-year length and end date.
- Pass integer index arrays with valid ranges; do not pass fractional indices.
  Each state row's area is counted once within its physical member. Alternative
  branches are not additional physical area and must not be added together.
- `daily_sparse_grid_flux_m3` and `daily_member_envelopes_m3` contain **m3 water
  per day**, even though their inherited component keys end in `_mm`. The separate
  `release_totals_mm` values remain accumulated depths. Do not convert volume twice.
- The grid aggregator uses `depth_mm * area_m2 / 1000`. Sparse index -1 deliberately
  excludes a row. Include all intended rows for a complete physical total. Distinct
  scenario/grid combinations require separate sparse supports.
- Member minimum/median/maximum envelopes are summaries across alternatives, not
  separate additive water sources and not necessarily one consistent trajectory.

## Checkpoints: limited, explicit scope

The inherited `checkpoint_roundtrip=True` option serializes and reloads a checkpoint
in memory during the same call, then continues. NPZ loading disables pickle.
`checkpoint_payload` is returned for inspection. This proves serialization behavior
in the tests, **not** restart of an externally interrupted process. There is no
external checkpoint input, atomic disk writer or restart scheduler in this batch.
The checkpoint index must also satisfy the inherited validator's `1 <= index < 365`
restriction, including leap years. The default index 183 is suitable for full years;
short terminal runs require an explicit earlier index.

## Run the synthetic example

Dependencies: Python 3.10 or newer, NumPy and pandas. Tested versions are recorded
in the local publication review; no claim is made for every dependency version.
Run from the repository root:

```bash
PYTHONPATH=src python examples/glacier_annual_demo.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

All example weather, areas, geometry, starting states and configurable parameters
are invented. The example runs one small synthetic year twice to compare states
and releases with and without checkpoint serialization. No research inputs,
observed discharge, DEM, real coordinates, fitted parameter tables or state files
are included. No external models or data downloads are launched.

## Scope and limitations

Source lineage links the annual and aggregation operators to the frozen formal
workflow. The thermal module is a required direct dependency of the annual
operator; its current source is separately hash-pinned locally rather than being
a row in that frozen registry. Do not treat import linkage as an independent
historical binary-reproduction claim. Local source records are not distributed.

The original floating-point tolerances are retained. Callers must supply midnight daily
dates, valid dimensions, independently justified physical inputs and finite outputs.
Extreme finite values may overflow. The AC02 mass check can be sensitive to
floating-point summation at very large stores; no threshold has been relaxed here.
Tests establish bounded software behavior, not hydrological validity. Full forcing
preparation, multiyear orchestration, disk recovery and VIC/RVIC coupling remain
outside this addition. The repository's existing licensing notice is unchanged.
