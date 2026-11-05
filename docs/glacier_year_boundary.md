# Starting a glacier trajectory and updating its geometry

The daily mass step needs starting stores. For already verified inputs, the initialization adapter keeps the two endpoint scenarios separate. Supply a mapping with one `state__<field>` array per daily state field in (2, bands) order, temperature in degrees Celsius in (2, bands, 10) order, and signed five-year balance history in mm water equivalent in (2, bands, 5) order. Supply one aligned initial ice-volume vector (m3). This registered volume replaces the endpoint ice volume in both alternatives; do not add their volumes. Outputs are independent copies, flattened in branch-major order. Select the corresponding band slice when advancing a single branch.

This is the array-assembly part of the project loader, not an estimator of historical ice thickness or a spin-up algorithm. The public adapter adds finite-value, dimension and nonnegative-storage checks. It does not verify files, hashes, dates, band IDs, elevation order, units or geographic alignment; these remain prerequisites. Temperature and balance history may be negative. The original internal registry and real endpoints are not distributed.

At year end, pass one scenario's simulated ice volume by band (m3), its registered band areas (m2), bed and surface elevations (m), and independently justified retreat coefficients to `synchronize_multiyear_geometry`. Loss is redistributed using a nonnegative elevation-dependent thickness-change curve. For positive balance, local target volumes set thickness within the registered footprint, not by reversing the retreat curve. A registered band may become active; no new band area is introduced. Near-neutral totals and extinction have explicit branches. Exceptional terminal local-balance routes remain opt-in with the original restrictions. Inspect the returned route and closure; numerical closure is not a validation of observed glacier change.

Geometry types, helpers and annual transition logic are extracted from the project operators. This module does not advance a full year, adjust forcing, remap other stores, select a curve for a real glacier or route discharge. Public dependencies: Python 3.10+ and NumPy. With the repository's src directory on the Python path, run:

```bash
PYTHONPATH=src python examples/glacier_year_boundary_demo.py
PYTHONPATH=src python -m unittest discover -s tests
```

All example elevations, volumes, stores and coefficients are invented; they are not a DEM, study calibration, or measured data.
