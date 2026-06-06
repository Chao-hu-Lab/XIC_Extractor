# Selected Full-Envelope FE3c Diagnostic Projection Prep

**Date:** 2026-06-03
**Goal context:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE3c adds the package-level projection needed before real selected-envelope
changed-row diagnostics can be generated.

It does not run RAW files, write diagnostic TSVs, add a CLI, or change product
quantitation behavior. FE4 remains stopped at `defer` until a real changed-row
artifact and a real manual/expert boundary oracle artifact exist.

## What Was Added

Package module:

- `xic_extractor/peak_detection/selected_envelope_projection.py`

Test:

- `tests/test_selected_full_envelope_projection.py`

The helper turns an already selected `PeakHypothesis`, the trace arrays, and an
explicit quantitation context into the existing
`SelectedEnvelopeDiagnosticRow` shape.

## Boundary Discipline

This helper is intentionally narrow:

- it requires `hypothesis.audit.selected`;
- it requires the caller to provide the quantitation context window;
- the quantitation context must contain the resolver interval;
- it requires matching one-dimensional trace arrays, finite values, and a
  strictly increasing RT axis;
- it computes the AsLS baseline only inside that explicit context;
- it preserves `hypothesis.resolver_mode` as legacy resolver provenance;
- it does not choose a new product boundary or mutate the hypothesis.

This means FE3c closes only the package projection gap. It is not evidence that
the selected full-envelope boundary policy is production-ready.

## Verification

Focused selected-envelope package shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_projection.py tests/test_selected_full_envelope_oracle_artifacts.py tests/test_selected_full_envelope_changed_row_review.py tests/test_selected_full_envelope_oracle.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_fe0_contract.py tests/test_baseline_integration.py tests/test_peak_candidate_boundaries.py
```

Observed result:

```text
93 passed in 2.22s
```

Lint/type:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\selected_envelope_projection.py tests\test_selected_full_envelope_projection.py xic_extractor\peak_detection\selected_envelope_oracle.py tests\test_selected_full_envelope_oracle.py xic_extractor\peak_detection\selected_envelope_oracle_artifacts.py tests\test_selected_full_envelope_oracle_artifacts.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Observed result:

```text
ruff: All checks passed
mypy: Success, no issues in 277 source files
```

## Next Gate

The next slice should connect this projection to a bounded real diagnostic
artifact. That means generating actual selected-envelope diagnostic rows from a
small, explicit real-data surface, then routing changed or high-risk rows into
the FE3b boundary-oracle review queue.

FE4 8RAW launch stays blocked until that diagnostic artifact and filled
manual/expert oracle artifact exist.
