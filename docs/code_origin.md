# Code Origin and Scope

The replacement example is a small release adaptation of the component-sum
calculation used in the Toshkan research workflow. It is not a copy of the full
research execution script. It exposes explicit scalar inputs instead of private
file paths, internal registries, and basin-wide arrays, and includes additional
input guards and synthetic tests.

The original calculation combines four glacier-area release components and
subtracts six land-surface contributions. The public example preserves that
arithmetic meaning, but it does not reproduce source selection, spatial
allocation, routing, or the numerical implementation of whole-basin arrays.
Small example tests do not establish full-workflow equivalence or hydrological
validation.

No VIC or RVIC source code is bundled in this draft. These upstream models retain
their own authorship and licensing terms. The current Python example uses only
the standard library. No project-wide software license has yet been selected;
this document is attribution and scope information, not a license grant.

## Daily-Routing Reference

The daily-routing module is a newly organized standard-library reference for
the discrete-convolution operation used in the research workflow. Production
calculations use blocked and compressed routing implementations; a separate
independent check uses direct convolution. The release is neither that complete
production runner nor a byte-identical copy of its independent check.

The release accepts explicit source identifiers, dates, volumes, lag weights,
and destinations instead of private arrays and internal dependencies. It routes
nonnegative combined volumes for one scenario, whereas the production workflow
also handles signed replacement increments separately. This distinction is
documented rather than hidden behind a claim of identical interfaces.

No upstream VIC/RVIC source or actual routing parameters are included. This
module does not generate RVIC parameters, implement the full routing workflow,
or reproduce its static attenuation stage. Synthetic tests verify this small
reference implementation, not the scientific validity of basin parameters or
the equivalence of the complete published research workflow.
