# Daily glacier melt, storage and release

This module exposes the project's daily mass-process kernel, not VIC or RVIC source code. It preserves the original daily function and extracts its required state-schema and storage helpers without changing their expressions. The package import is changed; synthetic examples and tests are new. Local frozen-source records identify the source versions used by the formal operator and subsequent frozen-workflow replay. Internal records and research inputs are not distributed.

## Role and boundaries

The kernel applies sublimation demand to snow and firn, then melts snow, firn and ice in sequence using the remaining positive degree days. The ice degree-day factor is weighted by debris fraction. Water can refreeze up to available cold capacity, remain in liquid storage, or leave as rain-, snow-, firn- or ice-origin release. Refrozen water is added to firn; source tracking here describes the release components, not permanent molecular provenance.

Cold capacity is supplied by the caller. Monthly heat conduction, annual aging, state initialization, area evolution and forcing preparation are not implemented by this function. A successful daily calculation is not a full model validation or paper reproduction.

## Inputs and units

Use nonempty one-dimensional NumPy float arrays with aligned spatial units. State arrays must share a shape; forcing and area must be broadcast-compatible. Rain and snowfall are nonnegative mm per day, and positive degree days are degrees Celsius times days. Derive these from hourly phase partition and positive-temperature accumulation, not positive daily-mean temperature. Temperature thresholds and preprocessing are external.

Snow, firn and four liquid stores are mm water equivalent. Ice is volume in m3; area is m2 and ice density is kg/m3. Cold content is capacity in mm water equivalent, not additional water mass. Degree-day factors are mm water equivalent per degree Celsius per day. The caller supplies scientifically justified parameters; example parameters are invented.

Outputs include updated states, melt/refreezing/sublimation, four release depths and a mass residual. Convert each release depth to water volume using `depth_mm * applicable_area_m2 / 1000`. Align time and spatial support before using the existing glacier replacement module; do not add glacier water to an unchanged baseline, count area twice, or add alternative branches together. This batch does not implement that full coupling adapter.

## Run the synthetic example

Use Python 3.10 or newer and NumPy. No research data or external models are required. From the repository root with `src` on the Python path:

```bash
PYTHONPATH=src python examples/glacier_daily_demo.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

The example releases 1.8 m3 of water in one day over an invented 100 m2 unit. It is not a research estimate. Tests cover sequential melting, finite ice, debris weighting, refreezing, retention, sublimation, input preservation and invalid inputs.

## Preserved implementation limitations

The copied kernel retains its original guards, not a new comprehensive input schema. Callers must enforce nonempty physically appropriate arrays, consistent units and finite outputs; passing validation alone does not establish those scientific conditions. The storage helper is an internal dependency, not a separately hardened public input API. Extreme finite inputs can exceed floating-point range. No guard or physical expression was silently strengthened or relaxed for publication.

No real forcing, observed discharge, DEM, calibration table or initial-state array is included. The repository's existing licensing notice remains unchanged.
