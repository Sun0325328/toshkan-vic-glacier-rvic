# Running the public workflow examples

Use this guide to try the published modules without supplying basin inputs.
The examples are separate synthetic cases, not consecutive stages that generate
the inputs to one another. Their outputs are not Toshkan simulation results.

## Setup

From the repository root, use a clean Python environment. The tested combination
is Python 3.12.14 with the direct dependencies in [requirements.txt](../requirements.txt).
These pins are a tested pair, not minimum versions or a lock on transitive packages.
No VIC or RVIC executable is required for these examples.

```bash
python -m pip install -r requirements.txt
export PYTHONPATH=src
python -B examples/daily_routing_demo.py
python -B -m unittest discover -s tests -v
```

In Windows PowerShell replace the export line with `$env:PYTHONPATH="src"`.
Each example below can be run with `python -B examples/<filename>` from the
repository root. Run one at a time; no station, terrain or calibration files
are needed.

## Choose an example

| Question | Example | Method and boundary |
| --- | --- | --- |
| How do hourly temperature and precipitation become daily inputs for one elevation band? | [glacier_daily_forcing_demo.py](../examples/glacier_daily_forcing_demo.py) | [Daily forcing](glacier_daily_forcing.md) partitions hourly precipitation and accumulates positive degree days. |
| How do signed glacier increments affect outlet flow after transmission loss? | [glacier_replacement_routing_demo.py](../examples/glacier_replacement_routing_demo.py) | [Replacement routing](glacier_replacement_routing.md) routes the baseline and signed change with the same lag-dependent attenuation. |
| How do daily depths become routing inputs? | [prepare_routing_inputs_demo.py](../examples/prepare_routing_inputs_demo.py) | [Input preparation](input_preparation.md): the caller supplies the spatial mapping. This is a baseline example, not glacier replacement. |
| What can melt, remain stored or be released today? | [glacier_daily_demo.py](../examples/glacier_daily_demo.py) | [Daily glacier kernel](glacier_daily.md): consumes prepared phase and positive degree days, not raw weather. |
| How are starting states assembled and glacier geometry updated? | [glacier_year_boundary_demo.py](../examples/glacier_year_boundary_demo.py) | [Year boundary](glacier_year_boundary.md): assembly is not historical initial-mass reconstruction. |
| How do daily, monthly and year-end processes fit together? | [glacier_annual_demo.py](../examples/glacier_annual_demo.py) | [Annual execution](glacier_annual.md): the checkpoint comparison occurs inside a call, not after an external interruption. |
| How is double counting avoided? | [glacier_replacement_demo.py](../examples/glacier_replacement_demo.py) | [Replacement](methods.md): subtract the corresponding baseline contribution and add glacier release on the same footprint. |
| How does the replaced water reach an outlet? | [daily_routing_demo.py](../examples/daily_routing_demo.py) | [Daily routing](routing.md): routes nonnegative total volumes with supplied lag weights, retaining the arrival tail; not production RVIC. |
| How are already paired outlet flows scored? | [discharge_metrics_demo.py](../examples/discharge_metrics_demo.py) | [Evaluation](discharge_evaluation.md): dates and units must be aligned by the caller. |

## Check the handoffs

- A depth in mm over an applicable area in m2 gives water volume in m3 as
  `depth * area / 1000`. The annual module's daily grid-volume output is already
  in m3 per day: do not apply the conversion again or sum alternative branches.
- Use integer grid, support and trajectory indices. The sparse aggregation
  interface reserves -1 for excluded rows.
- Align day, spatial support and scenario before replacement. Use the returned
  combined volume for basic daily routing. For routing with attenuation, pass
  the baseline and signed increment separately. A negative increment is valid;
  a negative final outlet volume raises an error. If subtraction rounds away
  a small residual, use the direct combined-volume procedure in
  [replacement routing](glacier_replacement_routing.md).
- Supply two aligned, one-dimensional series of daily mean discharge in m3/s for daily evaluation.
  Retain the routing tail and explicitly choose the overlapping evaluation dates.
  Two pandas Series must have matching, unique index labels in the same order.
  With unlabeled inputs, check the dates before passing the values.

## What passing the tests establishes

The tests exercise the published calculations on synthetic inputs. They do not
validate data provenance, fitted parameters, basin-scale accuracy or a complete
paper reproduction. The public examples do not implement the entire historical
initialization, multiyear forcing remapping, production VIC/RVIC execution,
calibration or statistical post-processing. See [code origin and scope](code_origin.md)
and the [repository licensing notice](../README.md#licensing-status).
