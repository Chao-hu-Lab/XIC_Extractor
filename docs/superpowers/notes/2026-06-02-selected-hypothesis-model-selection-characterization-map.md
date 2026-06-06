# Selected-Hypothesis Model-Selection Characterization Map

**Spec:** `docs/superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md`
**Status:** Phase 1 characterization map
**Current oracle:** `legacy_peak_scoring_current_oracle`
**Successor policy target:** `selected_hypothesis_model_selection_v1`

## Verdict

Legacy score arithmetic is still the current product oracle. The future product
invariant is selected-hypothesis model selection over `PeakHypothesis`, with raw
score retained only as compatibility projection while public outputs expose it.

Phase 1 does not retire scorer code or tests. It classifies the legacy selector
fixtures by the product invariant they protect, so later phases can replace
legacy scoring semantics only when a successor invariant exists.

## Invariant Classes

| Fixture family | Legacy surface | Product invariant | Class | Successor handling |
| --- | --- | --- | --- | --- |
| clean single peak | `score_candidate`, `select_candidate_with_confidence` | one selected hypothesis, accepted decision, same confidence/reason projection | future_policy | parity |
| confidence rank | `select_candidate_with_confidence` confidence ordering | stronger confidence wins unless stricter RT/evidence gate overrides by policy | future_policy | parity first |
| role-aware RT prior / ISTD | `ScoringContext.rt_prior`, `prefer_rt_prior_tiebreak`, reason text | RT is contextual support for paired ISTD/STD, not standalone veto | future_policy | parity first, expected-diff only with approved record |
| strict selection RT | `strict_selection_rt` key path | strict RT request preserves selected RT behavior | future_policy | parity |
| final intensity tie-break | selection key fallback | deterministic tie-break when evidence and RT are otherwise equal | compatibility_projection | parity while public |
| local S/N with AsLS | `local_sn_severity`, `baseline_array`, `residual_mad` | local S/N is baseline-aware evidence, not old linear-edge truth | future_policy | parity first |
| shape / width / morphology | severities and quality flags | morphology contributes evidence and review reasons | future_policy | parity first |
| MS2 present / strict NL OK | evidence score support and caps | candidate-aligned MS2/NL supports selected hypothesis | future_policy | parity only under complete candidate evidence, otherwise selected-candidate projection |
| no MS2 / NL fail | caps and review/not-counted reason | missing DDA evidence is not observed by default; legacy not-counted projection remains public | future_policy | parity first |
| MS2 trace tie-break | `ms2_trace_*` support and selection points | trace can support but not single-handedly override contextual selection | future_policy | parity first |
| CWT same-apex support | `cwt_same_apex_support` | CWT is support/context, not standalone authority | future_policy | parity first |
| low-scan demotion | `_low_scan_demotion_ids` | low scan is evidence/quality concern, not hidden scoring truth | retirement_candidate | expected-diff candidate after review |
| dominant strict-NL alternative | `_dominant_area_demotion_ids` | dominant alternative must be explained by multi-evidence semantics | retirement_candidate | expected-diff candidate after review |
| ADAP-like quality flags | quality and selection penalties | quality flags project to morphology/evidence concerns | future_policy | parity first |
| stale final result fallback | `selection_decision_from_hypothesis(..., peak_result=...)` | public fallback confidence/reason remains stable while exposed | compatibility_projection | parity |
| no-candidate / no-peak fallback | `PeakDetectionResult.status` and no decision | no product switch without a selected hypothesis | future_policy | parity |

## Do Not Delete Yet

- `tests/test_peak_scoring.py`
- `tests/test_peak_scoring_selection.py`
- `tests/test_peak_scoring_evidence.py`
- `tests/test_scoring_context.py`
- writer and workbook projection tests that expose confidence, reason, score
  breakdown, selected markers, or final matrix values

## Phase 1 Exit

Phase 1 is complete only when the successor test file names the same invariant
classes and no legacy test deletion is proposed without a successor invariant.
