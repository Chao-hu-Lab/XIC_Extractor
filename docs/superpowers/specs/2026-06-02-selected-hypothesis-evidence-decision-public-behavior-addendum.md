# Selected-Hypothesis Evidence Decision Public Behavior Addendum

Doc placement: repo_subcontract_doc
Doc kind: spec
Doc lifecycle: implemented
Repo owner: docs/product/evidence-spine.md
Doc exit rule: Retire or convert to support after selected-hypothesis evidence-decision behavior is fully represented in docs/product/evidence-spine.md and related model-selection docs.

**Date:** 2026-06-02
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Revised after xhigh spec review
**Behavior label:** production extraction-result projection, output values
preserved
**Parent launch contract:** [C4 / C6 / Region Public Behavior Retirement Productization Design](2026-06-02-public-behavior-retirement-productization-design.md)
**Primary design:** [C4 -- Peak Scoring Evidence-Decision Design](retired-provenance:af29f907f881)

Historical roadmap alias: this phase was previously tracked as `C4`; product
code, schema, metadata, and tests should use selected-hypothesis / evidence
decision naming instead of roadmap shorthand.

## Verdict

The current production path still uses `peak_scoring.py` to score candidates and
`select_candidate_with_confidence(...)` to choose the selected peak. That scorer
is not dead and must not be deleted or bypassed in this phase.

The product problem is that selected peak behavior is still explained as raw
score / cap mechanics even though the project direction is evidence-chain
selection. This phase does not complete scorer retirement. It promotes a
selected-hypothesis evidence decision projection into the production extraction
path and exits explicitly as `active_policy_remaining`:

```text
legacy scorer selects current peak
  -> selected PeakHypothesis records the selected candidate and evidence facts
  -> PeakHypothesisSelectionDecision exposes decision class, reasons, and
     compatibility projection
  -> public confidence/reason values remain exact legacy-compatible text
```

This is the smallest public behavior step that makes the evidence-chain
projection real without hiding a selected-candidate behavior change. The
remaining retirement decision is a later selected-hypothesis model-selection
parity or expected-diff behavior artifact.

## Production Projection Owner

The concrete production projection owner for this phase is
`PeakHypothesisSelectionDecision`.

Responsibilities:

- name the selected candidate through `selected_candidate_id`;
- name the selected hypothesis and its trace group;
- expose the decision class from `EvidenceDecisionSemantics`;
- expose support, conflict, review, not-counted, exclusion, and ambiguity
  reasons as typed evidence-decision facts;
- expose `evidence_sources` so downstream review can see whether the decision
  came from MS1, MS2/NL, RT, CWT/morphology, quality flags, or compatibility
  labels;
- preserve legacy public confidence, raw score, cap labels, and reason text as
  compatibility projection while current output contracts expose them;
- state `legacy_projection_status` so this phase cannot be mistaken for scorer
  retirement;
- state the policy source as `selected_hypothesis_decision_v1`;
- state the compatibility oracle as `legacy_peak_scoring_current_oracle`.

`PeakHypothesisSelectionDecision` is not a new evidence model. It is a selected
hypothesis decision projection over existing `PeakHypothesis`,
`EvidenceVector`, `CommonEvidence`, and `EvidenceDecisionSemantics`.

## Implementation Contract

Placement:

- Define `PeakHypothesisSelectionDecision` in a peak-domain module, preferably
  `xic_extractor/peak_detection/selection_decision.py`.
- Do not define it in `peak_scoring.py`, `extractor.py`, writers, GUI code, or
  `result_assembly.py`.

Required fields:

| Field | Required meaning |
|---|---|
| `selected_candidate_id` | Selected hypothesis id or empty fallback when no selected hypothesis exists. |
| `trace_group_id` | Selected hypothesis trace group id or empty fallback. |
| `decision_class` | Existing decision vocabulary: `accepted`, `review`, `not_counted`, `excluded`, or `ambiguous`. |
| `projected_confidence` | Public compatibility confidence. |
| `projected_reason` | Public compatibility reason text. |
| `support_reasons` | Typed support reasons from `EvidenceDecisionSemantics`. |
| `conflict_reasons` | Typed conflict reasons from `EvidenceDecisionSemantics`. |
| `review_reasons` | Typed review reasons from `EvidenceDecisionSemantics`. |
| `not_counted_reasons` | Typed not-counted reasons from `EvidenceDecisionSemantics`. |
| `exclusion_reasons` | Typed exclusion reasons from `EvidenceDecisionSemantics`. |
| `ambiguity_reasons` | Typed ambiguity reasons from `EvidenceDecisionSemantics`. |
| `compatibility_labels` | Legacy labels carried by `EvidenceDecisionSemantics`. |
| `evidence_sources` | Coarse source labels derived from the selected evidence, such as `ms1_trace`, `candidate_aligned_ms2_nl`, `role_aware_rt`, `cwt_boundary_morphology_context`, `trace_morphology`, `legacy_compatibility_projection`. |
| `legacy_projection_status` | `active_policy_remaining` in this phase. |
| `policy_source` | `selected_hypothesis_decision_v1`. |
| `compatibility_oracle` | `legacy_peak_scoring_current_oracle`. |

Fallback behavior:

- If a selected hypothesis exists, build the decision from that hypothesis.
- If the selected hypothesis lacks `EvidenceDecisionSemantics`, build a
  `review` decision with `insufficient_typed_evidence` and use existing
  confidence/reason fallbacks.
- If no selected hypothesis exists, `ExtractionResult.selection_decision` may be
  `None`; public confidence/reason fallback remains the existing behavior.

Public projection ownership:

- `build_extraction_result(...)` must derive `ExtractionResult.confidence` from
  `selection_decision.projected_confidence` when a decision exists.
- `build_extraction_result(...)` must derive `ExtractionResult.reason` from
  `selection_decision.projected_reason` when a decision exists.
- Tests must prove this path, so the decision object cannot be a decorative
  wrapper over unrelated legacy accessors.

## Public Diff Contract

Allowed diff:

- `ExtractionResult` may expose an additional `selection_decision` attribute.
- Candidate audit rows may expose decision-class / reason-projection columns
  only if this addendum is updated and output-schema tests are added before the
  writer change.
- Internal metadata, tests, and closeout docs may record that selected
  confidence/reason are projected from selected-hypothesis decision semantics.

Preserved values:

- selected candidate;
- selected RT, area, boundary, and integration values;
- public `confidence`;
- public `reason`;
- `score_breakdown`;
- support / concern / cap labels;
- candidate TSV / CSV / XLSX / workbook column order and values unless a
  reviewer-approved schema addendum is added first.

Output-schema rule:

- This phase initially preserves candidate TSV/CSV/XLSX/workbook schemas. If
  decision fields are added later, the schema must version or explicitly append
  fields with tests proving existing columns and values remain stable.

## Legacy Disposition

| Legacy surface | Current role | Phase disposition | Exit rule |
|---|---|---|---|
| `score_candidate(...)` | Active scorer policy and scorer fact source. | `active_policy_remaining` and `legacy_peak_scoring_current_oracle`. | Keep until a selected-hypothesis model-selection policy proves selected-candidate and explanation parity or a behavior spec approves changed rows. |
| `select_candidate_with_confidence(...)` | Active selected-candidate policy. | `active_policy`. | Keep. Do not move in this phase. |
| `EvidenceScore.raw_score`, confidence caps, cap labels | Current compatibility values and scorer policy. | `legacy_compatibility_projection`. | Keep exact public projection while exposed. Future policy may not treat raw score/caps as product truth. |
| `build_evidence_reason(...)` and `score_breakdown_fields(...)` | Public reason / breakdown projection. | `compatibility_adapter`. | Keep exact text and ordering. Extract only after review/not-counted policy is supplied by the decision owner. |
| `EvidenceVector.decision_semantics` | Internal typed evidence-decision projection. | `successor_decision_semantics`. | Use as the decision source for `PeakHypothesisSelectionDecision`. |
| `PeakHypothesis.audit.selected` | Records current selected candidate after scorer selection. | `successor_owned` for selected-hypothesis identity projection. | Later model selection may replace the scorer only with selected-candidate parity or explicit expected-diff contract. |

## Decision Classes And Compatibility Projection

`PeakHypothesisSelectionDecision.decision_class` uses the existing vocabulary:

- `accepted`
- `review`
- `not_counted`
- `excluded`
- `ambiguous`

The public `confidence` and `reason` fields remain compatibility projection:

- `projected_confidence` equals the selected hypothesis evidence confidence,
  then the existing `PeakDetectionResult` fallback;
- `projected_reason` equals the selected hypothesis evidence reason, then the
  existing `PeakDetectionResult` fallback;
- `compatibility_labels` includes legacy support, concern, cap, proposal-source,
  and quality labels from `EvidenceDecisionSemantics`.

Legacy `VERY_LOW` / review-only text may project to `not_counted` decision
semantics, but this phase does not change whether the old public result is
counted in downstream tables. That routing remains a later model-selection or
output-contract decision.

## Product Path Requirements

Implementation must connect the decision to the normal extraction path:

1. `selected_handoff_peak(...)` builds production `PeakHypothesis` objects.
2. The selected hypothesis produces a `PeakHypothesisSelectionDecision`.
3. `build_extraction_result(...)` attaches that decision to `ExtractionResult`.
4. `ExtractionResult.confidence` and `ExtractionResult.reason` are read from
   `selection_decision.projected_confidence` and
   `selection_decision.projected_reason` when a decision exists.
5. Candidate audit/hypothesis tests prove the decision is based on the selected
   hypothesis and not recomputed from a separate score path.

## Tests

Required focused coverage:

- selected-hypothesis decision construction for accepted / review /
  not-counted typed semantics;
- production handoff attaches a decision for an OK selected hypothesis;
- `build_extraction_result(...)` preserves existing public confidence/reason
  while deriving those fields from `selection_decision`;
- runtime type-hint/import smoke for `ExtractionResult.selection_decision`;
- candidate table / CSV / XLSX / workbook tests continue to prove no schema or
  value drift unless a later schema addendum is approved;
- public imports from `xic_extractor.peak_scoring` stay valid.

Focused verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

## Stop Rules

Stop and re-review if implementation requires:

- changing the selected candidate;
- changing public confidence, reason, score, cap, support, or concern values;
- changing candidate TSV / CSV / XLSX / workbook schema without a schema
  addendum;
- making CWT, RT, local S/N, shape, or MS2/NL a single-source authority;
- making raw-score parity the future product oracle;
- adding a fourth evidence model instead of projecting through
  `PeakHypothesis`, `EvidenceVector`, `CommonEvidence`, and
  `EvidenceDecisionSemantics`.

## Done When

- `PeakHypothesisSelectionDecision` is the named product decision projection for
  selected-hypothesis evidence decisions.
- Normal extraction results expose that decision.
- Public confidence/reason output parity is proven through
  `selection_decision.projected_confidence` and
  `selection_decision.projected_reason`.
- Legacy scorer policy is explicitly retained as current oracle, not future
  product truth.
- Closeout says `active_policy_remaining` and names the next required artifact:
  selected-hypothesis model-selection parity spec, expected-diff behavior spec,
  or legacy-retirement spec.
- No output schema changes occur without an approved addendum.
- xhigh spec review and implementation review findings are recorded in a
  closeout note.
