# AsLS Primary Matrix Value 8RAW Closeout

**Date:** 2026-06-02
**Readiness label:** `production_candidate`; superseded by 85RAW delivery closeout for `production_ready`
**Goal:** [AsLS primary matrix value policy goal](../plans/2026-06-02-asls-primary-matrix-value-policy-goal.md)
**Spec:** [AsLS primary matrix value policy spec](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md)
**85RAW follow-up:** [AsLS primary matrix value 85RAW closeout](2026-06-02-asls-primary-matrix-value-85raw-closeout.md)

## Verdict

8RAW `validation-minimal` supports the AsLS primary matrix value switch as a
`production_candidate`.

The run proves that matrix written cells are sourced from
`primary_matrix_area` with `primary_matrix_area_source=asls_baseline_corrected`
under `audit_evidence_mode=none`. The later 85RAW closeout is the
production-ready delivery/source gate for this policy.

## Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\asls_primary_matrix_value_8raw_validation `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\asls_primary_matrix_value_8raw_validation\timing.json `
  --timing-live-output output\asls_primary_matrix_value_8raw_validation\timing.live.json
```

Preflight passed before the run:

- discovery batch samples: `8`
- candidate CSVs found: `8`
- RAW paths found: `8`
- output level: `validation-minimal`
- audit evidence mode: `none`

## Artifacts

- `output\asls_primary_matrix_value_8raw_validation\alignment_matrix.tsv`
- `output\asls_primary_matrix_value_8raw_validation\alignment_review.tsv`
- `output\asls_primary_matrix_value_8raw_validation\alignment_cells.tsv`
- `output\asls_primary_matrix_value_8raw_validation\alignment_run_metadata.json`
- `output\asls_primary_matrix_value_8raw_validation\timing.json`

## Matrix Source Check

| Metric | Value |
|---|---:|
| matrix rows | 323 |
| matrix written cells | 2350 |
| alignment cell rows | 19160 |
| written-cell source mismatches | 0 |
| cells where primary matrix area differs from raw `area` | 15444 |
| `missing_asls_primary_area` cells | 2 |
| audit evidence mode | `none` |
| output level | `validation-minimal` |
| integration audit TSV emitted | `False` |

The `0` written-cell source mismatches mean every nonblank primary matrix cell
matched the corresponding `alignment_cells.tsv:primary_matrix_area` and had
`primary_matrix_area_source=asls_baseline_corrected`.

## Missing-AsLS Cells

Only two cells were marked `missing_asls_primary_area`, both rescued cells, and
neither wrote a matrix value:

| feature_family_id | sample_stem | status | raw_area | matrix value |
|---|---|---|---:|---|
| `FAM000389` | `BenignfatBC1055_DNA` | rescued | 1.03044e+06 | blank |
| `FAM000390` | `BenignfatBC1055_DNA` | rescued | 1.03044e+06 | blank |

This is not a widespread AP2 failure. It remains a small review queue for the
next validation pass or 85RAW readiness check.

## Remaining Risk

- This closes 8RAW `production_candidate`. The later 85RAW closeout closes the
  production-ready delivery/source gate.
- The primary matrix schema is stable, but `alignment_cells.tsv` and workbook
  `Audit` now expose `primary_matrix_area`, `primary_matrix_area_source`, and
  `primary_matrix_area_reason` so activation and human review do not reuse raw
  `area` as a product value.
