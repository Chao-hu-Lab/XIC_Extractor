# AsLS Primary Matrix Value Policy Spec

**Date:** 2026-06-02
**Status:** Implemented v0.2 - behavior/output contract for current PR
**Readiness label:** `production_ready` for primary matrix value delivery after focused tests, 8RAW, and 85RAW closeout
**Product-flow reference:** [Mature package flow reference](2026-06-02-mature-package-flow-reference-spec.md)
**Supersedes for final-matrix value policy:** historical final-matrix language in [P2b AsLS promotion](2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md)
**Human-facing companion:** [Raw to final matrix product story](../reports/2026-06-02-raw-to-final-matrix-product-story.html)
**8RAW closeout:** [AsLS primary matrix value 8RAW closeout](../notes/2026-06-02-asls-primary-matrix-value-8raw-closeout.md)
**85RAW closeout:** [AsLS primary matrix value 85RAW closeout](../notes/2026-06-02-asls-primary-matrix-value-85raw-closeout.md)

## Verdict

`alignment_matrix.tsv` and workbook `Matrix` must stop publishing a raw,
linear-edge-compatible, or otherwise legacy-baseline area as the primary
quantitative value.

The implemented v0.1 product behavior makes the primary matrix value:

```text
selected IntegrationResult.area_baseline_corrected
where IntegrationResult.baseline_type == "asls"
```

The existing primary matrix schema can stay unchanged at first: feature rows and
sample columns remain the downstream contract. The values in those sample cells
change to AsLS-corrected selected integration area.

Raw selected area remains useful as audit evidence. It must be named as raw or
historical; it must not be the main matrix value, unnamed fallback, or rollback
product path.

This spec now describes the implemented v0.2 behavior/output contract. The
8RAW and 85RAW closeouts support `production_ready` for primary matrix value
delivery/source semantics. That readiness label does not claim every
independent absolute baseline-truth axis, such as spike-in recovery,
concentration-series linearity, blank/carryover behavior, or synthetic
known-area validation.

## Why This Spec Exists

Before v0.1, the code had already retired `linear_edge` from baseline
integration, but the final matrix value path still behaved like this:

```text
AlignedCell.matrix_area
  -> selected_integration.area_raw_counts_seconds
  -> legacy cell.area fallback
  -> ProductionCellDecision.matrix_value
  -> production_matrix_area(...)
  -> alignment_matrix.tsv / workbook Matrix
```

`IntegrationResult` already carries the AsLS-relevant fields:

```text
area_raw_counts_seconds
area_baseline_corrected
area_uncertainty
baseline_residual_mad
area_uncertainty_noise_source
baseline_type
baseline_score
```

The missing product step is value ownership:

```text
AsLS is the product baseline direction
but final matrix still takes raw selected area
```

That mismatch was the remaining quantitation problem. The v0.1 implementation
removes this raw primary-value path while preserving raw area as audit evidence.

## Current Code Map

| Surface | Current role | Policy change needed |
|---|---|---|
| `peak_detection/hypotheses.py::IntegrationResult` | Carries raw area, AsLS-corrected area, uncertainty, baseline provenance. | Keep as the canonical integration value carrier. |
| `alignment/matrix_handoff.py::integration_from_values(...)` | Builds `IntegrationResult` from owner/backfill scalar values but currently lacks AsLS fields. | Must not be treated as product-ready AsLS integration until it can carry or compute AsLS fields. |
| `alignment/matrix.py::AlignedCell.matrix_area` | Returns `selected_integration.area_raw_counts_seconds`, then `cell.area`. | Replace with AsLS-primary selected integration area policy, with no silent raw fallback for current product cells. |
| `alignment/cell_quality.py::decide_cell_quality(...)` | Accepts `cell.matrix_area` as quantifiable area. | Continue to validate positive finite area, but area source must be AsLS-primary. Missing AsLS should route to review/invalid, not raw fallback. |
| `alignment/production_decisions.py` | Writes `quality.matrix_area` into `ProductionCellDecision.matrix_value`. | Can remain the row/cell decision owner if `quality.matrix_area` is already AsLS-primary. |
| `alignment/output_rows.py::production_matrix_area(...)` | Formats approved matrix values. | Keep formatting behavior; do not make it choose area source. |
| `alignment/tsv_writer.py::write_alignment_matrix_tsv(...)` | Writes `alignment_matrix.tsv`. | Schema can remain stable; sample values change to AsLS-primary values. |
| `alignment/tsv_writer.py::write_alignment_cells_tsv(...)` | Exposes per-cell `area` for audit/debug and currently labels it generically. | Keep raw area audit-only or rename/add companion source fields; this column must not be used as a primary matrix-value source. |
| `alignment/xlsx_writer.py::_write_matrix_sheet(...)` | Writes workbook `Matrix`. | Same value policy as TSV. |
| `alignment/xlsx_writer.py::_write_audit_sheet(...)` | Exposes per-cell `area` in workbook `Audit`. | Treat as raw audit value unless renamed or paired with primary-value fields. It must not redefine the workbook `Matrix` value. |
| `alignment/shared_peak_identity_explanation/product_activation.py` | Can activate cells into matrix-like output from `alignment_cells.tsv`. | Must not write activated matrix values from raw `area`; use an AsLS primary value field or block activation with a missing-AsLS reason. |
| `alignment_cell_integration_audit.tsv` | Already exposes baseline-corrected area and uncertainty fields. | Use as audit support, not as the only place AsLS appears. |

## Policy

### Primary Value Rule

For current product cells, primary matrix value is valid only when:

```text
cell.selected_integration is present
and selected_integration.baseline_type == "asls"
and selected_integration.area_baseline_corrected is positive finite
```

Then:

```text
ProductionCellDecision.matrix_value =
    selected_integration.area_baseline_corrected
```

`selected_integration.area_raw_counts_seconds` remains audit evidence.

### Missing AsLS Rule

If a detected or rescued cell has a selected integration but no valid AsLS
baseline-corrected area, production must not silently fall back to raw area.

The implementation may choose the exact internal label, but the behavior must
be equivalent to:

```text
quality_status = invalid or review_rescue
blank_reason = missing_asls_primary_area
write_matrix_value = false
```

The public blank/review reason must be machine-readable as
`missing_asls_primary_area` wherever production cell decisions, activation
deltas, or audit/review outputs explain why a detected/rescued cell did not
write a primary value. It may appear as `blank_reason`, `quality_reason`,
`matrix_value_effect`, or an equivalent public reason field depending on the
surface, but it must not be only an internal variable name.

For detected cells, this is a hard implementation blocker unless the migration
phase has not yet populated AsLS fields. For rescued cells, it may route to
`review_rescue` if the row identity exists but quantitation is not product-safe.

### Legacy Fallback Rule

`cell.area` and `selected_integration.area_raw_counts_seconds` may remain in
diagnostic, audit, comparison, or compatibility fields. They must not be the
primary matrix value for current product outputs.

Any temporary compatibility fallback must be:

- explicitly named as legacy/raw/diagnostic;
- excluded from `alignment_matrix.tsv` and workbook `Matrix`;
- time-boxed to a migration slice;
- covered by a stop rule that prevents accidental downstream use.

### Linear Edge Rule

`linear_edge` has no role in primary matrix value selection.

Allowed appearances:

- historical diagnostic labels such as `linear_edge_over_subtraction_plausible`;
- old artifact readers that explicitly interpret historical schemas;
- documentation explaining why linear edge was retired.

Disallowed appearances:

- config or CLI accepted baseline method;
- final matrix primary value;
- rollback product baseline;
- fallback when AsLS is missing;
- comparator that blocks AsLS primary matrix promotion by treating linear-edge
  area as truth.

## Output Contract

### Primary TSV

`alignment_matrix.tsv` keeps the same shape:

```text
feature_family_id | neutral_loss_tag | family_center_mz | family_center_rt | sample...
```

Sample cells write:

```text
AsLS-corrected selected integration area
```

Sample cells stay blank when:

- row identity is not `production_family`;
- cell is absent, unchecked, duplicate loser, ambiguous, review rescue, rejected
  rescue, invalid, or missing AsLS primary area;
- selected integration lacks valid AsLS-corrected area.

### Workbook Matrix

Workbook `Matrix` follows the same value policy as `alignment_matrix.tsv`.

Workbook `Review`, workbook `Audit`, `alignment_review.tsv`,
`alignment_cells.tsv`, and `alignment_cell_integration_audit.tsv` may expose raw
area and AsLS audit fields for traceability. If any new public audit field is
added, it must be named so downstream users cannot confuse it with the primary
matrix value.

### Recommended Audit Fields

The implementation does not have to add all of these fields in the first slice,
but the policy should support them:

| Field | Meaning |
|---|---|
| `primary_matrix_area` | Value actually written to Matrix / `alignment_matrix.tsv`. |
| `primary_matrix_area_source` | Expected value: `asls_baseline_corrected`. |
| `primary_matrix_baseline_type` | Expected value: `asls` for written cells. |
| `area_raw_counts_seconds` | Raw trapezoid selected integration area; audit only. |
| `area_baseline_corrected` | AsLS-corrected selected integration area. |
| `area_uncertainty` | Current uncertainty estimate for the selected integration. |
| `baseline_residual_mad` | Noise/residual basis for uncertainty and local S/N evidence. |

If schema stability is preferred, the first implementation may avoid adding new
primary TSV columns and instead strengthen existing audit outputs. It must still
make the sample cells AsLS-primary.

## Required Implementation Slices

### AP0 - Current-State Characterization

Pin current behavior before changing values:

- `AlignedCell.matrix_area` returns raw selected integration area today;
- `matrix_area_source` reports `selected_integration` even though that means raw
  selected integration area today;
- `ProductionCellDecision.matrix_value` uses the cell-quality matrix area;
- TSV and workbook Matrix sample cells use `ProductionCellDecision.matrix_value`;
- many test fixtures create `IntegrationResult` without AsLS fields.

This slice is characterization only.

### AP1 - AsLS Primary Area Selector

Introduce a small internal selector, for example:

```text
primary_matrix_area_from_integration(integration)
```

Contract:

- returns `area_baseline_corrected` only when `baseline_type == "asls"` and the
  corrected area is positive finite;
- returns no product value when AsLS is missing or invalid;
- never returns `area_raw_counts_seconds` for a current product cell;
- emits or preserves a machine-readable reason for missing AsLS.

This selector should live in alignment/domain code, not writer code.

### AP2 - Populate AsLS Fields For Alignment Cells

The implementation must close the current gap in `alignment/matrix_handoff.py`.
Owner and backfill cells currently build `IntegrationResult` from scalar peak
values and usually do not carry AsLS fields.

This population must happen on the product path before `cell_quality` and
`production_decisions` consume the cell. It must be independent of:

- `emit_region_audit`;
- `audit_evidence_mode`;
- `alignment_cell_integration_audit.tsv`;
- workbook `Audit`;
- `output_level`.

Audit outputs may display the AsLS facts, but they are not allowed to be the
only reason the product matrix can find them. A production-equivalent or
`validation-minimal` run with `audit_evidence_mode=none` must still be able to
produce AsLS-primary matrix values.

Acceptable approaches:

1. carry the selected `IntegrationResult` created by the peak-detection
   hypothesis path when trace context exists;
2. extend `integration_from_peak(...)` / `integration_from_values(...)` to accept
   explicit AsLS fields from the trace integration/audit path;
3. recompute AsLS integration in the alignment handoff only when trace arrays
   are already in memory and the result is identical to the selected interval.

Disallowed approach:

```text
Set area_baseline_corrected = area_raw_counts_seconds just to satisfy the new
selector.
```

That would only rename raw area as AsLS and would be worse than the current
state.

### AP3 - Production Matrix Value Switch

After AsLS fields are populated:

- update `AlignedCell.matrix_area` or an equivalent internal property to use the
  AsLS-primary selector;
- update `matrix_area_source` so it no longer says only `selected_integration`
  when the actual value is AsLS-corrected;
- keep `ProductionDecisionSet` and writers as policy consumers, not area-source
  owners;
- update unit tests that currently expect raw selected integration area as the
  matrix value.

### AP4 - Audit And Review Surface

Ensure review/audit surfaces explain the value change:

- primary matrix value source is AsLS-corrected;
- raw area remains visible where needed for diagnosis;
- missing AsLS is machine-readable;
- uncertainty and baseline residual are visible in the integration audit path;
- no user-facing output calls raw area the product value.

Known public bypasses that must be handled in this phase:

- `alignment_cells.tsv` currently has a generic `area` column. It may remain as
  a raw audit column only if activation/product code does not treat it as the
  matrix value. Prefer adding/using a `primary_matrix_area` field when a
  public activation path needs a value.
- workbook `Audit` currently has a generic `area` column. It must either be
  clearly interpreted as raw audit area or paired with primary-value/source
  fields.
- `product_activation` must not use `alignment_cells.tsv:area` to auto-write a
  primary matrix value. It must use an AsLS primary value field or emit a
  blank/review effect such as `missing_asls_primary_area`.

### AP5 - Validation

Because this changes quantitative values, it is a behavior/output phase.

Minimum validation:

- focused unit tests for `AlignedCell`, `cell_quality`, `production_decisions`,
  TSV writer, and XLSX writer;
- schema tests proving `alignment_matrix.tsv` and workbook `Matrix` shapes are
  unchanged unless a public schema change is explicitly approved;
- synthetic trace fixture where known baseline makes raw area too high or too
  low and AsLS-corrected area is the expected matrix value;
- no-audit-mode fixture proving AsLS primary values are still populated when
  `emit_region_audit` / `audit_evidence_mode` are off;
- activation fixture proving a raw `alignment_cells.tsv:area` value cannot be
  auto-written as a product matrix value;
- 8RAW validation-minimal run or equivalent existing 8RAW artifacts regenerated
  on the changed code path, with a closeout that reports row inclusion stability
  and matrix value-source status.

85RAW validation is the production-ready gate for the primary matrix value
delivery/source contract. It must show that nonblank matrix cells are backed by
`primary_matrix_area_source=asls_baseline_corrected` and that missing-AsLS cells
do not fall back to raw `area`.

## Test Migration Requirements

Existing tests that currently assert raw selected integration values in matrix
outputs must be updated deliberately.

Examples of tests expected to change:

- `tests/test_alignment_cell_quality.py`
- `tests/test_alignment_production_decisions.py`
- `tests/test_alignment_tsv_writer.py`
- `tests/test_alignment_xlsx_writer.py`
- `tests/test_untargeted_final_matrix_contract.py`

Fixture builders should create `IntegrationResult` with:

```text
area_raw_counts_seconds = raw audit value
area_baseline_corrected = AsLS product value
baseline_type = "asls"
area_uncertainty / baseline_residual_mad where relevant
```

At least one test must prove raw area is not used:

```text
raw area = 125
asls corrected area = 100
matrix sample cell = 100
audit raw area = 125
```

At least one test must prove missing AsLS does not fall back:

```text
raw area = 125
area_baseline_corrected = None
matrix sample cell = blank
blank_reason = missing_asls_primary_area
```

## Compatibility And Migration

### What does not change

- Feature row identity policy.
- Detected/rescued/review/rejected/blank cell routing, except missing AsLS can
  now blank a cell that previously wrote raw area.
- TSV and workbook Matrix shape, unless a later output spec approves companion
  columns.
- `linear_edge` remains rejected as a baseline method.

### What changes

- Numeric sample-cell values in `alignment_matrix.tsv`.
- Numeric sample-cell values in workbook `Matrix`.
- Matrix value source vocabulary.
- Some raw-area-only fixture expectations.
- Potential accepted-cell counts only if missing AsLS is not populated before
  the value switch. A correct implementation should populate AsLS first and keep
  row/cell inclusion stable except for true missing-AsLS blockers.

### Stop conditions

Stop implementation and write a narrower blocker note if:

- many product cells lack AsLS fields after AP2;
- the implementation can only pass by copying raw area into
  `area_baseline_corrected`;
- row inclusion changes for reasons unrelated to missing AsLS primary area;
- writers need a schema change before the value switch can be understood;
- 8RAW output shows widespread missing-AsLS blanks;
- any path attempts to re-enable `linear_edge` as fallback or rollback.

## Acceptance Criteria

The next implementation goal is done only when:

- primary matrix sample cells use AsLS-corrected selected integration area;
- raw selected area is audit-only;
- missing AsLS does not silently fall back to raw area;
- `baseline_type == "asls"` is required for written selected-integration matrix
  values;
- `linear_edge` remains retired and rejected;
- focused tests prove TSV and XLSX Matrix values use AsLS;
- focused tests prove missing AsLS blanks or reviews instead of falling back;
- review/audit outputs preserve enough raw and AsLS context to explain changed
  values;
- validation closeout states whether evidence is synthetic-only, 8RAW, or
  85RAW.

## Suggested Next Goal Shape

```text
Complete AP0-AP3 for AsLS primary matrix value policy:
characterize current raw selected-integration matrix behavior, populate AsLS
integration fields for alignment cells, switch production matrix value selection
to AsLS-corrected selected integration area, and preserve audit visibility for
raw area and uncertainty.
```

Recommended first PR scope:

- AP0/AP1/AP2/AP3 plus focused tests.
- AP4 only for existing audit fields unless a small companion field is needed.
- AP5 8RAW validation-minimal if the test and code changes pass.

Do not bundle C4 scorer migration, C6 downstream adapter cleanup, or region
boundary promotion into this PR.
