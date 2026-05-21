# Instrument QC Level 2.5 RT-Supported Shadow Gate Spec

Date: 2026-05-21

Branch: `codex/handoff-level2-rt-shadow-gate`

## Summary

Level 2.5 adds an audit-only shadow gate between the current Level 2
`rt_aware_audit_alignment_support` GO result and the Level 3
`rt_production_candidate` NO-GO result.

The goal is row-level review triage: identify matrix cells whose RT support is
strong enough to be reviewed as `rt_supported_shadow_candidate`, while clearly
separating rows that are clean-standard-only, missing biological context,
biological-transfer conflicts, uncertain RT models, unsupported coverage, or
blocked/not applicable.

This spec does not approve production RT correction, production response
correction, targeted reliability changes, peak scoring changes, resolver
changes, matrix identity changes, workbook schema changes, or DNP normalization
changes.

## Product Boundary

Allowed:

- read existing Level 1 matrix RT preview TSV / JSON artifacts;
- read biological ISTD transfer audit TSV / JSON artifacts;
- read row-level biological ISTD anchor evidence when available;
- emit TSV / JSON / Markdown diagnostics;
- classify rows for review.

Not allowed:

- mutate `alignment_matrix.tsv`, `alignment_review.tsv`, or
  `alignment_cells.tsv`;
- change targeted reliability;
- change peak scoring, resolver behavior, or RT windows;
- emit corrected production RT / area / response values;
- infer DNA-only, RNA-only, or multi-tag scope from labels when the input does
  not declare it.

## Required Inputs

The diagnostic requires:

- `matrix_rt_calibration_preview.tsv`
- `matrix_rt_calibration_preview_summary.json`
- `biological_istd_rt_transfer_audit.tsv`
- `biological_istd_rt_transfer_audit.json`

For a row to become `rt_supported_shadow_candidate`, the diagnostic also needs
row-level biological ISTD anchor evidence with at least:

- `target_label`
- `injection_order`
- `observed_rt_min` or existing biological drift row field `rt_min`

If row-level biological anchors are absent, the diagnostic may still run, but
the run verdict must be `context_incomplete` unless every row is otherwise
blocked or unsupported. It must not promote any row to
`rt_supported_shadow_candidate`.

## Required Matrix Preview Columns

The row-level matrix RT preview TSV must include:

- `source_row_id`
- `source_cell_key`
- `feature_id`
- `sample_name`
- `sample_stem`
- `feature_mz`
- `raw_feature_rt_min`
- `injection_order`
- `coverage_status`
- `rt_alignment_support_status`
- `local_residual_p95_min`
- `rt_uncertainty_min`
- `local_biological_istd_anchor_count`
- `correction_status`
- `correction_block_reason`

The maturity decision must use this row-level TSV. Summary JSON alone is not
enough to evaluate Level 2.5 or Level 3 blockers.

## Biological ISTD Scope

The transfer JSON must contain a non-empty `istd_scope`.

Default accepted scope for current 85RAW / 8RAW evidence:

```text
provided_biological_qc_istd_summary_rows_after_rt_gate_fix
```

Other scopes are acceptable only when explicitly written in the input JSON. The
diagnostic reports the scope verbatim and does not reinterpret it.

## Anchor Proximity

Biological ISTD anchor context is local. A matrix row may use a biological ISTD
anchor only when:

- both row and anchor have injection order;
- both row and anchor have RT;
- `abs(row_rt - anchor_rt) <= anchor_rt_window_min`;
- `abs(row_injection_order - anchor_injection_order) <= anchor_injection_window`.

Default thresholds:

- `anchor_rt_window_min = 1.0`
- `anchor_injection_window = 20`

These are review thresholds only. They do not mutate the matrix and do not
become production RT tolerances.

## Row Classification

Rows are classified in this precedence:

1. `blocked_or_not_applicable`
   - `correction_status != shadow_only`, or row has blocked / not-applicable
     correction status.
2. `coverage_not_supported`
   - `coverage_status != covered`, or `rt_alignment_support_status` is not
     `local_rt_supported`.
3. `rt_model_uncertain`
   - `local_residual_p95_min > 0.30`, or `rt_uncertainty_min > 0.30`, or either
     value is missing.
4. `biological_context_missing`
   - no biological ISTD anchor rows exist, transfer JSON lacks `istd_scope`,
     or nearby anchors lack transfer status.
5. `biological_transfer_conflict`
   - nearby anchors exist, but none has transfer status
     `transfer_supported` or `direction_supported_magnitude_shifted`.
6. `rt_supported_shadow_candidate`
   - all previous gates pass and at least one nearby biological ISTD anchor has
     supported transfer status.
7. `clean_standard_only_review`
   - clean-standard RT support is present and biological ISTD rows exist in the
     run, but no local anchor is close enough in both RT and injection order.

## Run Verdict

The run-level verdict is:

- `required_artifact_missing`: at least one required input path is absent.
- `input_invalid`: required columns or JSON fields are malformed.
- `context_incomplete`: inputs are readable but biological ISTD context is not
  sufficient to approve any candidate.
- `shadow_gate_ready`: at least one `rt_supported_shadow_candidate` row exists.
- `no_supported_rows`: inputs are complete but all candidate-shaped rows fail
  support gates.

The JSON and Markdown outputs must make the verdict explicit.

## Outputs

The diagnostic writes:

- `instrument_qc_rt_supported_shadow_gate_rows.tsv`
- `instrument_qc_rt_supported_shadow_gate_summary.tsv`
- `instrument_qc_rt_supported_shadow_gate.json`
- `instrument_qc_rt_supported_shadow_gate.md`

The row TSV must include enough context for review:

- matrix row identity;
- RT model status and uncertainty;
- local biological anchor counts;
- nearest biological ISTD label / status / RT delta / injection-order delta;
- supporting biological ISTD label / status / RT delta / injection-order delta
  when a different nearby anchor supplies the positive transfer evidence;
- final row classification;
- review reason.

The summary TSV / JSON must include counts by:

- row classification;
- coverage status;
- correction status;
- nearest biological transfer status;
- run verdict.

## Acceptance

The implementation is acceptable when:

- row-level TSV is required for Level 2.5 classification;
- missing `istd_scope` cannot pass;
- missing biological anchor rows cannot produce candidates;
- extrapolated or blocked rows cannot produce candidates;
- high residual / high uncertainty rows cannot produce candidates;
- transfer conflicts are explicit;
- output is diagnostic-only and no production artifact changes.
