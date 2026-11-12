# Toshkan VIC-Glacier-RVIC Workflow

Where does river water come from, when is it supplied, and which parts of a
mountain basin contribute most? This project studies these questions in the
Toshkan River basin, a headwater of the Aksu River in the Tien Shan region.

The research combines land-surface hydrology, glacier processes, and river
routing to examine rainfall, snowmelt, and glacier contributions to streamflow.
It considers both changes between years and differences between seasons, together
with the spatial distribution of runoff generation.

## How the Workflow Fits Together

| Component | Role in the research |
| --- | --- |
| VIC | Simulates land-surface water and energy processes, including runoff, soil drainage, and water storage. |
| External glacier module | Uses temperature-index calculations to represent snow, firn, and ice melt, with storage and refreezing processes affecting water release. |
| Glacier replacement interface | Removes the corresponding VIC contribution from glacier-covered areas and substitutes glacier-module water release to avoid double counting. |
| RVIC | Routes water generated across the basin to river outlets. |

The broader research compares simulations with streamflow observations and
remote-sensing information, and examines water-source composition and seasonal
patterns of runoff generation. These analyses are part of the research scope,
not a claim that all associated code or data are included in this repository.

Rainfall and snowmelt describe where water originates; surface runoff and soil
drainage describe how it moves through the land surface. The workflow keeps these
two distinctions separate. Likewise, total water released from glacier-covered
areas is not the same as the net change produced by replacing the original
land-surface calculation.

## Release Status

This release contains glacier process calculations from the Toshkan workflow,
public interfaces for input preparation and routing, and a discharge evaluation
function. The examples and tests use synthetic inputs.

## Available Modules

- Hourly weather is converted to daily glacier inputs. The glacier modules
  cover melt and release, thermal storage, annual aging, geometry updates
  and aggregation of release volumes to model grids.
- The scalar replacement function subtracts the VIC contribution on the
  glacier-covered area and adds glacier-module release on the same area.
- Two routing interfaces accept different inputs. `daily_routing.py` routes
  nonnegative source volumes to their outlets. `routing_loss.py` routes a
  baseline and signed replacement increments to one outlet, with attenuation
  that depends on travel time. Both retain the full arrival tail.
- The evaluation function compares aligned observed and simulated discharge
  series for one outlet and scenario at a time.

## Repository Guide

- [Workflow guide: setup, examples and coverage](docs/workflow_guide.md) | [Tested Python dependencies](requirements.txt)
- [Method](docs/methods.md)
- [Daily routing](docs/routing.md)
- [Inputs and outputs](docs/inputs.md)
- [Code origin and scope](docs/code_origin.md)

See [Repository structure](docs/repository_structure.md) for the published modules,
examples and tests.

## Scope and Attribution

### Licensing Status

No project-wide software license is granted. GitHub's terms, applicable law,
and third-party licenses apply.

VIC and RVIC are upstream models, not original models developed by this project.
The examples illustrate the project-specific calculations with synthetic inputs.

The scalar replacement and basic daily-routing examples use the Python standard
library. Install the dependencies for the full test suite and all nine examples.
From the repository root on Linux or macOS:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -B examples/glacier_replacement_demo.py
PYTHONPATH=src python -B examples/daily_routing_demo.py
PYTHONPATH=src python -B -m unittest discover -s tests -v
```

The synthetic example removes 30 from a baseline of 100 and adds 20, giving 90
cubic metres of water per day. No hydrological model is launched.
The routing example distributes those 90 cubic metres as 45, 27, and 18 over
three consecutive days. All example values and routing weights are synthetic.

For Windows PowerShell, set `$env:PYTHONPATH="src"` and run the same `python -B`
commands without the `PYTHONPATH=src` prefix. The examples require Python 3;
the tested environment is listed in the [workflow guide](docs/workflow_guide.md).
