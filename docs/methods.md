# Glacier and Land-Surface Runoff Replacement

This draft accompanies a scalar replacement function and synthetic example.
It does not implement the full research workflow.

## Avoiding Double Counting

A land-surface simulation already produces water over the area occupied by
glaciers. Simply adding external glacier water release would count contributions
from that area twice. The replacement calculation is:

```text
combined water = original land-surface water
                 - land-surface water assigned to the replacement area
                 + external glacier water release
```

The external release comprises rainfall-derived water, snowmelt, firn melt, and
ice melt. The removed land-surface contribution comprises surface runoff and
baseflow from each of three origins: rainfall, snow, and initial stored water.
Baseflow here refers to drainage from the lower soil layer in VIC.

The glacier replacement increment is external release minus the removed
land-surface contribution. It can be positive or negative; it is not the same
quantity as total glacier release. Source-origin components must not be added
again to totals that already include them.

## Matching Inputs

All quantities must refer to the same date, spatial support, and water-volume
basis. The source workflow represents these daily quantities in cubic metres of
water per day. Inputs in millimetres require the appropriate area conversion
before combination; this document does not prescribe an unverified area rule.

Alternative initial-state branches are separate simulations, not additive
contributions. The registered mapping from a glacier grid to routing-source
records must also be retained: a grid can appear in more than one routing-source
record. Those records are not automatically duplicates to remove or basin-wide
volumes to sum without reference to routing semantics.

## Boundaries

Replacement prepares water contributions for downstream routing. It does not
calculate glacier melt, solve river routing, or estimate transmission losses.
The first example will use synthetic inputs and will not reproduce the full
research simulation or establish its physical accuracy.
