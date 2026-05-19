# Untargeted MS1-Coherence Backfill Review

## Purpose

This note captures manual review for low-seed/high-backfill primary families. It
does not change production matrix identity, scoring, resolver behavior, or
backfill rules.

Allowed manual conclusions:

- `support_backfill`: MS1 shape/RT evidence supports the family and DDA trigger
  limitation is a plausible explanation for missing MS2/NL in many samples.
- `review_only`: evidence is plausible but drift, interference, or metric
  disagreement prevents automatic policy use.
- `reject_backfill`: MS1 evidence does not support using backfill as primary
  family evidence.

## Top 10 Calibration Batch

Batch input:

- Queue TSV: `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_backfill_review\family_ms1_backfill_review_queue.tsv`
- Alignment cells: `output\alignment\untargeted_revalidation_after_targeted_fix_85raw_region_first_safe_merge\alignment_cells.tsv`
- RAW dir: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R`
- DLL dir: `C:\Xcalibur\system\programs`
- Current batch output: `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_v2`

Machine summary after v2 metric tightening:

- Top 30 expansion: `blocked`
- `ms1_shape_supports_family_backfill`: 4
- `review_required_neighboring_ms1_interference`: 4
- `review_required_low_ms1_assessable_coverage`: 2

Review rows:

| rank | family | m/z | RT window | machine verdict | manual conclusion | notes |
|---:|---|---:|---|---|---|---|
| 1 | FAM002741 | 472.198 | 13.6723-15.8723 | review_required_neighboring_ms1_interference | pending | global conflict fraction 0.333 |
| 2 | FAM003689 | 744.831 | 31.4583-33.6583 | ms1_shape_supports_family_backfill | pending |  |
| 3 | FAM003693 | 745.332 | 31.5071-33.7071 | ms1_shape_supports_family_backfill | pending |  |
| 4 | FAM000643 | 283.155 | 9.2122-11.4122 | review_required_neighboring_ms1_interference | pending | global conflict fraction 0.464 |
| 5 | FAM001842 | 358.062 | 13.2032-15.4032 | review_required_low_ms1_assessable_coverage | pending | global assessable fraction 0.232 |
| 6 | FAM003516 | 616.805 | 33.1520-35.3520 | review_required_low_ms1_assessable_coverage | pending | selected-apex coverage 0.565 |
| 7 | FAM001722 | 349.05 | 7.1556-9.3556 | review_required_neighboring_ms1_interference | pending | global conflict fraction 0.431 |
| 8 | FAM000906 | 295.106 | 5.9232-8.1232 | review_required_neighboring_ms1_interference | reject_backfill | user manual review: visually unreasonable; global conflict fraction 0.703 |
| 9 | FAM002454 | 419.05 | 12.1475-14.3475 | ms1_shape_supports_family_backfill | pending |  |
| 10 | FAM000242 | 258.12 | 13.5239-15.7239 | ms1_shape_supports_family_backfill | pending |  |

## Decision Rule

- Top 30 expansion is `eligible` only when every rendered row succeeds with
  machine verdict `ms1_shape_supports_family_backfill`.
- Top 30 expansion is `blocked` by any failed overlay row, any
  `family_verdict` beginning with `review_required_`, or
  `insufficient_nl_seed_support`.
- A blocked Top 10 batch means continue manual review or tighten overlay
  metrics before expanding the audit sample; it is not a production gate,
  scoring change, or matrix identity change.
- Top 10 alone cannot justify a production gate, scoring change, or matrix
  identity change.

## Low MS1 Assessable Coverage Follow-up

Audit output:

- `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\low_ms1_assessable_coverage_audit`

Root-cause split:

| family | root cause | seed evidence | interpretation |
|---|---|---|---|
| FAM001842 | `single_center_xic_not_supported` | `weak_detected_seed_evidence` | selected RT is mostly inside the requested window, but family-center MS1 XIC is absent for many rescued cells |
| FAM003516 | `rt_window_or_multiseed_shift` | `weak_detected_seed_evidence` | single family-centered RT window under-covers selected apex positions, but seed evidence is weak |

Selected-apex window CP:

- Queue:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\low_ms1_assessable_coverage_audit\low_ms1_assessable_coverage_selected_apex_overlay_queue.tsv`
- Overlay output:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_selected_apex_window`
- FAM003516 selected-apex window changed selected apex coverage from `0.565`
  to `1.0`, but global MS1 assessable coverage only reached `0.659`.
- Therefore FAM003516 is not explained by RT/window alone. It remains
  review-only because detected seed evidence is weak (`min_seed_event_count=1`,
  `max_abs_nl_ppm=14.4102`) and many rescued cells still lack family-center XIC
  support.

Current implication:

- Do not promote an MS1-shape backfill gate from these low-coverage cases.
- A production demotion candidate is more defensible than a promotion candidate:
  low detected seed count + rescue-heavy + weak seed evidence + low
  family-center assessability should remain out of automatic primary expansion
  until seed-aware backfill provenance is recorded.

## Owner Backfill Seed Provenance CP

Implementation:

- Added opt-in alignment sidecar:
  `alignment_owner_backfill_seed_audit.tsv`.
- CLI flag:
  `--emit-alignment-backfill-seed-audit`.
- Existing `alignment_cells.tsv` schema is unchanged.
- Sidecar is audit-only and records the actual owner-backfill seed m/z/RT,
  request RT window, ppm, and apex-vs-seed/family-center deltas.

Validation:

- 85RAW rerun output:
  `output\alignment\untargeted_revalidation_after_targeted_fix_85raw_region_first_safe_merge_seed_audit`
- The rerun is not hash-equivalent to the earlier artifact, so old family ids
  were not reused as stable identifiers. For this CP, cases were matched by
  m/z/RT instead of family id.
- The sidecar initially exposed a TSV formatting issue: negative numeric
  deltas were escaped as Excel-protected strings. The writer now keeps numeric
  row values raw and lets the TSV layer format them once.

Matched cases:

| old family | matched current family | m/z | current RT | detected | rescued | seed RT distribution | interpretation |
|---|---|---:|---:|---:|---:|---|---|
| FAM001842 | FAM012728 | 358.062 | 14.1665 | 5 | 79 | 60 cells from 14.1913; 19 from 14.4487 | multi-seed backfill; family-center-only overlay is incomplete |
| FAM003516 | FAM020034 | 616.805 | 34.7364 | 5 | 80 | 55 cells from 33.7168; 25 from 34.5097 | major seed/family-center RT separation; previous low coverage was partly a seed/request-context issue |

Current implication:

- Low MS1 assessable coverage must be re-evaluated using actual
  backfill seed/request context, not only the final family center.
- Multi-seed or large seed-to-apex cases should be routed to seed-specific
  overlay before any production gate conclusion.

## Seed-aware Low-coverage CP

Implementation updates:

- `low_ms1_assessable_coverage_audit.py` now accepts
  `--backfill-seed-audit-tsv`.
- It adds seed distribution, seed-to-apex concern metrics, and a
  `low_ms1_assessable_coverage_seed_overlay_queue.tsv` output.
- If seed provenance shows multiple owner-backfill seeds or large seed-to-apex
  deltas, the root cause is now `seed_aware_overlay_required` instead of a
  premature `single_center_xic_not_supported` demotion conclusion.
- `family_ms1_overlay_batch.py` now honors queue-level `ppm`; seed overlays use
  the actual backfill request ppm instead of silently falling back to the CLI
  default.

Audit output:

- `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\low_ms1_assessable_coverage_seed_audit_cp`
- Seed overlay output:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_seed_overlay_low_coverage_cp`

Seed-aware audit rows:

| family | root cause | seed groups | seed RT span | seed evidence | next action |
|---|---|---:|---:|---|---|
| FAM012728 | `seed_aware_overlay_required` | 2 | 0.2574 | `weak_detected_seed_evidence` | run seed-aware overlay |
| FAM020034 | `seed_aware_overlay_required` | 2 | 0.7929 | `weak_detected_seed_evidence` | run seed-aware overlay |

Seed-specific overlay verdicts:

| family | seed RT | window | rescued cells | verdict | interpretation |
|---|---:|---|---:|---|---|
| FAM012728 | 14.1913 | 11.1913-17.1913 | 60 | `review_required_neighboring_ms1_interference` | assessable coverage becomes complete, but neighboring MS1 interference remains high |
| FAM012728 | 14.4487 | 11.4487-17.4487 | 19 | `review_required_neighboring_ms1_interference` | same family remains review-only because global conflict fraction is high |
| FAM020034 | 33.7168 | 30.7168-36.7168 | 55 | `ms1_shape_supports_family_backfill` | family-center overlay was a false negative caused by seed/request context |
| FAM020034 | 34.5097 | 31.5097-37.5097 | 25 | `ms1_shape_supports_family_backfill` | seed-specific MS1 shape supports the backfilled family |

Current implication:

- A single family-center overlay is not sufficient evidence for promotion or
  demotion in multi-seed backfill families.
- FAM020034 is a real example where seed-specific MS1 evidence supports the
  backfilled primary family despite low family-center assessable coverage.
- FAM012728 is a real example where seed-specific coverage alone is not enough;
  neighboring MS1 interference still blocks automatic promotion.
- The next production-facing candidate is not a broad MS1 gate. It is a
  seed-aware review rule: only escalate rescued-heavy families when
  seed-specific overlay supports shape and does not show high neighboring
  interference.

## Seed-aware Shadow Review Closeout

Review index:

- `docs\superpowers\notes\2026-05-19-seed-aware-backfill-review-index.md`

Diagnostic output:

- `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp`

Current 85RAW shadow result:

- `seed_shape_supported_review_candidate`: 5 families.
- `neighbor_interference_review`: 5 families.
- `not_assessable`: 91 families.
- Shadow blast radius: 5 families / 387 rescued cells would be withheld in a
  future gate candidate.
- Production matrix changes in this checkpoint: none.

Key interpretation:

- FAM020034 remains the positive example for seed-aware backfill review:
  seed-specific overlays support MS1 shape even though family-center overlay
  was low-coverage.
- FAM012728 remains the counterexample: seed-specific coverage improves, but
  neighboring interference is still too high for automatic escalation.
- FAM014256, FAM016922, FAM004459, and FAM006664 remain review-only because
  high neighboring MS1 interference blocks automatic use as a production gate.

Decision:

- `shadow_gate_ready`.
- The rule is ready for a future opt-in production-gate experiment, not for a
  default final-matrix change in this branch.
