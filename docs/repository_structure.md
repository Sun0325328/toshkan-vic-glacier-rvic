# Repository Structure

The planned layout separates method implementation, documentation, examples,
configuration, and tests. Directories are populated when reviewed content is
available; the list below does not indicate that code has already been released.

| Location | Purpose | Current status |
| --- | --- | --- |
| `README.md` | Project scope and entry point | Documentation draft |
| `docs/` | Method descriptions and input definitions | Structure and method drafts |
| `src/toshkan_workflow/` | Workflow implementation | Scalar replacement draft only |
| `examples/` | Minimal runnable examples using synthetic inputs | One synthetic daily record |
| `configs/` | Example configuration, when needed | Optional, not created |
| `tests/` | Tests accompanying each released function | Ten synthetic checks |
| `requirements.txt` | External dependencies | Not needed for the current standard-library example |

The initial code scope is the glacier-to-land-surface runoff interface. Additional
components will be added incrementally rather than exposing historical execution
directories as a public API. Internal review records and research run outputs are
not part of this layout.

The separation of concerns follows patterns used in
[VIC](https://github.com/UW-Hydro/VIC),
[OGGM](https://github.com/OGGM/oggm), and
[NeuralHydrology](https://github.com/neuralhydrology/neuralhydrology).
The `src/` layout is a project-specific choice. These references concern repository
organisation, not adoption of their algorithms or licensing terms.
