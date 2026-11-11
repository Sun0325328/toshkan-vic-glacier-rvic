# From glacier replacement to routed flow

Use one daily table for baseline source volumes and one for the signed
replacement (new release minus the displaced contribution). Both are in
cubic metres of water per day. A negative correction is not negative
discharge: do not clip it or add the entire new release to the baseline.

Supply consecutive midnight dates and identically ordered source columns.
Each column of the original travel-time weights must sum to one, with rows
ordered by lag in days from zero. For each source multiply each weight by
exp(-loss_per_day * lag_days). Do not renormalize afterwards. Route the
baseline and the signed correction separately with these same weights, then
add. Only divide the resulting daily volume by 86400 to report mean flow
in cubic metres per second. The returned series includes the convolution
tail and assumes no inflow before the supplied interval.

With src on PYTHONPATH run python examples/glacier_replacement_routing_demo.py.
All example inputs are invented. Of 90 units after replacement, 45 arrive
today and 22.5 tomorrow. The missing 22.5 represent modeled transmission
loss; tomorrow's 22.5 are delayed water, not another loss.

This is a one-outlet method example, not the RVIC executable, a basin
parameter set or a station hydrograph. Supply source volumes already on the
correct area basis and group sources by destination before calling. No
calibration, clipping or diagnosis of physical plausibility is performed.
