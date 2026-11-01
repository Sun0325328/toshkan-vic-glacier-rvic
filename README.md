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

This staged-release draft contains a small replacement calculation and synthetic
tests. It is not an executable basin workflow or a complete reproduction package.

## Planned First Module

The first module will demonstrate the interface between glacier water release
and land-surface runoff, with a synthetic example and matching tests. Its purpose
is to make the replacement of the corresponding land-surface contribution
explicit, rather than adding glacier release on top of an unchanged baseline.
The current function accepts one already aligned daily record. It does not load
research files, allocate areas, select scenarios, or map routing sources. It is
a release adaptation, not a byte-identical copy of the research runner. This module is a
connection between model components, not a standalone glacier model or the full
basin simulation.

## Repository Guide

- [Method](docs/methods.md)
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
PYTHONPATH=src python -B -m unittest discover -s tests -v
```

The synthetic example removes 30 from a baseline of 100 and adds 20, giving 90
cubic metres of water per day. No hydrological model is launched.

For Windows PowerShell, set `$env:PYTHONPATH="src"` and run the same `python -B`
commands without the `PYTHONPATH=src` prefix. The examples require Python 3;
the exact environment tested for this draft is recorded in the local review.
