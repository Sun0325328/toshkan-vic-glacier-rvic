# From Daily Water Volumes to Outlet Flow

Replacement determines how much water enters the routing calculation. Routing
determines when that water arrives at an outlet. These are distinct operations.

For a source with daily volume V and lag weights h, the contribution arriving
on day t is the sum of `V[t - lag] * h[lag]` over valid preceding input days.
Contributions from sources assigned to the same outlet are added. This is a
discrete convolution, using zero input outside the supplied period.

## Synthetic Example

The replacement example gives `100 - 30 + 20 = 90` cubic metres of water.
With illustrative weights `[0.5, 0.3, 0.2]`, that day's water arrives as 45,
27, and 18 cubic metres on the same day and the following two days. The sum
remains 90. Subsequent input days overlap with these arrivals.

Run `examples/daily_routing_demo.py` with `src` on the Python import path.
No external files, credentials, observation records, or basin parameters are used.

## Time, Units, and Conservation

The complete output tail is retained. Cropping output to the input period can
exclude water still in transit; that excluded water must not be described as a
physical loss. Volume conservation applies to the full output, subject to
floating-point summation and the stated weight-sum tolerance. The module never
rescales supplied weights to make a check pass.

Daily mean flow is daily water volume divided by 86,400 seconds. Area weighting
and conversion from millimetres must happen before this interface. A valid
source identifier does not establish correct spatial support or prevent the
caller from supplying overlapping areas under different identifiers.

## Relationship to the Research Workflow

The formal workflow uses supplied routing responses, source-to-outlet mapping,
and an explicitly aligned output window. It also includes a separately treated
static attenuation stage. This example only demonstrates routing without that
attenuation; it does not disclose fitted parameters or establish natural river
transmission losses. No physical tuning is performed here.

The formal execution separates baseline water and signed replacement increments
before combining routed contributions. For fixed linear routing weights and
the same temporal and spatial support, routing the already combined volume has
the same algebraic meaning. This example accepts only nonnegative combined
volumes and does not reproduce the production performance optimizations.

Use separate calls for separate scenarios. Full-basin initialization, RVIC
parameter generation, observed-flow evaluation, and model calibration are not
implemented. Passing the example tests is not full-workflow validation.
