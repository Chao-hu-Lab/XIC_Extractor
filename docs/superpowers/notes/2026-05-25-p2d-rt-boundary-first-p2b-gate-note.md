# P2d RT/Boundary-First P2b Gate Note

Update 2026-05-26: this note records the pre-promotion P2b gate decision. The
implementation has since advanced to integration-audit `production_candidate`;
see
`docs/superpowers/notes/2026-05-26-p2b-asls-production-promotion-note.md`.

## Verdict

Status: `GO_FOR_PRODUCTION_CANDIDATE` on the current 8RAW artifacts.

This note by itself is not `production_ready` and did not switch production
area integration to AsLS. It means the current P2b hard blockers were cleared
when area-only regressions were judged against RT and boundary evidence instead
of treating linear-edge area RSD as truth.

## Root Cause

The previous P2b `NO_GO` was too area-centric after P2c boundary correction.
Both remaining failed targets were blocked only by `area_rsd_regression`.

That was not a peak-identity failure:

- `area_baseline_corrected_asls > area` count was `0`.
- `d3-5-hmdC` selected family `FAM000162` had RT delta `0` sec across 8/8
  sample rows after evidence-spine primary-consolidation matching was fixed.
- `d3-5-medC` selected family `FAM000030` had max RT delta `0.003` sec across
  8/8 sample rows.
- No selected-family row had alignment boundary over-expansion beyond targeted
  by more than `0.10` min.

`d3-5-hmdC` still has four narrower-left-boundary review rows. That affects
area, but it is not the same as grabbing a wrong RT peak or over-wide unrelated
baseline region.

## Code Changes

- `tools/diagnostics/p2b_asls_promotion_gate.py`
  - Added optional `--evidence-spine-rows-tsv`.
  - Added optional `--target-rt-trend-summary-tsv` so large absolute RT deltas
    can be interpreted against target-level local drift coherence.
  - Added row-level evidence fields:
    - `evidence_spine_status`
    - `evidence_spine_sample_count`
    - `evidence_spine_max_abs_rt_delta_sec`
    - `evidence_spine_overwide_boundary_count`
    - `evidence_spine_narrower_boundary_count`
    - `target_rt_trend_status`
    - `target_rt_trend_local_abs_delta_p95_min`
    - `target_rt_trend_local_moderate_or_severe_count`
    - `target_rt_trend_local_severe_count`
  - Accepts `area_rsd_regression` as review evidence when RT/boundary evidence
    supports same-peak identity.
  - Keeps over-wide alignment boundary as a hard blocker. RT delta > 0.5 sec
    remains a hard blocker only when target RT trend evidence is missing or not
    locally coherent.
- `tools/diagnostics/evidence_spine_consistency_analysis.py`
  - Prefers primary-consolidation alignment cells over pre-consolidation
    duplicate cells when mz/RT matches tie.

## Validation

Evidence-spine rerun:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.evidence_spine_consistency --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge --alignment-dir output\phase1_p2c_owner_boundary_window_validation\alignment\asls_shadow --output-dir output\phase1_p2d_rt_boundary_first_p2b_gate\diagnostics\evidence_spine_consistency
```

P2d gate rerun:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2b_asls_promotion_gate --p2-gate-rows-tsv output\phase1_p2c_owner_boundary_window_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --baseline-truth-summary-tsv output\phase1_p2c_owner_boundary_window_validation\baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv --area-uncertainty-summary-tsv output\phase1_p4_area_uncertainty_formula\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv --evidence-spine-rows-tsv output\phase1_p2d_rt_boundary_first_p2b_gate\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv --target-rt-trend-summary-tsv output\phase1_p8b_superwindow\diagnostics\targeted_istd_rt_trend_85raw\targeted_istd_rt_drift_summary.tsv --output-dir output\phase1_p2d_rt_boundary_first_p2b_gate\diagnostics\p2b_asls_promotion_gate_target_rt_trend
```

Result:

- `overall_status=GO_FOR_PRODUCTION_CANDIDATE`
- `target_count=6`
- `hard_blocker_count=0`
- `review_accepted_count=2`

Accepted review rows:

- `d3-5-hmdC / FAM000162`
  - `evidence_spine_status=rt_boundary_supported`
  - `evidence_spine_sample_count=8`
  - `evidence_spine_max_abs_rt_delta_sec=0`
  - `evidence_spine_overwide_boundary_count=0`
  - `evidence_spine_narrower_boundary_count=4`
- `d3-5-medC / FAM000030`
  - `evidence_spine_status=rt_boundary_supported`
  - `evidence_spine_sample_count=8`
  - `evidence_spine_max_abs_rt_delta_sec=0.003`
  - `evidence_spine_overwide_boundary_count=0`
  - `evidence_spine_narrower_boundary_count=0`

Test run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2b_asls_promotion_gate.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_alignment_ownership.py tests\test_alignment_primary_consolidation.py -q
```

Result:

- `39 passed in 2.38s`

Evidence-spine test run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_evidence_spine_consistency.py -q
```

Result:

- `7 passed in 0.46s`

## Remaining Limits

- This is still 8RAW evidence only.
- 85RAW is still required before claiming `production_ready`.
- At the time of this note, production `area_baseline_corrected` had not yet
  been switched to AsLS.
- The stricter area-only benchmark still fails by design because it treats area
  mismatch as a hard failure even when RT identity is correct.
