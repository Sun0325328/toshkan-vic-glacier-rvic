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
