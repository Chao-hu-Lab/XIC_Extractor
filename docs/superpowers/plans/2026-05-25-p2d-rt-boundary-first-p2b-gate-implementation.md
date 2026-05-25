# P2d RT/Boundary-First P2b Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the P2b gate so `area_rsd_regression` is review evidence when RT identity and boundary evidence are sound, instead of treating area variability as a standalone hard blocker.

**Architecture:** Keep AsLS shadow and production integration unchanged. Extend the existing P2b diagnostic gate with optional evidence-spine rows so area regressions can be accepted only when selected-family RT deltas are small and alignment boundaries do not over-expand beyond targeted boundaries. Preserve the old baseline-truth acceptance path for backwards compatibility.

**Tech Stack:** Python stdlib CSV/JSON/dataclasses, existing `tools/diagnostics/` style, pytest, PowerShell validation commands.

---

## Plan Review Log

- Initial plan drafted after P2c evidence showed `area_rsd_regression` remained while selected-family RT deltas were effectively zero and no AsLS area exceeded raw area.
- Review patch 1: make evidence-spine input optional for backwards compatibility, but require it for the new RT/boundary acceptance path.
- Review patch 2: treat over-wide boundary as a hard blocker only when alignment expands beyond targeted by more than `0.10` min. Alignment being narrower than targeted is recorded as review evidence because it affects area but does not prove wrong RT identity.
- Review patch 3: keep this to gate semantics and notes only. Do not change area integration, owner backfill, or boundary algorithms in this step.

## Current Evidence

- P2 gate failures after P2c are only `area_rsd_regression`.
- `asls_exceeds_raw_area_count=0` for all current P2 rows.
- `d3-5-hmdC / FAM000162`: max RT delta across the 8 evidence-spine sample rows is `0.00` sec; 4 rows are narrower on the left boundary compared with targeted; no row is over-wide.
- `d3-5-medC / FAM000030`: max RT delta is `0.00` sec; no row has boundary start/end delta above `0.10` min.
- Targeted ISTD benchmark failures are `AREA_MISMATCH`; selected primary family, coverage, and RT pairing are present.

## Scope

Now:

- Add evidence-spine-aware acceptance to `tools/diagnostics/p2b_asls_promotion_gate.py`.
- Add tests for RT/boundary-supported area variability and for RT/boundary hard blockers.
- Rerun the current P2c artifacts through the revised gate.
- Update P2b spec wording and add a P2d note.

Later:

- Tune the `0.10` min boundary-overwide threshold only if 85RAW or manual EIC review shows it is too strict or too loose.
- Add a richer boundary-quality score if future rows show under-integration can become a production issue.

Not in scope:

- No production switch to AsLS.
- No change to owner backfill.
- No change to local-minimum or CWT boundary selection.
- No Cleanup C-spec implementation.

## Gate Semantics

Existing hard blockers remain:

- missing or unreadable inputs
- `sample_count_lt_2`
- `shadow_coverage_incomplete`
- `area_rsd_unavailable`
- `asls_area_exceeds_raw_area` or `asls_exceeds_raw_area_count > 0`
- unsupported old P2 failure reasons
- P4 area-uncertainty unexplained mismatch or incomplete integration context

Existing accepted review path remains:

- `area_rsd_regression` is accepted when baseline truth reports
  `review_status == linear_edge_over_subtraction_plausible`.

New accepted review path:

- `area_rsd_regression` is accepted when evidence-spine rows for the selected
  family show:
  - at least one row and no missing selected-family evidence
  - max absolute RT delta <= `0.5` sec
  - no alignment-over-wide boundary rows:
    - start over-wide if `boundary_delta_start_min < -0.10`
    - end over-wide if `boundary_delta_end_min > 0.10`

New hard blockers:

- `rt_boundary_evidence_missing`
- `rt_boundary_rt_delta_exceeds_0.5_sec`
- `rt_boundary_alignment_overwide`

Review-only evidence:

- alignment narrower than targeted by more than `0.10` min is recorded in the
  evidence summary, but does not block promotion by itself. It explains area
  differences without proving wrong RT identity.

## Files

- Modify: `tools/diagnostics/p2b_asls_promotion_gate.py`
- Modify: `tests/test_p2b_asls_promotion_gate.py`
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
- Create: `docs/superpowers/notes/2026-05-25-p2d-rt-boundary-first-p2b-gate-note.md`

## Task 1: Failing Tests

- [x] Add `test_revised_gate_accepts_area_rsd_regression_when_rt_boundary_evidence_supports_same_peak`.

Expected fixture:

```python
_write_tsv(
    evidence_spine,
    [
        {
            "sample": "s1",
            "target_label": "ISTD-A",
            "untargeted_family_id": "FAM001",
            "rt_delta_min": "0.00001",
            "boundary_delta_start_min": "0.20",
            "boundary_delta_end_min": "0",
            "mismatch_reason": "boundary_start_delta_gt_0.10",
        },
        {
            "sample": "s2",
            "target_label": "ISTD-A",
            "untargeted_family_id": "FAM001",
            "rt_delta_min": "0",
            "boundary_delta_start_min": "0",
            "boundary_delta_end_min": "0",
            "mismatch_reason": "consistent",
        },
    ],
)
```

Expected assertion:

```python
outputs, result = run_p2b_asls_promotion_gate(
    p2_gate_rows_tsv=p2_rows,
    baseline_truth_summary_tsv=truth,
    area_uncertainty_summary_tsv=uncertainty,
    evidence_spine_rows_tsv=evidence_spine,
    output_dir=tmp_path / "gate",
)
assert result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE"
assert result.rows[0].revised_status == "ACCEPTED_REVIEW"
assert "rt_boundary_evidence_supports_area_variability" in result.rows[0].accepted_reasons
assert result.rows[0].evidence_spine_status == "rt_boundary_supported"
```

- [x] Add `test_revised_gate_blocks_area_rsd_regression_when_rt_delta_is_large`.

Use the same fixture, but set `rt_delta_min` to `0.02`; expected hard blocker
`rt_boundary_rt_delta_exceeds_0.5_sec`.

- [x] Add `test_revised_gate_blocks_area_rsd_regression_when_alignment_is_overwide`.

Use the same fixture, but set `boundary_delta_start_min` to `-0.20`; expected
hard blocker `rt_boundary_alignment_overwide`.

- [x] Run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2b_asls_promotion_gate.py -q
```

Expected before implementation: failures because `evidence_spine_rows_tsv` and
evidence-spine row fields do not exist.

## Task 2: Gate Implementation

- [x] Add fields to `P2bAslsPromotionGateRow` and `ROW_FIELDS`:

```python
"evidence_spine_status",
"evidence_spine_sample_count",
"evidence_spine_max_abs_rt_delta_sec",
"evidence_spine_overwide_boundary_count",
"evidence_spine_narrower_boundary_count",
```

- [x] Add optional `evidence_spine_rows_tsv: Path | None = None` to
  `run_p2b_asls_promotion_gate()` and `--evidence-spine-rows-tsv` to the CLI.

- [x] Parse evidence-spine rows with required columns:

```python
_EVIDENCE_SPINE_REQUIRED_COLUMNS = {
    "target_label",
    "untargeted_family_id",
    "rt_delta_min",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
}
```

- [x] Add helper `_summarize_evidence_spine(rows, target_label, family_id)` that
  returns:

```python
{
    "status": "rt_boundary_supported" | "rt_boundary_evidence_missing" | "rt_boundary_rt_delta_exceeds_0.5_sec" | "rt_boundary_alignment_overwide",
    "sample_count": int,
    "max_abs_rt_delta_sec": float | None,
    "overwide_boundary_count": int,
    "narrower_boundary_count": int,
}
```

Rules:

```python
max_abs_rt_delta_sec = max(abs(rt_delta_min) * 60)
overwide if boundary_delta_start_min < -0.10 or boundary_delta_end_min > 0.10
narrower if boundary_delta_start_min > 0.10 or boundary_delta_end_min < -0.10
```

- [x] In `_build_row()`, when `area_rsd_regression` appears and baseline truth
  is not supportive, accept the row only if evidence-spine summary status is
  `rt_boundary_supported`.

- [x] If evidence status is a blocker, add it to `hard_blockers`.

## Task 3: Real 8RAW Rerun

- [x] Run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2b_asls_promotion_gate --p2-gate-rows-tsv output\phase1_p2c_owner_boundary_window_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --baseline-truth-summary-tsv output\phase1_p2c_owner_boundary_window_validation\baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv --area-uncertainty-summary-tsv output\phase1_p4_area_uncertainty_formula\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv --evidence-spine-rows-tsv output\phase1_p2c_owner_boundary_window_validation\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv --output-dir output\phase1_p2d_rt_boundary_first_p2b_gate
```

Expected current result:

- `overall_status=GO_FOR_PRODUCTION_CANDIDATE`
- `hard_blocker_count=0`
- `review_accepted_count=2`
- `d3-5-hmdC` accepted because RT is correct and remaining boundary difference
  is narrower, not over-wide
- `d3-5-medC` accepted because RT and boundaries are consistent

## Task 4: Documentation

- [x] Update P2b spec to state area RSD is not a standalone hard blocker when
  RT/boundary evidence supports same-peak identity.
- [x] Add P2d note with:
  - root cause of the old NO_GO
  - real command/result
  - remaining limits: 8RAW candidate only, not production-ready, 85RAW still
    required before production switch

## Acceptance Criteria

- Tests for baseline-truth path, RT/boundary-supported path, large RT blocker,
  over-wide boundary blocker, raw-area blocker, and P4 uncertainty blocker pass.
- Real P2d gate exits `0` on current P2c 8RAW artifacts.
- Output rows include machine-readable RT/boundary evidence fields.
- Final wording does not claim `production_ready` or switch production AsLS.
