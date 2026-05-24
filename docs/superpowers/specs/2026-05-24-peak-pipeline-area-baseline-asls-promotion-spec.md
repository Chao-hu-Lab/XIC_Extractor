# P2b — Area Integration AsLS Promotion Spec

**Date:** 2026-05-24
**Status:** Promotion gate draft v0.1
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** P2 AsLS shadow emitted, P3 third-party shadow comparison
findings recorded, and P4 uncertainty formula decision recorded.

## Purpose

Promote the AsLS area baseline path from P2 shadow evidence to the production
`area_baseline_corrected` source, but only if validation shows that AsLS is
strictly no worse than the existing linear-edge path on the strict ISTD and
real-cohort gates.

P2 is intentionally shadow-only. This spec is the missing promotion gate that
Phase 2 cleanup depends on. If P2b does not land with a GO note, Cleanup must
not assume AsLS is production and C1a / C5 / C1b have to be rewritten around
the linear-edge production state.

## Required Change

After the GO decision:

- switch the production area integration path from linear-edge baseline to
  AsLS for `area_baseline_corrected`
- keep `area_baseline_corrected_linear_edge` available as a temporary audit
  or rollback field if reviewers need side-by-side output during promotion
- update `BaselineIntegration.baseline_type` to report `"asls"` on production
  rows
- update the relevant config / CLI / settings-schema default so production
  runs select AsLS without requiring the P2 shadow flag
- keep shadow comparison artifacts from P2 / P3 as evidence only; production
  modules must not read those artifacts

## Validation Contract

Promotion requires:

1. 8RAW strict ISTD rerun:
   - area RSD under AsLS is lower than or within +0.3 absolute percentage
     points of linear-edge for every strict ISTD
   - RT residual median does not regress by more than 0.5 sec
   - identity coherence verdicts match the pre-promotion run
2. 85RAW cohort rerun:
   - no new `unexplained_area_mismatch`
   - no systematic loss of detected / rescued cells in the strict ISTD set
   - top area-difference outliers have manual-reviewable audit rows
3. P3 third-party comparison:
   - AsLS does not increase third-party area disagreement counts by more than
     the linear-edge baseline
   - matrix-hump cases where AsLS improves disagreement are listed in the GO
     note
4. P4 uncertainty formula:
   - the promoted area path and uncertainty audit use the same baseline
     residual source, or the difference is documented as a temporary
     compatibility exception

## Rollback Condition

Rollback to linear-edge production baseline if any of:

- a strict ISTD area RSD regression exceeds the threshold above
- identity coherence verdicts change without an accepted evidence explanation
- 85RAW produces new `unexplained_area_mismatch` rows
- downstream workbook / TSV consumers cannot tolerate the promoted area values
  after threshold review

Rollback keeps the P2 AsLS shadow implementation in place unless the bug is in
the AsLS integration function itself.

## Cleanup Handoff

Phase 2 cleanup may treat AsLS as the production area baseline only after this
spec has a GO note under `docs/superpowers/notes/`.

The GO note must state:

- production baseline method after promotion
- validation artifact paths
- any temporary linear-edge audit / rollback field that still exists
- whether C1a, C5, and C1b can start without rewriting their assumptions

## Acceptance Owner

Engineering owner and methodology owner jointly review the 8RAW, 85RAW, P3,
and P4 evidence. Without an explicit GO note, this promotion has not landed.
