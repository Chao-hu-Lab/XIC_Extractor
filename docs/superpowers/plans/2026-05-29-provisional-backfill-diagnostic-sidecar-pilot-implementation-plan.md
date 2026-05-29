# Provisional Backfill Diagnostic Sidecar Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `diagnostic_only` machine-readable sidecar pilot that classifies retained provisional backfill rows without promoting them into `alignment_matrix.tsv`.

**Architecture:** Add a focused alignment-domain evaluator for provisional backfill candidate gate semantics, then wrap it in a diagnostic CLI that reads existing `alignment_review.tsv`, `alignment_cells.tsv`, and `alignment_matrix.tsv` artifacts. The pilot writes `alignment_production_candidate_gate.tsv` plus a small JSON summary and never mutates existing alignment outputs.

**Tech Stack:** Python 3, `csv`, `json`, `dataclasses`, `pathlib`, existing `xic_extractor.alignment.machine_decision`, existing `tools.diagnostics.diagnostic_io`, pytest, ruff.

---

## Review Gate

Two read-only subagent reviewers re-reviewed `docs/superpowers/specs/2026-05-29-provisional-backfill-production-candidate-gate-design.md` before this plan:

- `strategy-challenger`: `NO BLOCKER`; proceed only as `diagnostic_only` sidecar pilot.
- `validation-evidence-reviewer`: `NO BLOCKER`; 8RAW/85RAW support candidate-scale feasibility, not production readiness.

Hard constraints from review:

- `alignment_matrix.tsv` schema and row membership must not change.
- `production_candidate` is a sidecar status only, not a product role.
- No promotion into primary matrix without a separate promotion contract.
- Existing 8RAW/85RAW artifacts are sufficient for implementation planning; do not rerun 85RAW unless implementation changes make the artifact stale.
- Source pinning is mechanical: emitted rows include source artifact paths and SHA256 hashes.

## File Structure

Create:

- `xic_extractor/alignment/production_candidate_gate.py`
  - Pure domain evaluator and TSV row writer for the sidecar.
  - Owns candidate eligibility, Tier 2 component classification, source hashing, output columns, and summary counts.
  - Does not import CLI code, RAW readers, workbook writers, or report renderers.

- `tools/diagnostics/provisional_backfill_candidate_gate.py`
  - Thin CLI facade.
  - Reads an alignment output directory, calls the domain evaluator, writes `alignment_production_candidate_gate.tsv` and `alignment_production_candidate_gate.json`.
  - Fails clearly for missing artifacts or required columns.

- `tests/test_production_candidate_gate.py`
  - Unit tests for eligibility, exact-token review-only handling, Tier 2 support, blockers, and source hashes.

- `tests/test_provisional_backfill_candidate_gate_cli.py`
  - CLI tests for sidecar output, missing artifacts, missing columns, and matrix hash parity.

Modify:

- `tools/diagnostics/INDEX.md`
  - Register the new diagnostic entry-point under Backfill Reviews.
  - Mark it `diagnostic_only` and explicitly non-authoritative for `alignment_matrix.tsv`.

Do not modify:

- `scripts/run_alignment.py`
- `xic_extractor/alignment/output_levels.py`
- `xic_extractor/alignment/pipeline_outputs.py`
- `xic_extractor/alignment/tsv_writer.py`
- Workbook schemas

The first pilot is an explicit diagnostic CLI over existing artifacts, not a new default alignment output.

## Sidecar Contract

The sidecar file is:

```text
alignment_production_candidate_gate.tsv
```

Rows are one per `provisional_retention_candidate` family in `alignment_review.tsv`. The CLI does not emit primary rows or broad provisional rows into this sidecar, so the pilot stays scoped to the selected retention-candidate subset.

Columns:

```python
PRODUCTION_CANDIDATE_GATE_COLUMNS = (
    "feature_family_id",
    "matrix_role",
    "candidate_gate_status",
    "recommended_action",
    "evidence_tier",
    "support_components",
    "dependent_context",
    "challenge_blockers",
    "tier2_evidence_available",
    "candidate_confidence",
    "source_review_artifact",
    "source_review_sha256",
    "source_cell_artifact",
    "source_cell_sha256",
    "source_matrix_artifact",
    "source_matrix_sha256",
)
```

Allowed enum values:

```python
CandidateGateStatus = Literal[
    "production_candidate",
    "keep_provisional",
    "audit",
    "excluded",
]
CandidateRecommendedAction = Literal[
    "track_candidate",
    "keep_provisional",
    "review",
    "exclude",
]
CandidateConfidence = Literal["medium", "review", "none"]
```

Pilot thresholds:

```python
MIN_SCAN_SUPPORT_SCORE = 0.5
LOW_SCAN_SUPPORT_MAX = 0.2
MAX_ABS_RT_DELTA_SEC = 180.0
MAX_RESCUED_APEX_RT_SPAN_MIN = 0.35
```

Explicit non-provenance Tier 2 positive support components:

- Tokens supplied by a reviewed, named Tier 2 evidence source through
  `independent_tier2_support_components`, and explicitly allowlisted by the
  gate.
- Initial pilot allowlist: `validated_tier2_trace_evidence`.
- Future tokens require a reviewed spec/plan update plus an implementation
  allowlist update before they can count as positive support.
- The current artifact-only pilot does not synthesize positive support from
  owner-backfill provenance, `trace_quality=owner_backfill`, or fields derived
  from `alignment_cells.tsv`.
- Unknown or merely non-dependent tokens are ignored for promotion.

Dependent context components:

- `owner_backfill_context`
- `family_ms1_context`
- `rescued_cell_scan_support_distribution`
- `selected_boundary_local_apex_consistency`
- `rescued_cell_rt_coherence`

Challenge blockers:

- `neighboring_interference_challenge`
- `low_assessable_coverage_challenge`
- `selected_boundary_local_apex_inconsistency`
- `missing_positive_tier2_support`
- `not_retention_candidate`

`production_candidate` requires at least one allowlisted explicit non-provenance
Tier 2 positive support component from a named source and no challenge blockers.
Current 8RAW/85RAW artifact-only runs are expected to emit
`production_candidate_count=0` unless a separate reviewed Tier 2 source is
present in the input. Missing independent Tier 2 evidence emits
`keep_provisional`, not promotion.

---

### Task 1: Domain Evaluator Tests

**Files:**
- Create: `tests/test_production_candidate_gate.py`
- Create later in Task 2: `xic_extractor/alignment/production_candidate_gate.py`

- [ ] **Step 1: Write failing evaluator tests**

Create `tests/test_production_candidate_gate.py` with:

```python
from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.production_candidate_gate import (
    PRODUCTION_CANDIDATE_GATE_COLUMNS,
    evaluate_production_candidate_gate,
    production_candidate_gate_as_row,
    source_context_for_artifacts,
)


def test_retention_candidate_with_explicit_independent_tier2_support_tracks_candidate(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate;skip_expensive_evidence",
            detected=1,
            rescued=2,
            independent_support="validated_tier2_trace_evidence",
        ),
        _cell_rows(detected=1, rescued=2),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "production_candidate"
    assert decision.recommended_action == "track_candidate"
    assert decision.evidence_tier == 2
    assert decision.support_components == ("validated_tier2_trace_evidence",)
    assert decision.dependent_context == (
        "owner_backfill_context",
        "family_ms1_context",
        "rescued_cell_scan_support_distribution",
        "selected_boundary_local_apex_consistency",
        "rescued_cell_rt_coherence",
    )
    assert decision.challenge_blockers == ()
    assert decision.tier2_evidence_available is True
    assert decision.candidate_confidence == "medium"


def test_retention_candidate_without_positive_tier2_support_stays_provisional(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1, scan_support_score="0.3"),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.recommended_action == "keep_provisional"
    assert decision.evidence_tier == 1
    assert decision.support_components == ()
    assert decision.dependent_context == (
        "owner_backfill_context",
        "family_ms1_context",
        "selected_boundary_local_apex_consistency",
    )
    assert decision.tier2_evidence_available is False
    assert "missing_positive_tier2_support" in decision.challenge_blockers
    assert decision.candidate_confidence == "review"


def test_neighboring_interference_forces_audit(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(
            detected=1,
            rescued=1,
            region_review_reason="neighboring_ms1_interference",
        ),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.recommended_action == "review"
    assert "neighboring_interference_challenge" in decision.challenge_blockers
    assert decision.candidate_confidence == "review"


def test_low_scan_support_forces_audit(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1, scan_support_score="0.1"),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.recommended_action == "review"
    assert "low_assessable_coverage_challenge" in decision.challenge_blockers
    assert "missing_positive_tier2_support" in decision.challenge_blockers


def test_review_only_exact_token_excludes_but_rescue_only_review_does_not(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )

    review_only = evaluate_production_candidate_gate(
        _review_row(
            identity_reason="review_only",
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )
    rescue_only_review = evaluate_production_candidate_gate(
        _review_row(
            flags=(
                "single_detected_seed;provisional_retention_candidate;"
                "rescue_only_review"
            ),
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )

    assert review_only.candidate_gate_status == "audit"
    assert review_only.recommended_action == "review"
    assert "review_only" in review_only.challenge_blockers
    assert "review_only" not in rescue_only_review.challenge_blockers
    assert rescue_only_review.candidate_gate_status == "keep_provisional"
    assert "missing_positive_tier2_support" in rescue_only_review.challenge_blockers


def test_non_retention_candidate_is_reported_without_tier2_promotion(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(flags="single_detected_seed", detected=1, rescued=1),
        _cell_rows(detected=1, rescued=1),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.recommended_action == "keep_provisional"
    assert decision.evidence_tier == 1
    assert decision.tier2_evidence_available is False
    assert decision.challenge_blockers == ("not_retention_candidate",)


def test_gate_row_has_stable_columns_and_hashes(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    row = production_candidate_gate_as_row(decision)

    assert tuple(row) == PRODUCTION_CANDIDATE_GATE_COLUMNS
    assert row["source_review_artifact"] == str(review_path)
    assert row["source_cell_artifact"] == str(cell_path)
    assert row["source_matrix_artifact"] == str(matrix_path)
    assert len(row["source_review_sha256"]) == 64
    assert len(row["source_cell_sha256"]) == 64
    assert len(row["source_matrix_sha256"]) == 64


def _review_row(
    *,
    flags: str,
    detected: int,
    rescued: int,
    decision: str = "provisional_discovery",
    identity_reason: str = "insufficient_detected_identity_support",
    duplicate: int = 0,
    ambiguous: int = 0,
    independent_support: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "neutral_loss_tag": "DNA_dR",
        "include_in_primary_matrix": "FALSE",
        "identity_decision": decision,
        "identity_confidence": "review",
        "identity_reason": identity_reason,
        "primary_evidence": "owner_complete_link",
        "quantifiable_detected_count": str(detected),
        "quantifiable_rescue_count": str(rescued),
        "accepted_rescue_count": str(rescued),
        "duplicate_assigned_count": str(duplicate),
        "ambiguous_ms1_owner_count": str(ambiguous),
        "row_flags": flags,
        "family_evidence": "owner_complete_link;owner_count=1",
        "independent_tier2_support_components": independent_support,
    }


def _cell_rows(
    *,
    detected: int,
    rescued: int,
    scan_support_score: str = "0.8",
    region_review_reason: str = "",
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index in range(detected):
        rows.append(_cell_row(index, "detected", "1000", "0.8", ""))
    for index in range(detected, detected + rescued):
        rows.append(
            _cell_row(
                index,
                "rescued",
                "500",
                scan_support_score,
                region_review_reason,
            )
        )
    return tuple(rows)


def _cell_row(
    index: int,
    status: str,
    area: str,
    scan_support_score: str,
    region_review_reason: str,
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "sample_stem": f"S{index + 1:03d}",
        "status": status,
        "area": area,
        "apex_rt": "8.00",
        "height": "100",
        "peak_start_rt": "7.95",
        "peak_end_rt": "8.05",
        "rt_delta_sec": "0.0",
        "trace_quality": "owner_backfill" if status == "rescued" else "clean",
        "scan_support_score": scan_support_score,
        "reason": status,
        "region_review_reason": region_review_reason,
    }


def _write_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    review_path = tmp_path / "alignment_review.tsv"
    cell_path = tmp_path / "alignment_cells.tsv"
    matrix_path = tmp_path / "alignment_matrix.tsv"
    review_path.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    cell_path.write_text("feature_family_id\tsample_stem\nFAM001\tS001\n", encoding="utf-8")
    matrix_path.write_text("feature_family_id\nFAM_PRIMARY\n", encoding="utf-8")
    return review_path, cell_path, matrix_path
```

- [ ] **Step 2: Run the failing evaluator tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_production_candidate_gate.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'xic_extractor.alignment.production_candidate_gate'
```

---

### Task 2: Domain Evaluator Implementation

**Files:**
- Create: `xic_extractor/alignment/production_candidate_gate.py`
- Test: `tests/test_production_candidate_gate.py`

- [ ] **Step 1: Implement the domain module**

Create `xic_extractor/alignment/production_candidate_gate.py` with:

```python
from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.alignment.machine_decision import project_machine_decision

CandidateGateStatus = Literal[
    "production_candidate",
    "keep_provisional",
    "audit",
    "excluded",
]
CandidateRecommendedAction = Literal[
    "track_candidate",
    "keep_provisional",
    "review",
    "exclude",
]
CandidateConfidence = Literal["medium", "review", "none"]

PRODUCTION_CANDIDATE_GATE_COLUMNS = (
    "feature_family_id",
    "matrix_role",
    "candidate_gate_status",
    "recommended_action",
    "evidence_tier",
    "support_components",
    "dependent_context",
    "challenge_blockers",
    "tier2_evidence_available",
    "candidate_confidence",
    "source_review_artifact",
    "source_review_sha256",
    "source_cell_artifact",
    "source_cell_sha256",
    "source_matrix_artifact",
    "source_matrix_sha256",
)

MIN_SCAN_SUPPORT_SCORE = 0.5
LOW_SCAN_SUPPORT_MAX = 0.2
MAX_ABS_RT_DELTA_SEC = 180.0
MAX_RESCUED_APEX_RT_SPAN_MIN = 0.35

_PROVISIONAL_DECISION = "provisional_discovery"
_REQUIRED_FLAGS = frozenset({"single_detected_seed", "provisional_retention_candidate"})
_STRUCTURAL_EXCLUDE_FLAGS = frozenset(
    {"family_consolidation_loser", "duplicate_only", "rescue_only", "zero_present"}
)
_INDEPENDENT_TIER2_SUPPORT_COMPONENTS = frozenset(
    {"validated_tier2_trace_evidence"}
)
_INTERFERENCE_MARKERS = ("neighbor", "interference")
_LOW_COVERAGE_MARKERS = (
    "low_scan_support",
    "skipped_low_scan_support",
    "coverage",
    "unassessable",
)


@dataclass(frozen=True)
class GateSourceContext:
    review_path: Path
    review_sha256: str
    cell_path: Path
    cell_sha256: str
    matrix_path: Path
    matrix_sha256: str


@dataclass(frozen=True)
class ProductionCandidateGateDecision:
    feature_family_id: str
    matrix_role: str
    candidate_gate_status: CandidateGateStatus
    recommended_action: CandidateRecommendedAction
    evidence_tier: int
    support_components: tuple[str, ...]
    dependent_context: tuple[str, ...]
    challenge_blockers: tuple[str, ...]
    tier2_evidence_available: bool
    candidate_confidence: CandidateConfidence
    source_context: GateSourceContext


def source_context_for_artifacts(
    *,
    review_path: Path,
    cell_path: Path,
    matrix_path: Path,
) -> GateSourceContext:
    return GateSourceContext(
        review_path=review_path,
        review_sha256=_sha256_file(review_path),
        cell_path=cell_path,
        cell_sha256=_sha256_file(cell_path),
        matrix_path=matrix_path,
        matrix_sha256=_sha256_file(matrix_path),
    )


def evaluate_production_candidate_gate(
    review_row: Mapping[str, object],
    cell_rows: Sequence[Mapping[str, object]],
    *,
    source_context: GateSourceContext,
) -> ProductionCandidateGateDecision:
    review = _string_row(review_row)
    cells = tuple(_string_row(row) for row in cell_rows)
    machine = project_machine_decision(review, cells)
    flags = _split_tokens(review.get("row_flags"))
    structural_blockers = _structural_blockers(review, flags)
    if structural_blockers:
        return _decision(
            review=review,
            machine_role=machine.matrix_role,
            status="excluded" if set(structural_blockers) & _STRUCTURAL_EXCLUDE_FLAGS else "audit",
            blockers=structural_blockers,
            evidence_tier=1,
            support=(),
            dependent=(),
            tier2_available=False,
            source_context=source_context,
        )
    if not _is_retention_candidate(review, flags):
        return _decision(
            review=review,
            machine_role=machine.matrix_role,
            status=_status_for_non_candidate(machine.matrix_role),
            blockers=("not_retention_candidate",),
            evidence_tier=1,
            support=(),
            dependent=(),
            tier2_available=False,
            source_context=source_context,
        )

    rescued = tuple(row for row in cells if row.get("status") == "rescued")
    support = _explicit_positive_support(review)
    tier2_available = bool(support)
    dependent = _dependent_context(review, rescued)
    blockers = _challenge_blockers(rescued)
    if not tier2_available:
        blockers = _ordered_unique((*blockers, "missing_positive_tier2_support"))

    if blockers and any(blocker != "missing_positive_tier2_support" for blocker in blockers):
        status: CandidateGateStatus = "audit"
    elif blockers:
        status = "keep_provisional"
    else:
        status = "production_candidate"
    return _decision(
        review=review,
        machine_role=machine.matrix_role,
        status=status,
        blockers=blockers,
        evidence_tier=2 if tier2_available else 1,
        support=support,
        dependent=dependent,
        tier2_available=tier2_available,
        source_context=source_context,
    )


def is_candidate_gate_scope(review_row: Mapping[str, object]) -> bool:
    return "provisional_retention_candidate" in _split_tokens(
        review_row.get("row_flags"),
    )


def production_candidate_gate_as_row(
    decision: ProductionCandidateGateDecision,
) -> dict[str, str]:
    return {
        "feature_family_id": decision.feature_family_id,
        "matrix_role": decision.matrix_role,
        "candidate_gate_status": decision.candidate_gate_status,
        "recommended_action": decision.recommended_action,
        "evidence_tier": str(decision.evidence_tier),
        "support_components": ";".join(decision.support_components),
        "dependent_context": ";".join(decision.dependent_context),
        "challenge_blockers": ";".join(decision.challenge_blockers),
        "tier2_evidence_available": "TRUE" if decision.tier2_evidence_available else "FALSE",
        "candidate_confidence": decision.candidate_confidence,
        "source_review_artifact": str(decision.source_context.review_path),
        "source_review_sha256": decision.source_context.review_sha256,
        "source_cell_artifact": str(decision.source_context.cell_path),
        "source_cell_sha256": decision.source_context.cell_sha256,
        "source_matrix_artifact": str(decision.source_context.matrix_path),
        "source_matrix_sha256": decision.source_context.matrix_sha256,
    }


def summarize_gate_decisions(
    decisions: Sequence[ProductionCandidateGateDecision],
) -> dict[str, object]:
    status_counts = Counter(decision.candidate_gate_status for decision in decisions)
    return {
        "schema_version": "production-candidate-gate-v1",
        "readiness_label": "diagnostic_only",
        "row_count": len(decisions),
        "production_candidate_count": status_counts["production_candidate"],
        "keep_provisional_count": status_counts["keep_provisional"],
        "audit_count": status_counts["audit"],
        "excluded_count": status_counts["excluded"],
        "production_ready": False,
        "matrix_contract_changed": False,
    }


def _decision(
    *,
    review: Mapping[str, str],
    machine_role: str,
    status: CandidateGateStatus,
    blockers: Sequence[str],
    evidence_tier: int,
    support: Sequence[str],
    dependent: Sequence[str],
    tier2_available: bool,
    source_context: GateSourceContext,
) -> ProductionCandidateGateDecision:
    return ProductionCandidateGateDecision(
        feature_family_id=review.get("feature_family_id", ""),
        matrix_role=machine_role,
        candidate_gate_status=status,
        recommended_action=_recommended_action(status),
        evidence_tier=evidence_tier,
        support_components=_ordered_unique(support),
        dependent_context=_ordered_unique(dependent),
        challenge_blockers=_ordered_unique(blockers),
        tier2_evidence_available=tier2_available,
        candidate_confidence=_confidence(status),
        source_context=source_context,
    )


def _status_for_non_candidate(matrix_role: str) -> CandidateGateStatus:
    if matrix_role == "excluded":
        return "excluded"
    if matrix_role == "audit":
        return "audit"
    return "keep_provisional"


def _recommended_action(status: CandidateGateStatus) -> CandidateRecommendedAction:
    if status == "production_candidate":
        return "track_candidate"
    if status == "keep_provisional":
        return "keep_provisional"
    if status == "excluded":
        return "exclude"
    return "review"


def _confidence(status: CandidateGateStatus) -> CandidateConfidence:
    if status == "production_candidate":
        return "medium"
    if status in {"keep_provisional", "audit"}:
        return "review"
    return "none"


def _is_retention_candidate(review: Mapping[str, str], flags: frozenset[str]) -> bool:
    if review.get("identity_decision") != _PROVISIONAL_DECISION:
        return False
    if not _REQUIRED_FLAGS.issubset(flags):
        return False
    if _int_value(review.get("quantifiable_detected_count")) != 1:
        return False
    if _int_value(review.get("quantifiable_rescue_count")) <= 0:
        return False
    if _int_value(review.get("duplicate_assigned_count")) != 0:
        return False
    if _int_value(review.get("ambiguous_ms1_owner_count")) != 0:
        return False
    return True


def _structural_blockers(
    review: Mapping[str, str],
    flags: frozenset[str],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if review.get("identity_reason") == "review_only" or "review_only" in flags:
        blockers.append("review_only")
    blockers.extend(flag for flag in sorted(flags & _STRUCTURAL_EXCLUDE_FLAGS))
    return tuple(blockers)


def _explicit_positive_support(review: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(
        token
        for token in _split_tokens(review.get("independent_tier2_support_components"))
        if token in _INDEPENDENT_TIER2_SUPPORT_COMPONENTS
    )


def _dependent_context(
    review: Mapping[str, str],
    rescued: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    context: list[str] = []
    if review.get("primary_evidence") == "owner_complete_link":
        context.append("owner_backfill_context")
    if rescued:
        context.append("family_ms1_context")
    if rescued and all(
        (_float(row.get("scan_support_score")) or 0.0) >= MIN_SCAN_SUPPORT_SCORE
        for row in rescued
    ):
        context.append("rescued_cell_scan_support_distribution")
    if rescued and all(_local_apex_consistent(row) for row in rescued):
        context.append("selected_boundary_local_apex_consistency")
    apex_rts = [_float(row.get("apex_rt")) for row in rescued]
    finite_apex_rts = [value for value in apex_rts if value is not None]
    if len(finite_apex_rts) >= 2 and max(finite_apex_rts) - min(finite_apex_rts) <= MAX_RESCUED_APEX_RT_SPAN_MIN:
        context.append("rescued_cell_rt_coherence")
    return tuple(context)


def _challenge_blockers(rescued: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    blockers: list[str] = []
    if any(_has_marker(row, _INTERFERENCE_MARKERS) for row in rescued):
        blockers.append("neighboring_interference_challenge")
    if any(_low_assessable_coverage(row) for row in rescued):
        blockers.append("low_assessable_coverage_challenge")
    if any(not _local_apex_consistent(row) for row in rescued):
        blockers.append("selected_boundary_local_apex_inconsistency")
    return tuple(blockers)


def _local_apex_consistent(row: Mapping[str, str]) -> bool:
    apex = _float(row.get("apex_rt"))
    start = _float(row.get("peak_start_rt"))
    end = _float(row.get("peak_end_rt"))
    rt_delta = _float(row.get("rt_delta_sec"))
    if apex is None or start is None or end is None or rt_delta is None:
        return False
    return start <= apex <= end and abs(rt_delta) <= MAX_ABS_RT_DELTA_SEC


def _low_assessable_coverage(row: Mapping[str, str]) -> bool:
    scan_support = _float(row.get("scan_support_score"))
    if scan_support is None:
        return True
    if scan_support <= LOW_SCAN_SUPPORT_MAX:
        return True
    return _has_marker(row, _LOW_COVERAGE_MARKERS)


def _has_marker(row: Mapping[str, str], markers: Sequence[str]) -> bool:
    text = " ".join(
        str(row.get(field, ""))
        for field in (
            "reason",
            "region_local_mixture_diagnostic",
            "region_local_mixture_reason",
            "region_review_reason",
            "region_shadow_status",
            "region_shadow_verdict",
        )
    ).lower()
    return any(marker in text for marker in markers)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _string_row(row: Mapping[str, object]) -> dict[str, str]:
    return {str(key): "" if value is None else str(value) for key, value in row.items()}


def _split_tokens(value: object) -> frozenset[str]:
    return frozenset(part.strip() for part in str(value or "").split(";") if part.strip())


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _float(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().lstrip("'"))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _int_value(value: object) -> int:
    number = _float(value)
    return 0 if number is None else int(number)
```

- [ ] **Step 2: Run evaluator tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_production_candidate_gate.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 3: Check current dirty scope**

Run:

```powershell
git status --short
```

Expected source additions from this task:

```text
?? tests/test_production_candidate_gate.py
?? xic_extractor/alignment/production_candidate_gate.py
```

Do not stage or commit in this thread unless the user explicitly grants commit authorization.

---

### Task 3: Diagnostic CLI Tests

**Files:**
- Create: `tests/test_provisional_backfill_candidate_gate_cli.py`
- Create later in Task 4: `tools/diagnostics/provisional_backfill_candidate_gate.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_provisional_backfill_candidate_gate_cli.py` with:

```python
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from tools.diagnostics import provisional_backfill_candidate_gate as gate_cli


def test_cli_writes_sidecar_and_summary_without_mutating_matrix(tmp_path: Path) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")
    matrix_path = alignment_dir / "alignment_matrix.tsv"
    before_hash = _sha256_file(matrix_path)
    output_dir = tmp_path / "gate"

    code = gate_cli.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert _sha256_file(matrix_path) == before_hash
    rows = _read_tsv(output_dir / "alignment_production_candidate_gate.tsv")
    by_id = {row["feature_family_id"]: row for row in rows}
    assert set(by_id) == {"FAM_CAND"}
    assert by_id["FAM_CAND"]["candidate_gate_status"] == "keep_provisional"
    assert by_id["FAM_CAND"]["support_components"] == ""
    assert "missing_positive_tier2_support" in by_id["FAM_CAND"]["challenge_blockers"]
    assert by_id["FAM_CAND"]["source_matrix_sha256"] == before_hash
    payload = json.loads(
        (output_dir / "alignment_production_candidate_gate.json").read_text(
            encoding="utf-8",
        )
    )
    assert payload["readiness_label"] == "diagnostic_only"
    assert payload["production_ready"] is False
    assert payload["matrix_contract_changed"] is False
    assert payload["production_candidate_count"] == 0
    assert payload["row_count"] == 1


def test_cli_defaults_output_dir_to_alignment_dir(tmp_path: Path) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 0
    assert (alignment_dir / "alignment_production_candidate_gate.tsv").is_file()
    assert (alignment_dir / "alignment_production_candidate_gate.json").is_file()


def test_cli_reports_missing_required_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 2
    stderr = capsys.readouterr().err
    assert "Required TSV not found" in stderr
    assert "alignment_review.tsv" in stderr


def test_cli_reports_missing_required_columns(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    _write_tsv(alignment_dir / "alignment_review.tsv", [{"feature_family_id": "FAM"}])
    _write_tsv(alignment_dir / "alignment_cells.tsv", [{"feature_family_id": "FAM"}])
    _write_tsv(alignment_dir / "alignment_matrix.tsv", [{"feature_family_id": "FAM"}])

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 2
    stderr = capsys.readouterr().err
    assert "missing required columns" in stderr
    assert "identity_decision" in stderr


def _write_alignment_run(path: Path) -> Path:
    path.mkdir(parents=True)
    _write_tsv(
        path / "alignment_review.tsv",
        [
            _review_row("FAM_KEEP", flags="single_detected_seed", detected=1, rescued=1),
            _review_row(
                "FAM_CAND",
                flags="single_detected_seed;provisional_retention_candidate",
                detected=1,
                rescued=2,
            ),
            _review_row(
                "FAM_PRIMARY",
                include="TRUE",
                decision="production_family",
                reason="owner_complete_link",
                flags="",
                detected=2,
                rescued=0,
            ),
        ],
    )
    _write_tsv(
        path / "alignment_cells.tsv",
        [
            _cell_row("FAM_KEEP", "S1", "detected"),
            _cell_row("FAM_KEEP", "S2", "rescued"),
            _cell_row("FAM_CAND", "S1", "detected"),
            _cell_row("FAM_CAND", "S2", "rescued"),
            _cell_row("FAM_CAND", "S3", "rescued"),
            _cell_row("FAM_PRIMARY", "S1", "detected"),
            _cell_row("FAM_PRIMARY", "S2", "detected"),
        ],
    )
    _write_tsv(
        path / "alignment_matrix.tsv",
        [{"feature_family_id": "FAM_PRIMARY", "S1": "100", "S2": "90"}],
    )
    return path


def _review_row(
    family_id: str,
    *,
    flags: str,
    detected: int,
    rescued: int,
    include: str = "FALSE",
    decision: str = "provisional_discovery",
    reason: str = "insufficient_detected_identity_support",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "include_in_primary_matrix": include,
        "identity_decision": decision,
        "identity_confidence": "review",
        "identity_reason": reason,
        "primary_evidence": "owner_complete_link",
        "quantifiable_detected_count": str(detected),
        "quantifiable_rescue_count": str(rescued),
        "accepted_rescue_count": str(rescued),
        "duplicate_assigned_count": "0",
        "ambiguous_ms1_owner_count": "0",
        "row_flags": flags,
        "family_evidence": "owner_complete_link;owner_count=1",
    }


def _cell_row(family_id: str, sample: str, status: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": status,
        "area": "100",
        "apex_rt": "8.00",
        "height": "50",
        "peak_start_rt": "7.95",
        "peak_end_rt": "8.05",
        "rt_delta_sec": "0.0",
        "trace_quality": "owner_backfill" if status == "rescued" else "clean",
        "scan_support_score": "0.8",
        "reason": status,
    }


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
```

- [ ] **Step 2: Run failing CLI tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_provisional_backfill_candidate_gate_cli.py -q
```

Expected:

```text
ImportError: cannot import name 'provisional_backfill_candidate_gate' from 'tools.diagnostics'
```

---

### Task 4: Diagnostic CLI Implementation

**Files:**
- Create: `tools/diagnostics/provisional_backfill_candidate_gate.py`
- Modify: `tools/diagnostics/INDEX.md`
- Test: `tests/test_provisional_backfill_candidate_gate_cli.py`

- [ ] **Step 1: Implement the CLI facade**

Create `tools/diagnostics/provisional_backfill_candidate_gate.py` with:

```python
"""Write a diagnostic-only provisional backfill candidate gate sidecar."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.diagnostics.diagnostic_io import read_tsv_required, write_tsv
from xic_extractor.alignment.production_candidate_gate import (
    PRODUCTION_CANDIDATE_GATE_COLUMNS,
    evaluate_production_candidate_gate,
    is_candidate_gate_scope,
    production_candidate_gate_as_row,
    source_context_for_artifacts,
    summarize_gate_decisions,
)

REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "include_in_primary_matrix",
    "identity_decision",
    "identity_confidence",
    "identity_reason",
    "primary_evidence",
    "quantifiable_detected_count",
    "quantifiable_rescue_count",
    "duplicate_assigned_count",
    "ambiguous_ms1_owner_count",
    "row_flags",
)
CELL_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "trace_quality",
    "scan_support_score",
    "reason",
)
MATRIX_REQUIRED_COLUMNS = ("feature_family_id",)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        output_dir = args.output_dir or args.alignment_dir
        outputs = run_gate(
            alignment_dir=args.alignment_dir,
            output_dir=output_dir,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"production candidate gate TSV: {outputs['tsv']}")
    print(f"production candidate gate JSON: {outputs['json']}")
    return 0


def run_gate(*, alignment_dir: Path, output_dir: Path) -> dict[str, Path]:
    review_path = alignment_dir / "alignment_review.tsv"
    cell_path = alignment_dir / "alignment_cells.tsv"
    matrix_path = alignment_dir / "alignment_matrix.tsv"
    review_rows = _read_required_tsv(review_path, REVIEW_REQUIRED_COLUMNS)
    cell_rows = _read_required_tsv(cell_path, CELL_REQUIRED_COLUMNS)
    _read_required_tsv(matrix_path, MATRIX_REQUIRED_COLUMNS)
    source_context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    cells_by_family = _cells_by_family(cell_rows)
    candidate_rows = [row for row in review_rows if is_candidate_gate_scope(row)]
    decisions = [
        evaluate_production_candidate_gate(
            review_row,
            cells_by_family.get(review_row["feature_family_id"], ()),
            source_context=source_context,
        )
        for review_row in candidate_rows
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = output_dir / "alignment_production_candidate_gate.tsv"
    json_path = output_dir / "alignment_production_candidate_gate.json"
    write_tsv(
        tsv_path,
        [production_candidate_gate_as_row(decision) for decision in decisions],
        PRODUCTION_CANDIDATE_GATE_COLUMNS,
        lineterminator="\n",
    )
    summary = summarize_gate_decisions(decisions)
    summary.update(
        {
            "alignment_dir": str(alignment_dir),
            "source_review_artifact": str(source_context.review_path),
            "source_review_sha256": source_context.review_sha256,
            "source_cell_artifact": str(source_context.cell_path),
            "source_cell_sha256": source_context.cell_sha256,
            "source_matrix_artifact": str(source_context.matrix_path),
            "source_matrix_sha256": source_context.matrix_sha256,
        }
    )
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {"tsv": tsv_path, "json": json_path}


def _read_required_tsv(
    path: Path,
    required_columns: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    try:
        return read_tsv_required(path, required_columns)
    except FileNotFoundError as exc:
        raise ValueError(f"Required TSV not found: {path}") from exc


def _cells_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["feature_family_id"], []).append(row)
    return {family_id: tuple(items) for family_id, items in grouped.items()}


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        required=True,
        help=(
            "Alignment output directory containing alignment_review.tsv, "
            "alignment_cells.tsv, and alignment_matrix.tsv."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory for alignment_production_candidate_gate.tsv and "
            "alignment_production_candidate_gate.json. Defaults to --alignment-dir."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Update the diagnostic index**

In `tools/diagnostics/INDEX.md`, update the Backfill Reviews count from 5 to 6 and add this entry inside the Backfill Reviews section after `owner_backfill_request_economics.py`:

```markdown
### `provisional_backfill_candidate_gate.py`

**Purpose**: Emit a `diagnostic_only` machine sidecar for retained provisional backfill rows, including Tier 2 support components, challenge blockers, and source artifact hashes.
**Topic group**: `provisional_backfill_candidate_gate.py` + `xic_extractor/alignment/production_candidate_gate.py`
**Originating spec/plan**: `specs/2026-05-29-provisional-backfill-production-candidate-gate-design.md`; `plans/2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-implementation-plan.md`
**Status note**: Writes `alignment_production_candidate_gate.tsv`; does not mutate `alignment_review.tsv`, `alignment_matrix.tsv`, workbook schemas, or downstream correction/statistics contracts.

---
```

- [ ] **Step 3: Run CLI tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_provisional_backfill_candidate_gate_cli.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 4: Run evaluator and CLI tests together**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py -q
```

Expected:

```text
11 passed
```

---

### Task 5: Matrix Contract Guard

**Files:**
- Modify: `tests/test_alignment_tsv_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Add an explicit writer guard test**

Append this test near `test_one_detected_provisional_retention_stays_out_of_primary_matrix` in `tests/test_alignment_tsv_writer.py`:

```python
def test_production_candidate_sidecar_status_does_not_change_matrix_writer(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.production_candidate_gate import (
        evaluate_production_candidate_gate,
        source_context_for_artifacts,
    )
    from xic_extractor.alignment.tsv_writer import (
        write_alignment_cells_tsv,
        write_alignment_matrix_tsv,
        write_alignment_review_tsv,
    )

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(
                fold_evidence="owner_complete_link;owner_count=1",
            ),
        ),
        cells=(
            _cell("sample-a", "detected", area=100.0, candidate_id="sample-a#1"),
            _cell("sample-b", "rescued", area=90.0),
            _cell("sample-c", "rescued", area=80.0),
        ),
        sample_order=("sample-a", "sample-b", "sample-c"),
    )
    review_path = write_alignment_review_tsv(tmp_path / "alignment_review.tsv", matrix)
    cells_path = write_alignment_cells_tsv(tmp_path / "alignment_cells.tsv", matrix)
    matrix_path = write_alignment_matrix_tsv(tmp_path / "alignment_matrix.tsv", matrix)
    review_rows = _read_tsv(review_path)
    cell_rows = _read_tsv(cells_path)

    sidecar_review_row = {
        **review_rows[0],
        "independent_tier2_support_components": "validated_tier2_trace_evidence",
    }
    decision = evaluate_production_candidate_gate(
        sidecar_review_row,
        cell_rows,
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cells_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "production_candidate"
    assert _read_tsv(matrix_path) == []
```

This test intentionally injects an explicit independent Tier 2 support token so
the sidecar can say `production_candidate` while proving the primary matrix
writer remains unchanged.

- [ ] **Step 2: Run the matrix guard**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_alignment_tsv_writer.py::test_production_candidate_sidecar_status_does_not_change_matrix_writer -q
```

Expected:

```text
1 passed
```

- [ ] **Step 3: Run adjacent TSV writer tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_alignment_tsv_writer.py::test_one_detected_provisional_retention_stays_out_of_primary_matrix tests\test_alignment_tsv_writer.py::test_production_candidate_sidecar_status_does_not_change_matrix_writer -q
```

Expected:

```text
2 passed
```

---

### Task 6: Existing Artifact Acceptance Check

**Files:**
- No source edits.
- Writes diagnostic outputs under existing ignored `output\` artifact directories.

- [ ] **Step 1: Run sidecar over current 8RAW artifacts**

Run:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate `
  --alignment-dir output\tiered_backfill_candidate_gate_8raw_current `
  --output-dir output\tiered_backfill_candidate_gate_8raw_current
```

Expected:

```text
production candidate gate TSV: output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv
production candidate gate JSON: output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.json
```

- [ ] **Step 2: Inspect 8RAW summary**

Run:

```powershell
.venv\Scripts\python.exe -c "import json; p='output/tiered_backfill_candidate_gate_8raw_current/alignment_production_candidate_gate.json'; d=json.load(open(p, encoding='utf-8')); print(d['readiness_label'], d['row_count'], d['production_candidate_count'], d['matrix_contract_changed'], d['production_ready'])"
```

Expected:

```text
diagnostic_only 7 0 False False
```

The artifact-only pilot must not report `production_candidate` rows unless the
input already contains an explicit independent Tier 2 support source from a
separate reviewed validation path. Existing 8RAW artifacts are expected to leave
retention candidates as `keep_provisional` or `audit`.

- [ ] **Step 3: Run sidecar over current 85RAW artifacts**

Run:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate `
  --alignment-dir output\tiered_backfill_candidate_gate_85raw_current `
  --output-dir output\tiered_backfill_candidate_gate_85raw_current
```

Expected:

```text
production candidate gate TSV: output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv
production candidate gate JSON: output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.json
```

- [ ] **Step 4: Inspect 85RAW summary**

Run:

```powershell
.venv\Scripts\python.exe -c "import json; p='output/tiered_backfill_candidate_gate_85raw_current/alignment_production_candidate_gate.json'; d=json.load(open(p, encoding='utf-8')); print(d['readiness_label'], d['row_count'], d['production_candidate_count'], d['matrix_contract_changed'], d['production_ready'])"
```

Expected:

```text
diagnostic_only 7 0 False False
```

Do not rerun 85RAW for this check. Use the existing artifacts unless source hashes or code changes show that the previous run no longer answers the sidecar determinism question.

- [ ] **Step 5: Confirm sidecar rows are not matrix rows**

Run:

```powershell
.venv\Scripts\python.exe -c "import csv; side=list(csv.DictReader(open('output/tiered_backfill_candidate_gate_85raw_current/alignment_production_candidate_gate.tsv', newline='', encoding='utf-8'), delimiter='\t')); matrix=list(csv.DictReader(open('output/tiered_backfill_candidate_gate_85raw_current/alignment_matrix.tsv', newline='', encoding='utf-8'), delimiter='\t')); print(len(side), len(matrix)); print(any(r['candidate_gate_status']=='production_candidate' for r in side), len(matrix)==610)"
```

Expected:

```text
7 610
False True
```

The first boolean is expected to be `False` for this artifact-only pilot. The
JSON summary and TSV blockers should show `missing_positive_tier2_support` for
retention candidates that lack explicit independent Tier 2 support.

---

### Task 7: Focused Regression Suite

**Files:**
- No source edits.

- [ ] **Step 1: Run new and adjacent tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_machine_decision.py `
  tests\test_matrix_identity_blast_radius.py `
  tests\test_alignment_tsv_writer.py::test_one_detected_provisional_retention_stays_out_of_primary_matrix `
  tests\test_alignment_tsv_writer.py::test_production_candidate_sidecar_status_does_not_change_matrix_writer `
  -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run ruff on touched Python files**

Run:

```powershell
.venv\Scripts\python.exe -m ruff check `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run diff check**

Run:

```powershell
git diff --check -- `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py `
  tools\diagnostics\INDEX.md
```

Expected: no output and exit code `0`.

---

### Task 8: Validation Note

**Files:**
- Create: `docs/superpowers/notes/2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md`

- [ ] **Step 1: Collect validation-note values from emitted JSON**

Run:

```powershell
.venv\Scripts\python.exe -c "import json; paths=('output/tiered_backfill_candidate_gate_8raw_current/alignment_production_candidate_gate.json','output/tiered_backfill_candidate_gate_85raw_current/alignment_production_candidate_gate.json'); keys=('alignment_dir','row_count','production_candidate_count','keep_provisional_count','audit_count','excluded_count','source_review_sha256','source_cell_sha256','source_matrix_sha256','production_ready','matrix_contract_changed'); [print(p, json.dumps({k: json.load(open(p, encoding='utf-8'))[k] for k in keys}, sort_keys=True)) for p in paths]"
```

Expected:

```text
output/tiered_backfill_candidate_gate_8raw_current/alignment_production_candidate_gate.json {"alignment_dir": "output\\tiered_backfill_candidate_gate_8raw_current", ...}
output/tiered_backfill_candidate_gate_85raw_current/alignment_production_candidate_gate.json {"alignment_dir": "output\\tiered_backfill_candidate_gate_85raw_current", ...}
```

The command prints exact row counts, status counts, hashes, and readiness booleans to copy into the note.

- [ ] **Step 2: Write the validation note with observed values**

Create `docs/superpowers/notes/2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md` after Task 8 Step 1. The note must use the exact values printed by the command and must have this structure:

```markdown
# Provisional Backfill Diagnostic Sidecar Pilot Validation Note

## Verdict

`diagnostic_only`

The implementation emits `alignment_production_candidate_gate.tsv` as a machine sidecar. It does not modify `alignment_review.tsv`, `alignment_matrix.tsv`, workbook schemas, or downstream correction/statistics contracts.

## Source Artifacts

| Run | Alignment Dir | Sidecar Rows | Production Candidate Rows | Keep Provisional Rows | Audit Rows | Excluded Rows | Source Review SHA256 | Source Cells SHA256 | Source Matrix SHA256 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
Add one 8RAW row and one 85RAW row. Every table cell must be a concrete value
from the Step 1 JSON output. The row is invalid if it contains a prose
instruction, an empty hash, or a non-numeric count.

## Commands

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tiered_backfill_candidate_gate_8raw_current
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_85raw_current --output-dir output\tiered_backfill_candidate_gate_85raw_current
```

## Gate Interpretation

- `production_candidate` remains a sidecar status only.
- `production_ready=false` remains true in both JSON summaries.
- `matrix_contract_changed=false` remains true in both JSON summaries.
- Any row without allowlisted non-provenance Tier 2 positive support remains `keep_provisional` or `audit`.

## Verification

```text
Focused pytest result: paste the observed Task 7 pytest summary line.
Ruff result: paste the observed Task 7 ruff summary line.
Diff check result: paste the observed Task 7 git diff --check result.
```

## Next Action

Use the sidecar for diagnostic calibration and future promotion-contract drafting. Do not promote any row into `alignment_matrix.tsv` without a separate reviewed promotion contract.
```

The final note must contain observed values and verification output, not prose
instructions copied from this plan.

- [ ] **Step 3: Run docs smoke checks**

Run:

```powershell
rg -n "paste the observed|concrete value|prose instruction" docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md
rg -n "[ \t]+$" docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md
git diff --check -- docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md
```

Expected:

```text
first rg exits 1 with no matches after values are filled
second rg exits 1 with no trailing whitespace
git diff --check exits 0
```

---

## Final Verification

Run:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_machine_decision.py `
  tests\test_matrix_identity_blast_radius.py `
  tests\test_alignment_tsv_writer.py::test_one_detected_provisional_retention_stays_out_of_primary_matrix `
  tests\test_alignment_tsv_writer.py::test_production_candidate_sidecar_status_does_not_change_matrix_writer `
  -q

.venv\Scripts\python.exe -m ruff check `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py

git diff --check -- `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py `
  tools\diagnostics\INDEX.md `
  docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md
```

Acceptance:

- New sidecar TSV exists for 8RAW and 85RAW artifact directories.
- JSON summaries say `readiness_label=diagnostic_only`, `production_ready=false`, and `matrix_contract_changed=false`.
- `alignment_matrix.tsv` row count and SHA256 are unchanged by the diagnostic CLI.
- Existing artifact-only 8RAW/85RAW JSON summaries have `production_candidate_count=0`.
- Any future `production_candidate` rows require explicit independent Tier 2
  `support_components` and empty `challenge_blockers`.
- `keep_provisional` / `audit` rows explain missing support or challenge blockers with machine-readable labels.
- No run requires manual EIC review.
- No 85RAW rerun is launched unless the existing artifact hashes cannot answer the acceptance question.

## Stop Rules

- Stop if implementing the sidecar requires changing `alignment_matrix.tsv`, `alignment_review.tsv`, workbook sheets, or `run_alignment` default outputs.
- Stop if the only possible `production_candidate` evidence is dependent owner-backfill context.
- Stop if source artifact hashes are absent from emitted rows.
- Stop before any primary matrix promotion; that requires a separate promotion contract and review.
- Stop before rerunning 85RAW if current artifacts and hashes already answer determinism and scale.

## Out Of Scope

- Direct product promotion.
- Primary matrix inclusion.
- Workbook schema changes.
- Broad Tier 2 routing for every provisional row.
- RAW-backed overlay generation as part of the default implementation.
- New `scripts.run_alignment` flags or output-level artifacts.

## Self-Review

Spec coverage:

- Sidecar schema is implemented in Tasks 1-4.
- Tier 0 / Tier 1 eligibility and `review_only` exact-token behavior are covered in Task 1.
- Tier 2 support, dependent context, and blockers are covered in Tasks 1-2.
- `alignment_matrix.tsv` primary-only behavior is covered in Task 5 and Final Verification.
- 8RAW/85RAW source-artifact validation is covered in Task 6 and Task 8.
- Diagnostic-only readiness and exit rules are covered in Review Gate, Acceptance, and Stop Rules.

Placeholder scan:

- The plan contains no unresolved implementation values. Task 8 uses exact JSON inspection and requires concrete observed values in the final validation note.

Type consistency:

- `CandidateGateStatus`, `CandidateRecommendedAction`, `CandidateConfidence`, `ProductionCandidateGateDecision`, `GateSourceContext`, `evaluate_production_candidate_gate`, `production_candidate_gate_as_row`, and `source_context_for_artifacts` are introduced before use.
