# RT x MS1 Backfill Cross Evidence Spec

Date: 2026-05-21

Branch: `codex/handoff-level2-rt-shadow-gate`

## Summary

This diagnostic joins two audit-only evidence surfaces:

- Level 2.5 RT-supported shadow gate rows.
- Seed-aware MS1 backfill review family decisions.

The goal is to identify families where RT transfer evidence and rescued-heavy
MS1 backfill evidence agree, while keeping interference, uncertainty, and scope
mismatch explicit.

This diagnostic does not change matrix values, matrix identity, backfill
behavior, targeted reliability, peak scoring, resolver behavior, workbook
schema, or downstream DNP normalization.

## Inputs

Required:

- `instrument_qc_rt_supported_shadow_gate_rows.tsv`
- `seed_aware_backfill_review_families.tsv`

The join key is:

- RT rows: `feature_id`
- seed-aware rows: `feature_family_id`

The input artifacts must come from the same alignment / family-id scope to make
scientific interpretation. If `matched_family_count` is low, the result is an
artifact-scope warning, not evidence that RT support is absent.

## Output

The diagnostic writes:

- `rt_ms1_backfill_cross_evidence_families.tsv`
- `rt_ms1_backfill_cross_evidence_summary.tsv`
- `rt_ms1_backfill_cross_evidence.json`
- `rt_ms1_backfill_cross_evidence.md`

The summary must include:

- seed-aware family count;
- RT family count;
- matched family count;
- counts by combined classification.
- counts by evidence grade.

## Combined Classifications

- `rt_ms1_supported_review_candidate`
  - seed-aware MS1 shape support exists and at least one local RT-supported cell
    exists.
- `rt_supported_ms1_interference_review`
  - RT support exists, but MS1 neighboring interference blocks automatic
    escalation.
- `ms1_supported_rt_conflict_review`
  - MS1 shape support exists, but biological ISTD RT transfer conflicts.
- `ms1_supported_rt_uncertain_review`
  - MS1 shape support exists, but RT model uncertainty remains high.
- `ms1_supported_rt_context_missing`
  - MS1 shape support exists, but no matching RT rows are available.
- `ms1_only_review`
  - MS1 shape support exists, but RT rows do not provide support/conflict/
    uncertainty signal.
- `rt_only_review`
  - RT support exists, but MS1 seed-aware support is not established.
- `rt_conflict_review`
  - RT transfer conflict exists and MS1 support is not sufficient.
- `rt_uncertain_review`
  - RT rows are present but uncertain and MS1 support is not sufficient.
- `ms1_not_ready_review`
  - MS1 evidence is not assessable or shape-insufficient.
- `not_supported`
  - neither evidence axis supports escalation.

## Interpretation Rules

- RT support alone must not rescue a family with high neighboring MS1
  interference.
- MS1 shape support alone must not become a production gate when RT context is
  missing or conflicting.
- RT uncertainty is neutral missing confirmation, not negative evidence. It must
  not downgrade strong seed-aware MS1 shape evidence into a failed family.
- `rt_ms1_supported_review_candidate` means candidate for future opt-in gate
  planning only. It is not a production approval.
- `matched_family_count` must be reviewed before interpreting the classification
  counts. Low overlap means the input artifacts likely came from mismatched
  scopes or stale runs.

## Evidence Grades

The human review surface must include `evidence_grade`, `blocking_evidence`, and
`missing_evidence` so that missing RT context is not confused with conflict.

- `A_dual_axis_supported`
  - Seed-aware MS1 shape support exists and local biological-ISTD RT support
    exists.
  - This is a future opt-in production-gate planning candidate, not production
    approval.
- `B_ms1_shape_supported_rt_unconfirmed`
  - Seed-aware MS1 shape support exists.
  - RT support is missing or uncertain, but there is no RT transfer conflict.
  - This is strong MS1-backed review evidence. It should not be treated as a
    failed family.
- `C_manual_review_interference`
  - Neighboring MS1 interference or comparable manual-review blocker exists.
  - RT support can add context but cannot override the blocker.
- `D_single_axis_or_not_ready`
  - Only RT support exists, or MS1 evidence is shape-insufficient/not
    assessable.
  - Keep as review-only until the missing axis is generated or manually
    resolved.
- `E_conflict_or_not_supported`
  - RT transfer conflict or no useful support exists.
  - This is the only grade family that should be interpreted as genuinely
    negative or blocked by current evidence.

## Current Smoke

The first smoke run used existing Level 2.5 RT rows and existing 85RAW
seed-aware backfill review rows.

Result:

- seed-aware families: `101`
- RT families: `2300`
- matched families: `10`

This proves the diagnostic can run, but it is not enough to judge FAM004459 or
other 85RAW review families. A scientifically interpretable run requires
matching RT shadow rows generated from the same 85RAW family-id scope.

The scope-matched 85RAW follow-up generated matching RT rows for all 101
seed-aware families. It found only two `A_dual_axis_supported` families, but
also surfaced `B_ms1_shape_supported_rt_unconfirmed` rows where MS1 shape is
strong and RT is neutral/missing rather than contradictory.
