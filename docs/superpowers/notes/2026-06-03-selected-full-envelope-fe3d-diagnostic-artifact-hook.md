# Selected Full-Envelope FE3d Diagnostic Artifact Hook

**Date:** 2026-06-03
**Goal context:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE3d connects the selected-envelope projection to a real audit artifact surface:

```text
selected PeakHypothesis + audit trace
  -> SelectedEnvelopeDiagnosticRow
  -> FileResult.selected_envelope_diagnostic_rows
  -> selected_envelope_diagnostics.tsv
```

This is still diagnostic-only. It does not change targeted CSV/workbook `Area`,
alignment primary matrix values, selected `IntegrationResult`, or product
boundary behavior.

## Public Surface

When `emit_peak_candidates=true`, the output dispatcher now writes:

- `selected_envelope_diagnostics.tsv`

The sidecar uses the existing selected-envelope diagnostic headers and is
written beside:

- `peak_candidates.tsv`
- `peak_candidate_boundaries.tsv`
- `peak_candidate_boundary_summary.tsv`
- `peak_region_selection_shadow.tsv`

The sidecar is an audit-output group extension, not a new diagnostic CLI.

## Boundary Discipline

Rows are produced only when the audit hypotheses contain exactly one
product-selected `PeakHypothesis`. The quantitation context is the full audit
trace used by the existing peak-candidate audit path. Writers serialize the
already built diagnostic row; they do not recompute boundaries, baselines, or
areas.

The exactly-one selected-hypothesis contract is covered directly: zero selected
rows and multiple selected rows do not emit a diagnostic row. Malformed selected
audit traces fail explicitly instead of being silently skipped.

The selected-envelope product path remains stopped before FE4. FE4 still needs
a bounded real-data changed-row artifact plus filled manual/expert boundary
oracle rows before any 8RAW launch can be justified.

## Verification

Minimal TDD slice:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_output.py tests/test_peak_candidate_audit.py::test_peak_audit_appender_builds_selected_envelope_diagnostic_rows tests/test_extractor.py::test_run_writes_peak_candidate_table_when_enabled tests/test_extractor.py::test_run_does_not_write_intermediate_csv_by_default
```

Observed result:

```text
6 passed in 1.56s
```

Focused selected-envelope and peak-candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_projection.py tests/test_selected_full_envelope_output.py tests/test_selected_full_envelope_oracle_artifacts.py tests/test_selected_full_envelope_changed_row_review.py tests/test_selected_full_envelope_oracle.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_fe0_contract.py tests/test_peak_candidate_audit.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_extractor.py::test_run_writes_peak_candidate_table_when_enabled tests/test_extractor.py::test_run_does_not_write_intermediate_csv_by_default tests/test_extractor.py::test_run_selected_output_is_unchanged_when_peak_candidate_table_enabled
```

Observed result:

```text
102 passed in 2.61s
```

Lint/type:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\selected_envelope_projection.py tests\test_selected_full_envelope_projection.py xic_extractor\peak_detection\selected_envelope_oracle.py tests\test_selected_full_envelope_oracle.py xic_extractor\peak_detection\selected_envelope_oracle_artifacts.py tests\test_selected_full_envelope_oracle_artifacts.py xic_extractor\output\selected_envelope_diagnostics.py tests\test_selected_full_envelope_output.py xic_extractor\extraction\peak_candidate_audit.py tests\test_peak_candidate_audit.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\output_dispatch.py xic_extractor\extractor.py tests\test_extractor.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Observed result:

```text
ruff: All checks passed
mypy: Success, no issues in 278 source files
```

## Next Gate

Use this sidecar to generate a bounded real changed-row artifact. The next
decision should be whether the actual changed rows are clean enough to route to
manual/expert boundary oracle review or whether the selected-envelope policy
must be stopped or externalized before FE4.
