# Untargeted GUI

![Untargeted Discovery workspace](../../assets/screenshots/untargeted-workspace.png)

The Untargeted workspace is the human GUI surface for discovery, alignment,
and reviewable output access. It orchestrates existing product workflows; it
does not create a separate product-authority lane.

## Contract

- The main window exposes **Targeted Extraction** and **Untargeted Discovery**
  as first-class workspaces.
- Untargeted settings are local GUI state in `config/discovery_gui.json`;
  that file stays ignored.
- Method settings come from built-in presets in
  `xic_extractor/presets/data/*.toml`.
- Advanced values are explicit user overrides layered on the selected preset.
- Stop requests cancellation, then waits for the current worker stage to
  yield.
- Backfill gallery generation is best-effort. Gallery failure must not hide
  primary discovery or alignment outputs.
- Frozen builds must bundle preset TOMLs, because GUI startup loads presets.

## Modes

| Mode | GUI input | Runs |
| --- | --- | --- |
| `full` | RAW directory, DLL directory, output directory | Batch discovery, alignment, gallery |
| `discovery_only` | Single RAW file, DLL directory, output directory | Single-file discovery |
| `align_only` | RAW directory, `discovery_batch_index.csv`, DLL directory, output directory | Alignment, gallery |

Batch discovery-only remains a CLI surface. Use `full` when the GUI should
run directory-level discovery plus alignment.

## Surfaces

| Surface | Role |
| --- | --- |
| `gui/views/untargeted_view.py` | Workspace state and run lifecycle |
| `gui/sections/discovery_source_section.py` | RAW, DLL, output, mode, and batch-index inputs |
| `gui/sections/discovery_method_section.py` | Preset selection and advanced overrides |
| `gui/sections/discovery_results_section.py` | Output links and run summary |
| `gui/workers/discovery_worker.py` | Threaded mode dispatch and gallery orchestration |
| `gui/discovery_config_io.py` | Local persisted Untargeted settings |
| `xic_extractor.spec` | Frozen-release resource bundle contract |

User-visible outputs surfaced by the GUI:

- `discovery_candidates.csv`
- `discovery_review.csv`
- `discovery_batch_index.csv`
- `alignment_matrix.tsv`
- `alignment_review.tsv`
- review HTML and gallery HTML

## Boundaries

- Owns: workspace layout, run/stop lifecycle, local config persistence,
  preset loading, mode dispatch, and output link presentation.
- Does not own: product authority, selected backfill values, counted
  detections, matrix publication, maturity tier, or RAW-tier production
  readiness. Those belong to [Discovery](discovery.md),
  [Alignment](alignment.md), [Presets](presets.md), and
  [Productization](productization.md).
- If a GUI change alters matrix values, schemas, selected peaks, counted
  detections, or product authority, update the owning product docs first.

## Verification

| Change area | Focused tests |
| --- | --- |
| Main-window routing | `tests/test_gui_main.py`, `tests/test_main_window_layout.py` |
| Local GUI config | `tests/test_gui_config_io.py` |
| Untargeted run/stop behavior | `tests/test_untargeted_view.py` |
| Worker mode dispatch | `tests/test_discovery_worker.py` |
| Shared run controls | `tests/test_pipeline_worker.py` |
| Gallery contract | `tests/test_backfill_gallery.py` |
| Alignment output surfaces | `tests/test_alignment_output_levels.py`, `tests/test_alignment_pipeline_outputs.py` |
| Frozen preset bundling | `tests/test_pyinstaller_spec.py` |

Full PR gate:

```powershell
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
uv run pytest -v --tb=short -x
```

## Pitfalls

- Adding a preset but forgetting the PyInstaller data bundle.
- Committing machine-specific GUI state.
- Treating optional gallery failure as total run failure after primary
  outputs were written.
- Re-enabling controls immediately after Stop while the worker is still
  alive.
- Letting the GUI recompute domain evidence or override Discovery/Alignment
  ownership rules.
