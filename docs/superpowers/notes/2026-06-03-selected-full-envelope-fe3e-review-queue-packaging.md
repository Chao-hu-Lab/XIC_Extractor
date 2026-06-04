# Selected Full-Envelope FE3e Review Queue Packaging

**Date:** 2026-06-03
**Goal context:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE3e adds the no-RAW packaging step that turns
`selected_envelope_diagnostics.tsv` into reviewable changed-row and
manual/expert boundary-oracle queue artifacts.

This is not FE4 and does not authorize 8RAW. It only prepares the artifact shape
needed before FE4 preflight can stop saying "missing changed-row artifact" or
"missing boundary-oracle review surface."

## Added Artifact CLI

New entry point:

- `tools/diagnostics/selected_envelope_review_queue.py`

Input:

- `selected_envelope_diagnostics.tsv`

Outputs under an explicit output directory:

- `selected_envelope_changed_rows.tsv`
- `selected_envelope_oracle_review_queue.tsv`
- `selected_envelope_diagnostic_manifest.tsv`
- `selected_envelope_review_queue.json`

The JSON and manifest are `diagnostic_only`. They report row counts and the
diagnostic gate state, but they do not launch RAW, fill expert oracle rows, or
promote selected-envelope behavior.

## Boundary Discipline

The changed-row TSV keeps only rows where the selected-envelope boundary changed
or the row-level boundary decision is not `accept_candidate`.

The oracle review queue uses the existing FE3b schema. It keeps manual/expert
review fields blank and allows only manual/expert sources for boundary truth.
Targeted workbook controls remain benchmark-only and cannot become
manual/expert oracle truth.

The diagnostic manifest can now be built from persisted TSV rows via
`build_selected_envelope_gate_manifest_from_rows`, so FE4 preflight can consume
the real sidecar without needing in-memory evaluator objects.

## Verification

TDD slice:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_diagnostics.py::test_manifest_from_diagnostic_rows_matches_evaluation_manifest tests/test_selected_full_envelope_diagnostics.py::test_manifest_from_empty_diagnostic_rows_defers tests/test_selected_envelope_review_queue.py
```

Observed result:

```text
6 passed in 1.31s
```

Focused selected-envelope / peak-candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_projection.py tests/test_selected_full_envelope_output.py tests/test_selected_envelope_review_queue.py tests/test_selected_full_envelope_oracle_artifacts.py tests/test_selected_full_envelope_changed_row_review.py tests/test_selected_full_envelope_oracle.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_fe0_contract.py tests/test_peak_candidate_audit.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_extractor.py::test_run_writes_peak_candidate_table_when_enabled tests/test_extractor.py::test_run_does_not_write_intermediate_csv_by_default tests/test_extractor.py::test_run_selected_output_is_unchanged_when_peak_candidate_table_enabled
```

Observed result:

```text
108 passed in 3.08s
```

Lint/type:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\selected_envelope_review_queue.py tests\test_selected_envelope_review_queue.py xic_extractor\peak_detection\selected_envelope_diagnostics.py tests\test_selected_full_envelope_diagnostics.py tools\diagnostics\INDEX.md
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Observed result:

```text
ruff: All checks passed
mypy: Success, no issues in 278 source files
```

## Next Gate

The next useful step is to run the normal targeted extraction with
`emit_peak_candidates=true` on a bounded real-data surface, then run this CLI
against the generated `selected_envelope_diagnostics.tsv`.

Only after changed rows are reviewed and filled manual/expert oracle rows exist
should FE4 preflight be re-run. FE4 remains blocked until then.
