# Identity Coherence Shape Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the next identity-coherence domain slice: prototype width, prototype-medoid shape similarity, seed-shape fallback, tier 3 width fallback, and weak-basis decision handling.

**Architecture:** This remains a pure domain slice inside `xic_extractor.alignment.identity_coherence`. It consumes pre-retrieved trace payloads supplied by tests or future adapters, but it does not request RAW files, extract XIC traces, call Backfill, write TSV files, parse controls manifests, or wire CLI/process execution. The slice extends existing `CellCandidateEvidence` and `CellEvidenceResult` so future retrieval and writer slices can plug in without changing identity rules.

**Tech Stack:** Python 3.11+, dataclasses, `numpy`, `pytest`, `ruff`, existing `identity_coherence` schema enums and models.

---

## Required Working Directory

All steps in this plan must run from this worktree root:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
```

Every relative path and every `git add`, `git commit`, `uv run`, and `rg`
command below assumes that exact directory. Do not execute this plan from
`C:\Users\user\Desktop\XIC_Extractor` or another sibling worktree.

## Current State

Already implemented in prior slices:

- fragment identity request builder and normalized case-sensitive `fragment_tags`;
- request-vs-candidate fragment matching with finite-positive mass guards;
- seed gate using pre-Backfill candidate evidence plus owner geometry;
- RT center estimation from synthetic `CellCandidateEvidence`;
- tier 1 non-seed cell evidence using diagnostic fragment support;
- tier1-only decision aggregation with promotion thresholds;
- frozen schema constants for requests, decisions, cells, and controls.

This plan starts after those pieces. It must not repeat the seed-gate or tier1 work.

## Scope Boundary

In scope:

- Active `ShapeConfig` and `WidthConfig` nested under `IdentityCoherenceConfig`.
- Trace payload models attached to `CellCandidateEvidence`.
- Pure shape normalization, boundary-local resampling, cosine scoring, and medoid selection.
- Prototype median width calculation and per-cell width-ratio assessment.
- Tier 2 `rt_shape_similarity` and tier 3 `rt_prototype_width` cell classification.
- Decision weak-basis rules for tier3-only, single-tier12-plus-tier3, and seed-shape-fallback-only support.
- Focused unit and schema/facade tests.

Out of scope:

- Layer 2 RAW/XIC request scheduling.
- Any real RAW reader, vendor API, `ms1_index_source`, `owner_backfill`, or alignment-output adapter changes.
- TSV writers, CLI wiring, `summary.md`, process-mode pickling integration, controls manifest parsing, workbook/report rendering.
- Final-matrix filtering, blank/QC filtering, area correction, normalization, or statistics.

## File Structure

- Modify `xic_extractor/alignment/identity_coherence/models.py`
  - Add `CandidateTrace`, `ShapeConfig`, `WidthConfig`, `ShapeReferenceResult`, `ShapeComparisonResult`, `PrototypeWidthResult`, and `WidthAssessmentResult`.
  - Extend `IdentityCoherenceConfig` with active `shape` and `width` configs.
  - Add optional `trace` to `CellCandidateEvidence`.
- Create `xic_extractor/alignment/identity_coherence/width.py`
  - Own prototype median width and per-cell width ratio logic.
  - No fragment matching, RT center estimation, RAW/XIC IO, or decisions.
- Create `xic_extractor/alignment/identity_coherence/shape.py`
  - Own boundary-local trace normalization, linear resampling, cosine similarity, prototype-medoid reference selection, and seed fallback reference handling.
  - No RAW/XIC retrieval and no decision aggregation.
- Modify `xic_extractor/alignment/identity_coherence/cell_evidence.py`
  - Consume optional row-level shape and width results.
  - Preserve tier 1 precedence, then try tier 2, then tier 3.
  - Keep tier 3 out of `tier12_count_contribution`.
- Modify `xic_extractor/alignment/identity_coherence/decision.py`
  - Add weak-basis decision branches and row-level shape/width summary fields.
- Create `xic_extractor/alignment/identity_coherence/row_evaluator.py`
  - Pure domain orchestration for one identity row: center, width, shape
    reference, cell evidence, and decision summary.
  - No RAW/XIC retrieval, adapters, writers, controls, CLI, Backfill, or final
    matrix filtering.
- Modify `xic_extractor/alignment/identity_coherence/__init__.py`
  - Re-export new stable domain models and functions.
- Modify `tests/alignment/identity_coherence/test_schema_contract.py`
  - Lock facade exports and shape/width config defaults.
- Create `tests/alignment/identity_coherence/test_width.py`
  - Prototype width and width-ratio behavior.
- Create `tests/alignment/identity_coherence/test_shape.py`
  - Trace normalization, medoid selection, seed fallback, and audit behavior.
- Modify `tests/alignment/identity_coherence/test_cell_evidence.py`
  - Tier 2 / tier 3 classification integration.
- Modify `tests/alignment/identity_coherence/test_identity_decision.py`
  - Weak-basis decision integration.
- Create `tests/alignment/identity_coherence/test_row_evaluator.py`
  - End-to-end pure domain row orchestration with pre-supplied candidates.

## Domain Rules To Preserve

- RT fields stored on candidates are minutes. Reported deltas and config RT tolerances are seconds.
- Shape uses each candidate's own original peak boundaries, not a common window.
- Shape resampling is boundary-normalized linear resampling over positions 0..1.
- Shape pass requires width sanity pass.
- Tier 1 diagnostic fragment support remains valid even if width sanity fails; the width failure is audit context on that tier 1 cell.
- Tier 3 can contribute to `total_coherent_sample_count` but cannot contribute to `tier12_non_seed_identity_sample_count`.
- Seed-shape fallback tier 2 can contribute to counts, but seed-shape-fallback-only support must be Review-only.
- `morphology_rt_medoid` can support provisional would-primary, but decision summaries must expose it separately through `shape_reference_basis`.
- Forbidden evidence remains a firewall: Backfill/post-Backfill trace or candidate evidence cannot support shape, width, tier 2, tier 3, or promotion.
- Prototype shape medoids exclude the seed sample. Seed trace can be used only
  through explicit `seed_fallback` and must set `shape_fallback_used = true`.
- Prototype width also excludes the seed sample. `width.prototype_min_candidates`
  is the minimum count after seed exclusion, so the width reference is based on
  non-seed morphology rather than seed self-reference.
- Shape-reference medoid tie-break uses a lightweight candidate-level tier 1
  support map, not a preliminary full cell-evaluation pass. This keeps Task 6
  pure-domain orchestration deterministic without doubling selector work.
- Width prototype eligibility is intentionally tighter than shape prototype
  eligibility: width candidates must be inside `seed_center_candidate_sec` of
  seed RT as well as inside final-center `preferred_rt_sec`. This limits width
  fallback to the local seed neighborhood.
- `PrototypeWidthResult.non_seed_candidate_count` is review/audit context. It
  should be reported so reviewers can see whether a width reference was built
  from independent non-seed evidence, but decision code must not re-derive
  promotion from that field.
- `non_rt_identity_result` remains the fragment-constraint result in V0.4.
  Tier 2 and tier 3 support are represented by `cell_identity_tier`,
  `cell_identity_basis`, and shape/width fields; do not overwrite
  `non_rt_identity_result` to `pass` for shape-only or width-only cells.

---

## Task 1: Add Trace, Shape, And Width Models

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence/models.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Test: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Add model contract tests**

Append these tests to `tests/alignment/identity_coherence/test_schema_contract.py`.
If the file does not already import `pytest`, add:

```python
import pytest
```

```python
def test_identity_coherence_config_exposes_active_shape_and_width_configs():
    config = IdentityCoherenceConfig()

    assert config.shape.min_points == 7
    assert config.shape.resample_points == 25
    assert config.shape.min_cosine == 0.85
    assert config.shape.prototype_min_candidates == 3
    assert config.shape.prototype_min_non_seed_candidates == 2
    assert config.shape.allow_seed_shape_fallback is True
    assert config.shape.allow_morphology_rt_medoid is True
    assert config.width.prototype_min_candidates == 3
    assert config.width.min_ratio == 0.50
    assert config.width.max_ratio == 2.00


def test_candidate_trace_is_nested_domain_model_not_flat_schema_columns():
    trace = CandidateTrace(
        rt_min=(7.75, 7.80, 7.85),
        intensity=(1.0, 5.0, 1.0),
        shape_audit_status=ShapeAuditStatus.PASS,
    )

    candidate = CellCandidateEvidence(
        sample_id="S2",
        candidate_evidence=_seed_candidate("C2"),
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        area=10.0,
        height=5.0,
        point_count=3,
        trace=trace,
    )

    assert candidate.trace is trace
    assert "rt_min" not in IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS
    assert "intensity" not in IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS


def test_candidate_trace_rejects_mismatched_rt_and_intensity_lengths():
    with pytest.raises(ValueError, match="rt_min and intensity"):
        CandidateTrace(
            rt_min=(7.75, 7.80, 7.85),
            intensity=(1.0, 5.0),
            shape_audit_status=ShapeAuditStatus.PASS,
        )


def test_identity_coherence_facade_exports_shape_width_models_and_functions():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    expected_names = {
        "CandidateTrace",
        "ShapeConfig",
        "WidthConfig",
        "ShapeReferenceResult",
        "ShapeComparisonResult",
        "PrototypeWidthResult",
        "WidthAssessmentResult",
    }

    for name in expected_names:
        assert hasattr(identity_coherence, name)
        assert name in identity_coherence.__all__
```

Add the missing imports near the top of the same test file:

```python
from xic_extractor.alignment.identity_coherence import (
    CandidateTrace,
)
```

If the file already imports from `xic_extractor.alignment.identity_coherence.models`,
merge `CandidateTrace` into that import instead of duplicating an import block.
Do not import `PrototypeWidthResult`, `ShapeComparisonResult`, `ShapeConfig`,
`ShapeReferenceResult`, `WidthAssessmentResult`, or `WidthConfig` unless a test
uses the name directly; the facade export test checks those names via `hasattr`
and string membership to avoid ruff `F401`.

- [ ] **Step 2: Run Task 1 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py -q
```

Expected: FAIL because `CandidateTrace`, shape/width config models, result models, and facade exports do not exist.

- [ ] **Step 3: Add dataclasses in `models.py`**

Add these dataclasses after `RtConfig` and before `IdentityCoherenceConfig`.
Place `CandidateTrace` before `CellCandidateEvidence`, because
`CellCandidateEvidence.trace` references it directly.

```python
@dataclass(frozen=True)
class ShapeConfig:
    min_points: int = 7
    resample_points: int = 25
    min_cosine: float = 0.85
    prototype_min_candidates: int = 3
    prototype_min_non_seed_candidates: int = 2
    allow_seed_shape_fallback: bool = True
    allow_morphology_rt_medoid: bool = True


@dataclass(frozen=True)
class WidthConfig:
    prototype_min_candidates: int = 3
    min_ratio: float = 0.50
    max_ratio: float = 2.00


@dataclass(frozen=True)
class CandidateTrace:
    rt_min: tuple[float, ...]
    intensity: tuple[float, ...]
    shape_audit_status: ShapeAuditStatus = ShapeAuditStatus.UNAVAILABLE

    def __post_init__(self) -> None:
        if len(self.rt_min) != len(self.intensity):
            raise ValueError("rt_min and intensity must have the same length")
```

Replace `IdentityCoherenceConfig` with:

```python
@dataclass(frozen=True)
class IdentityCoherenceConfig:
    seed_gate: SeedGateConfig = field(default_factory=SeedGateConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    rt: RtConfig = field(default_factory=RtConfig)
    shape: ShapeConfig = field(default_factory=ShapeConfig)
    width: WidthConfig = field(default_factory=WidthConfig)
```

Add optional trace to `CellCandidateEvidence`:

```python
    trace: CandidateTrace | None = None
```

Add result models after `CellCandidateEvidence`.

```python
@dataclass(frozen=True)
class PrototypeWidthResult:
    width_status: WidthStatus
    prototype_width_sec: float | None
    candidate_count: int
    non_seed_candidate_count: int
    width_candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class WidthAssessmentResult:
    width_status: WidthStatus
    width_ratio_to_prototype: float | None


@dataclass(frozen=True)
class ShapeReferenceResult:
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    normalized_intensity: tuple[float, ...]
    candidate_count: int
    non_seed_candidate_count: int
    seed_fallback_used: bool = False


@dataclass(frozen=True)
class ShapeComparisonResult:
    shape_status: ShapeStatus
    shape_similarity_cosine: float | None
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    shape_fallback_used: bool
    shape_audit_status: ShapeAuditStatus
```

- [ ] **Step 4: Update facade exports**

In `xic_extractor/alignment/identity_coherence/__init__.py`, import and add to `__all__`:

```python
CandidateTrace,
PrototypeWidthResult,
ShapeComparisonResult,
ShapeConfig,
ShapeReferenceResult,
WidthAssessmentResult,
WidthConfig,
```

- [ ] **Step 5: Run Task 1 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```powershell
git add xic_extractor/alignment/identity_coherence/models.py xic_extractor/alignment/identity_coherence/__init__.py tests/alignment/identity_coherence/test_schema_contract.py
git commit -m "feat: add identity coherence trace config models"
```

---

## Task 2: Implement Prototype Width Domain Logic

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/width.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Test: `tests/alignment/identity_coherence/test_width.py`
- Test: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Create failing width tests**

Create `tests/alignment/identity_coherence/test_width.py`.

```python
from __future__ import annotations

import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    SeedCandidateEvidence,
    ShapeConfig,
)
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    WidthStatus,
)
from xic_extractor.alignment.identity_coherence.width import (
    assess_width_against_prototype,
    estimate_prototype_width,
)


def _seed_candidate(
    candidate_id: str,
    *,
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
) -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id=candidate_id,
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("dR", "MeR"),
        best_seed_rt=7.80,
        ms1_scan_support_score=0.75,
        evidence_stage=evidence_stage,
    )


def _candidate(
    candidate_id: str,
    *,
    sample_id: str = "S2",
    start: float = 7.75,
    apex: float = 7.80,
    end: float = 7.85,
    duplicate_loser: bool = False,
    owner_assignment_status: str = "primary",
    blocked_reason: str = "",
    data_quality_reason: str = "",
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=_seed_candidate(candidate_id, evidence_stage=evidence_stage),
        apex_rt=apex,
        peak_start_rt=start,
        peak_end_rt=end,
        area=100.0,
        height=20.0,
        point_count=9,
        owner_assignment_status=owner_assignment_status,
        duplicate_loser=duplicate_loser,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )


def test_estimate_prototype_width_uses_median_width_seconds():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("C1", start=7.75, end=7.85),
            _candidate("C2", start=7.74, end=7.86),
            _candidate("C3", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.prototype_width_sec == pytest.approx(6.0)
    assert result.candidate_count == 3
    assert result.non_seed_candidate_count == 3
    assert result.width_candidate_ids == ("C1", "C2", "C3")


def test_estimate_prototype_width_requires_minimum_candidates():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("C1", start=7.75, end=7.85),
            _candidate("C2", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.prototype_width_sec is None
    assert result.candidate_count == 2


def test_estimate_prototype_width_excludes_seed_from_reference_and_minimum():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("SEED", sample_id="S1", start=7.75, end=7.85),
            _candidate("C1", sample_id="S2", start=7.75, end=7.85),
            _candidate("C2", sample_id="S3", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.prototype_width_sec is None
    assert result.candidate_count == 2
    assert result.non_seed_candidate_count == 2
    assert result.width_candidate_ids == ("C1", "C2")


def test_estimate_prototype_width_excludes_forbidden_and_bad_candidates():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("GOOD1", start=7.75, end=7.85),
            _candidate("GOOD2", start=7.76, end=7.84),
            _candidate("GOOD3", start=7.74, end=7.86),
            _candidate("BACKFILL", evidence_stage=EvidenceStage.BACKFILL_ONLY),
            _candidate("DUP", duplicate_loser=True),
            _candidate("AMB", owner_assignment_status="ambiguous"),
            _candidate("BLOCK", blocked_reason="raw_open_failed"),
            _candidate("DQ", data_quality_reason="invalid_peak_morphology"),
            _candidate("FAR_CENTER", apex=9.80, start=9.75, end=9.85),
            _candidate("FAR_SEED", apex=8.60, start=8.55, end=8.65),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_candidate_ids == ("GOOD1", "GOOD2", "GOOD3")


def test_estimate_prototype_width_accepts_public_string_stage_values():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("GOOD1", start=7.75, end=7.85),
            _candidate("GOOD2", start=7.76, end=7.84),
            _candidate("GOOD3", start=7.74, end=7.86),
            _candidate("BACKFILL", evidence_stage="backfill_only"),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_candidate_ids == ("GOOD1", "GOOD2", "GOOD3")


def test_assess_width_passes_inside_ratio_range():
    result = assess_width_against_prototype(
        _candidate("C1", start=7.75, end=7.85),
        prototype_width_sec=6.0,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_ratio_to_prototype == 1.0


def test_assess_width_fails_outside_ratio_range():
    result = assess_width_against_prototype(
        _candidate("WIDE", start=7.675, end=7.925),
        prototype_width_sec=6.0,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.FAIL
    assert result.width_ratio_to_prototype == pytest.approx(2.5)


def test_assess_width_not_assessed_without_prototype_width():
    result = assess_width_against_prototype(
        _candidate("C1"),
        prototype_width_sec=None,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.width_ratio_to_prototype is None
```

- [ ] **Step 2: Run Task 2 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_width.py -q
```

Expected: FAIL because `width.py` does not exist.

- [ ] **Step 3: Implement `width.py`**

Create `xic_extractor/alignment/identity_coherence/width.py`.

```python
from __future__ import annotations

import math
from statistics import median

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    PrototypeWidthResult,
    WidthAssessmentResult,
)
from .schema import EvidenceStage, WidthStatus

_WIDTH_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}


def estimate_prototype_width(
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    seed_rt_min: float,
    center_rt_min: float,
) -> PrototypeWidthResult:
    width_candidates = tuple(
        candidate
        for candidate in candidates
        if _is_width_candidate(
            candidate,
            config,
            seed_sample_id=seed_sample_id,
            seed_rt_min=seed_rt_min,
            center_rt_min=center_rt_min,
        )
    )
    non_seed_count = len(width_candidates)
    if len(width_candidates) < config.width.prototype_min_candidates:
        return PrototypeWidthResult(
            width_status=WidthStatus.NOT_ASSESSED,
            prototype_width_sec=None,
            candidate_count=len(width_candidates),
            non_seed_candidate_count=non_seed_count,
            width_candidate_ids=tuple(
                candidate.candidate_evidence.candidate_id
                for candidate in width_candidates
            ),
        )

    prototype_width_sec = median(
        _candidate_width_sec(candidate) for candidate in width_candidates
    )
    return PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=prototype_width_sec,
        candidate_count=len(width_candidates),
        non_seed_candidate_count=non_seed_count,
        width_candidate_ids=tuple(
            candidate.candidate_evidence.candidate_id for candidate in width_candidates
        ),
    )


def assess_width_against_prototype(
    candidate: CellCandidateEvidence,
    *,
    prototype_width_sec: float | None,
    config: IdentityCoherenceConfig,
) -> WidthAssessmentResult:
    if not _finite_positive(prototype_width_sec):
        return WidthAssessmentResult(
            width_status=WidthStatus.NOT_ASSESSED,
            width_ratio_to_prototype=None,
        )
    if not _has_complete_morphology(candidate):
        return WidthAssessmentResult(
            width_status=WidthStatus.NOT_ASSESSED,
            width_ratio_to_prototype=None,
        )

    ratio = _candidate_width_sec(candidate) / float(prototype_width_sec)
    status = (
        WidthStatus.PASS
        if config.width.min_ratio <= ratio <= config.width.max_ratio
        else WidthStatus.FAIL
    )
    return WidthAssessmentResult(
        width_status=status,
        width_ratio_to_prototype=ratio,
    )


def _is_width_candidate(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    seed_rt_min: float,
    center_rt_min: float,
) -> bool:
    if seed_sample_id is not None and candidate.sample_id == seed_sample_id:
        return False
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _WIDTH_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    center_delta_sec = abs(float(candidate.apex_rt) - center_rt_min) * 60.0
    if center_delta_sec > config.rt.preferred_rt_sec:
        return False
    seed_delta_sec = abs(float(candidate.apex_rt) - seed_rt_min) * 60.0
    return seed_delta_sec <= config.rt.seed_center_candidate_sec


def _candidate_width_sec(candidate: CellCandidateEvidence) -> float:
    return (float(candidate.peak_end_rt) - float(candidate.peak_start_rt)) * 60.0


def _has_complete_morphology(candidate: CellCandidateEvidence) -> bool:
    values = (
        candidate.apex_rt,
        candidate.peak_start_rt,
        candidate.peak_end_rt,
        candidate.area,
        candidate.height,
    )
    if any(not _finite_number(value) for value in values):
        return False
    return (
        float(candidate.peak_start_rt)
        < float(candidate.apex_rt)
        < float(candidate.peak_end_rt)
        and float(candidate.area) > 0.0
        and float(candidate.height) > 0.0
    )


def _finite_positive(value: object) -> bool:
    return _finite_number(value) and float(value) > 0.0


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
```

- [ ] **Step 4: Export width functions**

In `__init__.py`, import and export:

```python
from .width import assess_width_against_prototype, estimate_prototype_width
```

Add both function names to `__all__`.

- [ ] **Step 5: Add facade assertions for width functions**

Extend `test_identity_coherence_facade_exports_shape_width_models_and_functions` from Task 1:

```python
        "assess_width_against_prototype",
        "estimate_prototype_width",
```

- [ ] **Step 6: Run Task 2 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_width.py tests/alignment/identity_coherence/test_schema_contract.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```powershell
git add xic_extractor/alignment/identity_coherence/width.py xic_extractor/alignment/identity_coherence/__init__.py tests/alignment/identity_coherence/test_width.py tests/alignment/identity_coherence/test_schema_contract.py
git commit -m "feat: add identity coherence prototype width"
```

---

## Task 3: Implement Prototype Shape Domain Logic

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/shape.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Test: `tests/alignment/identity_coherence/test_shape.py`
- Test: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Create failing shape tests**

Create `tests/alignment/identity_coherence/test_shape.py`.

```python
from __future__ import annotations

import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    SeedCandidateEvidence,
    ShapeReferenceResult,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellIdentityTier,
    EvidenceStage,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
)
from xic_extractor.alignment.identity_coherence.shape import (
    compare_shape_to_reference,
    create_seed_shape_reference,
    estimate_shape_reference,
    normalize_trace_for_shape,
)


def _seed_candidate(
    candidate_id: str,
    *,
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
) -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id=candidate_id,
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("dR", "MeR"),
        best_seed_rt=7.80,
        ms1_scan_support_score=0.75,
        evidence_stage=evidence_stage,
    )


def _trace(
    intensities: tuple[float, ...],
    *,
    start: float = 7.75,
    end: float = 7.85,
    audit: ShapeAuditStatus = ShapeAuditStatus.PASS,
) -> CandidateTrace:
    count = len(intensities)
    step = (end - start) / (count - 1)
    return CandidateTrace(
        rt_min=tuple(start + step * i for i in range(count)),
        intensity=intensities,
        shape_audit_status=audit,
    )


def _candidate(
    candidate_id: str,
    *,
    sample_id: str = "S2",
    intensities: tuple[float, ...] = (0, 1, 3, 7, 10, 7, 3, 1, 0),
    tier: CellIdentityTier = CellIdentityTier.RT_ONLY,
    start: float = 7.75,
    apex: float = 7.80,
    end: float = 7.85,
    point_count: int | None = 9,
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
    duplicate_loser: bool = False,
    owner_assignment_status: str = "primary",
    blocked_reason: str = "",
    data_quality_reason: str = "",
    audit: ShapeAuditStatus = ShapeAuditStatus.PASS,
) -> CellCandidateEvidence:
    candidate = CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=_seed_candidate(candidate_id, evidence_stage=evidence_stage),
        apex_rt=apex,
        peak_start_rt=start,
        peak_end_rt=end,
        area=100.0,
        height=20.0,
        point_count=point_count,
        owner_assignment_status=owner_assignment_status,
        duplicate_loser=duplicate_loser,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
        trace=_trace(intensities, start=start, end=end, audit=audit),
    )
    return candidate


def test_normalize_trace_for_shape_uses_candidate_boundaries_and_unit_norm():
    config = IdentityCoherenceConfig()
    candidate = _candidate(
        "C1",
        intensities=(100, 101, 103, 107, 110, 107, 103, 101, 100),
    )

    normalized = normalize_trace_for_shape(candidate, config)

    assert normalized.shape_status is ShapeStatus.PASS
    assert len(normalized.normalized_intensity) == config.shape.resample_points
    assert max(normalized.normalized_intensity) > 0.0
    assert pytest.approx(
        sum(value * value for value in normalized.normalized_intensity),
        rel=1e-12,
    ) == 1.0


def test_normalize_trace_for_shape_rejects_low_raw_point_count():
    config = IdentityCoherenceConfig()
    candidate = _candidate("LOW", intensities=(0, 1, 2, 1, 0), point_count=5)

    normalized = normalize_trace_for_shape(candidate, config)

    assert normalized.shape_status is ShapeStatus.LOW_POINTS
    assert normalized.normalized_intensity == ()


def test_normalize_trace_for_shape_rejects_zero_signal_after_baseline_subtraction():
    config = IdentityCoherenceConfig()
    candidate = _candidate("ZERO", intensities=(5, 5, 5, 5, 5, 5, 5))

    normalized = normalize_trace_for_shape(candidate, config)

    assert normalized.shape_status is ShapeStatus.ZERO_SIGNAL
    assert normalized.normalized_intensity == ()


def test_estimate_shape_reference_prefers_tier1_supported_medoid_on_tie():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("TIER1", sample_id="S2", tier=CellIdentityTier.TIER1),
            _candidate("MORPH", sample_id="S3", tier=CellIdentityTier.RT_ONLY),
            _candidate("OTHER", sample_id="S4", tier=CellIdentityTier.RT_ONLY),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={
            "TIER1": CellIdentityTier.TIER1,
            "MORPH": CellIdentityTier.RT_ONLY,
            "OTHER": CellIdentityTier.RT_ONLY,
        },
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.TIER1_SUPPORTED_MEDOID
    assert result.shape_reference_candidate_id == "TIER1"
    assert result.candidate_count == 3
    assert result.non_seed_candidate_count == 3


def test_estimate_shape_reference_allows_morphology_rt_medoid_when_no_tier1():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("M1", sample_id="S2"),
            _candidate("M2", sample_id="S3"),
            _candidate("M3", sample_id="S4"),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={},
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert result.shape_reference_candidate_id in {"M1", "M2", "M3"}


def test_estimate_shape_reference_requires_non_seed_candidates():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("SEED", sample_id="S1"),
            _candidate("S2", sample_id="S2"),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={},
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.NONE
    assert result.shape_reference_candidate_id == ""
    assert result.normalized_intensity == ()


def test_estimate_shape_reference_excludes_seed_from_prototype_medoid():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("SEED", sample_id="S1"),
            _candidate("M1", sample_id="S2"),
            _candidate("M2", sample_id="S3"),
            _candidate("M3", sample_id="S4"),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={"SEED": CellIdentityTier.TIER1},
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert result.shape_reference_candidate_id in {"M1", "M2", "M3"}
    assert result.shape_reference_candidate_id != "SEED"
    assert result.seed_fallback_used is False


def test_estimate_shape_reference_accepts_public_string_stage_values():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("M1", sample_id="S2"),
            _candidate("M2", sample_id="S3"),
            _candidate("M3", sample_id="S4"),
            _candidate("BACKFILL", sample_id="S5", evidence_stage="backfill_only"),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={},
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert result.shape_reference_candidate_id in {"M1", "M2", "M3"}


def test_estimate_shape_reference_excludes_candidates_outside_rt_gate():
    config = IdentityCoherenceConfig()
    result = estimate_shape_reference(
        (
            _candidate("M1", sample_id="S2"),
            _candidate("M2", sample_id="S3"),
            _candidate("M3", sample_id="S4"),
            _candidate("FAR", sample_id="S5", start=9.75, apex=9.80, end=9.85),
        ),
        config,
        seed_sample_id="S1",
        tier_by_candidate_id={},
        center_rt_min=7.80,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert result.shape_reference_candidate_id in {"M1", "M2", "M3"}


def test_create_seed_shape_reference_marks_seed_fallback():
    config = IdentityCoherenceConfig()
    result = create_seed_shape_reference(
        _candidate("SEED", sample_id="S1"),
        config,
    )

    assert result.shape_reference_basis is ShapeReferenceBasis.SEED_FALLBACK
    assert result.shape_reference_candidate_id == "SEED"
    assert result.seed_fallback_used is True


def test_compare_shape_to_reference_passes_similar_trace_with_width_sanity():
    config = IdentityCoherenceConfig()
    reference = ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        shape_reference_candidate_id="REF",
        normalized_intensity=normalize_trace_for_shape(
            _candidate("REF"),
            config,
        ).normalized_intensity,
        candidate_count=3,
        non_seed_candidate_count=3,
    )

    result = compare_shape_to_reference(
        _candidate("QUERY"),
        reference,
        config,
        width_sanity_status=WidthStatus.PASS,
    )

    assert result.shape_status is ShapeStatus.PASS
    assert result.shape_similarity_cosine == pytest.approx(1.0)
    assert result.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert result.shape_reference_candidate_id == "REF"
    assert result.shape_fallback_used is False


def test_compare_shape_to_reference_requires_width_sanity_pass():
    config = IdentityCoherenceConfig()
    reference = create_seed_shape_reference(_candidate("SEED", sample_id="S1"), config)

    result = compare_shape_to_reference(
        _candidate("QUERY"),
        reference,
        config,
        width_sanity_status=WidthStatus.NOT_ASSESSED,
    )

    assert result.shape_status is ShapeStatus.NOT_ASSESSED
    assert result.shape_similarity_cosine is None


def test_compare_shape_to_reference_fails_reliable_bad_audit():
    config = IdentityCoherenceConfig()
    reference = create_seed_shape_reference(_candidate("SEED", sample_id="S1"), config)

    result = compare_shape_to_reference(
        _candidate("BAD", audit=ShapeAuditStatus.SHOULDER),
        reference,
        config,
        width_sanity_status=WidthStatus.PASS,
    )

    assert result.shape_status is ShapeStatus.FAIL
    assert result.shape_audit_status is ShapeAuditStatus.SHOULDER


def test_normalize_trace_for_shape_fails_generic_fail_audit():
    config = IdentityCoherenceConfig()
    normalized = normalize_trace_for_shape(
        _candidate("BAD", audit=ShapeAuditStatus.FAIL),
        config,
    )

    assert normalized.shape_status is ShapeStatus.FAIL
    assert normalized.shape_audit_status is ShapeAuditStatus.FAIL
```

- [ ] **Step 2: Run Task 3 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_shape.py -q
```

Expected: FAIL because `shape.py` does not exist.

- [ ] **Step 3: Implement `shape.py`**

Create `xic_extractor/alignment/identity_coherence/shape.py`.

```python
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    ShapeComparisonResult,
    ShapeReferenceResult,
)
from .schema import (
    CellIdentityTier,
    EvidenceStage,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
)

_SHAPE_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}
_SHAPE_FAIL_AUDIT_STATUSES = {
    ShapeAuditStatus.FAIL.value,
    ShapeAuditStatus.SHOULDER.value,
    ShapeAuditStatus.BIMODAL.value,
    ShapeAuditStatus.COELUTION.value,
    ShapeAuditStatus.SATURATED.value,
    ShapeAuditStatus.CLIPPED.value,
}


@dataclass(frozen=True)
class NormalizedShapeTrace:
    shape_status: ShapeStatus
    normalized_intensity: tuple[float, ...]
    shape_audit_status: ShapeAuditStatus


def normalize_trace_for_shape(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
) -> NormalizedShapeTrace:
    audit_status = _trace_audit_status(candidate)
    if _enum_value(audit_status) in _SHAPE_FAIL_AUDIT_STATUSES:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.FAIL,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if candidate.trace is None:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        )
    if not _has_complete_morphology(candidate):
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if candidate.point_count is None or candidate.point_count < config.shape.min_points:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.LOW_POINTS,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if len(candidate.trace.rt_min) != len(candidate.trace.intensity):
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )

    rt_values = np.asarray(candidate.trace.rt_min, dtype=float)
    intensity_values = np.asarray(candidate.trace.intensity, dtype=float)
    finite = np.isfinite(rt_values) & np.isfinite(intensity_values)
    inside = (
        (rt_values >= float(candidate.peak_start_rt))
        & (rt_values <= float(candidate.peak_end_rt))
        & finite
    )
    rt_inside = rt_values[inside]
    intensity_inside = intensity_values[inside]
    if rt_inside.size < config.shape.min_points:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.LOW_POINTS,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    order = np.argsort(rt_inside)
    rt_inside = rt_inside[order]
    intensity_inside = intensity_inside[order]

    shifted = np.clip(intensity_inside - np.min(intensity_inside), 0.0, None)
    norm = float(np.linalg.norm(shifted))
    if not math.isfinite(norm) or norm <= 0.0:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.ZERO_SIGNAL,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )

    normalized_positions = (
        (rt_inside - float(candidate.peak_start_rt))
        / (float(candidate.peak_end_rt) - float(candidate.peak_start_rt))
    )
    target_positions = np.linspace(0.0, 1.0, config.shape.resample_points)
    resampled = np.interp(target_positions, normalized_positions, shifted)
    resampled_norm = float(np.linalg.norm(resampled))
    if not math.isfinite(resampled_norm) or resampled_norm <= 0.0:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.ZERO_SIGNAL,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    unit = resampled / resampled_norm
    return NormalizedShapeTrace(
        shape_status=ShapeStatus.PASS,
        normalized_intensity=tuple(float(value) for value in unit),
        shape_audit_status=audit_status,
    )


def estimate_shape_reference(
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    tier_by_candidate_id: dict[str, CellIdentityTier],
    center_rt_min: float,
) -> ShapeReferenceResult:
    pool = tuple(
        (candidate, normalize_trace_for_shape(candidate, config))
        for candidate in candidates
        if _is_shape_pool_candidate(
            candidate,
            config,
            seed_sample_id=seed_sample_id,
            center_rt_min=center_rt_min,
        )
    )
    usable = tuple(
        (candidate, normalized)
        for candidate, normalized in pool
        if normalized.shape_status is ShapeStatus.PASS
    )
    non_seed_count = sum(1 for candidate, _ in usable if candidate.sample_id != seed_sample_id)
    if len(usable) < config.shape.prototype_min_candidates:
        return _empty_shape_reference(len(usable), non_seed_count)
    if non_seed_count < config.shape.prototype_min_non_seed_candidates:
        return _empty_shape_reference(len(usable), non_seed_count)

    ranked = sorted(
        usable,
        key=lambda item: _medoid_key(
            item,
            usable,
            tier_by_candidate_id=tier_by_candidate_id,
            center_rt_min=center_rt_min,
        ),
    )
    medoid_candidate, medoid_trace = ranked[0]
    medoid_tier = tier_by_candidate_id.get(
        medoid_candidate.candidate_evidence.candidate_id,
        CellIdentityTier.RT_ONLY,
    )
    basis = (
        ShapeReferenceBasis.TIER1_SUPPORTED_MEDOID
        if _enum_value(medoid_tier) == CellIdentityTier.TIER1.value
        else ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    )
    if _enum_value(basis) == ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID.value:
        if not config.shape.allow_morphology_rt_medoid:
            return _empty_shape_reference(len(usable), non_seed_count)
    return ShapeReferenceResult(
        shape_reference_basis=basis,
        shape_reference_candidate_id=medoid_candidate.candidate_evidence.candidate_id,
        normalized_intensity=medoid_trace.normalized_intensity,
        candidate_count=len(usable),
        non_seed_candidate_count=non_seed_count,
    )


def create_seed_shape_reference(
    seed_candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
) -> ShapeReferenceResult:
    if not config.shape.allow_seed_shape_fallback:
        return _empty_shape_reference(0, 0)
    normalized = normalize_trace_for_shape(seed_candidate, config)
    if _enum_value(normalized.shape_status) != ShapeStatus.PASS.value:
        return _empty_shape_reference(0, 0)
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.SEED_FALLBACK,
        shape_reference_candidate_id=seed_candidate.candidate_evidence.candidate_id,
        normalized_intensity=normalized.normalized_intensity,
        candidate_count=1,
        non_seed_candidate_count=0,
        seed_fallback_used=True,
    )


def compare_shape_to_reference(
    candidate: CellCandidateEvidence,
    reference: ShapeReferenceResult | None,
    config: IdentityCoherenceConfig,
    *,
    width_sanity_status: WidthStatus,
) -> ShapeComparisonResult:
    if _enum_value(width_sanity_status) != WidthStatus.PASS.value:
        return _shape_result(
            ShapeStatus.NOT_ASSESSED,
            None,
            reference,
            _trace_audit_status(candidate),
        )
    if reference is None or not reference.normalized_intensity:
        return _shape_result(
            ShapeStatus.NOT_ASSESSED,
            None,
            reference,
            _trace_audit_status(candidate),
        )
    normalized = normalize_trace_for_shape(candidate, config)
    if _enum_value(normalized.shape_status) != ShapeStatus.PASS.value:
        return _shape_result(
            normalized.shape_status,
            None,
            reference,
            normalized.shape_audit_status,
        )

    score = _cosine(normalized.normalized_intensity, reference.normalized_intensity)
    status = ShapeStatus.PASS if score >= config.shape.min_cosine else ShapeStatus.FAIL
    return _shape_result(status, score, reference, normalized.shape_audit_status)


def _shape_result(
    status: ShapeStatus,
    score: float | None,
    reference: ShapeReferenceResult | None,
    audit_status: ShapeAuditStatus,
) -> ShapeComparisonResult:
    return ShapeComparisonResult(
        shape_status=status,
        shape_similarity_cosine=score,
        shape_reference_basis=(
            reference.shape_reference_basis
            if reference is not None
            else ShapeReferenceBasis.NONE
        ),
        shape_reference_candidate_id=(
            reference.shape_reference_candidate_id if reference is not None else ""
        ),
        shape_fallback_used=(
            reference.seed_fallback_used if reference is not None else False
        ),
        shape_audit_status=audit_status,
    )


def _medoid_key(
    item: tuple[CellCandidateEvidence, NormalizedShapeTrace],
    usable: tuple[tuple[CellCandidateEvidence, NormalizedShapeTrace], ...],
    *,
    tier_by_candidate_id: dict[str, CellIdentityTier],
    center_rt_min: float,
) -> tuple[float, int, float, str]:
    candidate, normalized = item
    average_similarity = _average_similarity(normalized, usable)
    tier = tier_by_candidate_id.get(
        candidate.candidate_evidence.candidate_id,
        CellIdentityTier.RT_ONLY,
    )
    tier_penalty = 0 if _enum_value(tier) == CellIdentityTier.TIER1.value else 1
    rt_delta = abs(float(candidate.apex_rt) - center_rt_min)
    return (
        -average_similarity,
        tier_penalty,
        rt_delta,
        candidate.candidate_evidence.candidate_id,
    )


def _average_similarity(
    normalized: NormalizedShapeTrace,
    usable: tuple[tuple[CellCandidateEvidence, NormalizedShapeTrace], ...],
) -> float:
    scores = [
        _cosine(normalized.normalized_intensity, other.normalized_intensity)
        for _, other in usable
    ]
    return sum(scores) / len(scores)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return float(np.dot(np.asarray(left), np.asarray(right)))


def _empty_shape_reference(
    candidate_count: int,
    non_seed_candidate_count: int,
) -> ShapeReferenceResult:
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        normalized_intensity=(),
        candidate_count=candidate_count,
        non_seed_candidate_count=non_seed_candidate_count,
    )


def _is_shape_pool_candidate(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    center_rt_min: float,
) -> bool:
    if candidate.sample_id == seed_sample_id:
        return False
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _SHAPE_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    center_delta_sec = abs(float(candidate.apex_rt) - center_rt_min) * 60.0
    return center_delta_sec <= config.rt.preferred_rt_sec


def _trace_audit_status(candidate: CellCandidateEvidence) -> ShapeAuditStatus:
    if candidate.trace is None:
        return ShapeAuditStatus.NOT_ASSESSED
    return candidate.trace.shape_audit_status


def _has_complete_morphology(candidate: CellCandidateEvidence) -> bool:
    values = (
        candidate.apex_rt,
        candidate.peak_start_rt,
        candidate.peak_end_rt,
        candidate.area,
        candidate.height,
    )
    if any(not _finite_number(value) for value in values):
        return False
    return (
        float(candidate.peak_start_rt)
        < float(candidate.apex_rt)
        < float(candidate.peak_end_rt)
        and float(candidate.area) > 0.0
        and float(candidate.height) > 0.0
    )


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
```

- [ ] **Step 4: Fix test imports**

- [ ] **Step 5: Export shape functions**

In `__init__.py`, import and export:

```python
from .shape import (
    compare_shape_to_reference,
    create_seed_shape_reference,
    estimate_shape_reference,
    normalize_trace_for_shape,
)
```

Add these function names to `__all__`.

- [ ] **Step 6: Add facade assertions for shape functions**

Extend `test_identity_coherence_facade_exports_shape_width_models_and_functions`:

```python
        "compare_shape_to_reference",
        "create_seed_shape_reference",
        "estimate_shape_reference",
        "normalize_trace_for_shape",
```

- [ ] **Step 7: Run Task 3 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_shape.py tests/alignment/identity_coherence/test_schema_contract.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```powershell
git add xic_extractor/alignment/identity_coherence/shape.py xic_extractor/alignment/identity_coherence/__init__.py tests/alignment/identity_coherence/test_shape.py tests/alignment/identity_coherence/test_schema_contract.py
git commit -m "feat: add identity coherence prototype shape"
```

---

## Task 4: Integrate Tier 2 And Tier 3 Cell Evidence

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence/cell_evidence.py`
- Test: `tests/alignment/identity_coherence/test_cell_evidence.py`

- [ ] **Step 1: Add failing tier 2 and tier 3 integration tests**

Append to `tests/alignment/identity_coherence/test_cell_evidence.py`. Merge imports instead of duplicating existing imports.

```python
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    PrototypeWidthResult,
    ShapeConfig,
    ShapeReferenceResult,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ShapeAuditStatus,
    ShapeReferenceBasis,
    WidthStatus,
)
```

Append tests:

```python
def _trace(
    intensities: tuple[float, ...] = (0, 1, 3, 7, 10, 7, 3, 1, 0),
    *,
    start: float = 7.75,
    end: float = 7.85,
):
    step = (end - start) / (len(intensities) - 1)
    return CandidateTrace(
        rt_min=tuple(start + step * i for i in range(len(intensities))),
        intensity=intensities,
        shape_audit_status=ShapeAuditStatus.PASS,
    )


def _shape_reference() -> ShapeReferenceResult:
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        shape_reference_candidate_id="REF",
        normalized_intensity=(
            0.0,
            0.060522753266880246,
            0.18156825980064073,
            0.4236592728681617,
            0.6052275326688024,
            0.4236592728681617,
            0.18156825980064073,
            0.060522753266880246,
            0.0,
        ),
        candidate_count=3,
        non_seed_candidate_count=3,
    )


def test_evaluate_cell_evidence_promotes_tier2_shape_after_rt_and_width_pass():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="SHAPE",
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(),
        point_count=9,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="FAM1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER2
    assert cell.cell_identity_basis is CellIdentityBasis.RT_SHAPE_SIMILARITY
    assert cell.fragment_match_status is FragmentMatchStatus.FAIL
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.shape_status is ShapeStatus.PASS
    assert cell.width_status is WidthStatus.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is True


def test_evaluate_cell_evidence_promotes_tier3_width_when_shape_unavailable():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="WIDTH",
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=None,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        shape_reference=None,
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER3
    assert cell.cell_identity_basis is CellIdentityBasis.RT_PROTOTYPE_WIDTH
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.width_status is WidthStatus.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_keeps_tier1_even_when_width_sanity_fails():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="TIER1",
        trace=_trace(),
        point_count=9,
        peak_start_rt=7.70,
        peak_end_rt=7.90,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="FAM1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER1
    assert cell.cell_identity_basis is CellIdentityBasis.RT_FRAGMENT_SUPPORT
    assert cell.width_status is WidthStatus.FAIL
    assert cell.tier12_count_contribution is True


def test_evaluate_cell_evidence_does_not_use_shape_without_width_sanity():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="NO_WIDTH",
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(),
        point_count=9,
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="FAM1",
        shape_reference=_shape_reference(),
        prototype_width=None,
    )

    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.shape_status is ShapeStatus.NOT_ASSESSED
    assert cell.width_status is WidthStatus.NOT_ASSESSED
    assert cell.coherent_count_contribution is False


def test_select_cell_evidence_prefers_tier2_over_closer_rt_only_candidate():
    request = _request()
    center = _center()
    shape_candidate = _candidate(
        candidate_id="SHAPE",
        sample_id="S2",
        apex_rt=7.875,
        peak_start_rt=7.825,
        peak_end_rt=7.925,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(start=7.825, end=7.925),
        point_count=9,
    )
    rt_only_candidate = _candidate(
        candidate_id="RT_ONLY",
        sample_id="S2",
        apex_rt=7.820,
        peak_start_rt=7.700,
        peak_end_rt=7.940,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=None,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    selected = select_cell_evidence_for_sample(
        request,
        (rt_only_candidate, shape_candidate),
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="FAM1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert selected.candidate_id == "SHAPE"
    assert selected.cell_identity_tier is CellIdentityTier.TIER2
```

If existing helper `_candidate` does not accept `sample_id`, `trace`,
`point_count`, `apex_rt`, `peak_start_rt`, `peak_end_rt`, or `loss_da`, extend
the helper instead of introducing a second fixture factory.

- [ ] **Step 2: Run Task 4 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_cell_evidence.py -q
```

Expected: FAIL because `evaluate_cell_evidence` does not accept shape/width references or produce tier2/tier3 cells.

- [ ] **Step 3: Update `cell_evidence.py` function signatures**

Add imports:

```python
from .shape import compare_shape_to_reference
from .width import assess_width_against_prototype
from .models import PrototypeWidthResult, ShapeReferenceResult
```

Extend `select_cell_evidence_for_sample` signature:

```python
    shape_reference: ShapeReferenceResult | None = None,
    prototype_width: PrototypeWidthResult | None = None,
```

Pass those through to `evaluate_cell_evidence`.

Extend `evaluate_cell_evidence` signature:

```python
    shape_reference: ShapeReferenceResult | None = None,
    prototype_width: PrototypeWidthResult | None = None,
```

- [ ] **Step 4: Add tier precedence implementation**

In `evaluate_cell_evidence`, after computing `fragment_match_status`, compute:

```python
    prototype_width_sec = (
        prototype_width.prototype_width_sec if prototype_width is not None else None
    )
    width_assessment = assess_width_against_prototype(
        candidate,
        prototype_width_sec=prototype_width_sec,
        config=config,
    )
    shape_comparison = compare_shape_to_reference(
        candidate,
        shape_reference,
        config,
        width_sanity_status=width_assessment.width_status,
    )
```

Replace tier assignment with this precedence:

```python
    rt_gate_pass = _enum_value(rt_gate_status) == RtGateStatus.PASS.value
    non_rt_pass = (
        _enum_value(non_rt_identity_result) == NonRtIdentityResult.PASS.value
    )
    shape_pass = (
        _enum_value(shape_comparison.shape_status) == ShapeStatus.PASS.value
    )
    width_pass = (
        _enum_value(width_assessment.width_status) == WidthStatus.PASS.value
    )

    if (
        rt_gate_pass
        and non_rt_pass
    ):
        tier = CellIdentityTier.TIER1
        basis = CellIdentityBasis.RT_FRAGMENT_SUPPORT
        coherent = True
        tier12 = True
    elif rt_gate_pass and shape_pass:
        tier = CellIdentityTier.TIER2
        basis = CellIdentityBasis.RT_SHAPE_SIMILARITY
        coherent = True
        tier12 = True
    elif rt_gate_pass and width_pass:
        tier = CellIdentityTier.TIER3
        basis = CellIdentityBasis.RT_PROTOTYPE_WIDTH
        coherent = True
        tier12 = False
    else:
        tier = CellIdentityTier.RT_ONLY
        basis = CellIdentityBasis.NONE
        coherent = False
        tier12 = False
```

Update `_cell(...)` parameters to accept:

```python
        shape_status=shape_comparison.shape_status,
        shape_similarity_cosine=shape_comparison.shape_similarity_cosine,
        shape_reference_basis=shape_comparison.shape_reference_basis,
        shape_reference_candidate_id=shape_comparison.shape_reference_candidate_id,
        shape_fallback_used=shape_comparison.shape_fallback_used,
        shape_audit_status=shape_comparison.shape_audit_status,
        width_status=width_assessment.width_status,
        width_ratio_to_prototype=width_assessment.width_ratio_to_prototype,
```

For blocked and data-quality cells, keep existing `not_assessed` shape/width values by passing explicit defaults.
Keep `non_rt_identity_result` tied to fragment constraint matching. A tier 2
shape pass or tier 3 width pass must not overwrite a fragment `fail` into
`pass`; the support basis is carried by `cell_identity_basis`.

Replace `_non_tier1_fallback_key` so the sample selector does not discard tier 2
or tier 3 evidence in favor of a closer RT-only candidate:

```python
def _non_tier1_fallback_key(
    cell: CellEvidenceResult,
) -> tuple[int, int, float, str]:
    tier_rank = {
        CellIdentityTier.TIER2.value: 0,
        CellIdentityTier.TIER3.value: 1,
    }.get(_enum_value(cell.cell_identity_tier), 2)
    rt_pass_penalty = (
        0
        if _enum_value(cell.rt_gate_status) == RtGateStatus.PASS.value
        else 1
    )
    rt_delta = _abs_or_inf(cell.rt_delta_center_sec)
    return (tier_rank, rt_pass_penalty, rt_delta, cell.candidate_id)
```

- [ ] **Step 5: Preserve string enum public input handling**

Add this helper near the bottom of `cell_evidence.py` if it is not already present:

```python
def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
```

Where the new code compares enum values from public dataclasses, compare against enum values through this helper or coerce to schema enums at the boundary. Do not use `is` against public string payloads.

- [ ] **Step 6: Run Task 4 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_cell_evidence.py tests/alignment/identity_coherence/test_shape.py tests/alignment/identity_coherence/test_width.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```powershell
git add xic_extractor/alignment/identity_coherence/cell_evidence.py tests/alignment/identity_coherence/test_cell_evidence.py
git commit -m "feat: classify shape and width identity cells"
```

---

## Task 5: Add Weak-Basis Decision Rules And Row Summaries

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence/decision.py`
- Test: `tests/alignment/identity_coherence/test_identity_decision.py`

- [ ] **Step 1: Add failing weak-basis tests**

Append tests to `tests/alignment/identity_coherence/test_identity_decision.py`.
Merge these imports into existing import blocks:

```python
from xic_extractor.alignment.identity_coherence.models import PrototypeWidthResult
from xic_extractor.alignment.identity_coherence.schema import WidthStatus
```

```python
def _cell(
    sample_id: str,
    *,
    tier: CellIdentityTier,
    coherent: bool,
    tier12: bool,
    shape_fallback_used: bool = False,
    shape_reference_basis: ShapeReferenceBasis = ShapeReferenceBasis.NONE,
    shape_reference_candidate_id: str = "",
) -> CellEvidenceResult:
    cell = _tier1_cell(sample_id)
    basis = CellIdentityBasis.RT_FRAGMENT_SUPPORT
    if tier == CellIdentityTier.TIER2:
        basis = CellIdentityBasis.RT_SHAPE_SIMILARITY
    elif tier == CellIdentityTier.TIER3:
        basis = CellIdentityBasis.RT_PROTOTYPE_WIDTH
    return replace(
        cell,
        cell_identity_tier=tier,
        cell_identity_basis=basis,
        shape_fallback_used=shape_fallback_used,
        shape_reference_basis=shape_reference_basis,
        shape_reference_candidate_id=shape_reference_candidate_id,
        coherent_count_contribution=coherent,
        tier12_count_contribution=tier12,
    )


def test_decision_marks_tier3_only_support_review_only():
    seed_gate = _seed_result()
    cells = (
        _cell("S2", tier=CellIdentityTier.TIER3, coherent=True, tier12=False),
        _cell("S3", tier=CellIdentityTier.TIER3, coherent=True, tier12=False),
    )

    summary = summarize_identity_decision(
        seed_gate,
        cells,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        assessed_sample_count=3,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_WEAK_BASIS_TIER3_ONLY
    assert summary.weak_basis_reason is WeakBasisReason.TIER3_ONLY
    assert summary.total_coherent_sample_count == 3
    assert summary.tier12_non_seed_identity_sample_count == 0


def test_decision_marks_single_tier12_plus_tier3_review_only():
    seed_gate = _seed_result()
    cells = (
        _cell("S2", tier=CellIdentityTier.TIER2, coherent=True, tier12=True),
        _cell("S3", tier=CellIdentityTier.TIER3, coherent=True, tier12=False),
    )

    summary = summarize_identity_decision(
        seed_gate,
        cells,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        assessed_sample_count=3,
    )

    assert (
        summary.decision
        is IdentityDecision.REVIEW_ONLY_WEAK_BASIS_SINGLE_TIER12_PLUS_TIER3
    )
    assert summary.weak_basis_reason is WeakBasisReason.SINGLE_TIER12_PLUS_TIER3
    assert summary.total_coherent_sample_count == 3
    assert summary.tier12_non_seed_identity_sample_count == 1


def test_decision_marks_seed_shape_fallback_only_review_only():
    seed_gate = _seed_result()
    cells = (
        _cell(
            "S2",
            tier=CellIdentityTier.TIER2,
            coherent=True,
            tier12=True,
            shape_fallback_used=True,
        ),
        _cell(
            "S3",
            tier=CellIdentityTier.TIER2,
            coherent=True,
            tier12=True,
            shape_fallback_used=True,
        ),
    )

    summary = summarize_identity_decision(
        seed_gate,
        cells,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        assessed_sample_count=3,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT
    assert summary.weak_basis_reason is WeakBasisReason.SEED_SHAPE_FALLBACK_ONLY


def test_decision_allows_seed_fallback_when_supported_by_prototype_shape():
    seed_gate = _seed_result()
    cells = (
        _cell(
            "S2",
            tier=CellIdentityTier.TIER2,
            coherent=True,
            tier12=True,
            shape_reference_basis=ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        ),
        _cell(
            "S3",
            tier=CellIdentityTier.TIER2,
            coherent=True,
            tier12=True,
            shape_fallback_used=True,
            shape_reference_basis=ShapeReferenceBasis.SEED_FALLBACK,
        ),
    )

    summary = summarize_identity_decision(
        seed_gate,
        cells,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        assessed_sample_count=3,
    )

    assert summary.decision is IdentityDecision.WOULD_PRIMARY
    assert summary.weak_basis_reason is WeakBasisReason.NONE


def test_decision_records_row_shape_reference_and_prototype_width():
    seed_gate = _seed_result()
    cells = (
        _cell(
            "S2",
            tier=CellIdentityTier.TIER2,
            coherent=True,
            tier12=True,
            shape_reference_basis=ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
            shape_reference_candidate_id="REF",
        ),
        _cell("S3", tier=CellIdentityTier.TIER1, coherent=True, tier12=True),
    )
    prototype_width = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.2,
        candidate_count=3,
        non_seed_candidate_count=2,
        width_candidate_ids=("REF", "S2", "S3"),
    )

    summary = summarize_identity_decision(
        seed_gate,
        cells,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="FAM1",
        assessed_sample_count=3,
        prototype_width=prototype_width,
    )

    assert summary.shape_reference_basis is ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    assert summary.shape_reference_candidate_id == "REF"
    assert summary.prototype_width_sec == 6.2
```

The helper intentionally wraps existing `_tier1_cell()` with `dataclasses.replace`
so this task does not duplicate the large `CellEvidenceResult` fixture.

- [ ] **Step 2: Run Task 5 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_identity_decision.py -q
```

Expected: FAIL because weak-basis decisions are not implemented.

- [ ] **Step 3: Update decision branching**

First extend the public function signature so row-level prototype width can be recorded without deriving it from flattened per-cell ratios:

```python
def summarize_identity_decision(
    seed_gate: SeedGateResult,
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
    prototype_width: PrototypeWidthResult | None = None,
) -> IdentityDecisionSummary:
```

Add `PrototypeWidthResult` to imports from `.models`. Give `_summary(...)` a default
`prototype_width: PrototypeWidthResult | None = None`, and pass
`prototype_width=prototype_width` from the coherent-seed path. The seed-gate-failed
path may rely on the `_summary` default because no non-seed row support is allowed
when the seed itself is not coherent.

In `_decision_for_coherent_seed`, calculate:

```python
    tier3 = _tier3_count(cells)
    seed_fallback_tier2 = _tier2_seed_fallback_count(cells)
    prototype_tier2 = _tier2_prototype_shape_count(cells)
```

Before the would-primary branch, add:

```python
    if non_seed_coherent >= config.promotion.min_non_seed_coherent_samples:
        if tier12 == 0 and tier3 > 0:
            return IdentityDecision.REVIEW_ONLY_WEAK_BASIS_TIER3_ONLY
        if tier12 == 1 and tier3 > 0:
            return IdentityDecision.REVIEW_ONLY_WEAK_BASIS_SINGLE_TIER12_PLUS_TIER3
        if tier12 >= config.promotion.min_non_seed_tier12_identity_samples:
            if seed_fallback_tier2 == tier12 and prototype_tier2 == 0 and _tier1_count(cells) == 0:
                return IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT
```

Keep would-primary rule after these weak-basis guards.

Add helper:

```python
def _tier2_prototype_shape_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(
        1
        for cell in cells
        if cell.cell_identity_tier == CellIdentityTier.TIER2
        and not cell.shape_fallback_used
    )
```

- [ ] **Step 4: Update weak-basis reason helper**

Replace `_weak_basis_reason` with:

```python
def _weak_basis_reason(
    cells: tuple[CellEvidenceResult, ...],
    decision: IdentityDecision,
) -> WeakBasisReason:
    decision_value = _enum_value(decision)
    if decision_value == IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT.value:
        return WeakBasisReason.RT_ONLY
    if decision_value == IdentityDecision.REVIEW_ONLY_WEAK_BASIS_TIER3_ONLY.value:
        return WeakBasisReason.TIER3_ONLY
    if (
        decision_value
        == IdentityDecision.REVIEW_ONLY_WEAK_BASIS_SINGLE_TIER12_PLUS_TIER3.value
    ):
        return WeakBasisReason.SINGLE_TIER12_PLUS_TIER3
    if (
        decision_value == IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT.value
        and _tier12_count(cells) > 0
        and _tier2_seed_fallback_count(cells) == _tier12_count(cells)
        and _tier1_count(cells) == 0
        and _tier2_prototype_shape_count(cells) == 0
    ):
        return WeakBasisReason.SEED_SHAPE_FALLBACK_ONLY
    return WeakBasisReason.NONE
```

Add `_enum_value` to `decision.py` if the existing helper is not already present:

```python
def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
```

- [ ] **Step 5: Summarize row-level shape and width**

Extend `_summary(...)` with:

```python
    prototype_width: PrototypeWidthResult | None,
```

Replace summary fields currently hard-coded to `ShapeReferenceBasis.NONE`, empty candidate ID, and `None` prototype width with derived values:

```python
        shape_reference_basis=_row_shape_reference_basis(cells),
        shape_reference_candidate_id=_row_shape_reference_candidate_id(cells),
        prototype_width_sec=(
            prototype_width.prototype_width_sec
            if prototype_width is not None
            else None
        ),
```

Add helpers:

```python
def _row_shape_reference_basis(cells: tuple[CellEvidenceResult, ...]) -> ShapeReferenceBasis:
    tier2_cells = tuple(
        cell
        for cell in cells
        if _enum_value(cell.cell_identity_tier) == CellIdentityTier.TIER2.value
    )
    if not tier2_cells:
        return ShapeReferenceBasis.NONE
    preferred = sorted(
        tier2_cells,
        key=lambda cell: (
            1 if cell.shape_reference_basis == ShapeReferenceBasis.SEED_FALLBACK else 0,
            cell.shape_reference_candidate_id,
        ),
    )
    return preferred[0].shape_reference_basis


def _row_shape_reference_candidate_id(cells: tuple[CellEvidenceResult, ...]) -> str:
    tier2_cells = tuple(
        cell
        for cell in cells
        if _enum_value(cell.cell_identity_tier) == CellIdentityTier.TIER2.value
    )
    if not tier2_cells:
        return ""
    preferred = sorted(
        tier2_cells,
        key=lambda cell: (
            1 if cell.shape_reference_basis == ShapeReferenceBasis.SEED_FALLBACK else 0,
            cell.shape_reference_candidate_id,
        ),
    )
    return preferred[0].shape_reference_candidate_id
```

Do not infer `prototype_width_sec` from per-cell ratios. The field is populated only from the optional row-level `PrototypeWidthResult`; otherwise it stays `None`. This avoids deriving a row-level prototype from incomplete per-cell flattened audit data.

- [ ] **Step 6: Run Task 5 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_identity_decision.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```powershell
git add xic_extractor/alignment/identity_coherence/decision.py tests/alignment/identity_coherence/test_identity_decision.py
git commit -m "feat: add identity coherence weak basis decisions"
```

---

## Task 6: Add Pure Row-Level Domain Orchestration

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/row_evaluator.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Test: `tests/alignment/identity_coherence/test_row_evaluator.py`
- Test: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Create failing row orchestration tests**

Create `tests/alignment/identity_coherence/test_row_evaluator.py`.

```python
from __future__ import annotations

from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.row_evaluator import (
    evaluate_identity_coherence_row,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellIdentityTier,
    EvidenceStage,
    IdentityDecision,
    ShapeReferenceBasis,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


class SeedLike:
    candidate_id = "SEED"
    sample_name = "S1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"
    best_seed_rt = 7.80
    ms1_scan_support_score = 0.80


class OwnerLike:
    owner_apex_rt = 7.80
    owner_peak_start_rt = 7.75
    owner_peak_end_rt = 7.85
    owner_area = 1000.0
    owner_height = 200.0


def _request():
    return build_identity_coherence_request(
        SeedLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _seed_evidence() -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="SEED",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.80,
        ms1_scan_support_score=0.80,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )


def _trace() -> CandidateTrace:
    return CandidateTrace(
        rt_min=(7.75, 7.7625, 7.775, 7.7875, 7.80, 7.8125, 7.825, 7.8375, 7.85),
        intensity=(0.0, 1.0, 3.0, 7.0, 10.0, 7.0, 3.0, 1.0, 0.0),
    )


def _candidate(
    candidate_id: str,
    sample_id: str,
    *,
    fragment_tags: tuple[str, ...] = ("other",),
    precursor_mz: float = 500.5,
    product_mz: float = 384.5,
    loss_da: float = 116.5,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            cid_observed_loss_da=loss_da,
            fragment_tags=fragment_tags,
            best_seed_rt=7.80,
            ms1_scan_support_score=0.70,
            evidence_stage=EvidenceStage.PRE_BACKFILL,
        ),
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        area=100.0,
        height=20.0,
        point_count=9,
        trace=_trace(),
    )


def test_evaluate_identity_coherence_row_promotes_two_prototype_shape_cells():
    request = _request()
    seed_evidence = _seed_evidence()
    seed_gate = evaluate_seed_gate(request, seed_evidence, OwnerLike())
    seed_candidate = _candidate(
        "SEED",
        "S1",
        fragment_tags=("MeR", "dR"),
        precursor_mz=500.0,
        product_mz=384.0,
        loss_da=116.0,
    )

    result = evaluate_identity_coherence_row(
        seed_gate,
        seed_evidence,
        seed_candidate,
        (
            _candidate("A", "S2"),
            _candidate("B", "S3"),
            _candidate("C", "S4"),
        ),
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="FAM1",
        assessed_sample_count=4,
    )

    assert result.decision.decision is IdentityDecision.WOULD_PRIMARY
    assert result.decision.tier2_shape_supported_sample_count >= 2
    assert result.decision.tier12_non_seed_identity_sample_count >= 2
    assert result.shape_reference.shape_reference_basis in {
        ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        ShapeReferenceBasis.TIER1_SUPPORTED_MEDOID,
    }
    assert result.shape_reference.shape_reference_candidate_id != "SEED"
    assert all(
        cell.cell_identity_tier in {CellIdentityTier.TIER2, CellIdentityTier.TIER3}
        for cell in result.cells
    )
```

- [ ] **Step 2: Run Task 6 tests and verify they fail**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_row_evaluator.py -q
```

Expected: FAIL because `row_evaluator.py` does not exist.

- [ ] **Step 3: Implement `row_evaluator.py`**

Create `xic_extractor/alignment/identity_coherence/row_evaluator.py`.

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .candidate_matcher import match_identity_constraints_to_candidate
from .cell_evidence import select_cell_evidence_for_sample
from .decision import summarize_identity_decision
from .models import (
    CellCandidateEvidence,
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    PrototypeWidthResult,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
    ShapeReferenceResult,
)
from .rt_center import estimate_rt_center
from .schema import CellIdentityTier, EvidenceStage, RequestCandidateIdentityStatus
from .shape import create_seed_shape_reference, estimate_shape_reference
from .width import estimate_prototype_width


@dataclass(frozen=True)
class IdentityCoherenceRowResult:
    center: RtCenterResult
    prototype_width: PrototypeWidthResult
    shape_reference: ShapeReferenceResult
    cells: tuple[CellEvidenceResult, ...]
    decision: IdentityDecisionSummary


def evaluate_identity_coherence_row(
    seed_gate: SeedGateResult,
    seed_evidence: SeedCandidateEvidence,
    seed_candidate: CellCandidateEvidence | None,
    non_seed_candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
) -> IdentityCoherenceRowResult:
    center = estimate_rt_center(seed_evidence, non_seed_candidates, config)
    all_width_candidates = (
        (seed_candidate,) + non_seed_candidates
        if seed_candidate is not None
        else non_seed_candidates
    )
    prototype_width = estimate_prototype_width(
        all_width_candidates,
        config,
        seed_sample_id=seed_gate.resolved_request.seed_sample,
        seed_rt_min=float(seed_evidence.best_seed_rt),
        center_rt_min=center.center_rt_min,
    )

    tier_by_candidate_id = _candidate_tier1_support_map(
        seed_gate,
        non_seed_candidates,
        center,
        config,
    )
    shape_reference = estimate_shape_reference(
        non_seed_candidates,
        config,
        seed_sample_id=seed_gate.resolved_request.seed_sample,
        tier_by_candidate_id=tier_by_candidate_id,
        center_rt_min=center.center_rt_min,
    )
    if not shape_reference.normalized_intensity and seed_candidate is not None:
        shape_reference = create_seed_shape_reference(seed_candidate, config)

    cells = _evaluate_cells(
        seed_gate,
        non_seed_candidates,
        center,
        config,
        identity_family_id=identity_family_id,
        shape_reference=shape_reference,
        prototype_width=prototype_width,
    )
    decision = summarize_identity_decision(
        seed_gate,
        cells,
        center,
        config,
        identity_family_id=identity_family_id,
        assessed_sample_count=assessed_sample_count,
        prototype_width=prototype_width,
    )
    return IdentityCoherenceRowResult(
        center=center,
        prototype_width=prototype_width,
        shape_reference=shape_reference,
        cells=cells,
        decision=decision,
    )


def _evaluate_cells(
    seed_gate: SeedGateResult,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    shape_reference: ShapeReferenceResult | None,
    prototype_width: PrototypeWidthResult | None,
) -> tuple[CellEvidenceResult, ...]:
    grouped = _group_by_sample(candidates)
    return tuple(
        select_cell_evidence_for_sample(
            seed_gate.resolved_request,
            tuple(sample_candidates),
            center,
            config,
            identity_family_id=identity_family_id,
            shape_reference=shape_reference,
            prototype_width=prototype_width,
        )
        for _, sample_candidates in sorted(grouped.items())
    )


def _group_by_sample(
    candidates: tuple[CellCandidateEvidence, ...],
) -> dict[str, list[CellCandidateEvidence]]:
    grouped: dict[str, list[CellCandidateEvidence]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.sample_id].append(candidate)
    return dict(grouped)


def _candidate_tier1_support_map(
    seed_gate: SeedGateResult,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> dict[str, CellIdentityTier]:
    return {
        candidate.candidate_evidence.candidate_id: CellIdentityTier.TIER1
        for candidate in candidates
        if _candidate_has_tier1_support(
            seed_gate,
            candidate,
            center,
            config,
        )
    }


def _candidate_has_tier1_support(
    seed_gate: SeedGateResult,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> bool:
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    rt_delta_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    if abs(rt_delta_sec) > config.rt.preferred_rt_sec:
        return False
    match = match_identity_constraints_to_candidate(
        seed_gate.resolved_request,
        candidate.candidate_evidence,
    )
    return (
        _enum_value(match.request_candidate_identity_status)
        == RequestCandidateIdentityStatus.MATCH.value
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
```

- [ ] **Step 4: Export row evaluator**

In `__init__.py`, import and export:

```python
from .row_evaluator import IdentityCoherenceRowResult, evaluate_identity_coherence_row
```

Add both names to `__all__`.

Extend `test_identity_coherence_facade_exports_shape_width_models_and_functions`:

```python
        "IdentityCoherenceRowResult",
        "evaluate_identity_coherence_row",
```

- [ ] **Step 5: Run Task 6 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_row_evaluator.py tests/alignment/identity_coherence/test_schema_contract.py -q
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```powershell
git add xic_extractor/alignment/identity_coherence/row_evaluator.py xic_extractor/alignment/identity_coherence/__init__.py tests/alignment/identity_coherence/test_row_evaluator.py tests/alignment/identity_coherence/test_schema_contract.py
git commit -m "feat: add identity coherence row evaluator"
```

---

## Task 7: Run End-To-End Domain Verification

**Files:**
- No production edits unless prior tasks revealed a failing contract.
- Test: `tests/alignment/identity_coherence/*`

- [ ] **Step 1: Run focused identity coherence tests**

```powershell
uv run pytest tests/alignment/identity_coherence -q
```

Expected: all identity coherence tests pass.

- [ ] **Step 2: Run repository short full suite**

```powershell
uv run pytest --tb=short -q
```

Expected: all tests pass. If unrelated legacy tests fail, capture exact failing test names and error messages before deciding whether they are unrelated.

- [ ] **Step 3: Run lint**

```powershell
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: PASS.

- [ ] **Step 4: Run import smoke**

```powershell
uv run python -c "import xic_extractor.alignment.identity_coherence as ic; print(ic.ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID.value)"
```

Expected output:

```text
morphology_rt_medoid
```

- [ ] **Step 5: Check scope guard**

Run these searches:

```powershell
rg -n "from xic_extractor\.(raw_reader|alignment\.(backfill|owner_backfill|ms1_index_source))|import xic_extractor\.(raw_reader|alignment\.(backfill|owner_backfill|ms1_index_source))|ReadRaw|Thermo" xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
rg -n "openpyxl|Workbook|worksheet|to_excel|argparse|click|csv_to_excel|tsv_writer|xlsx_writer" xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
rg -n "blank|QC|qc|normalization|statistics|final_matrix|matrix_filter|downstream_filter" xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected:

- no imports of RAW readers, `owner_backfill`, workbook, CLI, or writer surfaces;
- no new downstream blank/QC filtering, normalization, statistics, or final-matrix logic;
- the only acceptable matches are schema enum names or test strings that do not
  introduce dependencies or downstream filtering behavior. If a command returns
  matches, inspect each line and document why it is allowed before finishing.

- [ ] **Step 6: Check whitespace and worktree state**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --check
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
```

Expected:

- no whitespace errors;
- clean worktree after all implementation commits. The plan file should already be committed before worker execution starts.

---

## Self-Review Checklist

- [ ] Plan starts after the tier1 cell-evidence slice and does not repeat seed gate or tier1 matcher work.
- [ ] No task imports RAW readers, MS1 index sources, Backfill, workbook, CLI, or TSV writers.
- [ ] Shape and width code operates only on supplied `CandidateTrace` / `CellCandidateEvidence` domain payloads.
- [ ] Shape uses each candidate's own peak boundaries and boundary-normalized linear resampling.
- [ ] Shape pass requires width sanity pass.
- [ ] Tier 1 cells remain tier 1 even when width sanity fails.
- [ ] Tier 3 can increase total coherent count but never tier12 count.
- [ ] Tier 2 and tier 3 cells do not overwrite fragment-level
      `non_rt_identity_result`.
- [ ] Non-tier1 selector fallback prefers tier 2, then tier 3, then RT-only.
- [ ] Seed-shape-fallback-only support is Review-only.
- [ ] `morphology_rt_medoid` support is visible in cell evidence and decision summary.
- [ ] Prototype shape medoids exclude the seed sample.
- [ ] Prototype width excludes the seed sample and records non-seed candidate
      count as audit context.
- [ ] A pure row-level evaluator proves center -> width -> shape -> cells ->
      decision works without any retrieval or writer code.
- [ ] All new public models/functions are exported from the facade and covered by schema/facade tests.

## Implementation Order

1. Trace/config models.
2. Width domain logic.
3. Shape domain logic.
4. Cell evidence integration.
5. Weak-basis decisions.
6. Pure row-level domain orchestration.
7. Verification.

Do not invert steps 2 and 3 into cell-evidence integration first. Tier 2 shape depends on width sanity, so width must exist before the integrated tier classification.

## Review Notes

Subagent review ran with devex and CEO/founder perspectives. Engineering review
subagent did not complete before timeout and was shut down; the main thread ran a
targeted engineering self-review on the same concerns.

Integrated findings:

- Added a required worktree root so workers do not modify the parent checkout.
- Added RT eligibility to width and shape prototype pools.
- Excluded the seed sample from prototype-medoid shape selection; seed shape is
  allowed only through explicit `seed_fallback`.
- Excluded the seed sample from prototype-width reference construction as well,
  and documented `non_seed_candidate_count` as audit context.
- Updated selector fallback ordering so tier 2 and tier 3 evidence cannot be
  discarded in favor of closer RT-only candidates.
- Kept `non_rt_identity_result` tied to fragment constraint matching; shape and
  width support are carried by `cell_identity_basis` and their own fields.
- Replaced the row evaluator's preliminary full cell pass with a lightweight
  candidate-level tier1 support map for shape-medoid tie-breaks.
- Moved public enum/string handling into width, shape, and cell-evidence snippets
  instead of leaving it as a late reminder.
- Added a pure row-level domain evaluator task so the prototype proves center ->
  width -> shape -> cells -> decision composition without retrieval or writers.
- Tightened scope guard searches to avoid noisy `xic` / `.tsv` false positives
  while still checking RAW, Backfill, writer, downstream filtering,
  normalization, and statistics boundaries.
