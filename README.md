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

This staged release contains small replacement and daily-routing calculations,
with synthetic examples and tests. It is not an executable basin workflow or a
complete reproduction package.

## Available Modules

The first module demonstrates the interface between glacier water release
and land-surface runoff, with a synthetic example and matching tests. Its purpose
is to make the replacement of the corresponding land-surface contribution
explicit, rather than adding glacier release on top of an unchanged baseline.
The current function accepts one already aligned daily record. It does not load
research files, allocate areas, select scenarios, or map routing sources. It is
a release adaptation, not a byte-identical copy of the research runner. This module is a
connection between model components, not a standalone glacier model or the full
basin simulation.

The daily-routing module distributes aligned water volumes over arrival days
using supplied lag weights. It retains the full arrival tail and converts daily
volumes to daily mean flow. It is a small reference implementation, not the
production routing engine or an RVIC parameter generator. The synthetic example
connects replacement to routing without using research data. Static attenuation,
real routing weights, and parameter calibration are not included.

## Repository Guide

- [Workflow guide: setup, examples and coverage](docs/workflow_guide.md) | [Tested Python dependencies](requirements.txt)
- [Method](docs/methods.md)
- [Daily routing](docs/routing.md)
- [Inputs and outputs](docs/inputs.md)
- [Code origin and scope](docs/code_origin.md)

See [Repository structure](docs/repository_structure.md) for the intended layout
and the distinction between current documentation and planned code.

## Scope and Attribution

### Licensing Status

This repository is being assembled in stages. No open-source license is granted
at this stage. A licensing decision will be made after the codebase has been
consolidated and reviewed. This notice does not override GitHub's terms,
applicable law, or any third-party licenses.

VIC and RVIC are upstream models, not original models developed by this project.
Project-specific workflow code will be distinguished from upstream components.
Synthetic examples will be labelled separately from research results.

Research inputs are not bundled here. The example uses only the Python standard
library. From the repository root on Linux or macOS:

```bash
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
the exact environment tested for this draft is recorded in the local review.
