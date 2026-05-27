# P2b 85RAW Foreground Validation Note

**Date:** 2026-05-26
**Status:** `production_candidate` for the 85RAW primary matrix/review/cells
surface; `WARN` decision report after known AREA_MISMATCH exceptions.

## Verdict

The foreground 85RAW validation run completed successfully with the maintained
operational command shape:

- `.venv\Scripts\python.exe`
- 85RAW discovery batch index with `85` rows
- `--output-level validation-minimal`
- `--backfill-scope production-equivalent`
- `--audit-evidence-mode none`
- `--performance-profile validation-fast`
- `--owner-backfill-window-strategy super-window`
- `--owner-backfill-superwindow-span-factor 2`
- timing JSON plus live heartbeat

This validates the primary alignment delivery surface for the current P2b
state. It does not by itself retire `linear_edge`; that remains blocked on the
separate AsLS truth-validation requirement.

## Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --baseline-integration-method asls `
  --timing-output output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\timing.json `
  --timing-live-output output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\timing.live.json
```

Result: exit code `0`, shell wall-clock about `706 s`.

## Artifacts

- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\alignment_matrix.tsv`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\alignment_review.tsv`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\alignment_cells.tsv`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\skipped_evidence_ledger.tsv`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\alignment_run_metadata.json`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\timing.json`
- `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground\timing.live.json`
- `output\phase1_p2b_85raw_formal_validation\diagnostics\targeted_istd_benchmark_85raw_foreground\targeted_istd_benchmark_summary.tsv`
- `output\phase1_p2b_85raw_formal_validation\diagnostics\alignment_decision_report_85raw_foreground\alignment_decision_report.html`

## Metadata Check

`alignment_run_metadata.json` records:

- `baseline_integration_method = asls`
- `output_level = validation-minimal`
- `backfill_scope = production-equivalent`
- `audit_evidence_mode = none`
- `owner_backfill_window_strategy = super-window`
- `owner_backfill_superwindow_span_factor = 2`
- `resolver_mode = local_minimum` after alignment's production resolver guard

## Equivalence

Compared against the accepted P8b 85RAW super-window run:

`output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow`

Primary TSV hashes were byte-identical:

- `alignment_matrix.tsv`
- `alignment_review.tsv`
- `alignment_cells.tsv`

Targeted ISTD benchmark summary was also byte-identical to the accepted P8b
benchmark summary.

## Timing

Key timing records:

- `alignment.build_owners`: `31.35 s`
- `alignment.cluster_owners`: `125.53 s`
- `alignment.backfill_scope`: `105.80 s`
- `alignment.owner_backfill`: `212.21 s`
- `alignment.build_matrix`: `3.48 s`
- `alignment.write_outputs`: `77.05 s`

Owner-backfill metrics:

- `extract_xic_count`: `160,939`
- `extract_xic_batch_count`: `679`
- `raw_chromatogram_call_count`: `679`
- `point_count`: `109,254,070`

## Targeted Benchmark

`tools.diagnostics.targeted_istd_benchmark` returned exit code `1` because the
strict benchmark still marks two known `AREA_MISMATCH` rows as failures:

- `d4-N6-2HE-dA`
- `d3-N6-medA`

This is unchanged from the accepted P8b result and does not introduce new RT,
identity, or coverage failures.

## Decision Report

`tools.diagnostics.alignment_decision_report` with known exceptions returned
exit code `0` and verdict `WARN`:

- matrix rows: `592`
- samples: `85`
- ISTD pass: `4`
- ISTD known: `2`
- ISTD fail: `0`

## Remaining Risk

- `AREA_MISMATCH` remains a strict-area policy warning, not a new P2b blocker.
- Linear-edge retirement still requires a separate AsLS truth-validation result.
- `alignment_cell_integration_audit.tsv` is intentionally not emitted in this
  validation-minimal run. This run validates the primary delivery surface, not a
  full audit export.
