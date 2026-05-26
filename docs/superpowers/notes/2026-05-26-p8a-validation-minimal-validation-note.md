# P8a Validation Minimal Output Note

Status: `validated_8raw_machine_gate_surface`

Date: 2026-05-26

## Goal

Fix the alignment validation delivery contract:

- downstream correction/statistics consumes `alignment_matrix.tsv`;
- targeted ISTD benchmark additionally needs `alignment_review.tsv` and
  `alignment_cells.tsv`;
- `.xlsx`, HTML, owner-edge, status-matrix, event-owner, and ambiguous-owner
  artifacts are not default validation handoff outputs.

This is output thinning only. It does not change peak selection, backfill
selection, matrix construction, or benchmark logic.

## Code Contract

New output level:

```text
validation-minimal
```

Artifacts:

- `alignment_matrix.tsv`
- `alignment_review.tsv`
- `alignment_cells.tsv`

P7 scoped runs may also emit sidecars:

- `alignment_run_metadata.json`
- `skipped_evidence_ledger.tsv`
- `timing.json`
- `timing.live.json`

## 8RAW Smoke

First command shape, with explicit audit-evidence skip:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --timing-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal\timing.json `
  --timing-live-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal\timing.live.json
```

Result:

- exit code: 0
- shell wall-clock: 46.2 s
- heavy audit enabled: `False`
- output level: `validation-minimal`

Second command omitted `--audit-evidence-mode none` to verify the
`validation-minimal` auto default:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal_auto `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --performance-profile validation-fast `
  --timing-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal_auto\timing.json `
  --timing-live-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal_auto\timing.live.json
```

Auto-default result:

- exit code: 0
- shell wall-clock: 38.2 s
- requested audit evidence mode: `auto`
- resolved audit evidence mode: `none`
- audit evidence mode reason: `validation_minimal_default_no_audit`
- heavy audit enabled: `False`
- `alignment.write_outputs`: 0.78 s

Artifacts written:

| Artifact | Size bytes |
|---|---:|
| `alignment_cells.tsv` | 4,046,443 |
| `alignment_review.tsv` | 1,044,564 |
| `skipped_evidence_ledger.tsv` | 348,027 |
| `alignment_matrix.tsv` | 29,461 |
| `timing.json` | 16,602 |
| `timing.live.json` | 16,602 |
| `alignment_run_metadata.json` | 985 |

The auto-default run wrote the same artifact set with the same data artifact
sizes, except sidecar JSON size differences caused by metadata text.

Not written:

- `alignment_results.xlsx`
- `review_report.html`
- `owner_edge_evidence.tsv`
- `alignment_matrix_status.tsv`
- `event_to_ms1_owner.tsv`
- `ambiguous_ms1_owners.tsv`

## Timing

| Stage | Previous 8RAW full output sec | P8a minimal sec |
|---|---:|---:|
| `alignment.build_owners` | 9.28 | 12.05 |
| `alignment.backfill_scope` | 1.09 | 1.19 |
| `alignment.owner_backfill` | 22.87 | 25.35 |
| `alignment.write_outputs` | 6.22 | 0.95 |

`write_outputs` dropped from 6.22 s to 0.95 s for 8RAW. The same contract
prevents the known 85RAW large-output problem, where the previous validation
run wrote a 263.4 MB `.xlsx`, 163.7 MB owner-edge TSV, and 30.7 MB status
matrix that were not required for downstream correction/statistics handoff.

New owner-backfill aggregate timing metrics are now available on
`alignment.owner_backfill`:

- `extract_xic_count`: 14,056
- `extract_xic_batch_count`: 235
- `raw_chromatogram_call_count`: 5,660
- `point_count`: 2,690,779
- `mean_xic_per_extract_batch`: 59.81
- `mean_xic_per_raw_chromatogram_call`: 2.48

This confirms batching by `raw_xic_batch_size` works at the request layer, but
raw chromatogram locality is still poor. That is a separate optimization
candidate and was not changed in P8a.

## Targeted ISTD Benchmark

Command shape:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal `
  --output-dir output\phase1_p8a_validation_minimal\diagnostics\targeted_istd_benchmark_8raw_validation_minimal
```

Result:

- exit code: 1
- benchmark artifacts were produced from minimal TSV outputs
- overall strict benchmark status: `FAIL`
- all failures are `AREA_MISMATCH`

The same benchmark command also completed against
`output/phase1_p8a_validation_minimal/alignment/8raw_validation_minimal_auto`,
again producing summary/matches/json/report from minimal TSV outputs only.

Rows:

| Target | Status | Failure | Selected |
|---|---|---|---|
| `d3-5-hmdC` | `FAIL` | `AREA_MISMATCH` | `FAM000162` |
| `d3-5-medC` | `FAIL` | `AREA_MISMATCH` | `FAM000030` |
| `d4-N6-2HE-dA` | `FAIL` | `AREA_MISMATCH` | `FAM000803` |
| `15N5-8-oxodG` | `PASS` |  | `FAM000563` |
| `[13C,15N2]-8-oxo-Guo` | `PASS` | inactive tag excluded |  |
| `d3-N6-medA` | `FAIL` | `AREA_MISMATCH` | `FAM000285` |
| `d3-dG-C8-MeIQx` | `FAIL` | `AREA_MISMATCH` | `FAM001807` |

Interpretation:

- The output contract fix is valid: targeted benchmark no longer needs `.xlsx`
  or HTML alignment artifacts.
- The strict 8RAW benchmark still reports area-only mismatches. This is not a
  new output-thinning failure.
- No RT or identity logic was changed in this P8a slice.

## Decision

P8a is ready as a small, positive optimization.

It removes meaningless large validation outputs from the default machine gate
surface and adds the missing batching/locality metrics needed to decide the next
optimization from evidence instead of guessing.

Next likely optimization candidates:

1. Keep validation runs on `validation-minimal`.
2. Investigate raw chromatogram locality / super-window batching separately.
3. Do not reintroduce `.xlsx` or HTML into 85RAW validation unless the task is
   explicitly human review or workbook compatibility.
