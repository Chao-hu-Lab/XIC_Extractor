# AsLS Primary Matrix Value 85RAW Closeout

**Date:** 2026-06-02
**Readiness label:** `production_ready` for primary matrix value delivery
**Goal:** [AsLS primary matrix value policy goal](../plans/2026-06-02-asls-primary-matrix-value-policy-goal.md)
**Spec:** [AsLS primary matrix value policy spec](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md)

## Verdict

85RAW `validation-minimal` with `production-equivalent` backfill supports the
AsLS primary matrix value switch as `production_ready` for the delivery/source
contract:

```text
alignment_matrix.tsv sample cells =
  alignment_cells.tsv:primary_matrix_area
  where primary_matrix_area_source == asls_baseline_corrected
```

This closes the product-output question that previously left the final matrix
on a raw or linear-edge-compatible area path. It does not claim that AsLS has
completed every independent baseline-truth axis such as spike-in recovery,
concentration-series linearity, blank/carryover behavior, or synthetic absolute
area truth.

## Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\asls_primary_matrix_value_85raw_validation `
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\asls_primary_matrix_value_85raw_validation\timing.json `
  --timing-live-output output\asls_primary_matrix_value_85raw_validation\timing.live.json
```

Preflight passed before the run:

- discovery batch samples: `85`
- candidate CSVs found: `85`
- RAW paths found: `85`
- output level: `validation-minimal`
- backfill scope: `production-equivalent`
- audit evidence mode: `none`
- owner backfill window strategy: `super-window`

## Artifacts

- `output\asls_primary_matrix_value_85raw_validation\alignment_matrix.tsv`
- `output\asls_primary_matrix_value_85raw_validation\alignment_review.tsv`
- `output\asls_primary_matrix_value_85raw_validation\alignment_cells.tsv`
- `output\asls_primary_matrix_value_85raw_validation\skipped_evidence_ledger.tsv`
- `output\asls_primary_matrix_value_85raw_validation\alignment_run_metadata.json`
- `output\asls_primary_matrix_value_85raw_validation\timing.json`

## Matrix Source Check

| Metric | Value |
|---|---:|
| matrix rows | 610 |
| matrix nonblank cells | 39094 |
| alignment cell rows | 1854020 |
| matrix cells with a matching cell row | 39094 |
| missing cell joins | 0 |
| written-cell source mismatches | 0 |
| written-cell value mismatches | 0 |
| `missing_asls_primary_area` cells | 25 |
| `missing_asls_primary_area` cells written to Matrix | 0 |
| audit evidence mode | `none` |
| output level | `validation-minimal` |
| backfill scope | `production-equivalent` |

The `0` source and value mismatches mean every nonblank primary matrix cell
matched the corresponding `alignment_cells.tsv:primary_matrix_area` and had
`primary_matrix_area_source=asls_baseline_corrected`.

## Missing-AsLS Cells

All 25 `missing_asls_primary_area` cells were rescued cells, and none wrote a
matrix value. This is not an AP2 product-path failure because the invariant is
to blank missing-AsLS cells rather than silently fall back to raw `area`.

Representative rows:

| feature_family_id | sample_stem | status | raw_area | matrix value |
|---|---|---|---:|---|
| `FAM003801` | `BenignfatBC1068_DNA` | rescued | 752976 | blank |
| `FAM003801` | `BenignfatBC1117_DNA` | rescued | 390935 | blank |
| `FAM003801` | `NormalBC2263_DNA` | rescued | 412634 | blank |
| `FAM003801` | `NormalBC2283_DNA` | rescued | 827367 | blank |
| `FAM003801` | `TumorBC2265_DNA` | rescued | 1.08835e+06 | blank |

## Remaining Risk

- `production_ready` here is scoped to final-matrix delivery/source semantics:
  the matrix no longer publishes raw or linear-edge-compatible area as the
  primary quantitative value.
- Absolute baseline-truth validation remains a separate science question. The
  current PR should not claim that AsLS has completed spike-in, linearity, blank
  subtraction, carryover, or synthetic absolute-area truth validation.
- `linear_edge` references that remain in diagnostics or docs must stay
  historical, guarded, or side-by-side audit labels; they must not become
  product fallback.
