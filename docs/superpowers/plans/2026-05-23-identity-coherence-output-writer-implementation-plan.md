# Identity Coherence Output Writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the frozen identity-coherence output surface: `requests.tsv`, `decisions.tsv`, `cell_evidence.tsv`, optional pass-through `controls.tsv`, and a minimal `summary.md` rendered from already-evaluated domain rows.

**Architecture:** This is an output projection slice only. It consumes `SeedGateResult` plus `IdentityCoherenceRowResult` objects produced by the existing pure-domain pipeline, validates frozen-row invariants, writes schema-constant TSVs, and renders a markdown review summary. It must not schedule RAW/XIC retrieval, import Backfill/alignment orchestration, parse controls manifests, generate decoys, mutate final matrices, or perform downstream feature filtering.

**Tech Stack:** Python 3.11+, dataclasses, `csv.DictWriter`, `pathlib.Path`, existing `identity_coherence` schema constants, `pytest`, `ruff`.

---

## Required Working Directory

Run every command from this worktree:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
```

Do not run this plan from `C:\Users\user\Desktop\XIC_Extractor` or another sibling worktree.

Before starting Task 1, record the base commit:

```powershell
git rev-parse HEAD
```

Use that exact hash as `<base_commit_before_task1>` in the final scope guard.
Do not use `HEAD~N`; this plan allows workers to split or combine commits.

## Current State

Already implemented:

- request builder and canonical semicolon tag formatting;
- request-vs-candidate identity matching;
- seed gate;
- RT center estimation;
- tier 1 / tier 2 / tier 3 cell evidence;
- prototype width and prototype/seed-fallback shape;
- row-level domain evaluator;
- decision summary aggregation;
- frozen schema column constants and contract marker parity tests.

This plan starts after those domain pieces. It must not repeat them.

## Scope Boundary

In scope:

- `IdentityCoherenceOutputRecord`, `IdentityCoherenceOutputContext`, and `IdentityCoherenceOutputPaths` writer-side dataclasses.
- Projection helpers for request, decision, cell evidence, and pass-through controls rows.
- TSV writers that always use the frozen schema constants.
- A minimal markdown summary renderer with required section headers and count tables.
- Facade exports for the output writer surface.
- Boundary tests proving domain modules do not import the writer surface.

Out of scope:

- RAW/XIC retrieval, XIC request planning, `ms1_index_source`, vendor APIs, and process worker payload changes.
- Alignment pipeline orchestration or `owner_backfill`.
- CLI wiring.
- Controls manifest parsing, positive-control mapping, decoy generation, or control pass/fail interpretation.
- Workbook/HTML report rendering.
- Final-matrix filtering, contaminant/background filtering, blank/QC filtering, area correction, normalization, or statistics.

## File Structure

- Create `xic_extractor/alignment/identity_coherence/output.py`
  - Own writer-side output dataclasses.
  - Own flat-row projection helpers.
  - Own TSV writers and markdown summary renderer.
  - This file may import `csv`, `Counter`, and `Path`; domain modules must not import this file.
- Modify `xic_extractor/alignment/identity_coherence/__init__.py`
  - Re-export stable output dataclasses and writer functions.
- Create `tests/alignment/identity_coherence/test_output_projection.py`
  - Test request/decision/cell/control row projection without filesystem IO.
- Create `tests/alignment/identity_coherence/output_fixtures.py`
  - Shared writer-test fixture builders. This is intentionally not named
    `test_*.py`, so writer tests do not import private helpers from another test
    module.
- Create `tests/alignment/identity_coherence/test_output_writer.py`
  - Test TSV writing, headers, summary rendering, path bundle, and facade exports.
- Modify `tests/alignment/identity_coherence/test_schema_contract.py`
  - Add boundary/facade assertions for the output writer surface.

## Design Rules

- Output code is a writer/report surface. It may depend inward on domain models, but no existing domain module may import it.
- `controls.tsv` is pass-through only in this slice. A caller may provide already-built control rows; this slice does not parse or generate controls.
- `summary.md` in this slice is a writer-contract review surface. It includes a
  staged subset of the full diagnostic summary and emits
  `not_assessed`/pass-through counts when controls, decoys, retrieval timing, or
  full diagnostic evidence are not available. It must not present the
  method-level Go/No-Go decision; that belongs after controls/decoy and
  retrieval slices exist.
- Every emitted TSV row must have exactly the columns from its schema constant.
- `requests.tsv` must reject a complete request whose `request_candidate_identity_status` is still `not_assessed`.
- `request_candidate_identity_status = not_assessed` is allowed only when the request is incomplete.
- `cell_evidence.tsv` contains non-seed sample rows only. The writer does not duplicate seed sample rows.
- Stable formatting:
  - `None` -> empty string.
  - `StrEnum` -> `.value`.
  - string enum values are accepted as strings.
  - booleans -> lowercase `true` / `false`.
  - finite floats -> `"{value:.12g}"`.
  - non-finite floats -> empty string.
  - tuple/list/set values -> semicolon-joined stable string, preserving tuple/list order and sorting sets.
  - `fragment_tags` and `fragment_tags_supported` use `format_fragment_tags()`
    so request/cell audit strings have the same canonical ordering.
  - textual values beginning with `=`, `+`, `-`, or `@` are prefixed with
    `'` to avoid spreadsheet formula injection.
  - finite numeric values remain numeric strings, including negative RT deltas,
    so downstream parsers can treat numeric columns as numeric.
- TSV files use `csv.DictWriter(..., dialect="excel-tab")`; cells containing
  tabs, newlines, or quotes are quoted by the csv module.
- Retrieval cost counters default to `None` and render as `not_assessed` until
  the later retrieval slice supplies measured values.
- Keep the code-side API nested and small. Do not add a new config key for every summary counter; summary counts are computed from records.

---

## Task 1: Projection Helpers And Invariants

**Files:**

- Create: `tests/alignment/identity_coherence/test_output_projection.py`
- Create: `xic_extractor/alignment/identity_coherence/output.py`

- [ ] **Step 1: Write failing projection tests**

Create `tests/alignment/identity_coherence/test_output_projection.py` with focused fixtures and tests:

```python
from dataclasses import replace

import pytest

from xic_extractor.alignment.identity_coherence.candidate_matcher import (
    match_request_to_candidate,
)
from xic_extractor.alignment.identity_coherence.models import (
    CandidateIdentityMatch,
    CellEvidenceResult,
    IdentityCoherenceRequest,
    IdentityDecisionSummary,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.output import (
    project_cell_evidence_row,
    project_control_row,
    project_decision_row,
    project_request_row,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    DecisionReason,
    EvidenceStage,
    FragmentMatchStatus,
    IdentityDecision,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    RtCenterDecision,
    RtGateStatus,
    SeedGateClass,
    SeedRejectReason,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WeakBasisReason,
    WidthStatus,
)


class CandidateLike:
    candidate_id = "CAND-1"
    sample_name = "RAW-1"
    sample_id = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"


def _request() -> IdentityCoherenceRequest:
    return build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )


def _candidate() -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="CAND-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=5.0,
        ms1_scan_support_score=0.9,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )


def _seed_gate() -> SeedGateResult:
    request = _request()
    match = match_request_to_candidate(request, _candidate())
    resolved = replace(
        request,
        request_candidate_identity_status=match.request_candidate_identity_status,
    )
    return SeedGateResult(
        resolved_request=resolved,
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=match,
        review_flags=(),
    )


def _center() -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=5.0,
        center_rt_sec=300.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=3,
        center_drift_sec=0.0,
    )


def _decision() -> IdentityDecisionSummary:
    return IdentityDecisionSummary(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        seed_candidate_id="CAND-1",
        seed_sample="RAW-1",
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        request_identity_completeness_status=(
            RequestIdentityCompletenessStatus.COMPLETE
        ),
        request_candidate_identity_status=RequestCandidateIdentityStatus.MATCH,
        decision=IdentityDecision.WOULD_PRIMARY,
        decision_reason=DecisionReason.TIER1_SUPPORT.value,
        total_coherent_sample_count=3,
        non_seed_coherent_sample_count=2,
        tier12_non_seed_identity_sample_count=2,
        tier1_fragment_confirmed_sample_count=2,
        tier2_shape_supported_sample_count=0,
        tier2_seed_shape_fallback_sample_count=0,
        tier3_width_only_sample_count=0,
        min_total_coherent_samples=3,
        min_non_seed_coherent_samples=2,
        min_non_seed_tier12_identity_samples=2,
        weak_basis_reason=WeakBasisReason.NONE,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        prototype_width_sec=None,
        center_rt_source=RtCenterDecision.RECENTERED_STABLE.value,
        center=_center(),
        coherent_fraction=0.375,
        infrastructure_blocked_sample_count=0,
        data_quality_reject_sample_count=0,
        forbidden_evidence_seen=False,
        forbidden_evidence_used=False,
    )


def _cell() -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id="RAW-2",
        candidate_id="CAND-2",
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode="cid_neutral_loss",
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=3.25,
        rt_gate_status=RtGateStatus.PASS,
        shape_status=ShapeStatus.NOT_ASSESSED,
        shape_similarity_cosine=None,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        shape_fallback_used=False,
        shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        width_status=WidthStatus.NOT_ASSESSED,
        width_ratio_to_prototype=None,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=NonRtIdentityResult.PASS,
        coherent_count_contribution=True,
        tier12_count_contribution=True,
        blocked_reason="",
        data_quality_reason="",
        forbidden_evidence_seen=False,
    )


def test_project_request_row_uses_frozen_columns_and_canonical_values():
    row = project_request_row(_seed_gate())

    assert tuple(row) == IDENTITY_COHERENCE_REQUEST_COLUMNS
    assert row["request_id"] == "REQ-1"
    assert row["decision_id"] == "DEC-1"
    assert row["fragment_tags"] == "MeR;dR"
    assert row["request_candidate_identity_status"] == "match"
    assert row["precursor_error_ppm"] == "0"
    assert row["product_error_ppm"] == "0"
    assert row["cid_observed_loss_error_ppm"] == "0"
    assert row["request_builder_flags"] == ""


def test_project_request_row_rejects_complete_not_assessed_frozen_row():
    request = replace(
        _request(),
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
    )
    seed_gate = replace(_seed_gate(), resolved_request=request)

    with pytest.raises(ValueError, match="complete request .* not_assessed"):
        project_request_row(seed_gate)


def test_project_request_row_allows_incomplete_not_assessed_frozen_row():
    request = replace(
        _request(),
        request_identity_completeness_status=(
            RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ
        ),
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
    )
    seed_gate = replace(
        _seed_gate(),
        resolved_request=request,
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=SeedRejectReason.MISSING_REQUEST_IDENTITY_CONSTRAINT,
        candidate_match=CandidateIdentityMatch(
            request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
            precursor_error_ppm=None,
            product_error_ppm=None,
            cid_observed_loss_error_ppm=None,
            cid_observed_loss_error_da=None,
        ),
    )

    row = project_request_row(seed_gate)

    assert row["request_identity_completeness_status"] == "missing_product_mz"
    assert row["request_candidate_identity_status"] == "not_assessed"


def test_project_decision_row_uses_frozen_columns_and_thresholds():
    row = project_decision_row(_decision())

    assert tuple(row) == IDENTITY_COHERENCE_DECISION_COLUMNS
    assert row["decision"] == "would_primary_provisional_identity_family_support"
    assert row["decision_reason"] == "tier1_support"
    assert row["min_total_coherent_samples"] == "3"
    assert row["min_non_seed_coherent_samples"] == "2"
    assert row["min_non_seed_tier12_identity_samples"] == "2"
    assert row["center_rt_sec"] == "300"
    assert row["forbidden_evidence_used"] == "false"


def test_project_decision_row_rejects_forbidden_evidence_used():
    summary = replace(_decision(), forbidden_evidence_used=True)

    with pytest.raises(ValueError, match="forbidden_evidence_used"):
        project_decision_row(summary)


def test_project_cell_evidence_row_uses_non_seed_audit_columns():
    row = project_cell_evidence_row(_cell())

    assert tuple(row) == IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS
    assert row["sample_id"] == "RAW-2"
    assert row["fragment_tags_supported"] == "MeR;dR"
    assert row["coherent_count_contribution"] == "true"
    assert row["tier12_count_contribution"] == "true"


def test_project_control_row_is_pass_through_schema_projection_only():
    row = project_control_row(
        {
            "control_id": "CTRL-1",
            "control_type": "positive_identity_control",
            "control_name": "ISTD-A",
            "decision_id": "DEC-1",
            "identity_family_id": "IDF-1",
            "seed_candidate_id": "CAND-1",
            "control_status": "assessed",
            "control_expected_behavior": "would_primary",
            "control_observed_behavior": "would_primary",
            "control_pass": True,
            "control_failure_reason": "",
            "fragment_observation_mode": "cid_neutral_loss",
            "decoy_generation_method": "",
            "decoy_source_request_id": "",
            "decoy_shift_value": None,
            "decoy_identity_constraint_changed": "",
            "positive_control_mapping_status": "mapped",
            "positive_control_target_name": "ISTD-A",
            "positive_control_target_mz": 500.0,
            "positive_control_target_rt_sec": 300.0,
            "positive_control_mapping_error_ppm": 0.1,
            "positive_control_mapping_delta_rt_sec": 2.0,
            "control_notes": "=not a formula",
        }
    )

    assert tuple(row) == IDENTITY_COHERENCE_CONTROL_COLUMNS
    assert row["control_pass"] == "true"
    assert row["positive_control_target_mz"] == "500"
    assert row["control_notes"] == "'=not a formula"
```

- [ ] **Step 2: Run projection tests and confirm they fail**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_projection.py -q
```

Expected: fail because `identity_coherence.output` does not exist.

- [ ] **Step 3: Create the projection module**

Create `xic_extractor/alignment/identity_coherence/output.py` with:

```python
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
    SeedGateResult,
)
from .row_evaluator import IdentityCoherenceRowResult
from .schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)
from .tags import format_fragment_tags


@dataclass(frozen=True)
class IdentityCoherenceOutputRecord:
    seed_gate: SeedGateResult
    row_result: IdentityCoherenceRowResult


@dataclass(frozen=True)
class IdentityCoherenceOutputContext:
    command: str
    mode: str
    input_source: str
    input_hashes: tuple[tuple[str, str], ...] = ()
    control_manifest_path: str = "not_provided"
    raw_xic_request_count: int | None = None
    xic_point_count: int | None = None
    projected_85raw_identity_request_count: int | None = None


@dataclass(frozen=True)
class IdentityCoherenceOutputPaths:
    requests_tsv: Path
    decisions_tsv: Path
    cell_evidence_tsv: Path
    controls_tsv: Path
    summary_md: Path


def project_request_row(seed_gate: SeedGateResult) -> dict[str, str]:
    request = seed_gate.resolved_request
    _validate_frozen_request_status(request)
    identity = request.identity
    match = seed_gate.candidate_match
    values = {
        "request_id": request.request_id,
        "decision_id": request.decision_id,
        "seed_candidate_id": request.seed_candidate_id,
        "seed_sample": request.seed_sample,
        "fragment_observation_mode": identity.fragment_observation_mode,
        "precursor_mz": identity.precursor_mz,
        "product_mz": identity.product_mz,
        "fragment_tags": format_fragment_tags(identity.fragment_tags),
        "fragment_tag_match_policy": identity.fragment_tag_match_policy,
        "fragment_profile_id": identity.fragment_profile_id,
        "fragment_profile_hash": identity.fragment_profile_hash,
        "precursor_tolerance_ppm": identity.precursor_tolerance_ppm,
        "product_tolerance_ppm": identity.product_tolerance_ppm,
        "cid_observed_loss_da": identity.mode_constraint.cid_observed_loss_da,
        "cid_observed_loss_tolerance_ppm": (
            identity.mode_constraint.cid_observed_loss_tolerance_ppm
        ),
        "request_identity_completeness_status": (
            request.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            request.request_candidate_identity_status
        ),
        "precursor_error_ppm": match.precursor_error_ppm,
        "product_error_ppm": match.product_error_ppm,
        "cid_observed_loss_error_ppm": match.cid_observed_loss_error_ppm,
        "cid_observed_loss_error_da": match.cid_observed_loss_error_da,
        "request_builder_flags": request.request_builder_flags,
    }
    return _project_columns(IDENTITY_COHERENCE_REQUEST_COLUMNS, values)


def project_decision_row(summary: IdentityDecisionSummary) -> dict[str, str]:
    _validate_decision_summary(summary)
    values = {
        "decision_id": summary.decision_id,
        "identity_family_id": summary.identity_family_id,
        "seed_candidate_id": summary.seed_candidate_id,
        "seed_sample": summary.seed_sample,
        "seed_gate_class": summary.seed_gate_class,
        "decision": summary.decision,
        "decision_reason": summary.decision_reason,
        "request_identity_completeness_status": (
            summary.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            summary.request_candidate_identity_status
        ),
        "total_coherent_sample_count": summary.total_coherent_sample_count,
        "non_seed_coherent_sample_count": summary.non_seed_coherent_sample_count,
        "tier12_non_seed_identity_sample_count": (
            summary.tier12_non_seed_identity_sample_count
        ),
        "tier1_fragment_confirmed_sample_count": (
            summary.tier1_fragment_confirmed_sample_count
        ),
        "tier2_shape_supported_sample_count": (
            summary.tier2_shape_supported_sample_count
        ),
        "tier2_seed_shape_fallback_sample_count": (
            summary.tier2_seed_shape_fallback_sample_count
        ),
        "tier3_width_only_sample_count": summary.tier3_width_only_sample_count,
        "min_total_coherent_samples": summary.min_total_coherent_samples,
        "min_non_seed_coherent_samples": summary.min_non_seed_coherent_samples,
        "min_non_seed_tier12_identity_samples": (
            summary.min_non_seed_tier12_identity_samples
        ),
        "weak_basis_reason": summary.weak_basis_reason,
        "shape_reference_basis": summary.shape_reference_basis,
        "shape_reference_candidate_id": summary.shape_reference_candidate_id,
        "prototype_width_sec": summary.prototype_width_sec,
        "center_rt_sec": summary.center.center_rt_sec,
        "center_rt_source": summary.center_rt_source,
        "coherent_fraction": summary.coherent_fraction,
        "infrastructure_blocked_sample_count": (
            summary.infrastructure_blocked_sample_count
        ),
        "data_quality_reject_sample_count": (
            summary.data_quality_reject_sample_count
        ),
        "forbidden_evidence_used": summary.forbidden_evidence_used,
    }
    return _project_columns(IDENTITY_COHERENCE_DECISION_COLUMNS, values)


def project_cell_evidence_row(cell: CellEvidenceResult) -> dict[str, str]:
    values = {
        "decision_id": cell.decision_id,
        "identity_family_id": cell.identity_family_id,
        "sample_id": cell.sample_id,
        "candidate_id": cell.candidate_id,
        "cell_assessment_status": cell.cell_assessment_status,
        "cell_identity_tier": cell.cell_identity_tier,
        "cell_identity_basis": cell.cell_identity_basis,
        "fragment_observation_mode": cell.fragment_observation_mode,
        "fragment_match_status": cell.fragment_match_status,
        "fragment_tags_supported": format_fragment_tags(
            cell.fragment_tags_supported,
        ),
        "rt_delta_center_sec": cell.rt_delta_center_sec,
        "rt_gate_status": cell.rt_gate_status,
        "shape_status": cell.shape_status,
        "shape_similarity_cosine": cell.shape_similarity_cosine,
        "shape_reference_basis": cell.shape_reference_basis,
        "shape_reference_candidate_id": cell.shape_reference_candidate_id,
        "shape_fallback_used": cell.shape_fallback_used,
        "shape_audit_status": cell.shape_audit_status,
        "width_status": cell.width_status,
        "width_ratio_to_prototype": cell.width_ratio_to_prototype,
        "baseline_audit_status": cell.baseline_audit_status,
        "area_height_status": cell.area_height_status,
        "non_rt_identity_result": cell.non_rt_identity_result,
        "coherent_count_contribution": cell.coherent_count_contribution,
        "tier12_count_contribution": cell.tier12_count_contribution,
        "blocked_reason": cell.blocked_reason,
        "data_quality_reason": cell.data_quality_reason,
        "forbidden_evidence_seen": cell.forbidden_evidence_seen,
    }
    return _project_columns(IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, values)


def project_control_row(row: Mapping[str, object]) -> dict[str, str]:
    return _project_columns(IDENTITY_COHERENCE_CONTROL_COLUMNS, row)


def _validate_frozen_request_status(request: object) -> None:
    completeness = _enum_value(request.request_identity_completeness_status)
    candidate_status = _enum_value(request.request_candidate_identity_status)
    if (
        completeness == RequestIdentityCompletenessStatus.COMPLETE.value
        and candidate_status == RequestCandidateIdentityStatus.NOT_ASSESSED.value
    ):
        raise ValueError("complete request cannot be emitted as not_assessed")


def _validate_decision_summary(summary: IdentityDecisionSummary) -> None:
    if summary.forbidden_evidence_used:
        raise ValueError("forbidden_evidence_used cannot be emitted")


def _project_columns(
    columns: tuple[str, ...],
    values: Mapping[str, object],
) -> dict[str, str]:
    return {column: _format_tsv_value(values.get(column)) for column in columns}


def _format_tsv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.12g}"
    if isinstance(value, tuple):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, list):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, set):
        return ";".join(_format_tsv_value(item) for item in sorted(value))
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
```

- [ ] **Step 4: Run projection tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_projection.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\test_output_projection.py
git commit -m "feat: add identity coherence output projection"
```

---

## Task 2: TSV Writers

**Files:**

- Modify: `tests/alignment/identity_coherence/test_output_writer.py`
- Create: `tests/alignment/identity_coherence/output_fixtures.py`
- Modify: `xic_extractor/alignment/identity_coherence/output.py`

- [ ] **Step 1: Write failing writer tests**

This repo already has `tests/__init__.py`; import the shared writer fixture as
`tests.alignment.identity_coherence.output_fixtures` and do not add production
test helpers under `xic_extractor/`.

Create `tests/alignment/identity_coherence/output_fixtures.py` first:

```python
from dataclasses import replace

from xic_extractor.alignment.identity_coherence.candidate_matcher import (
    match_request_to_candidate,
)
from xic_extractor.alignment.identity_coherence.models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
    PrototypeWidthResult,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
    ShapeReferenceResult,
)
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputRecord,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.row_evaluator import (
    IdentityCoherenceRowResult,
)
from xic_extractor.alignment.identity_coherence.schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    DecisionReason,
    EvidenceStage,
    FragmentMatchStatus,
    IdentityDecision,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    RtCenterDecision,
    RtGateStatus,
    SeedGateClass,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WeakBasisReason,
    WidthStatus,
)


class CandidateLike:
    candidate_id = "CAND-1"
    sample_name = "RAW-1"
    sample_id = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"


def seed_candidate() -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="CAND-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=5.0,
        ms1_scan_support_score=0.9,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )


def seed_gate() -> SeedGateResult:
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )
    match = match_request_to_candidate(request, seed_candidate())
    resolved = replace(
        request,
        request_candidate_identity_status=match.request_candidate_identity_status,
    )
    return SeedGateResult(
        resolved_request=resolved,
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=match,
        review_flags=(),
    )


def center() -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=5.0,
        center_rt_sec=300.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=3,
        center_drift_sec=0.0,
    )


def decision_summary() -> IdentityDecisionSummary:
    return IdentityDecisionSummary(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        seed_candidate_id="CAND-1",
        seed_sample="RAW-1",
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        request_identity_completeness_status=(
            RequestIdentityCompletenessStatus.COMPLETE
        ),
        request_candidate_identity_status=RequestCandidateIdentityStatus.MATCH,
        decision=IdentityDecision.WOULD_PRIMARY,
        decision_reason=DecisionReason.TIER1_SUPPORT.value,
        total_coherent_sample_count=3,
        non_seed_coherent_sample_count=2,
        tier12_non_seed_identity_sample_count=2,
        tier1_fragment_confirmed_sample_count=2,
        tier2_shape_supported_sample_count=0,
        tier2_seed_shape_fallback_sample_count=0,
        tier3_width_only_sample_count=0,
        min_total_coherent_samples=3,
        min_non_seed_coherent_samples=2,
        min_non_seed_tier12_identity_samples=2,
        weak_basis_reason=WeakBasisReason.NONE,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        prototype_width_sec=None,
        center_rt_source=RtCenterDecision.RECENTERED_STABLE.value,
        center=center(),
        coherent_fraction=0.375,
        infrastructure_blocked_sample_count=0,
        data_quality_reject_sample_count=0,
        forbidden_evidence_seen=False,
        forbidden_evidence_used=False,
    )


def cell() -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id="RAW-2",
        candidate_id="CAND-2",
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode="cid_neutral_loss",
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=3.25,
        rt_gate_status=RtGateStatus.PASS,
        shape_status=ShapeStatus.NOT_ASSESSED,
        shape_similarity_cosine=None,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        shape_fallback_used=False,
        shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        width_status=WidthStatus.NOT_ASSESSED,
        width_ratio_to_prototype=None,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=NonRtIdentityResult.PASS,
        coherent_count_contribution=True,
        tier12_count_contribution=True,
        blocked_reason="",
        data_quality_reason="",
        forbidden_evidence_seen=False,
    )


def output_record() -> IdentityCoherenceOutputRecord:
    row_result = IdentityCoherenceRowResult(
        center=center(),
        prototype_width=PrototypeWidthResult(
            width_status=WidthStatus.NOT_ASSESSED,
            prototype_width_sec=None,
            candidate_count=0,
            non_seed_candidate_count=0,
            width_candidate_ids=(),
        ),
        shape_reference=ShapeReferenceResult(
            shape_reference_basis=ShapeReferenceBasis.NONE,
            shape_reference_candidate_id="",
            normalized_intensity=(),
            candidate_count=0,
            non_seed_candidate_count=0,
            seed_fallback_used=False,
        ),
        cells=(cell(),),
        decision=decision_summary(),
    )
    return IdentityCoherenceOutputRecord(
        seed_gate=seed_gate(),
        row_result=row_result,
    )
```

Then create `tests/alignment/identity_coherence/test_output_writer.py`:

```python
import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputRecord,
    write_identity_coherence_cell_evidence_tsv,
    write_identity_coherence_controls_tsv,
    write_identity_coherence_decisions_tsv,
    write_identity_coherence_requests_tsv,
)
from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
)


def _read_tsv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle, delimiter="\t"))


def _read_header(path: Path) -> tuple[str, ...]:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    return tuple(first_line.split("\t"))


def _record() -> IdentityCoherenceOutputRecord:
    return output_record()


def test_request_decision_and_cell_tsv_writers_use_contract_headers(tmp_path):
    record = _record()

    requests_path = write_identity_coherence_requests_tsv(
        tmp_path / "requests.tsv",
        (record,),
    )
    decisions_path = write_identity_coherence_decisions_tsv(
        tmp_path / "decisions.tsv",
        (record,),
    )
    cells_path = write_identity_coherence_cell_evidence_tsv(
        tmp_path / "cells.tsv",
        (record,),
    )

    assert _read_header(requests_path) == IDENTITY_COHERENCE_REQUEST_COLUMNS
    assert _read_header(decisions_path) == IDENTITY_COHERENCE_DECISION_COLUMNS
    assert _read_header(cells_path) == IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS
    assert _read_tsv(requests_path)[0]["request_id"] == "REQ-1"
    assert _read_tsv(decisions_path)[0]["decision_id"] == "DEC-1"
    assert _read_tsv(cells_path)[0]["sample_id"] == "RAW-2"


def test_controls_writer_writes_header_when_rows_are_empty(tmp_path):
    path = write_identity_coherence_controls_tsv(tmp_path / "controls.tsv", ())

    text = path.read_text(encoding="utf-8")

    assert text.startswith("control_id\tcontrol_type\tcontrol_name")
    assert _read_header(path) == IDENTITY_COHERENCE_CONTROL_COLUMNS
    assert len(text.splitlines()) == 1


def test_cell_writer_rejects_seed_sample_cell(tmp_path):
    record = _record()
    seed_cell = replace(record.row_result.cells[0], sample_id="RAW-1")
    bad_row = replace(record.row_result, cells=(seed_cell,))
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="seed sample"):
        write_identity_coherence_cell_evidence_tsv(
            tmp_path / "cells.tsv",
            (bad_record,),
        )


def test_writers_reject_mismatched_record_join_keys(tmp_path):
    record = _record()
    bad_decision = replace(record.row_result.decision, decision_id="OTHER")
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="decision_id"):
        write_identity_coherence_decisions_tsv(
            tmp_path / "decisions.tsv",
            (bad_record,),
        )


def test_writers_reject_forbidden_evidence_used(tmp_path):
    record = _record()
    bad_decision = replace(
        record.row_result.decision,
        forbidden_evidence_used=True,
    )
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="forbidden_evidence_used"):
        write_identity_coherence_decisions_tsv(
            tmp_path / "decisions.tsv",
            (bad_record,),
        )
```

- [ ] **Step 2: Run writer tests and confirm they fail**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: fail because writer functions are not implemented.

- [ ] **Step 3: Add TSV writer functions**

Update the imports in `output.py` first. Add `csv` and replace the existing
`from collections.abc import Mapping` line with:

```python
import csv
from collections.abc import Mapping, Sequence
```

Then append to `output.py`:

```python
def _validate_output_record(
    record: IdentityCoherenceOutputRecord,
) -> IdentityCoherenceOutputRecord:
    request = record.seed_gate.resolved_request
    decision = record.row_result.decision
    if request.decision_id != decision.decision_id:
        raise ValueError("decision_id mismatch between request and decision")
    if request.seed_candidate_id != decision.seed_candidate_id:
        raise ValueError("seed_candidate_id mismatch between request and decision")
    if request.seed_sample != decision.seed_sample:
        raise ValueError("seed_sample mismatch between request and decision")
    if (
        request.request_identity_completeness_status
        != decision.request_identity_completeness_status
    ):
        raise ValueError(
            "request_identity_completeness_status mismatch between "
            "request and decision"
        )
    if (
        request.request_candidate_identity_status
        != decision.request_candidate_identity_status
    ):
        raise ValueError(
            "request_candidate_identity_status mismatch between "
            "request and decision"
        )
    _validate_decision_summary(decision)
    for cell in record.row_result.cells:
        if cell.decision_id != decision.decision_id:
            raise ValueError("decision_id mismatch between decision and cell")
        if cell.identity_family_id != decision.identity_family_id:
            raise ValueError(
                "identity_family_id mismatch between decision and cell"
            )
        if request.seed_sample and cell.sample_id == request.seed_sample:
            raise ValueError("seed sample cannot be emitted in cell_evidence.tsv")
    return record


def write_identity_coherence_requests_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_REQUEST_COLUMNS,
        [project_request_row(record.seed_gate) for record in validated],
    )


def write_identity_coherence_decisions_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_DECISION_COLUMNS,
        [project_decision_row(record.row_result.decision) for record in validated],
    )


def write_identity_coherence_cell_evidence_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    rows: list[dict[str, str]] = []
    for record in validated:
        rows.extend(
            project_cell_evidence_row(cell)
            for cell in record.row_result.cells
        )
    return _write_tsv(path, IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, rows)


def write_identity_coherence_controls_tsv(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> Path:
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_CONTROL_COLUMNS,
        [project_control_row(row) for row in rows],
    )


def _write_tsv(
    path: Path,
    columns: tuple[str, ...],
    rows: Sequence[Mapping[str, str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path
```

The bundle writer is intentionally deferred to Task 3 so this task never leaves
a failing test in the repository.

- [ ] **Step 4: Run direct TSV writer tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\output_fixtures.py tests\alignment\identity_coherence\test_output_writer.py
git commit -m "feat: write identity coherence TSV outputs"
```

---

## Task 3: Markdown Summary Renderer

**Files:**

- Modify: `tests/alignment/identity_coherence/test_output_writer.py`
- Modify: `xic_extractor/alignment/identity_coherence/output.py`

- [ ] **Step 1: Add failing summary tests**

Modify the existing `from xic_extractor.alignment.identity_coherence.output`
import block in `test_output_writer.py` to add
`IdentityCoherenceOutputContext`, `render_identity_coherence_summary`, and
`write_identity_coherence_outputs`. Do not append a second import block at the
end of the file. Then append only the new test functions below the existing
tests:

The existing output import block should contain these added names:

```python
    IdentityCoherenceOutputContext,
    render_identity_coherence_summary,
    write_identity_coherence_outputs,
```

Append these test functions below the existing tests:

```python

def _assert_in_order(text: str, headings: tuple[str, ...]) -> None:
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_summary_renderer_reports_required_sections_and_counts():
    markdown = render_identity_coherence_summary(
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="identity-coherence --inline",
            mode="inline_pre_backfill",
            input_source="pre_backfill_ownership",
            input_hashes=(("ownership.pkl", "sha256:def"),),
            control_manifest_path="not_provided",
            projected_85raw_identity_request_count=255,
        ),
        control_rows=(),
    )

    headings = (
        "# Untargeted Identity Coherence Summary",
        "## Run Context",
        "## Input Hashes",
        "## Request Status Counts",
        "## Evidence Firewall",
        "## Seed Gate Counts",
        "## Decision Counts",
        "## Tier Support Counts",
        "## RT-Only Candidate Counts",
        "## Shape And Width Review",
        "## Per-Sample Evidence Coverage",
        "## Infrastructure And Data Quality",
        "## Threshold Count And Fraction Summaries",
        "## Weak Basis Counts",
        "## Controls Pass-Through",
        "## Cost Counters",
        "## Writer Contract Checks",
    )
    for heading in headings:
        assert heading in markdown
    _assert_in_order(markdown, headings)
    assert "| `promotion_used_forbidden_evidence` | `false` |" in markdown
    assert "| `would_primary_provisional_identity_family_support` | 1 |" in markdown
    assert "| raw_xic_request_count | not_assessed |" in markdown
    assert "| xic_point_count | not_assessed |" in markdown
    assert "| projected_85raw_identity_request_count | 255 |" in markdown


def test_summary_renderer_reports_control_rows_without_interpreting_them():
    markdown = render_identity_coherence_summary(
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="synthetic",
            control_manifest_path="controls.tsv",
        ),
        control_rows=(
            {
                "control_id": "CTRL-1",
                "control_type": "positive_identity_control",
                "control_status": "assessed",
                "control_pass": True,
            },
        ),
    )

    assert "| control_manifest_path | `controls.tsv` |" in markdown
    assert "| `positive_identity_control` | 1 |" in markdown
    assert "| `true` | 1 |" in markdown
    assert "reported only, not evaluated by this writer slice" in markdown


def test_write_identity_coherence_outputs_writes_all_frozen_paths(tmp_path):
    paths = write_identity_coherence_outputs(
        tmp_path,
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="synthetic",
            input_hashes=(("synthetic.tsv", "sha256:abc"),),
            projected_85raw_identity_request_count=255,
        ),
        control_rows=(),
    )

    assert paths.requests_tsv.name == "untargeted_identity_coherence_requests.tsv"
    assert paths.decisions_tsv.name == "untargeted_identity_coherence_decisions.tsv"
    assert paths.cell_evidence_tsv.name == (
        "untargeted_identity_coherence_cell_evidence.tsv"
    )
    assert paths.controls_tsv.name == "untargeted_identity_coherence_controls.tsv"
    assert paths.summary_md.name == "untargeted_identity_coherence_summary.md"
    assert paths.requests_tsv.is_file()
    assert paths.decisions_tsv.is_file()
    assert paths.cell_evidence_tsv.is_file()
    assert paths.controls_tsv.is_file()
    assert paths.summary_md.is_file()


def test_summary_renderer_rejects_mixed_threshold_rows():
    record = _record()
    bad_decision = replace(
        record.row_result.decision,
        min_total_coherent_samples=4,
    )
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="min_total_coherent_samples"):
        render_identity_coherence_summary(
            (record, bad_record),
            context=IdentityCoherenceOutputContext(
                command="pytest",
                mode="inline_pre_backfill",
                input_source="synthetic",
            ),
            control_rows=(),
        )
```

- [ ] **Step 2: Run summary tests and confirm they fail**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: fail because `render_identity_coherence_summary` and the bundle writer
are not implemented.

- [ ] **Step 3: Implement summary renderer**

Add the `Counter` import above the `collections.abc` import:

```python
from collections import Counter
```

Then append to `output.py`:

```python
def write_identity_coherence_outputs(
    output_dir: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
    *,
    context: IdentityCoherenceOutputContext,
    control_rows: Sequence[Mapping[str, object]] = (),
) -> IdentityCoherenceOutputPaths:
    validated = tuple(_validate_output_record(record) for record in records)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = IdentityCoherenceOutputPaths(
        requests_tsv=output_dir / "untargeted_identity_coherence_requests.tsv",
        decisions_tsv=output_dir / "untargeted_identity_coherence_decisions.tsv",
        cell_evidence_tsv=(
            output_dir / "untargeted_identity_coherence_cell_evidence.tsv"
        ),
        controls_tsv=output_dir / "untargeted_identity_coherence_controls.tsv",
        summary_md=output_dir / "untargeted_identity_coherence_summary.md",
    )
    write_identity_coherence_requests_tsv(paths.requests_tsv, validated)
    write_identity_coherence_decisions_tsv(paths.decisions_tsv, validated)
    write_identity_coherence_cell_evidence_tsv(paths.cell_evidence_tsv, validated)
    write_identity_coherence_controls_tsv(paths.controls_tsv, control_rows)
    paths.summary_md.write_text(
        render_identity_coherence_summary(
            validated,
            context=context,
            control_rows=control_rows,
        ),
        encoding="utf-8",
    )
    return paths


def render_identity_coherence_summary(
    records: Sequence[IdentityCoherenceOutputRecord],
    *,
    context: IdentityCoherenceOutputContext,
    control_rows: Sequence[Mapping[str, object]] = (),
) -> str:
    validated = tuple(_validate_output_record(record) for record in records)
    decision_rows = [record.row_result.decision for record in validated]
    cell_rows = [
        cell
        for record in validated
        for cell in record.row_result.cells
    ]
    request_rows = [record.seed_gate.resolved_request for record in validated]
    projected_85raw = (
        context.projected_85raw_identity_request_count
        if context.projected_85raw_identity_request_count is not None
        else "not_assessed"
    )
    raw_xic_requests = (
        context.raw_xic_request_count
        if context.raw_xic_request_count is not None
        else "not_assessed"
    )
    xic_points = (
        context.xic_point_count
        if context.xic_point_count is not None
        else "not_assessed"
    )

    lines = [
        "# Untargeted Identity Coherence Summary",
        "",
        "This diagnostic is non-mutating. It reports identity-family evidence only; "
        "it does not perform final-matrix filtering, background filtering, area "
        "correction, normalization, statistics, Backfill, or RAW/XIC retrieval.",
        "",
        "## Run Context",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| command | `{context.command}` |",
        f"| mode | `{context.mode}` |",
        f"| input_source | `{context.input_source}` |",
        f"| input_row_count | {len(validated)} |",
        f"| control_manifest_path | `{context.control_manifest_path}` |",
        "",
        "## Input Hashes",
        "",
    ]
    lines.extend(_hash_lines(context.input_hashes))
    lines.extend(
        [
            "",
            "## Request Status Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                _enum_value(row.request_identity_completeness_status)
                for row in request_rows
            ),
            "request_identity_completeness_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _enum_value(row.request_candidate_identity_status)
                for row in request_rows
            ),
            "request_candidate_identity_status",
        )
    )
    lines.extend(
        [
            "",
            "## Evidence Firewall",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            "| `promotion_used_forbidden_evidence` | `false` |",
            (
                "| `forbidden_evidence_seen_count` | "
                f"{sum(1 for row in decision_rows if row.forbidden_evidence_seen)} |"
            ),
            "",
            "## Seed Gate Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(_enum_value(row.seed_gate_class) for row in decision_rows),
            "seed_gate_class",
        )
    )
    lines.extend(
        [
            "",
            "## Decision Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(_enum_value(row.decision) for row in decision_rows),
            "decision",
        )
    )
    lines.extend(
        [
            "",
            "## Tier Support Counts",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            (
                "| tier1_fragment_confirmed_sample_count | "
                f"{sum(row.tier1_fragment_confirmed_sample_count for row in decision_rows)} |"
            ),
            (
                "| tier2_shape_supported_sample_count | "
                f"{sum(row.tier2_shape_supported_sample_count for row in decision_rows)} |"
            ),
            (
                "| tier2_seed_shape_fallback_sample_count | "
                f"{sum(row.tier2_seed_shape_fallback_sample_count for row in decision_rows)} |"
            ),
            (
                "| tier3_width_only_sample_count | "
                f"{sum(row.tier3_width_only_sample_count for row in decision_rows)} |"
            ),
            "",
            "## RT-Only Candidate Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                _enum_value(cell.cell_identity_tier)
                for cell in cell_rows
                if _enum_value(cell.cell_identity_tier) == "rt_only"
            ),
            "rt_only_cell_identity_tier",
        )
    )
    lines.extend(
        [
            "",
            "## Shape And Width Review",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(_enum_value(cell.shape_reference_basis) for cell in cell_rows),
            "shape_reference_basis",
        )
    )
    lines.extend(
        _counter_table(
            Counter(_enum_value(cell.width_status) for cell in cell_rows),
            "width_status",
        )
    )
    lines.extend(
        [
            "",
            "## Per-Sample Evidence Coverage",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| assessed_non_seed_cell_count | {len(cell_rows)} |",
            (
                "| missing_shape_basis_count | "
                f"{_cell_status_count(cell_rows, 'shape_status', 'not_assessed')} |"
            ),
            (
                "| missing_width_basis_count | "
                f"{_cell_status_count(cell_rows, 'width_status', 'not_assessed')} |"
            ),
            "",
            "## Infrastructure And Data Quality",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            (
                "| infrastructure_blocked_sample_count | "
                f"{sum(row.infrastructure_blocked_sample_count for row in decision_rows)} |"
            ),
            (
                "| data_quality_reject_sample_count | "
                f"{sum(row.data_quality_reject_sample_count for row in decision_rows)} |"
            ),
            "",
            "## Threshold Count And Fraction Summaries",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            (
                "| min_total_coherent_samples | "
                f"{_first_threshold(decision_rows, 'min_total_coherent_samples')} |"
            ),
            (
                "| min_non_seed_coherent_samples | "
                f"{_first_threshold(decision_rows, 'min_non_seed_coherent_samples')} |"
            ),
            (
                "| min_non_seed_tier12_identity_samples | "
                f"{_first_threshold(decision_rows, 'min_non_seed_tier12_identity_samples')} |"
            ),
            "",
            "## Weak Basis Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(_enum_value(row.weak_basis_reason) for row in decision_rows),
            "weak_basis_reason",
        )
    )
    lines.extend(
        [
            "",
            "## Controls Pass-Through",
            "",
            "Control fields are reported only, not evaluated by this writer slice.",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(str(row.get("control_type", "")) for row in control_rows),
            "control_type",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_pass"))
                for row in control_rows
            ),
            "supplied_control_pass_value",
        )
    )
    lines.extend(
        [
            "",
            "## Cost Counters",
            "",
            "| Counter | Value |",
            "| --- | ---: |",
            f"| raw_xic_request_count | {raw_xic_requests} |",
            f"| xic_point_count | {xic_points} |",
            f"| projected_85raw_identity_request_count | {projected_85raw} |",
            "",
            "## Writer Contract Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
            "| forbidden_evidence_used | enforced: writer raises before emission |",
            "| schema_projection | Proceed when TSV headers match schema constants |",
            "| controls | pass-through only; evaluation belongs to a later controls slice |",
            "",
        ]
    )
    return "\n".join(lines)


def _first_threshold(
    rows: list[IdentityDecisionSummary],
    field_name: str,
) -> object:
    if not rows:
        return "not_assessed"
    values = {getattr(row, field_name) for row in rows}
    if len(values) != 1:
        raise ValueError(f"mixed {field_name} values in summary rows")
    return getattr(rows[0], field_name)


def _cell_status_count(
    rows: list[CellEvidenceResult],
    field_name: str,
    value: str,
) -> int:
    return sum(
        1 for row in rows
        if _enum_value(getattr(row, field_name)) == value
    )


def _counter_table(counter: Counter[str], label: str) -> list[str]:
    if not counter:
        return [
            f"| {label} | Count |",
            "| --- | ---: |",
            "| `none` | 0 |",
            "",
        ]
    return [
        f"| {label} | Count |",
        "| --- | ---: |",
        *[f"| `{key}` | {count} |" for key, count in sorted(counter.items())],
        "",
    ]


def _hash_lines(input_hashes: tuple[tuple[str, str], ...]) -> list[str]:
    if not input_hashes:
        return [
            "| Input | Hash |",
            "| --- | --- |",
            "| `not_provided` | `not_provided` |",
        ]
    return [
        "| Input | Hash |",
        "| --- | --- |",
        *[f"| `{name}` | `{digest}` |" for name, digest in input_hashes],
    ]
```

- [ ] **Step 4: Run summary and full writer tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\output_fixtures.py tests\alignment\identity_coherence\test_output_writer.py
git commit -m "feat: render identity coherence output summary"
```

---

## Task 4: Facade Exports And Boundary Tests

**Files:**

- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`

- [ ] **Step 1: Add failing facade and boundary tests**

Append to `test_schema_contract.py`:

```python
def test_identity_coherence_facade_exports_output_writer_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.IdentityCoherenceOutputContext is not None
    assert identity_coherence.IdentityCoherenceOutputPaths is not None
    assert identity_coherence.IdentityCoherenceOutputRecord is not None
    assert identity_coherence.project_request_row is not None
    assert identity_coherence.project_decision_row is not None
    assert identity_coherence.project_cell_evidence_row is not None
    assert identity_coherence.project_control_row is not None
    assert identity_coherence.render_identity_coherence_summary is not None
    assert identity_coherence.write_identity_coherence_outputs is not None
    assert identity_coherence.write_identity_coherence_requests_tsv is not None
    assert identity_coherence.write_identity_coherence_decisions_tsv is not None
    assert identity_coherence.write_identity_coherence_cell_evidence_tsv is not None
    assert identity_coherence.write_identity_coherence_controls_tsv is not None


def test_identity_coherence_domain_modules_do_not_import_output_writer():
    package_root = (
        Path(__file__).resolve().parents[3]
        / "xic_extractor"
        / "alignment"
        / "identity_coherence"
    )
    domain_modules = (
        "candidate_matcher.py",
        "cell_evidence.py",
        "decision.py",
        "models.py",
        "request_builder.py",
        "row_evaluator.py",
        "rt_center.py",
        "schema.py",
        "seed_gate.py",
        "shape.py",
        "tags.py",
        "width.py",
    )
    forbidden_snippets = (
        "from .output import",
        "from . import output",
        "from xic_extractor.alignment.identity_coherence.output",
        "import xic_extractor.alignment.identity_coherence.output",
    )
    for module_name in domain_modules:
        source = (package_root / module_name).read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            assert snippet not in source, f"{module_name} imports output writer"
```

- [ ] **Step 2: Run facade tests and confirm they fail**

```powershell
uv run pytest tests\alignment\identity_coherence\test_schema_contract.py::test_identity_coherence_facade_exports_output_writer_surface -q
```

Expected: fail because `__init__.py` does not re-export the new writer surface.

- [ ] **Step 3: Re-export the writer surface**

Modify `xic_extractor/alignment/identity_coherence/__init__.py`. Place this
import after the existing `.row_evaluator` import so `IdentityCoherenceRowResult`
is available before the facade imports the output writer:

```python
from .output import (
    IdentityCoherenceOutputContext,
    IdentityCoherenceOutputPaths,
    IdentityCoherenceOutputRecord,
    project_cell_evidence_row,
    project_control_row,
    project_decision_row,
    project_request_row,
    render_identity_coherence_summary,
    write_identity_coherence_cell_evidence_tsv,
    write_identity_coherence_controls_tsv,
    write_identity_coherence_decisions_tsv,
    write_identity_coherence_outputs,
    write_identity_coherence_requests_tsv,
)
```

Add these exact string names to `__all__`:

```python
    "IdentityCoherenceOutputContext",
    "IdentityCoherenceOutputPaths",
    "IdentityCoherenceOutputRecord",
    "project_cell_evidence_row",
    "project_control_row",
    "project_decision_row",
    "project_request_row",
    "render_identity_coherence_summary",
    "write_identity_coherence_cell_evidence_tsv",
    "write_identity_coherence_controls_tsv",
    "write_identity_coherence_decisions_tsv",
    "write_identity_coherence_outputs",
    "write_identity_coherence_requests_tsv",
```

- [ ] **Step 4: Run schema contract tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\__init__.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: expose identity coherence output writer facade"
```

---

## Task 5: Verification And Scope Guard

**Files:**

- Modify: `docs/superpowers/plans/2026-05-23-identity-coherence-output-writer-implementation-plan.md` only if implementation notes are discovered.

- [ ] **Step 1: Run the identity coherence test group**

```powershell
uv run pytest tests\alignment\identity_coherence -q
```

Expected: pass.

- [ ] **Step 2: Run focused lint**

```powershell
uv run ruff check xic_extractor\alignment\identity_coherence tests\alignment\identity_coherence tests\test_run_extraction.py
```

Expected: pass.

- [ ] **Step 3: Check output slice did not touch retrieval or production writers**

```powershell
git diff --name-only <base_commit_before_task1>..HEAD
```

Expected changed paths are limited to:

```text
xic_extractor/alignment/identity_coherence/output.py
xic_extractor/alignment/identity_coherence/__init__.py
tests/alignment/identity_coherence/test_output_projection.py
tests/alignment/identity_coherence/output_fixtures.py
tests/alignment/identity_coherence/test_output_writer.py
tests/alignment/identity_coherence/test_schema_contract.py
```

If the diff contains `xic_extractor/alignment/pipeline_outputs.py`, `xic_extractor/alignment/tsv_writer.py`, `xic_extractor/extraction/`, RAW adapters, workbook/report renderers, CLI scripts, or Backfill modules, stop and justify the change before proceeding.

- [ ] **Step 4: Run full test suite if the focused checks pass**

```powershell
uv run pytest --tb=short -q
```

Expected: pass. On this Windows sandbox, if the process-spawn test fails with `PermissionError: [WinError 5]`, rerun the same command with approved escalation and report both results.

- [ ] **Step 5: Final self-review checklist**

Check before handing back:

- [ ] Four TSV files use schema constants as headers.
- [ ] `summary.md` is written but does not claim controls pass/fail semantics beyond supplied rows.
- [ ] Complete requests cannot be emitted with `request_candidate_identity_status = not_assessed`.
- [ ] `controls.tsv` is pass-through only; no decoy generation or positive-control mapping logic exists in this slice.
- [ ] No RAW/XIC retrieval code was imported or modified.
- [ ] No final matrix, workbook, HTML report, or downstream filtering code was modified.
- [ ] Domain modules do not import `identity_coherence.output`.
- [ ] All verification commands and any failures are recorded in the final response.

---

## Follow-On Slice After This Plan

Do not bundle this into the output writer slice.

The next logical plan should be **Controls Manifest And Decoy Evaluation**:

- parse an identity controls manifest;
- generate identity decoys;
- map controls to output records;
- evaluate control pass/fail;
- fill `controls.tsv` rows from real controls;
- expand summary control Go/No-Go interpretation.

That follow-on slice still must not implement RAW/XIC retrieval. Retrieval adapter planning remains a separate later slice.

After controls/decoys and retrieval counters exist, add a separate
**Diagnostic Summary Hardening** slice to complete the full implementation
contract summary sections and method-level Go/No-Go/Pivot table.
