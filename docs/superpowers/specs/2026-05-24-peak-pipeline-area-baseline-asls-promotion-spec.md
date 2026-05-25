# P2b — Area Integration AsLS Promotion Spec

**Date:** 2026-05-24
**Status:** Revised 8RAW promotion-candidate gate implemented
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** P2 AsLS shadow emitted, P4 uncertainty formula decision
recorded, and baseline-truth plus RT/boundary evidence available. P3
third-party shadow disposition should be recorded when available, but P3 is
`diagnostic_only` external-reference evidence and is not a hard P2b gate.

## Purpose

Promote the AsLS area baseline path from P2 shadow evidence toward the
production `area_baseline_corrected` source, but only if validation shows that
AsLS has no hard correctness blockers and the apparent regressions are
explained by baseline-truth evidence.

P2 is intentionally shadow-only. This spec is the missing promotion gate that
Phase 2 cleanup depends on. If P2b does not land with a GO note, Cleanup must
not assume AsLS is production and C1a / C5 / C1b have to be rewritten around
the linear-edge production state.

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
- selected-family RT delta above 0.5 sec
- alignment boundary expansion beyond the targeted boundary by more than
  0.10 min on either side
- P4 area-uncertainty rows with unexplained area mismatches or incomplete
  integration context

The revised P2b gate accepts `area_rsd_regression` when either:

- the baseline truth summary for that selected feature reports
  `review_status == linear_edge_over_subtraction_plausible`; or
- evidence-spine rows for the selected family show same-peak support:
  selected-family evidence is complete, max absolute RT delta is <= 0.5 sec,
  and alignment does not over-expand beyond the targeted boundary.

Alignment being narrower than targeted is review evidence, not a hard blocker,
because it changes area but does not prove wrong RT identity.

The revised 8RAW gate can produce `GO_FOR_PRODUCTION_CANDIDATE`. It is not a
`production_ready` release gate because 85RAW has not been rerun in this
worktree. A direct production switch still requires a separate owner-accepted
promotion step or an explicit waiver of the 85RAW requirement.

## Required Change After Production-Switch GO

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
   - area RSD rows that are worse than linear-edge are either absent or have
     accepted baseline-truth or RT/boundary evidence; strict RSD-only
     comparison is not a hard blocker by itself
   - no `area_baseline_corrected_asls > area` row
   - RT residual median does not regress by more than 0.5 sec
   - selected-family boundary evidence has no over-wide expansion beyond the
     targeted boundary by more than 0.10 min
   - identity coherence verdicts match the pre-promotion run
2. 85RAW cohort rerun:
   - no new `unexplained_area_mismatch`
   - no systematic loss of detected / rescued cells in the strict ISTD set
   - top area-difference outliers have manual-reviewable audit rows
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

Engineering owner and methodology owner jointly review the 8RAW, 85RAW, P4,
baseline-truth, RT/boundary, and any available P3 disposition evidence. Without
an explicit GO note, this promotion has not landed.
