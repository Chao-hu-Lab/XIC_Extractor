# Peak Model Selection

Document status: product-topic source of truth.
Evidence label: `diagnostic_only` for this documentation-governance patch; the
current behavior remains owned by code, tests, and the active model-selection
contracts named below.

This page defines the durable product invariants for selected-hypothesis model
selection over `PeakHypothesis`. It replaces the old notes-path
characterization map as the repo-readable method document.

## Answers

- Which legacy peak-scoring fixture families must remain covered while the
  selected-hypothesis model-selection policy matures.
- Which fixture families are compatibility projections, future policy
  invariants, or retirement candidates.
- Why legacy scoring tests cannot be deleted without a successor invariant.

## Does Not Answer

- It does not approve selected-candidate switching in product outputs.
- It does not change workbook, TSV, final-matrix, GUI, or ProductWriter
  behavior.
- It does not replace the current parity and expected-diff gates in tests and
  implementation contracts.

## Current Contract

Legacy score arithmetic remains the current product oracle wherever public
outputs still expose legacy confidence, reason, score breakdown, selected
markers, or matrix values.

The successor target is `selected_hypothesis_model_selection_v1`. It may become
product authority only through parity or explicit expected-diff approval records
that satisfy the relevant validation tier and matrix-impact gates.

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

## Public Surfaces

- `xic_extractor.peak_detection.model_selection`
- `xic_extractor.evidence_semantics`
- candidate-table and workbook projections that expose selected marker,
  confidence, reason, score breakdown, or final matrix value
- tests that lock parity, blocked-diff, inconclusive, expected-diff, and matrix
  impact behavior

## Workflow

1. Build candidate `PeakHypothesis` values with evidence and audit context.
2. Select a successor hypothesis under `selected_hypothesis_model_selection_v1`.
3. Compare successor selection with the legacy selected candidate.
4. Publish product behavior only when parity holds or an approved expected-diff
   record allows the change.
5. Treat blocked and inconclusive states as no-switch states.

## Verification Gates

- The invariant classes above must remain represented by tests.
- Legacy scoring coverage remains protected while public projections still
  expose legacy scoring semantics:
  `tests/test_peak_scoring.py`, `tests/test_peak_scoring_selection.py`,
  `tests/test_peak_scoring_evidence.py`, and `tests/test_scoring_context.py`.
- Expected-diff approval must include row identity, touched public outputs,
  validation tier, reviewer verdict, and assessed matrix impact when matrix
  values can change.
- Synthetic fixtures alone cannot authorize final-matrix behavior changes.
- Missing legacy selection, parity mismatch, blocked diff, and inconclusive
  states cannot product-switch.

## Common Wrong Moves

- Deleting legacy scoring tests before a successor invariant covers the same
  public behavior.
- Treating stronger successor confidence as product authority without
  expected-diff approval.
- Allowing matrix-value changes from synthetic-only evidence.
- Treating CWT, trace, RT prior, or morphology as standalone authority.

## Source Owners

- [`docs/superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md`](../superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md)
- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/product/evidence-spine.md`](evidence-spine.md)
- [`docs/product/targeted-selection.md`](targeted-selection.md)
- [`docs/product/quantitation-context.md`](quantitation-context.md)
- [`tests/test_peak_model_selection.py`](../../tests/test_peak_model_selection.py)

## When To Update

Update this page when model-selection policy, expected-diff approval, public
selected-candidate behavior, confidence/reason projection, matrix-impact gates,
or the legacy scoring retirement plan changes.
