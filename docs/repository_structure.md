# Repository structure

| Location | Contents |
| --- | --- |
| [Preprocessing](../src/toshkan_workflow/preprocessing/) | Daily inputs, source-volume mapping and hourly weather aggregation for glacier bands. |
| [Glacier](../src/toshkan_workflow/glacier/) | Initialization, daily water balance, thermal processes, annual calculations, geometry and grid aggregation. |
| [Replacement](../src/toshkan_workflow/glacier_replacement.py) | Daily glacier-area water replacement. |
| [Daily routing](../src/toshkan_workflow/daily_routing.py) | Routing nonnegative source volumes to outlets. |
| [Routing with attenuation](../src/toshkan_workflow/routing_loss.py) | Routing baseline volumes and signed replacement increments to one outlet. |
| [Evaluation](../src/toshkan_workflow/evaluation.py) | Metrics for paired observed and simulated discharge. |
| [Examples](../examples/) and [tests](../tests/) | Runnable examples and checks using synthetic inputs. |
| [Dependencies](../requirements.txt) | Tested NumPy and pandas versions. |

See the [workflow guide](workflow_guide.md) for setup and example commands and
[code origin and scope](code_origin.md) for the relationship to the research scripts.
