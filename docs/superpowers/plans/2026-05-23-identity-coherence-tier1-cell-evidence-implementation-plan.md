# Identity Coherence Tier 1 Cell Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the next identity-coherence slice after seed gate: RT center estimation, non-seed tier 1 diagnostic-fragment cell evidence, and tier1-only decision aggregation.

**Architecture:** This slice stays inside `xic_extractor.alignment.identity_coherence`. It consumes already-normalized `IdentityCoherenceRequest`, `SeedGateResult`, `SeedCandidateEvidence`, and synthetic pre-retrieved non-seed candidate evidence; it does not perform RAW/XIC retrieval, Backfill, TSV writing, controls execution, workbook rendering, or CLI wiring. Later slices can add prototype shape, width fallback, real retrieval adapters, and writers on top of these domain models.

**Tech Stack:** Python dataclasses, `StrEnum`, pytest, ruff, existing `identity_coherence` package.

---

## Preflight

Run from:

```powershell
Set-Location C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
```

Expected: clean worktree before starting. This plan file itself must be
committed before implementation starts; do not start worker execution from an
untracked plan file. If dirty, stop and classify unrelated changes before
editing.

Authoritative inputs:

- `docs/superpowers/specs/2026-05-22-untargeted-identity-coherence-core-spec.md`
- `docs/superpowers/specs/2026-05-22-untargeted-identity-coherence-implementation-contract.md`
- `docs/superpowers/plans/2026-05-23-identity-coherence-seed-gate-implementation-plan.md`

This plan starts after commit `0b50359 fix: harden identity coherence seed gate`.

## Scope

In scope:

- Typed `IdentityCoherenceConfig` with nested groups.
- Cell/decision enum constants needed by frozen output schemas.
- Synthetic `CellCandidateEvidence` and `CellEvidenceResult` domain models.
- Median/drift RT center estimation from seed RT plus eligible morphology-complete
  non-seed candidates.
- Firewall-safe RT center candidate eligibility: center candidates must be
  pre-Backfill, non-blocked, non-duplicate, and owner-clean enough to avoid
  indirect Backfill/downstream influence on promotion.
- RT gate calculation in seconds while storing candidate RT values in minutes.
- A separate non-seed identity-constraint matcher that reuses mass/tag logic
  without requiring the non-seed candidate id to equal the seed candidate id.
- Tier 1 non-seed diagnostic fragment support using the identity-constraint
  matcher, including same-sample candidate tie-breaks and ambiguous no-count
  behavior.
- Tier1-only row decision aggregation and count invariants.
- Row-level decision summary fields needed by the frozen decision schema and
  firewall audit, without adding TSV writers in this slice.
- Tests for schema stability, center rules, cell evidence, and promotion rules.

Out of scope:

- RAW/XIC retrieval and broad `max_rt_sec` extraction adapter.
- Prototype-medoid shape similarity.
- Seed-shape fallback.
- Prototype-width tier 3 fallback.
- Tier2/tier3 weak-basis decision semantics. This slice may keep future-facing
  counters/enums for schema parity, but only tier1 and RT-only logic can affect
  decisions.
- Mixed-center clustering/spread policy beyond the median drift guard. This must
  be implemented before any real retrieval adapter can call this domain slice on
  broad candidate pools.
- Frozen TSV writers.
- `summary.md` rendering.
- controls/decoy execution.
- process-mode orchestration and CLI flags.
- Backfill or production alignment behavior changes.

Hard scope guard:

- Allowed production write paths are limited to
  `xic_extractor/alignment/identity_coherence/`.
- Allowed test write paths are limited to
  `tests/alignment/identity_coherence/`.
- Do not modify RAW/XIC retrieval modules, including
  `xic_extractor/raw_reader.py`, `xic_extractor/alignment/raw_sources.py`,
  `xic_extractor/alignment/process_backend.py`,
  `xic_extractor/alignment/ms1_index_source.py`, or any extraction backend.
- Do not modify Backfill or production alignment modules, including
  `xic_extractor/alignment/backfill.py`,
  `xic_extractor/alignment/owner_backfill.py`,
  `xic_extractor/alignment/ownership.py`,
  `xic_extractor/alignment/pipeline.py`, or downstream final-matrix filters.
- Do not modify TSV/workbook/report/CLI surfaces, including
  `xic_extractor/alignment/tsv_writer.py`, `scripts/`, workbook builders, or
  HTML/report renderers.
- New identity-coherence domain modules must not import RAW readers, raw source
  adapters, extraction backends, Backfill modules, TSV writers, CLI scripts,
  workbook builders, or report renderers. They consume already-normalized,
  pre-retrieved evidence objects only.

## File Responsibilities

- Modify `xic_extractor/alignment/identity_coherence/schema.py`
  - Own stable enum values for decisions and cell-evidence categorical fields.
- Modify `xic_extractor/alignment/identity_coherence/models.py`
  - Own config dataclasses and new result/evidence dataclasses.
- Create `xic_extractor/alignment/identity_coherence/rt_center.py`
  - Own seed-anchored and recentered RT center logic.
- Create `xic_extractor/alignment/identity_coherence/cell_evidence.py`
  - Own one non-seed sample candidate-to-cell assessment plus same-sample
    candidate tie-break and ambiguity handling.
- Modify `xic_extractor/alignment/identity_coherence/candidate_matcher.py`
  - Keep seed join matching strict while exposing non-seed identity-constraint
    matching for tier 1 cells.
- Create `xic_extractor/alignment/identity_coherence/decision.py`
  - Own row-level tier1-only promotion aggregation.
- Modify `xic_extractor/alignment/identity_coherence/__init__.py`
  - Export stable public domain surface only.
- Modify `tests/alignment/identity_coherence/test_schema_contract.py`
  - Assert enum and facade stability.
- Create `tests/alignment/identity_coherence/test_rt_center.py`
  - Test RT center rules.
- Create `tests/alignment/identity_coherence/test_cell_evidence.py`
  - Test tier 1 cell assessment.
- Modify `tests/alignment/identity_coherence/test_candidate_matcher.py`
  - Verify seed join matching stays strict and non-seed identity matching allows
    different candidate ids.
- Create `tests/alignment/identity_coherence/test_identity_decision.py`
  - Test count and promotion invariants.

## Representation Choice For RT-Failed Cells

The frozen `cell_identity_tier` enum does not include `none`. In this slice:

- `cell_identity_tier = rt_only` means "not tier1, tier2, or tier3".
- `rt_gate_status` disambiguates actual RT-only support from RT failure.
- `rt_gate_status = pass` plus `non_rt_identity_result = fail` is true RT-only support.
- `rt_gate_status = fail` plus `non_rt_identity_result = pass|fail|not_assessed` is an assessed non-contributing cell, not RT-only support for `weak_basis_reason = rt_only`.
- `coherent_count_contribution = false` whenever `rt_gate_status != pass`.

Do not change frozen schemas in this slice.

---

## Task 1: Add Config, Cell, Center, And Decision Models

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/schema.py`
- Modify: `xic_extractor/alignment/identity_coherence/models.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Add failing schema enum tests**

Extend the existing schema import block in
`tests/alignment/identity_coherence/test_schema_contract.py` with these names:

```python
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    FragmentMatchStatus,
    FragmentObservationMode,
    IdentityDecision,
    NonRtIdentityResult,
    RtCenterDecision,
    RtGateStatus,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WeakBasisReason,
    WidthStatus,
```

Append these test functions to the same file:

```python

def test_cell_evidence_enum_values_are_stable_strings():
    assert {value.value for value in CellAssessmentStatus} == {
        "assessed",
        "blocked",
        "data_quality_reject",
        "not_assessed",
    }
    assert {value.value for value in CellIdentityTier} == {
        "tier1",
        "tier2",
        "tier3",
        "rt_only",
        "blocked",
        "data_quality",
    }
    assert {value.value for value in CellIdentityBasis} == {
        "rt_fragment_support",
        "rt_shape_similarity",
        "rt_prototype_width",
        "none",
    }
    assert {value.value for value in FragmentMatchStatus} == {
        "pass",
        "fail",
        "ambiguous",
        "not_assessed",
    }
    assert {value.value for value in RtGateStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in ShapeStatus} == {
        "pass",
        "fail",
        "low_points",
        "zero_signal",
        "not_assessed",
    }
    assert {value.value for value in ShapeReferenceBasis} == {
        "tier1_supported_medoid",
        "morphology_rt_medoid",
        "seed_fallback",
        "none",
    }
    assert {value.value for value in ShapeAuditStatus} == {
        "pass",
        "fail",
        "shoulder",
        "bimodal",
        "coelution",
        "saturated",
        "clipped",
        "unavailable",
        "not_assessed",
    }
    assert {value.value for value in WidthStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in BaselineAuditStatus} == {
        "pass",
        "fail",
        "unavailable",
        "not_assessed",
    }
    assert {value.value for value in AreaHeightStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in NonRtIdentityResult} == {
        "pass",
        "fail",
        "not_assessed",
        "blocked",
    }


def test_decision_and_center_enum_values_are_stable_strings():
    assert {value.value for value in IdentityDecision} == {
        "would_primary_provisional_identity_family_support",
        "review_only_seed_gate_failed",
        "review_only_rt_only_support",
        "review_only_insufficient_support",
        "review_only_center_unstable",
        "review_only_weak_basis_tier3_only",
        "review_only_weak_basis_single_tier12_plus_tier3",
        "review_only_multi_seed_requires_phase2",
        "blocked_infrastructure",
    }
    assert {value.value for value in WeakBasisReason} == {
        "none",
        "tier3_only",
        "single_tier12_plus_tier3",
        "seed_shape_fallback_only",
        "rt_only",
    }
    assert {value.value for value in RtCenterDecision} == {
        "seed_anchored",
        "recentered_stable",
        "center_unstable_review_only",
    }
```

- [ ] **Step 2: Run enum tests and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py -q
```

Expected: FAIL because the new enums do not exist.

- [ ] **Step 3: Add schema enums**

Append these enum classes to `xic_extractor/alignment/identity_coherence/schema.py` below `SeedRejectReason`:

```python
class IdentityDecision(StrEnum):
    WOULD_PRIMARY = "would_primary_provisional_identity_family_support"
    REVIEW_ONLY_SEED_GATE_FAILED = "review_only_seed_gate_failed"
    REVIEW_ONLY_RT_ONLY_SUPPORT = "review_only_rt_only_support"
    REVIEW_ONLY_INSUFFICIENT_SUPPORT = "review_only_insufficient_support"
    REVIEW_ONLY_CENTER_UNSTABLE = "review_only_center_unstable"
    REVIEW_ONLY_WEAK_BASIS_TIER3_ONLY = "review_only_weak_basis_tier3_only"
    REVIEW_ONLY_WEAK_BASIS_SINGLE_TIER12_PLUS_TIER3 = (
        "review_only_weak_basis_single_tier12_plus_tier3"
    )
    REVIEW_ONLY_MULTI_SEED_REQUIRES_PHASE2 = (
        "review_only_multi_seed_requires_phase2"
    )
    BLOCKED_INFRASTRUCTURE = "blocked_infrastructure"


class WeakBasisReason(StrEnum):
    NONE = "none"
    TIER3_ONLY = "tier3_only"
    SINGLE_TIER12_PLUS_TIER3 = "single_tier12_plus_tier3"
    SEED_SHAPE_FALLBACK_ONLY = "seed_shape_fallback_only"
    RT_ONLY = "rt_only"


class RtCenterDecision(StrEnum):
    SEED_ANCHORED = "seed_anchored"
    RECENTERED_STABLE = "recentered_stable"
    CENTER_UNSTABLE_REVIEW_ONLY = "center_unstable_review_only"


class CellAssessmentStatus(StrEnum):
    ASSESSED = "assessed"
    BLOCKED = "blocked"
    DATA_QUALITY_REJECT = "data_quality_reject"
    NOT_ASSESSED = "not_assessed"


class CellIdentityTier(StrEnum):
    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"
    RT_ONLY = "rt_only"
    BLOCKED = "blocked"
    DATA_QUALITY = "data_quality"


class CellIdentityBasis(StrEnum):
    RT_FRAGMENT_SUPPORT = "rt_fragment_support"
    RT_SHAPE_SIMILARITY = "rt_shape_similarity"
    RT_PROTOTYPE_WIDTH = "rt_prototype_width"
    NONE = "none"


class FragmentMatchStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    AMBIGUOUS = "ambiguous"
    NOT_ASSESSED = "not_assessed"


class RtGateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_ASSESSED = "not_assessed"


class ShapeStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    LOW_POINTS = "low_points"
    ZERO_SIGNAL = "zero_signal"
    NOT_ASSESSED = "not_assessed"


class ShapeReferenceBasis(StrEnum):
    TIER1_SUPPORTED_MEDOID = "tier1_supported_medoid"
    MORPHOLOGY_RT_MEDOID = "morphology_rt_medoid"
    SEED_FALLBACK = "seed_fallback"
    NONE = "none"


class ShapeAuditStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SHOULDER = "shoulder"
    BIMODAL = "bimodal"
    COELUTION = "coelution"
    SATURATED = "saturated"
    CLIPPED = "clipped"
    UNAVAILABLE = "unavailable"
    NOT_ASSESSED = "not_assessed"


class WidthStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_ASSESSED = "not_assessed"


class BaselineAuditStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"
    NOT_ASSESSED = "not_assessed"


class AreaHeightStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_ASSESSED = "not_assessed"


class NonRtIdentityResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_ASSESSED = "not_assessed"
    BLOCKED = "blocked"
```

- [ ] **Step 4: Add failing model tests**

Extend the existing models import block in
`tests/alignment/identity_coherence/test_schema_contract.py` with these names:

```python
    CellCandidateEvidence,
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    RtCenterResult,
```

Append these test functions to the same file:

```python

def test_identity_coherence_config_defaults_match_v04_review_values():
    config = IdentityCoherenceConfig()

    assert config.promotion.min_total_coherent_samples == 3
    assert config.promotion.min_non_seed_coherent_samples == 2
    assert config.promotion.min_non_seed_tier12_identity_samples == 2
    assert config.rt.max_rt_sec == 180.0
    assert config.rt.preferred_rt_sec == 60.0
    assert config.rt.seed_center_candidate_sec == 30.0
    assert config.rt.max_center_drift_sec == 30.0
    assert config.shape.min_points == 7
    assert config.shape.resample_points == 25
    assert config.shape.min_cosine == 0.85
    assert config.width.min_ratio == 0.50
    assert config.width.max_ratio == 2.00


def test_cell_and_decision_models_hold_tier1_slice_state():
    candidate = SeedCandidateEvidence(
        candidate_id="CAND-2",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.90,
        ms1_scan_support_score=0.75,
    )
    cell_candidate = CellCandidateEvidence(
        sample_id="RAW-2",
        candidate_evidence=candidate,
        apex_rt=7.90,
        peak_start_rt=7.80,
        peak_end_rt=8.00,
        area=1000.0,
        height=200.0,
        point_count=9,
    )
    center = RtCenterResult(
        center_rt_min=7.85,
        center_rt_sec=471.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=2,
        center_drift_sec=1.2,
    )
    cell = CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id=cell_candidate.sample_id,
        candidate_id=cell_candidate.candidate_evidence.candidate_id,
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=3.0,
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
    summary = IdentityDecisionSummary(
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
        decision_reason="tier1_support",
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
        center_rt_source="recentered_stable",
        center=center,
        coherent_fraction=0.375,
        infrastructure_blocked_sample_count=0,
        data_quality_reject_sample_count=0,
        forbidden_evidence_seen=False,
        forbidden_evidence_used=False,
    )

    assert cell.coherent_count_contribution is True
    assert summary.total_coherent_sample_count == 3
```

- [ ] **Step 5: Run model tests and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py -q
```

Expected: FAIL because the dataclasses do not exist.

- [ ] **Step 6: Add config and result models**

Modify imports at the top of `xic_extractor/alignment/identity_coherence/models.py`:

```python
from dataclasses import dataclass, field
```

Extend the schema import in `models.py`:

```python
from .schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    FragmentObservationMode,
    FragmentTagMatchPolicy,
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
```

Append to `models.py` after `SeedGateResult`:

```python
@dataclass(frozen=True)
class PromotionConfig:
    min_total_coherent_samples: int = 3
    min_non_seed_coherent_samples: int = 2
    min_non_seed_tier12_identity_samples: int = 2


@dataclass(frozen=True)
class RtConfig:
    max_rt_sec: float = 180.0
    preferred_rt_sec: float = 60.0
    seed_center_candidate_sec: float = 30.0
    max_center_drift_sec: float = 30.0


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
class IdentityCoherenceConfig:
    seed_gate: SeedGateConfig = field(default_factory=SeedGateConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    rt: RtConfig = field(default_factory=RtConfig)
    shape: ShapeConfig = field(default_factory=ShapeConfig)
    width: WidthConfig = field(default_factory=WidthConfig)


@dataclass(frozen=True)
class CellCandidateEvidence:
    sample_id: str
    candidate_evidence: SeedCandidateEvidence
    apex_rt: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    area: float | None
    height: float | None
    point_count: int | None = None
    owner_assignment_status: str = "primary"
    duplicate_loser: bool = False
    forbidden_evidence_seen: bool = False
    blocked_reason: str = ""
    data_quality_reason: str = ""


@dataclass(frozen=True)
class RtCenterResult:
    center_rt_min: float
    center_rt_sec: float
    center_decision: RtCenterDecision
    center_candidate_count: int
    center_drift_sec: float


@dataclass(frozen=True)
class CellEvidenceResult:
    decision_id: str
    identity_family_id: str
    sample_id: str
    candidate_id: str
    cell_assessment_status: CellAssessmentStatus
    cell_identity_tier: CellIdentityTier
    cell_identity_basis: CellIdentityBasis
    fragment_observation_mode: FragmentObservationMode
    fragment_match_status: FragmentMatchStatus
    fragment_tags_supported: tuple[str, ...]
    rt_delta_center_sec: float | None
    rt_gate_status: RtGateStatus
    shape_status: ShapeStatus
    shape_similarity_cosine: float | None
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    shape_fallback_used: bool
    shape_audit_status: ShapeAuditStatus
    width_status: WidthStatus
    width_ratio_to_prototype: float | None
    baseline_audit_status: BaselineAuditStatus
    area_height_status: AreaHeightStatus
    non_rt_identity_result: NonRtIdentityResult
    coherent_count_contribution: bool
    tier12_count_contribution: bool
    blocked_reason: str
    data_quality_reason: str
    forbidden_evidence_seen: bool


@dataclass(frozen=True)
class IdentityDecisionSummary:
    decision_id: str
    identity_family_id: str
    seed_candidate_id: str
    seed_sample: str | None
    seed_gate_class: SeedGateClass
    request_identity_completeness_status: RequestIdentityCompletenessStatus
    request_candidate_identity_status: RequestCandidateIdentityStatus
    decision: IdentityDecision
    decision_reason: str
    total_coherent_sample_count: int
    non_seed_coherent_sample_count: int
    tier12_non_seed_identity_sample_count: int
    tier1_fragment_confirmed_sample_count: int
    tier2_shape_supported_sample_count: int
    tier2_seed_shape_fallback_sample_count: int
    tier3_width_only_sample_count: int
    min_total_coherent_samples: int
    min_non_seed_coherent_samples: int
    min_non_seed_tier12_identity_samples: int
    weak_basis_reason: WeakBasisReason
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    prototype_width_sec: float | None
    center_rt_source: str
    center: RtCenterResult
    coherent_fraction: float | None
    infrastructure_blocked_sample_count: int
    data_quality_reject_sample_count: int
    forbidden_evidence_seen: bool
    forbidden_evidence_used: bool
```

This slice intentionally omits request, fragment, controls, and engineering
config groups from the broader implementation contract. Add those groups in the
slices that first consume them; do not add inert config placeholders here.

- [ ] **Step 7: Run Task 1 tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add xic_extractor/alignment/identity_coherence/schema.py xic_extractor/alignment/identity_coherence/models.py tests/alignment/identity_coherence/test_schema_contract.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: add identity coherence cell evidence models"
```

---

## Task 2: Implement RT Center Estimation

**Files:**

- Create: `xic_extractor/alignment/identity_coherence/rt_center.py`
- Create: `tests/alignment/identity_coherence/test_rt_center.py`

- [ ] **Step 1: Write failing RT center tests**

Create `tests/alignment/identity_coherence/test_rt_center.py`:

```python
from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtConfig,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.rt_center import estimate_rt_center
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    RtCenterDecision,
)


def _seed(rt: float = 7.80) -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="SEED-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=rt,
        ms1_scan_support_score=0.80,
    )


def _cell(
    candidate_id: str,
    apex_rt: float,
    *,
    start_rt: float | None = None,
    end_rt: float | None = None,
    area: float | None = 1000.0,
    height: float | None = 200.0,
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
    owner_assignment_status: str = "primary",
    duplicate_loser: bool = False,
    blocked_reason: str = "",
    data_quality_reason: str = "",
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=f"RAW-{candidate_id}",
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=500.0,
            product_mz=384.0,
            cid_observed_loss_da=116.0,
            fragment_tags=("MeR", "dR"),
            best_seed_rt=apex_rt,
            ms1_scan_support_score=0.75,
            evidence_stage=evidence_stage,
        ),
        apex_rt=apex_rt,
        peak_start_rt=apex_rt - 0.05 if start_rt is None else start_rt,
        peak_end_rt=apex_rt + 0.05 if end_rt is None else end_rt,
        area=area,
        height=height,
        point_count=9,
        owner_assignment_status=owner_assignment_status,
        duplicate_loser=duplicate_loser,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )


def test_estimate_rt_center_seed_anchored_without_center_candidates():
    center = estimate_rt_center(_seed(7.80), (), IdentityCoherenceConfig())

    assert center.center_rt_min == 7.80
    assert center.center_rt_sec == 468.0
    assert center.center_candidate_count == 0
    assert center.center_drift_sec == 0.0
    assert center.center_decision is RtCenterDecision.SEED_ANCHORED


def test_estimate_rt_center_recenters_to_median_complete_candidate_apex():
    center = estimate_rt_center(
        _seed(7.80),
        (_cell("A", 7.81), _cell("B", 7.82), _cell("C", 7.83)),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.82
    assert center.center_rt_sec == 469.2
    assert center.center_candidate_count == 3
    assert center.center_drift_sec == 1.2
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_excludes_far_or_incomplete_candidates():
    center = estimate_rt_center(
        _seed(7.80),
        (
            _cell("A", 7.81),
            _cell("FAR", 8.80),
            _cell("BAD", 7.82, area=0.0),
        ),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.81
    assert center.center_candidate_count == 1
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_excludes_forbidden_or_invalid_candidates():
    center = estimate_rt_center(
        _seed(7.80),
        (
            _cell("A", 7.81),
            _cell(
                "BACKFILL",
                7.82,
                evidence_stage=EvidenceStage.BACKFILL_ONLY,
            ),
            _cell("DUP", 7.83, duplicate_loser=True),
            _cell("BLOCKED", 7.84, blocked_reason="blocked_input"),
            _cell("BADOWNER", 7.85, owner_assignment_status="ambiguous"),
        ),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.81
    assert center.center_candidate_count == 1
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_marks_unstable_when_median_drift_exceeds_guard():
    config = IdentityCoherenceConfig(
        rt=RtConfig(
            seed_center_candidate_sec=60.0,
            max_center_drift_sec=10.0,
        ),
    )
    center = estimate_rt_center(
        _seed(7.80),
        (_cell("A", 8.00), _cell("B", 8.01), _cell("C", 8.02)),
        config,
    )

    assert center.center_rt_min == 7.80
    assert center.center_candidate_count == 3
    assert center.center_drift_sec > config.rt.max_center_drift_sec
    assert center.center_decision is RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY
```

- [ ] **Step 2: Run RT center tests and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_rt_center.py -q
```

Expected: FAIL because `rt_center.py` does not exist.

- [ ] **Step 3: Implement RT center**

Create `xic_extractor/alignment/identity_coherence/rt_center.py`:

```python
from __future__ import annotations

import math
from statistics import median

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
)
from .schema import EvidenceStage, RtCenterDecision

_CENTER_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}


def estimate_rt_center(
    seed_evidence: SeedCandidateEvidence,
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
) -> RtCenterResult:
    seed_rt_min = seed_evidence.best_seed_rt
    if not _finite_number(seed_rt_min):
        raise ValueError("seed best_seed_rt must be finite")

    center_candidates = tuple(
        candidate
        for candidate in candidates
        if _is_center_candidate(candidate, seed_rt_min, config)
    )
    if not center_candidates:
        return RtCenterResult(
            center_rt_min=float(seed_rt_min),
            center_rt_sec=float(seed_rt_min) * 60.0,
            center_decision=RtCenterDecision.SEED_ANCHORED,
            center_candidate_count=0,
            center_drift_sec=0.0,
        )

    proposed_center_rt_min = median(
        float(candidate.apex_rt) for candidate in center_candidates
    )
    center_drift_sec = abs(proposed_center_rt_min - float(seed_rt_min)) * 60.0
    if center_drift_sec > config.rt.max_center_drift_sec:
        return RtCenterResult(
            center_rt_min=float(seed_rt_min),
            center_rt_sec=float(seed_rt_min) * 60.0,
            center_decision=RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY,
            center_candidate_count=len(center_candidates),
            center_drift_sec=center_drift_sec,
        )

    return RtCenterResult(
        center_rt_min=proposed_center_rt_min,
        center_rt_sec=proposed_center_rt_min * 60.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=len(center_candidates),
        center_drift_sec=center_drift_sec,
    )


def _is_center_candidate(
    candidate: CellCandidateEvidence,
    seed_rt_min: float,
    config: IdentityCoherenceConfig,
) -> bool:
    if candidate.candidate_evidence.evidence_stage != EvidenceStage.PRE_BACKFILL:
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _CENTER_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    return abs(float(candidate.apex_rt) - seed_rt_min) * 60.0 <= (
        config.rt.seed_center_candidate_sec
    )


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
```

- [ ] **Step 4: Run RT center tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_rt_center.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add xic_extractor/alignment/identity_coherence/rt_center.py tests/alignment/identity_coherence/test_rt_center.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: estimate identity coherence rt center"
```

---

## Task 3: Implement Tier 1 Non-Seed Cell Evidence

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/candidate_matcher.py`
- Create: `xic_extractor/alignment/identity_coherence/cell_evidence.py`
- Modify: `tests/alignment/identity_coherence/test_candidate_matcher.py`
- Create: `tests/alignment/identity_coherence/test_cell_evidence.py`

- [ ] **Step 1: Add failing non-seed identity constraint matcher test**

Modify the import in `tests/alignment/identity_coherence/test_candidate_matcher.py`:

```python
from xic_extractor.alignment.identity_coherence.candidate_matcher import (
    match_identity_constraints_to_candidate,
    match_request_to_candidate,
)
```

Append this test:

```python
def test_identity_constraint_match_allows_non_seed_candidate_id():
    request = _request(CandidateLike())
    non_seed_candidate = replace(
        _evidence(CandidateLike()),
        candidate_id="NON-SEED-CAND",
    )

    seed_join_match = match_request_to_candidate(request, non_seed_candidate)
    identity_match = match_identity_constraints_to_candidate(
        request,
        non_seed_candidate,
    )

    assert seed_join_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    )
    assert identity_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
```

- [ ] **Step 2: Run matcher test and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_candidate_matcher.py::test_identity_constraint_match_allows_non_seed_candidate_id -q
```

Expected: FAIL because `match_identity_constraints_to_candidate` does not exist.

- [ ] **Step 3: Split seed-join matching from identity-constraint matching**

Refactor `xic_extractor/alignment/identity_coherence/candidate_matcher.py` so
the existing strict seed gate function remains unchanged for callers:

```python
def match_request_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
) -> CandidateIdentityMatch:
    return _match_request_to_candidate(
        request,
        candidate_evidence,
        require_seed_candidate_id_match=True,
    )


def match_identity_constraints_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
) -> CandidateIdentityMatch:
    return _match_request_to_candidate(
        request,
        candidate_evidence,
        require_seed_candidate_id_match=False,
    )


def _match_request_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
    *,
    require_seed_candidate_id_match: bool,
) -> CandidateIdentityMatch:
    if (
        request.request_identity_completeness_status
        != RequestIdentityCompletenessStatus.COMPLETE
    ):
        return _match(RequestCandidateIdentityStatus.NOT_ASSESSED)

    identity = request.identity
    if (
        identity.fragment_observation_mode
        != FragmentObservationMode.CID_NEUTRAL_LOSS
    ):
        return _match(
            RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE,
        )

    if candidate_evidence is None:
        return _match(
            RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN,
            missing_fields=("candidate",),
        )
    if (
        require_seed_candidate_id_match
        and candidate_evidence.candidate_id != request.seed_candidate_id
    ):
        return _match(
            RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN,
            missing_fields=("candidate_id",),
        )

    # Keep the existing numeric, tag, ppm, and mismatch logic below this point.
```

Move the current body below the join check into the private helper. Do not
remove the finite-positive candidate numeric checks added in commit `0b50359`.

- [ ] **Step 4: Run matcher tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_candidate_matcher.py -q
```

Expected: PASS.

- [ ] **Step 5: Write failing cell evidence tests**

Create `tests/alignment/identity_coherence/test_cell_evidence.py`:

```python
from dataclasses import replace

from xic_extractor.alignment.identity_coherence.cell_evidence import (
    evaluate_cell_evidence,
    select_cell_evidence_for_sample,
)
from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    NonRtIdentityResult,
    RtCenterDecision,
    RtGateStatus,
    ShapeStatus,
)


class SeedLike:
    candidate_id = "SEED-1"
    sample_name = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"


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


def _center(rt: float = 7.80) -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=rt,
        center_rt_sec=rt * 60.0,
        center_decision=RtCenterDecision.SEED_ANCHORED,
        center_candidate_count=0,
        center_drift_sec=0.0,
    )


def _candidate(
    *,
    candidate_id: str = "CAND-2",
    sample_id: str = "RAW-2",
    apex_rt: float = 7.82,
    product_mz: float = 384.0,
    fragment_tags: tuple[str, ...] = ("MeR", "dR"),
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
    forbidden_evidence_seen: bool = False,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=500.0,
            product_mz=product_mz,
            cid_observed_loss_da=116.0,
            fragment_tags=fragment_tags,
            best_seed_rt=apex_rt,
            ms1_scan_support_score=0.75,
            evidence_stage=evidence_stage,
        ),
        apex_rt=apex_rt,
        peak_start_rt=apex_rt - 0.05,
        peak_end_rt=apex_rt + 0.05,
        area=1000.0,
        height=200.0,
        point_count=9,
        forbidden_evidence_seen=forbidden_evidence_seen,
    )


def test_evaluate_cell_evidence_admits_tier1_fragment_support():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.ASSESSED
    assert cell.cell_identity_tier is CellIdentityTier.TIER1
    assert cell.cell_identity_basis is CellIdentityBasis.RT_FRAGMENT_SUPPORT
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.rt_gate_status is RtGateStatus.PASS
    assert cell.shape_status is ShapeStatus.NOT_ASSESSED
    assert cell.non_rt_identity_result is NonRtIdentityResult.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is True


def test_select_cell_evidence_marks_unresolved_tie_as_ambiguous_no_count():
    first = _candidate(candidate_id="NON-SEED-A")
    second = _candidate(candidate_id="NON-SEED-B")

    cell = select_cell_evidence_for_sample(
        _request(),
        (first, second),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.fragment_match_status is FragmentMatchStatus.AMBIGUOUS
    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_select_cell_evidence_tiebreaks_by_precursor_error():
    farther = _candidate(candidate_id="NON-SEED-FAR", precursor_mz=500.001)
    closer = _candidate(candidate_id="NON-SEED-CLOSE", precursor_mz=500.0001)

    cell = select_cell_evidence_for_sample(
        _request(),
        (farther, closer),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.candidate_id == "NON-SEED-CLOSE"
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.coherent_count_contribution is True


def test_evaluate_cell_evidence_keeps_rt_pass_fragment_mismatch_as_rt_only():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(product_mz=390.0),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.cell_identity_basis is CellIdentityBasis.NONE
    assert cell.fragment_match_status is FragmentMatchStatus.FAIL
    assert cell.rt_gate_status is RtGateStatus.PASS
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_does_not_count_rt_fail_even_if_fragment_matches():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(apex_rt=9.50),
        _center(7.80),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.rt_gate_status is RtGateStatus.FAIL
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.non_rt_identity_result is NonRtIdentityResult.PASS
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_blocks_backfill_only_candidate_evidence():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(evidence_stage="backfill_only"),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.BLOCKED
    assert cell.cell_identity_tier is CellIdentityTier.BLOCKED
    assert cell.non_rt_identity_result is NonRtIdentityResult.BLOCKED
    assert cell.blocked_reason == "backfill_only_evidence"
    assert cell.coherent_count_contribution is False
    assert cell.forbidden_evidence_seen is True


def test_evaluate_cell_evidence_rejects_bad_morphology_as_data_quality():
    bad = replace(_candidate(), area=0.0)
    cell = evaluate_cell_evidence(
        _request(),
        bad,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.DATA_QUALITY_REJECT
    assert cell.cell_identity_tier is CellIdentityTier.DATA_QUALITY
    assert cell.area_height_status.value == "fail"
    assert cell.data_quality_reason == "invalid_peak_morphology"
```

- [ ] **Step 6: Run cell evidence tests and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_cell_evidence.py -q
```

Expected: FAIL because `cell_evidence.py` does not exist.

- [ ] **Step 7: Implement cell evidence evaluator**

Create `xic_extractor/alignment/identity_coherence/cell_evidence.py`:

```python
from __future__ import annotations

import math
from dataclasses import replace

from .candidate_matcher import match_identity_constraints_to_candidate
from .models import (
    CandidateIdentityMatch,
    CellCandidateEvidence,
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    RtCenterResult,
)
from .schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
    RtGateStatus,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
)


def select_cell_evidence_for_sample(
    request: IdentityCoherenceRequest,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
) -> CellEvidenceResult:
    if not candidates:
        raise ValueError("at least one candidate is required for cell selection")

    assessed = tuple(
        evaluate_cell_evidence(
            request,
            candidate,
            center,
            config,
            identity_family_id=identity_family_id,
        )
        for candidate in candidates
    )
    tier1 = tuple(
        (
            candidate,
            cell,
            match_identity_constraints_to_candidate(
                request,
                candidate.candidate_evidence,
            ),
        )
        for candidate, cell in zip(candidates, assessed, strict=True)
        if cell.cell_identity_tier == CellIdentityTier.TIER1
    )
    if not tier1:
        return assessed[0]
    if len(tier1) == 1:
        return tier1[0][1]

    ranked = sorted(
        tier1,
        key=lambda item: _tier1_tie_break_key(request, item[0], center, item[2]),
    )
    first_key = _tier1_tie_break_key(
        request, ranked[0][0], center, ranked[0][2]
    )
    second_key = _tier1_tie_break_key(
        request, ranked[1][0], center, ranked[1][2]
    )
    if first_key == second_key:
        return _ambiguous_cell(ranked[0][1])
    return ranked[0][1]


def evaluate_cell_evidence(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
) -> CellEvidenceResult:
    if candidate.candidate_evidence.evidence_stage != EvidenceStage.PRE_BACKFILL:
        return _blocked_cell(
            request,
            candidate,
            identity_family_id,
            "backfill_only_evidence",
        )
    if candidate.blocked_reason:
        return _blocked_cell(
            request,
            candidate,
            identity_family_id,
            candidate.blocked_reason,
        )
    if candidate.data_quality_reason:
        return _data_quality_cell(
            request,
            candidate,
            identity_family_id,
            candidate.data_quality_reason,
        )
    if not _has_valid_morphology(candidate):
        return _data_quality_cell(
            request,
            candidate,
            identity_family_id,
            "invalid_peak_morphology",
        )

    rt_delta_center_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    rt_gate_status = (
        RtGateStatus.PASS
        if abs(rt_delta_center_sec) <= config.rt.preferred_rt_sec
        else RtGateStatus.FAIL
    )
    candidate_match = match_identity_constraints_to_candidate(
        request,
        candidate.candidate_evidence,
    )
    fragment_match_status = _fragment_match_status(candidate_match)
    non_rt_identity_result = (
        NonRtIdentityResult.PASS
        if candidate_match.request_candidate_identity_status
        == RequestCandidateIdentityStatus.MATCH
        else NonRtIdentityResult.FAIL
    )

    if (
        rt_gate_status is RtGateStatus.PASS
        and non_rt_identity_result is NonRtIdentityResult.PASS
    ):
        tier = CellIdentityTier.TIER1
        basis = CellIdentityBasis.RT_FRAGMENT_SUPPORT
        coherent = True
        tier12 = True
    else:
        tier = CellIdentityTier.RT_ONLY
        basis = CellIdentityBasis.NONE
        coherent = False
        tier12 = False

    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=tier,
        cell_identity_basis=basis,
        fragment_match_status=fragment_match_status,
        rt_delta_center_sec=rt_delta_center_sec,
        rt_gate_status=rt_gate_status,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=non_rt_identity_result,
        coherent_count_contribution=coherent,
        tier12_count_contribution=tier12,
        blocked_reason="",
        data_quality_reason="",
    )


def _blocked_cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    reason: str,
) -> CellEvidenceResult:
    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.BLOCKED,
        cell_identity_tier=CellIdentityTier.BLOCKED,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.NOT_ASSESSED,
        rt_delta_center_sec=None,
        rt_gate_status=RtGateStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.NOT_ASSESSED,
        non_rt_identity_result=NonRtIdentityResult.BLOCKED,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
        blocked_reason=reason,
        data_quality_reason="",
    )


def _data_quality_cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    reason: str,
) -> CellEvidenceResult:
    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.DATA_QUALITY_REJECT,
        cell_identity_tier=CellIdentityTier.DATA_QUALITY,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.NOT_ASSESSED,
        rt_delta_center_sec=None,
        rt_gate_status=RtGateStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.FAIL,
        non_rt_identity_result=NonRtIdentityResult.NOT_ASSESSED,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
        blocked_reason="",
        data_quality_reason=reason,
    )


def _cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    *,
    cell_assessment_status: CellAssessmentStatus,
    cell_identity_tier: CellIdentityTier,
    cell_identity_basis: CellIdentityBasis,
    fragment_match_status: FragmentMatchStatus,
    rt_delta_center_sec: float | None,
    rt_gate_status: RtGateStatus,
    area_height_status: AreaHeightStatus,
    non_rt_identity_result: NonRtIdentityResult,
    coherent_count_contribution: bool,
    tier12_count_contribution: bool,
    blocked_reason: str,
    data_quality_reason: str,
) -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id=request.decision_id,
        identity_family_id=identity_family_id,
        sample_id=candidate.sample_id,
        candidate_id=candidate.candidate_evidence.candidate_id,
        cell_assessment_status=cell_assessment_status,
        cell_identity_tier=cell_identity_tier,
        cell_identity_basis=cell_identity_basis,
        fragment_observation_mode=request.identity.fragment_observation_mode,
        fragment_match_status=fragment_match_status,
        fragment_tags_supported=candidate.candidate_evidence.fragment_tags,
        rt_delta_center_sec=rt_delta_center_sec,
        rt_gate_status=rt_gate_status,
        shape_status=ShapeStatus.NOT_ASSESSED,
        shape_similarity_cosine=None,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        shape_fallback_used=False,
        shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        width_status=WidthStatus.NOT_ASSESSED,
        width_ratio_to_prototype=None,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=area_height_status,
        non_rt_identity_result=non_rt_identity_result,
        coherent_count_contribution=coherent_count_contribution,
        tier12_count_contribution=tier12_count_contribution,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
        forbidden_evidence_seen=(
            candidate.forbidden_evidence_seen
            or candidate.candidate_evidence.evidence_stage
            != EvidenceStage.PRE_BACKFILL
        ),
    )


def _tier1_tie_break_key(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    candidate_match: CandidateIdentityMatch,
) -> tuple[float, float, float, float]:
    requested_tags = set(request.identity.fragment_tags)
    supported_tags = set(candidate_match.fragment_tags_supported)
    tag_set_penalty = 0.0 if supported_tags == requested_tags else 1.0
    rt_delta_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    return (
        tag_set_penalty,
        _abs_or_inf(candidate_match.precursor_error_ppm),
        _abs_or_inf(candidate_match.cid_observed_loss_error_ppm),
        abs(rt_delta_sec),
    )


def _ambiguous_cell(cell: CellEvidenceResult) -> CellEvidenceResult:
    return replace(
        cell,
        cell_identity_tier=CellIdentityTier.RT_ONLY,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.AMBIGUOUS,
        non_rt_identity_result=NonRtIdentityResult.FAIL,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
    )


def _abs_or_inf(value: float | None) -> float:
    return abs(value) if value is not None else math.inf


def _fragment_match_status(
    candidate_match: CandidateIdentityMatch,
) -> FragmentMatchStatus:
    if (
        candidate_match.request_candidate_identity_status
        == RequestCandidateIdentityStatus.MATCH
    ):
        return FragmentMatchStatus.PASS
    return FragmentMatchStatus.FAIL


def _has_valid_morphology(candidate: CellCandidateEvidence) -> bool:
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
```

- [ ] **Step 8: Run cell evidence tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_cell_evidence.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit Task 3**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add xic_extractor/alignment/identity_coherence/candidate_matcher.py xic_extractor/alignment/identity_coherence/cell_evidence.py tests/alignment/identity_coherence/test_candidate_matcher.py tests/alignment/identity_coherence/test_cell_evidence.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: evaluate identity coherence tier1 cells"
```

---

## Task 4: Implement Tier1-Only Decision Aggregation

**Files:**

- Create: `xic_extractor/alignment/identity_coherence/decision.py`
- Create: `tests/alignment/identity_coherence/test_identity_decision.py`

- [ ] **Step 1: Write failing decision tests**

Create `tests/alignment/identity_coherence/test_identity_decision.py`:

```python
from dataclasses import replace

from xic_extractor.alignment.identity_coherence.decision import (
    summarize_identity_decision,
)
from xic_extractor.alignment.identity_coherence.models import (
    CellEvidenceResult,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    FragmentObservationMode,
    IdentityDecision,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
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
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


class SeedLike:
    candidate_id = "SEED-1"
    sample_name = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"
    best_seed_rt = 7.80
    ms1_scan_support_score = 0.80


class OwnerLike:
    owner_apex_rt = 7.80
    owner_peak_start_rt = 7.70
    owner_peak_end_rt = 7.90
    owner_area = 1000.0
    owner_height = 200.0


def _seed_result() -> SeedGateResult:
    request = build_identity_coherence_request(
        SeedLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )
    candidate = SeedLike()
    evidence = SeedCandidateEvidence(
        candidate_id=candidate.candidate_id,
        precursor_mz=candidate.precursor_mz,
        product_mz=candidate.product_mz,
        cid_observed_loss_da=candidate.observed_neutral_loss_da,
        fragment_tags=candidate.matched_tag_names,
        best_seed_rt=candidate.best_seed_rt,
        ms1_scan_support_score=candidate.ms1_scan_support_score,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )
    return evaluate_seed_gate(request, evidence, OwnerLike())


def _center(decision=RtCenterDecision.SEED_ANCHORED) -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=7.80,
        center_rt_sec=468.0,
        center_decision=decision,
        center_candidate_count=2,
        center_drift_sec=0.0,
    )


def _tier1_cell(sample_id: str) -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id=sample_id,
        candidate_id=f"CAND-{sample_id}",
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=2.0,
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


def test_summarize_identity_decision_promotes_seed_plus_two_tier1_cells():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.WOULD_PRIMARY
    assert summary.total_coherent_sample_count == 3
    assert summary.non_seed_coherent_sample_count == 2
    assert summary.tier12_non_seed_identity_sample_count == 2
    assert summary.tier1_fragment_confirmed_sample_count == 2
    assert summary.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
    assert summary.center_rt_source == RtCenterDecision.SEED_ANCHORED.value
    assert summary.forbidden_evidence_seen is False
    assert summary.weak_basis_reason is WeakBasisReason.NONE
    assert summary.coherent_fraction == 0.375


def test_summarize_identity_decision_keeps_failed_seed_review_only():
    failed_seed = replace(
        _seed_result(),
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=SeedRejectReason.LOW_MS1_SCAN_SUPPORT,
    )
    summary = summarize_identity_decision(
        failed_seed,
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED
    assert summary.total_coherent_sample_count == 0


def test_summarize_identity_decision_blocks_center_unstable_promotion():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_CENTER_UNSTABLE
    assert summary.total_coherent_sample_count == 3


def test_summarize_identity_decision_rejects_seed_plus_one_tier1_cell():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"),),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT
    assert summary.total_coherent_sample_count == 2
    assert summary.non_seed_coherent_sample_count == 1
    assert summary.tier12_non_seed_identity_sample_count == 1


def test_summarize_identity_decision_detects_forbidden_evidence_seen():
    forbidden = replace(_tier1_cell("RAW-2"), forbidden_evidence_seen=True)
    summary = summarize_identity_decision(
        _seed_result(),
        (forbidden, _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.WOULD_PRIMARY
    assert summary.forbidden_evidence_seen is True
    assert summary.forbidden_evidence_used is False
```

- [ ] **Step 2: Run decision tests and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_identity_decision.py -q
```

Expected: FAIL because `decision.py` does not exist.

- [ ] **Step 3: Implement decision aggregation**

Create `xic_extractor/alignment/identity_coherence/decision.py`:

```python
from __future__ import annotations

from .models import (
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    RtCenterResult,
    SeedGateResult,
)
from .schema import (
    CellIdentityTier,
    IdentityDecision,
    RtCenterDecision,
    SeedGateClass,
    ShapeReferenceBasis,
    WeakBasisReason,
)


def summarize_identity_decision(
    seed_gate: SeedGateResult,
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
) -> IdentityDecisionSummary:
    if seed_gate.seed_gate_class != SeedGateClass.COHERENT_SEED:
        return _summary(
            seed_gate,
            cells,
            center,
            config,
            identity_family_id=identity_family_id,
            assessed_sample_count=assessed_sample_count,
            decision=IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED,
            decision_reason=(
                seed_gate.seed_reject_reason.value
                if seed_gate.seed_reject_reason is not None
                else "seed_gate_failed"
            ),
            weak_basis_reason=WeakBasisReason.NONE,
            include_seed=False,
        )

    decision = _decision_for_coherent_seed(cells, center, config)
    return _summary(
        seed_gate,
        cells,
        center,
        config,
        identity_family_id=identity_family_id,
        assessed_sample_count=assessed_sample_count,
        decision=decision,
        decision_reason=_decision_reason(decision),
        weak_basis_reason=_weak_basis_reason(cells, decision),
        include_seed=True,
    )


def _decision_for_coherent_seed(
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> IdentityDecision:
    if center.center_decision == RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY:
        return IdentityDecision.REVIEW_ONLY_CENTER_UNSTABLE

    non_seed_coherent = _non_seed_coherent_count(cells)
    tier12 = _tier12_count(cells)
    total = 1 + non_seed_coherent

    if (
        total >= config.promotion.min_total_coherent_samples
        and non_seed_coherent >= config.promotion.min_non_seed_coherent_samples
        and tier12 >= config.promotion.min_non_seed_tier12_identity_samples
    ):
        return IdentityDecision.WOULD_PRIMARY
    if _has_rt_only_support(cells):
        return IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT
    return IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT


def _summary(
    seed_gate: SeedGateResult,
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
    decision: IdentityDecision,
    decision_reason: str,
    weak_basis_reason: WeakBasisReason,
    include_seed: bool,
) -> IdentityDecisionSummary:
    non_seed_coherent = _non_seed_coherent_count(cells)
    total = (1 if include_seed else 0) + non_seed_coherent
    coherent_fraction = (
        total / assessed_sample_count if assessed_sample_count > 0 else None
    )
    return IdentityDecisionSummary(
        decision_id=seed_gate.resolved_request.decision_id,
        identity_family_id=identity_family_id,
        seed_candidate_id=seed_gate.resolved_request.seed_candidate_id,
        seed_sample=seed_gate.resolved_request.seed_sample,
        seed_gate_class=seed_gate.seed_gate_class,
        request_identity_completeness_status=(
            seed_gate.resolved_request.request_identity_completeness_status
        ),
        request_candidate_identity_status=(
            seed_gate.resolved_request.request_candidate_identity_status
        ),
        decision=decision,
        decision_reason=decision_reason,
        total_coherent_sample_count=total,
        non_seed_coherent_sample_count=non_seed_coherent,
        tier12_non_seed_identity_sample_count=_tier12_count(cells),
        tier1_fragment_confirmed_sample_count=_tier1_count(cells),
        tier2_shape_supported_sample_count=_tier2_shape_count(cells),
        tier2_seed_shape_fallback_sample_count=_tier2_seed_fallback_count(cells),
        tier3_width_only_sample_count=_tier3_count(cells),
        min_total_coherent_samples=config.promotion.min_total_coherent_samples,
        min_non_seed_coherent_samples=(
            config.promotion.min_non_seed_coherent_samples
        ),
        min_non_seed_tier12_identity_samples=(
            config.promotion.min_non_seed_tier12_identity_samples
        ),
        weak_basis_reason=weak_basis_reason,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        prototype_width_sec=None,
        center_rt_source=center.center_decision.value,
        center=center,
        coherent_fraction=coherent_fraction,
        infrastructure_blocked_sample_count=sum(
            1 for cell in cells if cell.blocked_reason
        ),
        data_quality_reject_sample_count=sum(
            1 for cell in cells if cell.data_quality_reason
        ),
        forbidden_evidence_seen=any(
            cell.forbidden_evidence_seen for cell in cells
        ),
        forbidden_evidence_used=False,
    )


def _decision_reason(decision: IdentityDecision) -> str:
    if decision is IdentityDecision.WOULD_PRIMARY:
        return "tier1_support"
    return decision.value


def _weak_basis_reason(
    cells: tuple[CellEvidenceResult, ...],
    decision: IdentityDecision,
) -> WeakBasisReason:
    if decision is IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT:
        return WeakBasisReason.RT_ONLY
    return WeakBasisReason.NONE


def _non_seed_coherent_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.coherent_count_contribution)


def _tier12_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.tier12_count_contribution)


def _tier1_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER1)


def _tier2_shape_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER2)


def _tier2_seed_fallback_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(
        1
        for cell in cells
        if cell.cell_identity_tier == CellIdentityTier.TIER2
        and cell.shape_fallback_used
    )


def _tier3_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER3)


def _has_rt_only_support(cells: tuple[CellEvidenceResult, ...]) -> bool:
    return any(
        cell.cell_identity_tier == CellIdentityTier.RT_ONLY
        and cell.rt_gate_status.value == "pass"
        for cell in cells
    )
```

- [ ] **Step 4: Run decision tests**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_identity_decision.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add xic_extractor/alignment/identity_coherence/decision.py tests/alignment/identity_coherence/test_identity_decision.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: summarize tier1 identity coherence decisions"
```

---

## Task 5: Export Facade And Run Contract Verification

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Add facade export assertions**

Extend `test_identity_coherence_facade_exports_stable_contract` in `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
    assert identity_coherence.CellCandidateEvidence is not None
    assert identity_coherence.CellEvidenceResult is not None
    assert identity_coherence.IdentityCoherenceConfig is not None
    assert identity_coherence.IdentityDecisionSummary is not None
    assert identity_coherence.RtCenterResult is not None
    assert identity_coherence.estimate_rt_center is not None
    assert identity_coherence.evaluate_cell_evidence is not None
    assert identity_coherence.select_cell_evidence_for_sample is not None
    assert identity_coherence.summarize_identity_decision is not None
    assert identity_coherence.match_identity_constraints_to_candidate is not None
```

- [ ] **Step 2: Run facade test and verify failure**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence/test_schema_contract.py::test_identity_coherence_facade_exports_stable_contract -q
```

Expected: FAIL until facade exports are added.

- [ ] **Step 3: Update package facade**

Modify `xic_extractor/alignment/identity_coherence/__init__.py`:

```python
from .candidate_matcher import (
    match_identity_constraints_to_candidate,
    match_request_to_candidate,
)
from .cell_evidence import evaluate_cell_evidence, select_cell_evidence_for_sample
from .decision import summarize_identity_decision
from .models import (
    CellCandidateEvidence,
    CellEvidenceResult,
    CandidateIdentityMatch,
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    IdentityDecisionSummary,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
)
from .rt_center import estimate_rt_center
```

Add these names to `__all__`:

```python
    "CellCandidateEvidence",
    "CellEvidenceResult",
    "IdentityCoherenceConfig",
    "IdentityDecisionSummary",
    "RtCenterResult",
    "estimate_rt_center",
    "evaluate_cell_evidence",
    "match_identity_constraints_to_candidate",
    "match_request_to_candidate",
    "select_cell_evidence_for_sample",
    "summarize_identity_decision",
```

- [ ] **Step 4: Run focused test suite**

Run:

```powershell
uv run pytest tests/alignment/identity_coherence -q
```

Expected: PASS.

- [ ] **Step 5: Run ruff**

Run:

```powershell
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
```

Expected: `All checks passed!`

- [ ] **Step 6: Run diff checks**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --check
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
```

Expected: no whitespace errors; only intended files dirty.

- [ ] **Step 7: Commit Task 5**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add xic_extractor/alignment/identity_coherence/__init__.py tests/alignment/identity_coherence/test_schema_contract.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "test: verify identity coherence tier1 facade"
```

---

## Final Verification

Run:

```powershell
uv run pytest tests/alignment/identity_coherence
uv run ruff check xic_extractor/alignment/identity_coherence tests/alignment/identity_coherence
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --check
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
```

Expected:

- all identity coherence tests pass;
- ruff passes;
- no whitespace errors;
- clean worktree after implementation commits. The plan file should already be
  committed before worker execution starts.

## Out Of Scope For This Plan

- Layer 2 RAW/XIC request scheduling.
- Real retrieval adapter from RAW files or alignment outputs.
- Tier 2 prototype medoid shape similarity.
- Seed-shape fallback.
- Tier 3 prototype width fallback.
- Frozen TSV writers.
- controls manifest parsing and controls output.
- `summary.md`, CLI, process-mode integration.
- Backfill, owner_backfill, final matrix, workbook, or downstream filtering.

## Self-Review Checklist

- [ ] Plan starts after seed gate and does not repeat seed-gate implementation.
- [ ] Layer 1 rejects and blocked seeds do not trigger this domain slice in normal use.
- [ ] All candidate RT values remain in minutes; all reported RT deltas use seconds.
- [ ] RT center candidates exclude Backfill/post-Backfill, blocked,
      duplicate-loser, data-quality reject, and ambiguous/unresolved owner
      evidence.
- [ ] Tier 1 uses existing request-vs-candidate matcher and pre-Backfill evidence only.
- [ ] Same-sample Tier 1 candidate ambiguity produces
      `fragment_match_status = ambiguous` and cannot increment coherent counts.
- [ ] RT-only and RT-failed cells cannot increment coherent counts.
- [ ] `forbidden_evidence_seen` is aggregated for row audit while
      `forbidden_evidence_used` stays false because this slice records seen
      forbidden evidence but does not use it for promotion.
- [ ] Would-primary requires seed plus two non-seed tier1 cells in this tier1-only slice.
- [ ] No TSV writer or CLI is added.
- [ ] No Backfill or downstream filtering behavior is changed.
