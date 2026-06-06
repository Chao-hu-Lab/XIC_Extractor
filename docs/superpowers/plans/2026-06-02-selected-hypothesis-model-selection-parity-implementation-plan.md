# Selected-Hypothesis Model-Selection Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the selected-hypothesis model-selection parity migration from Phase 1 through Phase 4 without changing product outputs unless the parity or approved expected-diff gate allows it.

**Architecture:** Keep legacy `score_candidate(...)` and `select_candidate_with_confidence(...)` as the current oracle while a peak-domain shadow selector is introduced under `xic_extractor/peak_detection/model_selection.py`. The successor selector consumes existing `PeakHypothesis` objects, emits machine-readable parity status, and only becomes product owner after parity and expected-diff gates pass.

**Tech Stack:** Python dataclasses and literals, pytest characterization tests, existing `PeakHypothesis`, `PeakHypothesisSelectionDecision`, and legacy peak scoring contracts.

---

## Source Contract

Authoritative spec:

- `docs/superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md`

Current oracle:

- `xic_extractor/peak_scoring.py::score_candidate`
- `xic_extractor/peak_scoring.py::select_candidate_with_confidence`
- `xic_extractor/peak_detection/facade.py::find_peak_and_area`
- `xic_extractor/peak_detection/hypotheses.py::build_peak_hypotheses`
- `xic_extractor/peak_detection/selection_decision.py::selection_decision_from_hypothesis`
- `xic_extractor/extraction/handoff_spine_runtime.py::selected_handoff_peak`

Stop rule:

- Do not product-switch if any row is `blocked_diff` or `inconclusive`.
- Do not approve an MS2/NL-driven expected diff under `limited_evidence_shadow`.
- Do not delete legacy scorer tests before a successor invariant covers the same product behavior.

## Phase 1: Characterization Map

**Files:**

- Create: `docs/superpowers/notes/2026-06-02-selected-hypothesis-model-selection-characterization-map.md`
- Test: `tests/test_peak_model_selection.py`
- Read: `tests/test_peak_scoring.py`
- Read: `tests/test_signal_processing_selection.py`
- Read: `tests/test_peak_hypotheses.py`
- Read: `tests/test_peak_selection_decision.py`

- [ ] **Step 1: Create the characterization map**

  Create `docs/superpowers/notes/2026-06-02-selected-hypothesis-model-selection-characterization-map.md` with this structure:

  ```markdown
  # Selected-Hypothesis Model-Selection Characterization Map

  **Spec:** `docs/superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md`
  **Status:** Phase 1 characterization map
  **Current oracle:** `legacy_peak_scoring_current_oracle`
  **Successor policy target:** `selected_hypothesis_model_selection_v1`

  ## Verdict

  Legacy score arithmetic is still the current product oracle. The future product invariant is selected-hypothesis model selection over `PeakHypothesis`, with raw score retained only as compatibility projection while public outputs expose it.

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
  - writer and workbook projection tests that expose confidence, reason, score breakdown, selected markers, or final matrix values

  ## Phase 1 Exit

  Phase 1 is complete only when the successor test file names the same invariant classes and no legacy test deletion is proposed without a successor invariant.
  ```

- [ ] **Step 2: Add a characterization-map smoke test**

  Add `tests/test_peak_model_selection.py`:

  ```python
  from pathlib import Path


  CHARACTERIZATION_MAP = Path(
      "docs/superpowers/notes/"
      "2026-06-02-selected-hypothesis-model-selection-characterization-map.md"
  )


  def test_characterization_map_covers_required_fixture_families() -> None:
      text = CHARACTERIZATION_MAP.read_text(encoding="utf-8")
      required = [
          "clean single peak",
          "confidence rank",
          "role-aware RT prior / ISTD",
          "strict selection RT",
          "final intensity tie-break",
          "local S/N with AsLS",
          "shape / width / morphology",
          "MS2 present / strict NL OK",
          "no MS2 / NL fail",
          "MS2 trace tie-break",
          "CWT same-apex support",
          "low-scan demotion",
          "dominant strict-NL alternative",
          "ADAP-like quality flags",
          "stale final result fallback",
          "no-candidate / no-peak fallback",
      ]

      for fixture_family in required:
          assert fixture_family in text


  def test_characterization_map_blocks_legacy_test_deletion() -> None:
      text = CHARACTERIZATION_MAP.read_text(encoding="utf-8")

      assert "Do Not Delete Yet" in text
      assert "tests/test_peak_scoring.py" in text
      assert "no legacy test deletion is proposed" in text
  ```

- [ ] **Step 3: Run Phase 1 tests**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py
  ```

  Expected: PASS.

## Phase 2: Shadow Successor Selector

**Files:**

- Create: `xic_extractor/peak_detection/model_selection.py`
- Modify: `tests/test_peak_model_selection.py`
- Modify: `xic_extractor/extraction/handoff_spine_runtime.py`
- Modify only if needed: `xic_extractor/peak_detection/selection_decision.py`

- [ ] **Step 1: Write failing tests for the model-selection result contract**

  Extend `tests/test_peak_model_selection.py` with imports and tests:

  ```python
  from xic_extractor.evidence_semantics import EvidenceDecisionSemantics
  from xic_extractor.peak_detection.hypotheses import (
      AuditTrail,
      EvidenceVector,
      IntegrationResult,
      PeakHypothesis,
  )
  from xic_extractor.peak_detection.model_selection import (
      ExpectedDiffApprovalRecord,
      model_select_peak_hypothesis,
  )


  def test_shadow_model_selection_reports_parity_for_legacy_selected_hypothesis() -> None:
      selected = _hypothesis(
          "selected",
          selected=True,
          confidence="HIGH",
          reason="decision: accepted",
          decision_class="accepted",
      )
      rejected = _hypothesis(
          "rejected",
          selected=False,
          confidence="LOW",
          reason="decision: review",
          decision_class="review",
      )

      result = model_select_peak_hypothesis((selected, rejected))

      assert result.selected_candidate_id == selected.hypothesis_id
      assert result.legacy_selected_candidate_id == selected.hypothesis_id
      assert result.trace_group_id == selected.trace_group_id
      assert result.decision_class == "accepted"
      assert result.selection_status == "parity"
      assert result.public_projection["confidence"] == "HIGH"
      assert result.public_projection["reason"] == "decision: accepted"
      assert result.compatibility_oracle == "legacy_peak_scoring_current_oracle"
      assert result.policy_source == "selected_hypothesis_model_selection_v1"
      assert result.evidence_comparison_policy == "limited_evidence_shadow"
      assert result.product_switch_allowed is True


  def test_shadow_model_selection_blocks_no_legacy_selected_hypothesis() -> None:
      result = model_select_peak_hypothesis(
          (
              _hypothesis("first", selected=False, confidence="HIGH"),
              _hypothesis("second", selected=False, confidence="MEDIUM"),
          )
      )

      assert result.selected_candidate_id == ""
      assert result.legacy_selected_candidate_id == ""
      assert result.selection_status == "inconclusive"
      assert result.product_switch_allowed is False
      assert "missing_legacy_selected_hypothesis" in result.diff_reasons


  def test_expected_diff_without_approval_record_cannot_product_switch() -> None:
      legacy = _hypothesis("legacy", selected=True, confidence="LOW")
      successor = _hypothesis("successor", selected=False, confidence="HIGH")

      result = model_select_peak_hypothesis(
          (legacy, successor),
          successor_selected_candidate_id=successor.hypothesis_id,
      )

      assert result.selection_status == "expected_diff"
      assert result.product_switch_allowed is False
      assert "missing_expected_diff_approval_record" in result.diff_reasons


  def test_blocked_and_inconclusive_statuses_cannot_product_switch() -> None:
      legacy = _hypothesis("legacy", selected=True, confidence="HIGH")
      successor = _hypothesis("successor", selected=False, confidence="HIGH")

      blocked = model_select_peak_hypothesis(
          (legacy, successor),
          successor_selected_candidate_id=successor.hypothesis_id,
          force_selection_status="blocked_diff",
          diff_reasons=("unexplained_successor_mismatch",),
      )
      inconclusive = model_select_peak_hypothesis(
          (legacy, successor),
          force_selection_status="inconclusive",
          diff_reasons=("candidate_evidence_incomplete",),
      )

      assert blocked.product_switch_allowed is False
      assert inconclusive.product_switch_allowed is False


  def test_matrix_affecting_expected_diff_requires_stronger_than_synthetic_validation() -> None:
      legacy = _hypothesis("legacy", selected=True, confidence="LOW")
      successor = _hypothesis("successor", selected=False, confidence="HIGH")
      synthetic_record = ExpectedDiffApprovalRecord(
          stable_row_id="fixture-1",
          sample_name="SampleA",
          target_label="Analyte",
          legacy_selected_candidate_id=legacy.hypothesis_id,
          successor_selected_candidate_id=successor.hypothesis_id,
          public_outputs_touched=("final matrix value",),
          matrix_value_impact="area_value_changed",
          evidence_sources=("ms1_trace",),
          evidence_summary="successor has stronger multi-evidence support",
          validation_tier="synthetic_fixture",
          reviewer_role="implementation-contract-reviewer",
          reviewer_verdict="approved",
          final_label="expected_diff",
      )

      result = model_select_peak_hypothesis(
          (legacy, successor),
          successor_selected_candidate_id=successor.hypothesis_id,
          expected_diff_approval=synthetic_record,
      )

      assert result.selection_status == "expected_diff"
      assert result.product_switch_allowed is False
      assert "matrix_expected_diff_requires_real_validation" in result.diff_reasons
  ```

  Add this helper at the bottom of `tests/test_peak_model_selection.py`:

  ```python
  def _hypothesis(
      suffix: str,
      *,
      selected: bool,
      confidence: str = "HIGH",
      reason: str = "decision: accepted",
      decision_class: str = "accepted",
  ) -> PeakHypothesis:
      return PeakHypothesis(
          hypothesis_id=f"SampleA|Analyte|{suffix}",
          trace_group_id="SampleA|Analyte|trace",
          target_label="Analyte",
          role="Analyte",
          istd_pair="ISTD",
          analysis_mode="targeted",
          resolver_mode="region_first_safe_merge",
          integration=IntegrationResult(
              rt_left_min=8.4,
              rt_apex_min=8.5,
              rt_right_min=8.6,
              raw_apex_rt_min=8.5,
              rt_width_min=0.2,
              height_raw=1200.0,
              height_smoothed=1100.0,
              area_raw_counts_seconds=1234.0,
          ),
          evidence=EvidenceVector(
              confidence=confidence,
              reason=reason,
              decision_semantics=EvidenceDecisionSemantics(
                  decision_class=decision_class,
                  support_reasons=("ms1_coherent",),
                  compatibility_labels=("strict_nl_ok",),
              ),
          ),
          audit=AuditTrail(
              selected=selected,
              selection_rank=1 if selected else 2,
              selection_reference_rt_min=8.5,
          ),
      )
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py
  ```

  Expected: FAIL because `xic_extractor.peak_detection.model_selection` does not exist.

- [ ] **Step 3: Implement the shadow selector**

  Create `xic_extractor/peak_detection/model_selection.py`:

  ```python
  from __future__ import annotations

  from collections.abc import Mapping
  from dataclasses import dataclass
  from typing import Literal

  from xic_extractor.evidence_semantics import DecisionClass
  from xic_extractor.peak_detection.hypotheses import PeakHypothesis
  from xic_extractor.peak_detection.selection_decision import (
      SelectionDecisionCompatibilityOracle,
  )

  ModelSelectionStatus = Literal[
      "parity",
      "expected_diff",
      "blocked_diff",
      "inconclusive",
  ]
  EvidenceComparisonPolicy = Literal[
      "complete_candidate_evidence",
      "limited_evidence_shadow",
  ]
  MatrixValueImpact = Literal[
      "none",
      "area_value_changed",
      "presence_changed",
      "not_assessed",
  ]
  ExpectedDiffValidationTier = Literal[
      "synthetic_fixture",
      "targeted_benchmark",
      "8raw",
      "manual_eic_ms2_review",
      "not_validated",
  ]
  ExpectedDiffReviewerVerdict = Literal["approved", "blocked", "inconclusive"]
  ExpectedDiffFinalLabel = Literal[
      "expected_diff",
      "blocked_diff",
      "inconclusive",
  ]
  ModelSelectionPolicySource = Literal[
      "selected_hypothesis_model_selection_v1"
  ]


  @dataclass(frozen=True)
  class ExpectedDiffApprovalRecord:
      stable_row_id: str
      sample_name: str
      target_label: str
      legacy_selected_candidate_id: str
      successor_selected_candidate_id: str
      public_outputs_touched: tuple[str, ...]
      matrix_value_impact: MatrixValueImpact
      evidence_sources: tuple[str, ...]
      evidence_summary: str
      validation_tier: ExpectedDiffValidationTier
      reviewer_role: str
      reviewer_verdict: ExpectedDiffReviewerVerdict
      final_label: ExpectedDiffFinalLabel


  @dataclass(frozen=True)
  class PeakModelSelectionResult:
      selected_candidate_id: str
      legacy_selected_candidate_id: str
      trace_group_id: str
      decision_class: DecisionClass | Literal["ambiguous"]
      selection_status: ModelSelectionStatus
      selection_reasons: tuple[str, ...]
      legacy_reasons: tuple[str, ...]
      diff_reasons: tuple[str, ...]
      public_projection: Mapping[str, str]
      evidence_sources: tuple[str, ...]
      compatibility_oracle: SelectionDecisionCompatibilityOracle
      policy_source: ModelSelectionPolicySource
      product_switch_allowed: bool
      evidence_comparison_policy: EvidenceComparisonPolicy


  def model_select_peak_hypothesis(
      hypotheses: tuple[PeakHypothesis, ...],
      *,
      successor_selected_candidate_id: str | None = None,
      expected_diff_approval: ExpectedDiffApprovalRecord | None = None,
      force_selection_status: ModelSelectionStatus | None = None,
      diff_reasons: tuple[str, ...] = (),
      evidence_comparison_policy: EvidenceComparisonPolicy = "limited_evidence_shadow",
  ) -> PeakModelSelectionResult:
      legacy_selected = _legacy_selected_hypothesis(hypotheses)
      if legacy_selected is None:
          return _blocked_result(
              hypotheses,
              status="inconclusive",
              diff_reasons=("missing_legacy_selected_hypothesis", *diff_reasons),
              evidence_comparison_policy=evidence_comparison_policy,
          )

      selected_id = successor_selected_candidate_id or legacy_selected.hypothesis_id
      selected = _hypothesis_by_id(hypotheses, selected_id)
      if selected is None:
          return _blocked_result(
              hypotheses,
              status="inconclusive",
              legacy_selected_candidate_id=legacy_selected.hypothesis_id,
              diff_reasons=("missing_successor_selected_hypothesis", *diff_reasons),
              evidence_comparison_policy=evidence_comparison_policy,
          )

      status = force_selection_status or (
          "parity"
          if selected.hypothesis_id == legacy_selected.hypothesis_id
          else "expected_diff"
      )
      final_diff_reasons = diff_reasons
      if status == "expected_diff":
          final_diff_reasons = _expected_diff_reasons(
              expected_diff_approval,
              selected=selected,
              legacy_selected=legacy_selected,
              existing=diff_reasons,
          )

      return PeakModelSelectionResult(
          selected_candidate_id=selected.hypothesis_id,
          legacy_selected_candidate_id=legacy_selected.hypothesis_id,
          trace_group_id=selected.trace_group_id,
          decision_class=_decision_class(selected),
          selection_status=status,
          selection_reasons=_selection_reasons(selected),
          legacy_reasons=_selection_reasons(legacy_selected),
          diff_reasons=final_diff_reasons,
          public_projection=_public_projection(selected),
          evidence_sources=_evidence_sources(selected),
          compatibility_oracle="legacy_peak_scoring_current_oracle",
          policy_source="selected_hypothesis_model_selection_v1",
          product_switch_allowed=_product_switch_allowed(
              status,
              expected_diff_approval,
              final_diff_reasons,
          ),
          evidence_comparison_policy=evidence_comparison_policy,
      )


  def _legacy_selected_hypothesis(
      hypotheses: tuple[PeakHypothesis, ...],
  ) -> PeakHypothesis | None:
      for hypothesis in hypotheses:
          if hypothesis.audit.selected:
              return hypothesis
      return None


  def _hypothesis_by_id(
      hypotheses: tuple[PeakHypothesis, ...],
      hypothesis_id: str,
  ) -> PeakHypothesis | None:
      for hypothesis in hypotheses:
          if hypothesis.hypothesis_id == hypothesis_id:
              return hypothesis
      return None


  def _blocked_result(
      hypotheses: tuple[PeakHypothesis, ...],
      *,
      status: Literal["blocked_diff", "inconclusive"],
      diff_reasons: tuple[str, ...],
      evidence_comparison_policy: EvidenceComparisonPolicy,
      legacy_selected_candidate_id: str = "",
  ) -> PeakModelSelectionResult:
      trace_group_id = hypotheses[0].trace_group_id if hypotheses else ""
      return PeakModelSelectionResult(
          selected_candidate_id="",
          legacy_selected_candidate_id=legacy_selected_candidate_id,
          trace_group_id=trace_group_id,
          decision_class="ambiguous",
          selection_status=status,
          selection_reasons=(),
          legacy_reasons=(),
          diff_reasons=diff_reasons,
          public_projection={},
          evidence_sources=(),
          compatibility_oracle="legacy_peak_scoring_current_oracle",
          policy_source="selected_hypothesis_model_selection_v1",
          product_switch_allowed=False,
          evidence_comparison_policy=evidence_comparison_policy,
      )


  def _selection_reasons(hypothesis: PeakHypothesis) -> tuple[str, ...]:
      semantics = hypothesis.evidence.decision_semantics
      if semantics is None:
          return tuple(
              dict.fromkeys(
                  (
                      *hypothesis.evidence.support_labels,
                      *hypothesis.evidence.concern_labels,
                      *hypothesis.evidence.cap_labels,
                  )
              )
          )
      return tuple(
          dict.fromkeys(
              (
                  *semantics.support_reasons,
                  *semantics.conflict_reasons,
                  *semantics.review_reasons,
                  *semantics.not_counted_reasons,
                  *semantics.exclusion_reasons,
                  *semantics.ambiguity_reasons,
              )
          )
      )


  def _decision_class(
      hypothesis: PeakHypothesis,
  ) -> DecisionClass | Literal["ambiguous"]:
      semantics = hypothesis.evidence.decision_semantics
      return semantics.decision_class if semantics is not None else "review"


  def _public_projection(hypothesis: PeakHypothesis) -> dict[str, str]:
      return {
          "confidence": hypothesis.evidence.confidence,
          "reason": hypothesis.evidence.reason,
      }


  def _evidence_sources(hypothesis: PeakHypothesis) -> tuple[str, ...]:
      sources: list[str] = []
      evidence = hypothesis.evidence
      if evidence.common is not None or evidence.prominence is not None:
          sources.append("ms1_trace")
      if evidence.ms2_present is not None or evidence.nl_match is not None:
          sources.append("candidate_aligned_ms2_nl")
      if evidence.rt_prior_min is not None:
          sources.append("role_aware_rt")
      if (
          evidence.cwt_best_scale is not None
          or evidence.cwt_ridge_persistence is not None
          or "centwave_cwt" in hypothesis.audit.proposal_sources
      ):
          sources.append("cwt_boundary_morphology_context")
      if evidence.quality_flags or evidence.region_trace_continuity is not None:
          sources.append("trace_morphology")
      if (
          evidence.confidence
          or evidence.reason
          or evidence.raw_score is not None
          or evidence.support_labels
          or evidence.concern_labels
          or evidence.cap_labels
      ):
          sources.append("legacy_compatibility_projection")
      return tuple(dict.fromkeys(sources))


  def _expected_diff_reasons(
      approval: ExpectedDiffApprovalRecord | None,
      *,
      selected: PeakHypothesis,
      legacy_selected: PeakHypothesis,
      existing: tuple[str, ...],
  ) -> tuple[str, ...]:
      reasons = list(existing)
      if approval is None:
          reasons.append("missing_expected_diff_approval_record")
          return tuple(dict.fromkeys(reasons))
      if approval.reviewer_verdict != "approved":
          reasons.append("expected_diff_approval_not_approved")
      if approval.final_label != "expected_diff":
          reasons.append("expected_diff_final_label_not_expected_diff")
      if approval.legacy_selected_candidate_id != legacy_selected.hypothesis_id:
          reasons.append("expected_diff_legacy_candidate_mismatch")
      if approval.successor_selected_candidate_id != selected.hypothesis_id:
          reasons.append("expected_diff_successor_candidate_mismatch")
      if not approval.public_outputs_touched:
          reasons.append("expected_diff_missing_public_output_impact")
      if (
          approval.matrix_value_impact in {"area_value_changed", "presence_changed"}
          and approval.validation_tier == "synthetic_fixture"
      ):
          reasons.append("matrix_expected_diff_requires_real_validation")
      return tuple(dict.fromkeys(reasons))


  def _product_switch_allowed(
      status: ModelSelectionStatus,
      approval: ExpectedDiffApprovalRecord | None,
      diff_reasons: tuple[str, ...],
  ) -> bool:
      if status == "parity":
          return True
      if status != "expected_diff" or approval is None or diff_reasons:
          return False
      return approval.reviewer_verdict == "approved" and approval.final_label == "expected_diff"
  ```

- [ ] **Step 4: Add shadow result to handoff runtime without changing product output**

  Modify `xic_extractor/extraction/handoff_spine_runtime.py`:

  ```python
  from xic_extractor.peak_detection.model_selection import (
      PeakModelSelectionResult,
      model_select_peak_hypothesis,
  )
  ```

  Extend `HandoffPeakSelection`:

  ```python
  @dataclass(frozen=True)
  class HandoffPeakSelection:
      candidate_ms2_evidence: CandidateMS2Evidence | None
      selected_hypothesis: PeakHypothesis | None
      selection_decision: PeakHypothesisSelectionDecision | None
      trace_group: TraceGroup | None
      model_selection_result: PeakModelSelectionResult | None = None
  ```

  In `selected_handoff_peak`, compute and attach the shadow result:

  ```python
      model_selection_result = (
          model_select_peak_hypothesis(hypotheses) if hypotheses else None
      )
      return HandoffPeakSelection(
          candidate_ms2_evidence=candidate_ms2_evidence,
          selected_hypothesis=selected_hypothesis,
          selection_decision=(
              selection_decision_from_hypothesis(
                  selected_hypothesis,
                  peak_result=peak_result,
              )
              if selected_hypothesis is not None
              else None
          ),
          trace_group=trace_group,
          model_selection_result=model_selection_result,
      )
  ```

- [ ] **Step 5: Run Phase 2 focused tests**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py tests/test_target_extraction.py tests/test_peak_selection_decision.py tests/test_result_assembly.py
  ```

  Expected: PASS.

## Phase 3: Expected-Diff Review Gate

**Files:**

- Modify: `tests/test_peak_model_selection.py`
- Modify: `xic_extractor/peak_detection/model_selection.py`

- [ ] **Step 1: Add approval-record switch tests**

  Add tests:

  ```python
  def test_approved_non_matrix_expected_diff_can_product_switch() -> None:
      legacy = _hypothesis("legacy", selected=True, confidence="LOW")
      successor = _hypothesis("successor", selected=False, confidence="HIGH")
      approval = ExpectedDiffApprovalRecord(
          stable_row_id="fixture-2",
          sample_name="SampleA",
          target_label="Analyte",
          legacy_selected_candidate_id=legacy.hypothesis_id,
          successor_selected_candidate_id=successor.hypothesis_id,
          public_outputs_touched=("confidence", "reason"),
          matrix_value_impact="none",
          evidence_sources=("ms1_trace", "trace_morphology"),
          evidence_summary="successor projection is better supported",
          validation_tier="synthetic_fixture",
          reviewer_role="implementation-contract-reviewer",
          reviewer_verdict="approved",
          final_label="expected_diff",
      )

      result = model_select_peak_hypothesis(
          (legacy, successor),
          successor_selected_candidate_id=successor.hypothesis_id,
          expected_diff_approval=approval,
      )

      assert result.selection_status == "expected_diff"
      assert result.diff_reasons == ()
      assert result.product_switch_allowed is True


  def test_ms2_expected_diff_is_inconclusive_under_limited_evidence_shadow() -> None:
      legacy = _hypothesis("legacy", selected=True, confidence="LOW")
      successor = _hypothesis("successor", selected=False, confidence="HIGH")
      approval = ExpectedDiffApprovalRecord(
          stable_row_id="fixture-3",
          sample_name="SampleA",
          target_label="Analyte",
          legacy_selected_candidate_id=legacy.hypothesis_id,
          successor_selected_candidate_id=successor.hypothesis_id,
          public_outputs_touched=("confidence",),
          matrix_value_impact="none",
          evidence_sources=("candidate_aligned_ms2_nl",),
          evidence_summary="candidate MS2/NL supports successor",
          validation_tier="synthetic_fixture",
          reviewer_role="implementation-contract-reviewer",
          reviewer_verdict="approved",
          final_label="expected_diff",
      )

      result = model_select_peak_hypothesis(
          (legacy, successor),
          successor_selected_candidate_id=successor.hypothesis_id,
          expected_diff_approval=approval,
          evidence_comparison_policy="limited_evidence_shadow",
      )

      assert result.selection_status == "inconclusive"
      assert result.product_switch_allowed is False
      assert "ms2_expected_diff_requires_complete_candidate_evidence" in result.diff_reasons
  ```

- [ ] **Step 2: Implement limited-evidence MS2/NL guard**

  In `model_select_peak_hypothesis`, after computing `status`, add:

  ```python
      if (
          status == "expected_diff"
          and expected_diff_approval is not None
          and evidence_comparison_policy == "limited_evidence_shadow"
          and "candidate_aligned_ms2_nl" in expected_diff_approval.evidence_sources
      ):
          status = "inconclusive"
          final_diff_reasons = (
              "ms2_expected_diff_requires_complete_candidate_evidence",
              *diff_reasons,
          )
      else:
          final_diff_reasons = diff_reasons
          if status == "expected_diff":
              final_diff_reasons = _expected_diff_reasons(
                  expected_diff_approval,
                  selected=selected,
                  legacy_selected=legacy_selected,
                  existing=diff_reasons,
              )
  ```

  Remove the earlier duplicate `final_diff_reasons` block so the function has one status/reason decision point.

- [ ] **Step 3: Run Phase 3 tests**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py
  ```

  Expected: PASS.

## Phase 4: Product Switch Candidate

**Files:**

- Modify: `xic_extractor/extraction/handoff_spine_runtime.py`
- Modify: `tests/test_target_extraction.py`
- Modify only if public projection must change: `xic_extractor/peak_detection/selection_decision.py`

Important: Phase 4 is a candidate switch only if Phase 2 and Phase 3 are green. If any mismatch is not classified as `parity` or approved `expected_diff`, stop and report `shadow_ready`, not `production_ready`.

- [ ] **Step 1: Add product-switch safety test**

  Extend `tests/test_target_extraction.py` around the existing handoff assertions:

  ```python
      assert handoff.model_selection_result is not None
      assert handoff.model_selection_result.selection_status == "parity"
      assert handoff.model_selection_result.product_switch_allowed is True
      assert handoff.selection_decision is not None
      assert (
          handoff.selection_decision.selected_candidate_id
          == handoff.model_selection_result.selected_candidate_id
      )
  ```

  Use the existing local variable name from the test. If the test currently names the return value `selection`, apply the assertions to `selection`.

- [ ] **Step 2: Keep product decision projection legacy-compatible**

  Do not change `selection_decision_from_hypothesis` unless tests expose a parity break. Product output remains driven by `PeakHypothesisSelectionDecision`; `model_selection_result` is the switch gate and audit fact.

- [ ] **Step 3: Run focused product-switch tests**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_target_extraction.py tests/test_peak_model_selection.py tests/test_peak_selection_decision.py tests/test_result_assembly.py
  ```

  Expected: PASS.

- [ ] **Step 4: Run spec-required focused shard**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
  ```

  Expected: PASS.

- [ ] **Step 5: Run static checks**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
  $env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
  git diff --check
  ```

  Expected: all PASS.

## Completion Audit

- [x] `PeakModelSelectionResult` exists and records `parity`, `expected_diff`, `blocked_diff`, or `inconclusive`.
- [x] `ExpectedDiffApprovalRecord` exists and gates `expected_diff`.
- [x] `blocked_diff` and `inconclusive` always prevent product switching.
- [x] Matrix-affecting expected diffs cannot product-switch with synthetic-only evidence.
- [x] MS2/NL expected diffs cannot product-switch under `limited_evidence_shadow`.
- [x] Normal product outputs remain legacy-compatible unless approved expected diff is recorded.
- [x] Expected-diff approval records can pass through `extractor.run`, serial backend, process jobs, target extraction, and handoff runtime without changing default outputs.
- [x] Runtime approval matching requires stable row id, sample, target, legacy candidate id, and successor candidate id to match the current model-selection result.
- [x] Expected-diff approvals cannot under-declare actual public-output or matrix impact derived from selected-vs-legacy hypotheses.
- [x] Candidate table and boundary audit selected markers follow the product-selected hypothesis when an approved expected diff switches selection, including CWT audit merges that add `centwave_cwt` and change the audit candidate id.
- [x] `target_extraction.py` module-boundary test uses semantic delegation checks instead of a fixed line-count ceiling.
- [x] Legacy selector is not deleted.
- [x] Final status is reported as `production_candidate`; do not claim `production_ready` without targeted benchmark, 8RAW, or manual EIC/MS2 evidence for real matrix-affecting expected diffs.
