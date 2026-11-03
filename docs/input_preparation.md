# Preparing Daily Inputs for Routing

This release adapter connects explicit daily-depth records to the published
daily-routing interface. It uses only the Python standard library and neither
reads research registries nor starts VIC or RVIC. It is not a native VIC output
parser, geographic allocation tool, or complete basin preprocessing workflow.

## Daily CSV

`read_daily_depths(path, start_date=..., end_date=..., expected_grid_ids=...)`
reads UTF-8 CSV with exactly four uniquely named columns:

```csv
date,grid_id,depth_mm,units
2000-02-28,synthetic_grid,1,mm/day
2000-02-29,synthetic_grid,2,mm/day
```

All values above are synthetic. Declare the inclusive expected period and exact
grid set explicitly. Every grid must have one record for each day, including
leap days. Records must be chronological within each grid; different grids may
be interleaved. Extra or missing grids, duplicate or missing days, malformed
rows, unknown units and nonfinite or negative depths are rejected. The file is
opened read-only. Missing files raise an error. There is no gap filling, date
sorting, cropping, unit inference or automatic correction.

Depths represent an already selected nonnegative daily runoff quantity on a
known spatial support. They are not precipitation forcing, signed evaporation,
or signed glacier replacement increments. Field selection from model output
must be performed and justified before using this CSV interface.

## Source Mapping and Conversion

`prepare_source_volumes(daily, mapping)` accepts the reader result and records
with exactly `source_id`, `grid_id`, and `m3_per_mm`. Each source identifier is
unique. All supplied grids must be used. Several sources may reference one
grid, provided their externally verified conversion factors represent the
intended spatial allocation.

For each date and source, `volume = depth_mm * m3_per_mm`. The factor must be
finite and positive and already includes any required spatial weighting. Do
not multiply by area or divide by 1,000 a second time. These checks cannot
determine whether real factors, geographic support, or overlapping areas are
scientifically correct. Factors are never inferred from private research data.

The return value contains `dates`, `source_volumes`, and
`units="m3 water per day"`. Pass it to `route_daily` with separate `kernels` and
`outlets` mappings using exactly the same source identifiers. No automatic
selection or combination of scenarios occurs. Output routing dates retain the
complete arrival tail rather than being cropped to the input period.

## Run the Synthetic Baseline Example

From the repository root, with `src` on the Python import path:

```bash
PYTHONPATH=src python -B examples/prepare_routing_inputs_demo.py
PYTHONPATH=src python -B -m unittest discover -s tests -v
```

In PowerShell, set `$env:PYTHONPATH="src"` and use the same Python commands
without the `PYTHONPATH=src` prefix. The example writes only a small synthetic
CSV in an automatically cleaned temporary directory. Two depths of 1 and 2,
a synthetic factor of 100, and lag weights of 0.5 and 0.5 produce daily arrivals
of 50, 150 and 100 cubic metres, totalling 300.

This is a **baseline-only** example: it does not perform glacier replacement.
For a replacement scenario, the applicable baseline and release/removal
components must first be aligned on the same spatial and temporal support and
combined using the replacement interface. Do not label unmodified VIC volumes
as replacement-adjusted totals. Signed increments cannot be passed directly
to the current nonnegative daily-routing interface.

## Origin and Limits

The research workflow explicitly checks dates and source identities and applies
verified depth-to-volume factors when assembling routing inputs. This public
adapter preserves those interface principles, but replaces internal file
formats, registries and fixed array sizes with an explicit CSV and mappings.
It is newly organized release code, not a byte-identical production runner.

The production path reviewed for this release recovers existing conversion
factors from frozen depth and source-volume series and checks their consistency.
That recovery process is not implemented here; supplied synthetic factors do
not reproduce the real basin allocation. Expected input and output dates must
be specified according to each artifact's role, not inferred from a period
title. No actual parameters, observations, DEM, upstream model source, or
research results are included. Small tests establish interface behavior, not
hydrological validation or complete research reproducibility. The repository's
existing licensing notice remains unchanged.
