# P2b — Area Integration AsLS Promotion Spec

**Date:** 2026-05-24
**Status:** Conditional audit promotion implemented; 8RAW promoted-schema gate
and 85RAW primary-delivery validation passed; not production-ready baseline
truth
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** P2 AsLS shadow emitted, P4 uncertainty formula decision
recorded, and baseline-truth plus RT/boundary evidence available. P3
third-party shadow disposition should be recorded when available, but P3 is
`diagnostic_only` external-reference evidence and is not a hard P2b gate.
**Superseding product-flow correction:** [Mature package flow reference](2026-06-02-mature-package-flow-reference-spec.md)

## 2026-06-02 Final-Matrix Correction

This spec predates the completed linear-edge retirement and must be read as a
historical audit-promotion contract.

Any references below to linear-edge production state, linear-edge rollback, or
linear-edge-compatible output are historical transition language. They do not
authorize `linear_edge` as a current product baseline, final-matrix primary
value, fallback value, or rollback target.

Current product direction:

- `linear_edge` is retired from product quantitation;
- final matrix quantitation must not use a linear-edge or legacy-baseline value
  as its primary area;
- any historical linear-edge-compatible value may exist only in explicitly named
  diagnostic, side-by-side validation, or migration notes;
- the next downstream behavior/output contract is
  [AsLS primary matrix value policy](2026-06-02-asls-primary-matrix-value-policy-spec.md),
  which defines how AsLS-corrected selected integration area becomes the primary
  `alignment_matrix.tsv` value and which audit/uncertainty fields accompany it.

## Purpose

Promote the AsLS area baseline path from P2 shadow evidence toward the
integration-audit `area_baseline_corrected` source, but only if validation shows
that AsLS has no hard identity / RT / boundary correctness blockers and the
apparent regressions are explained by review evidence.

At the time this spec was written, it did not prove that AsLS had better
absolute area accuracy, linearity, blank subtraction, or tuned parameters. Those
truth axes remain useful validation evidence, but they no longer make
linear-edge a current product fallback.

P2 was intentionally shadow-only. In the historical 2026-05-24 checkpoint, this
spec was the missing promotion gate that Phase 2 cleanup depended on. Current
cleanup and final-matrix work must use the 2026-06-02 correction above instead
of rewriting around a retired linear-edge product state.

## 2026-05-25 Revised Gate Semantics

The original strict comparator treated linear-edge area RSD as the truth: AsLS
failed when its area RSD was more than +0.3 absolute percentage points worse
than linear-edge. The P2 baseline truth audit showed that this was the wrong
hard-blocker semantics. Area is baseline-sensitive and can vary under manual or
algorithmic integration without proving wrong peak identity.

The all-status baseline truth audit also checked the old P2 `PASS` families.
Those families showed the same `linear_edge_over_subtraction_plausible` pattern,
so old P2 `PASS` does not prove linear-edge area is the better baseline truth.
It only means the old RSD comparator did not flag the family.

The revised P2b gate keeps hard blockers for:

- missing or unreadable inputs
- incomplete AsLS shadow coverage
- unavailable area RSD
- `area_baseline_corrected_asls > area`
- unsupported old P2 failure reasons
- missing baseline truth for an `area_rsd_regression`
- missing RT/boundary evidence when baseline truth is not enough to accept an
  `area_rsd_regression`
- selected-family RT delta above 0.5 sec unless target-level RT trend evidence
  shows the target is locally coherent
- alignment boundary expansion beyond the targeted boundary by more than
  0.10 min on either side
- P4 area-uncertainty rows with unexplained area mismatches or incomplete
  integration context

The revised P2b gate accepts `area_rsd_regression` when either:

- the baseline truth summary for that selected feature reports
  `review_status == linear_edge_over_subtraction_plausible`; or
- evidence-spine rows for the selected family show same-peak support:
  selected-family evidence is complete, max absolute RT delta is <= 0.5 sec,
  and alignment does not over-expand beyond the targeted boundary; or
- evidence-spine rows have large absolute RT delta, but a target RT trend
  summary shows the target is locally coherent
  (`local_abs_delta_p95_min <= 0.10` and no local moderate/severe drift rows),
  so the absolute delta is explained by target-level drift rather than a wrong
  selected peak.

Alignment being narrower than targeted is review evidence, not a hard blocker,
because it changes area but does not prove wrong RT identity.

The revised 8RAW gate can produce a conditional audit promotion. It is not a
`production_ready` release gate and it is not evidence enough to delete
linear-edge. A direct production switch that affects downstream quantitative
delivery still requires a separate owner-accepted promotion step and the
required 85RAW / truth-validation evidence.

## Required Change After Conditional Audit Promotion

After the conditional audit-promotion decision:

- switch the integration-audit baseline path from linear-edge baseline to
  AsLS for `alignment_cell_integration_audit.tsv:area_baseline_corrected`
- keep `area_baseline_corrected_linear_edge` available as a temporary audit
  or rollback field if reviewers need side-by-side output during promotion
- update `BaselineIntegration.baseline_type` to report `"asls"` on production
  audit rows
- update the relevant config / CLI / settings-schema default so audit
  integration can select AsLS without requiring the P2 shadow flag
- keep shadow comparison artifacts from P2 / P3 as evidence only; production
  modules must not read those artifacts

## 2026-05-26 Promotion Implementation Contract

The conditional audit-promotion implementation is intentionally limited to
`alignment_cell_integration_audit.tsv`.

- `baseline_integration_method` was the integration-audit baseline selector for
  this historical checkpoint. Default was `asls`; the historical rollback value
  was `linear_edge`, but the 2026-06-02 correction above supersedes that rollback
  option for current product and final-matrix work.
- Default promoted schema reports `area_baseline_corrected` with
  `baseline_type=asls` and emits `area_baseline_corrected_linear_edge` plus
  `baseline_score_linear_edge` as temporary rollback/audit columns.
- Legacy P2 shadow reruns remain available: `--emit-baseline-audit-asls`
  preserves linear-edge production output and emits `area_baseline_corrected_asls`
  plus `baseline_score_asls` unless an explicit
  `--baseline-integration-method` override is supplied.
- At this historical checkpoint, `alignment_matrix.tsv` stayed driven by
  accepted `cell.area`. Current downstream matrix work must not use this as
  permission to keep a retired-baseline primary value; the final matrix now
  needs an AsLS primary-value behavior/output contract.
- P2/P2b diagnostic tools must interpret both schemas explicitly. In promoted
  schema, linear-edge comparisons use `area_baseline_corrected_linear_edge` and
  AsLS comparisons use `area_baseline_corrected`; in legacy shadow schema,
  linear-edge comparisons use `area_baseline_corrected` and AsLS comparisons use
  `area_baseline_corrected_asls`.
- Area-uncertainty diagnostics compare targeted linear-edge area against
  alignment linear-edge-compatible rollback area when the promoted schema is
  present. Baseline promotion by itself must not create a false
  `unexplained_area_mismatch`.

## Validation Contract

Promotion requires:

1. 8RAW strict ISTD rerun:
   - area RSD rows that are worse than linear-edge are either absent or have
     accepted baseline-truth or RT/boundary evidence; strict RSD-only
     comparison is not a hard blocker by itself
   - no `area_baseline_corrected_asls > area` row
   - RT residual median does not regress by more than 0.5 sec
   - selected-family boundary evidence has no over-wide expansion beyond the
     targeted boundary by more than 0.10 min
   - identity coherence verdicts match the pre-promotion run
2. 85RAW cohort rerun for primary-delivery validation:
   - no new `unexplained_area_mismatch`
   - no systematic loss of detected / rescued cells in the strict ISTD set
   - top area-difference outliers have existing manual-reviewable audit rows or
     known-exception notes
   - primary delivery TSVs (`alignment_matrix.tsv`, `alignment_review.tsv`,
     `alignment_cells.tsv`) are stable against the accepted 85RAW baseline
3. P3 third-party disposition:
   - if P3 findings are available, the GO note records whether they raise any
     new hard blocker; `diagnostic_only`, unavailable external output,
     MassCube runner failure, or absolute-area scale mismatch does not block
     8RAW `GO_FOR_PRODUCTION_CANDIDATE` by itself
   - P3 may support follow-up investigation, but it must not override
     targeted ISTD identity, baseline-truth, or RT/boundary same-peak evidence
4. P4 uncertainty formula:
   - the promoted area path and uncertainty audit use the same baseline
     residual source, or the difference is documented as a temporary
     compatibility exception

## Historical Rollback Condition

Historical rollback to linear-edge production baseline was specified if any of:

- a strict ISTD area RSD regression exceeds the threshold above
- identity coherence verdicts change without an accepted evidence explanation
- 85RAW produces new `unexplained_area_mismatch` rows
- downstream workbook / TSV consumers cannot tolerate the promoted area values
  after threshold review

This rollback language is superseded for current product work. If AsLS primary
matrix promotion finds a blocker now, the allowed outcome is to stop, record a
NO-GO or diagnostic-only state, and fix the AsLS/boundary/matrix contract. It is
not to make linear-edge a current product baseline again.

## Linear-Edge Retirement Blocker

Do not use this spec as approval for C1b or any deletion of
`integrate_linear_edge_baseline`. C1b requires an additional AsLS truth
validation note that addresses at least one real ground-truth axis:

- spike-in recovery,
- concentration-series linearity,
- blank / carryover behavior,
- or synthetic trace benchmark with known baseline and peak area.

RSD, RT/boundary same-peak support, and manual plausibility review are useful
diagnostics, but they are not sufficient to prove baseline accuracy.

## Cleanup Handoff

Phase 2 cleanup may treat AsLS as the conditional integration-audit baseline
only after this spec has a note under `docs/superpowers/notes/`. It may not
retire linear-edge until the separate truth-validation blocker above is cleared.

Current GO note:

- `docs/superpowers/notes/2026-05-26-p2b-asls-production-promotion-note.md`
- `docs/superpowers/notes/2026-05-26-p2b-85raw-foreground-validation-note.md`

The GO note must state:

- production baseline method after promotion
- validation artifact paths
- any temporary linear-edge audit / rollback field that still exists
- whether C1a, C5, and C1b can start without rewriting their assumptions

## Acceptance Owner

Engineering owner and methodology owner jointly review the 8RAW, 85RAW, P4,
baseline-truth, RT/boundary, and any available P3 disposition evidence. Without
an explicit GO note, this promotion has not landed.
