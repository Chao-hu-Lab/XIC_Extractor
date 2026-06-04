# Selected Full-Envelope FE3b Oracle Artifact Prep

**Date:** 2026-06-03
**Goal context:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE3b closes the schema gap that blocked FE4 preflight, but it does not provide
real manual/expert boundary evidence yet.

This slice adds a machine-readable path from selected-envelope diagnostics to a
manual/expert boundary oracle:

```text
selected-envelope diagnostic rows
  -> boundary-oracle review queue
  -> expert/manual filled oracle artifact rows
  -> BoundaryOracle objects
  -> FE3 oracle comparison manifest
```

The selected full-envelope product path remains stopped at FE4 `defer` until a
real changed-row artifact and a real expert/manual boundary oracle artifact
exist.

## What Was Added

Package-level artifact schema:

- `xic_extractor/peak_detection/selected_envelope_oracle_artifacts.py`
- `xic_extractor/peak_detection/selected_envelope_projection.py`

Tests:

- `tests/test_selected_full_envelope_oracle_artifacts.py`
- `tests/test_selected_full_envelope_projection.py`

The schema provides:

- a projection helper that turns a selected `PeakHypothesis`, raw trace, and
  explicit quantitation context into a selected-envelope diagnostic row;
- a review queue for changed or high-risk selected-envelope diagnostic rows;
- strict rejection of missing `selected_candidate_id`;
- manual/expert oracle sources limited to `manual_overlay`,
  `expert_overlay`, and matching `manual_2raw`;
- targeted workbook controls allowed only as `benchmark_control_only`;
- `benchmark_control_only` rows limited to `targeted_workbook_control`, so
  manual/expert overlays cannot be downgraded into benchmark-only rows;
- expert-reviewed rows requiring reviewed RT bounds and positive
  baseline-corrected area;
- round-trip conversion between `BoundaryOracle` and TSV-like oracle rows.

## Boundary Discipline

This is intentionally not a product behavior change.

The projection helper requires an already selected hypothesis and an explicit
quantitation context that contains the resolver interval. It does not invent a
context window, write files, rescan RAW, or mutate selected integration results.

The queue recommends review rows. It does not create oracle truth. The oracle
artifact loader accepts only filled manual/expert boundary rows as boundary
truth. Targeted workbook rows cannot masquerade as expert-reviewed boundary
truth.

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

The next useful slice is not 8RAW. It is generating a real selected-envelope
diagnostic row artifact from a bounded real-data surface, then using this review
queue to collect manual/expert boundary rows.

Only after the FE3 oracle manifest emits `gate_decision=promote` should FE4
8RAW changed-row diagnostics be launched.
