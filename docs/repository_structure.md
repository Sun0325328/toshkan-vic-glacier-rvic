# Repository Structure

The planned layout separates method implementation, documentation, examples,
configuration, and tests. Directories are populated when reviewed content is
available; the list below does not indicate that code has already been released.

| Location | Purpose | Current status |
| --- | --- | --- |
| `README.md` | Project scope and entry point | Published project overview |
| `docs/` | Method descriptions and input definitions | Replacement, routing, inputs, origin and structure |
| `src/toshkan_workflow/` | Workflow implementation | Scalar replacement and daily-routing reference |
| `examples/` | Minimal runnable examples using synthetic inputs | Replacement and replacement-to-routing examples |
| `configs/` | Example configuration, when needed | Optional, not created |
| `tests/` | Tests accompanying each released function | Twenty-four synthetic checks |
| `requirements.txt` | External dependencies | Not needed for the current standard-library modules |

The initial code scope is the glacier-to-land-surface runoff interface. Additional
components will be added incrementally rather than exposing historical execution
directories as a public API. Internal review records and research run outputs are
not part of this layout.

## Incremental Organization

The two published modules retain their current paths and interfaces:
`src/toshkan_workflow/glacier_replacement.py` and
`src/toshkan_workflow/daily_routing.py`. No relocation is needed at this stage.

Future code will be grouped by function within `src/toshkan_workflow/`:

| Planned location | Role | Status |
| --- | --- | --- |
| `preprocessing/` | Input preparation and time, unit and spatial alignment | Planned; not implemented here |
| `glacier/` | Glacier processes, initialization and geometry evolution | Planned; not implemented here |
| `workflow/` | Execution configuration and component integration | Planned; not implemented here |
| `evaluation/` | Evaluation and analysis utilities | Planned; not implemented here |

Directories and dependency metadata will be added only with reviewed working
content, not as empty placeholders. Examples and tests will accompany the
corresponding functionality. Configuration templates will contain no research
data, private paths or credentials. Release batches do not define code folders.

The approximate eight-stage release plan covers introduction and replacement;
basic routing; input preparation; glacier processes; initialization and geometry;
workflow integration; evaluation and analysis; and integrated documentation and
coverage review. Only the first two stages have been released. Later stages are
subject to source and publication-scope review; this plan is not a claim of
complete implementation or reproducibility. Licensing remains a separate
decision, as stated in the project overview.

The separation of concerns follows patterns used in
[VIC](https://github.com/UW-Hydro/VIC),
[OGGM](https://github.com/OGGM/oggm), and
[NeuralHydrology](https://github.com/neuralhydrology/neuralhydrology).
The `src/` layout is a project-specific choice. These references concern repository
organisation, not adoption of their algorithms or licensing terms.
