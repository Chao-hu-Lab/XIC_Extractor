# P2c Owner Boundary Window Validation Note

## Verdict

Status: `diagnostic_only`.

The owner boundary regression reported from the old `d3-5-hmdC / FAM000153`
plot was reproduced and fixed in the alignment owner path. The baseline
subtraction itself is not the main defect for that row. The defect was the owner
XIC re-resolution window: alignment owner construction used the broad fallback
`seed_rt +/- max_rt_sec` window even when the discovery candidate already had a
tighter MS1 peak boundary.

After the fix, the problematic row uses the candidate peak-bound request window
and no longer reaches back into unrelated low-intensity trace.

## Code Changes

- `xic_extractor/alignment/ownership.py`
  - Prefer candidate `ms1_peak_rt_start` / `ms1_peak_rt_end` with 0.10 min
    padding for owner XIC request windows.
  - Fall back to candidate `ms1_search_rt_min` / `ms1_search_rt_max` when peak
    bounds are unavailable.
  - Keep the old `seed_rt +/- max_rt_sec` behavior only as the last fallback.
- `xic_extractor/alignment/primary_consolidation.py`
  - Prefer a detected observation over a same-apex rescued duplicate projection.
  - Preserve the existing stronger-area preference for distinct apex peaks.
- `tests/test_alignment_ownership.py`
  - Adds a regression test proving owner XIC requests use padded candidate peak
    bounds instead of the broad fallback.
- `tests/test_alignment_primary_consolidation.py`
  - Adds a regression test for detected-vs-same-apex rescued duplicate
    selection.

## Key Evidence

Original problematic row from the older audit:

- Sample: `BenignfatBC1055_DNA`
- Target: `d3-5-hmdC`
- Old untargeted family: `FAM000153`
- Targeted boundary: `8.83531-9.12608`
- Old alignment boundary: `7.25717-9.12608`
- Old consistency: `boundary_start_delta_gt_0.10;region_verdict_mismatch;local_mixture_mismatch`

New validation row:

- Sample: `BenignfatBC1055_DNA`
- Target: `d3-5-hmdC`
- New untargeted family: `FAM000162`
- Targeted boundary: `8.83531-9.12608`
- New alignment boundary: `8.83531-9.12608`
- New consistency: `consistent`
- Untargeted/targeted area ratio: `1.000002127`

New plot:

- `output/phase1_p2c_owner_boundary_window_validation/baseline_truth_audit_all_statuses/plots/d3-5-hmdC__FAM000162.png`

## Validation Commands

Unit and process tests:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_ownership.py tests\test_alignment_owner_backfill.py tests\test_alignment_primary_consolidation.py tests\test_alignment_process_backend.py tests\test_alignment_pipeline.py -q
```

Result:

- Initial run: `50 passed in 1.83s`
- Post-review expanded ownership/consolidation run: `53 passed in 1.80s`

Compile smoke:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile xic_extractor\alignment\ownership.py xic_extractor\alignment\owner_backfill.py xic_extractor\alignment\primary_consolidation.py
```

Result:

- Passed.

8-RAW alignment validation:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2c_owner_boundary_window_validation\alignment\asls_shadow --output-level validation --resolver-mode region_first_safe_merge --emit-alignment-cells --emit-alignment-integration-audit --emit-baseline-audit-asls --performance-profile validation-fast
```

Result:

- Passed.

Evidence spine consistency:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.evidence_spine_consistency --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge --alignment-dir output\phase1_p2c_owner_boundary_window_validation\alignment\asls_shadow --output-dir output\phase1_p2c_owner_boundary_window_validation\diagnostics\evidence_spine_consistency
```

Result:

- Rows checked: `72`
- Matched rows: `56`
- Consistent rows: `34`
- Missing alignment rows: `16`
- Mismatch reasons:
  `area_ratio_outside_2x:5;boundary_end_delta_gt_0.10:9;boundary_start_delta_gt_0.10:10;consistent:34;local_mixture_mismatch:11;no_alignment_mz_rt_match:16;region_verdict_mismatch:11`

P2 AsLS shadow gate:

- `overall_status=FAIL`
- Failed rows: `2`
- `max_asls_exceeds_raw_area_count=0`
- `max_area_rsd_delta_pct=2.44774`
- `max_median_abs_relative_diff_pct=14.8289`

P2b promotion gate:

- `overall_status=NO_GO`
- Hard blockers: `2`
- Global blockers: none

## Interpretation

The boundary issue is fixed for the row that triggered this audit. The new
boundary now matches the targeted extraction boundary for the representative
problem row.

This does not make P2b ready by itself. The current P2/P2b gates still fail
because two targets have area RSD regression under AsLS and the revised baseline
truth audit now classifies the corresponding baseline cases as
`manual_review_required` rather than clear `linear_edge_over_subtraction`
support. That means the remaining blocker is gate semantics and area-distribution
review, not the original broad-boundary defect.

## Next Recommendation

Do not change production integration yet. Treat this patch as a boundary-fix
candidate and keep P2b at `NO_GO` until the remaining area/RSD gate semantics are
reviewed with the new boundary-corrected evidence.
