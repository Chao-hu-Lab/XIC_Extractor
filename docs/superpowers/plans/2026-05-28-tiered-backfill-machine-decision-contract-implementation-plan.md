# Tiered Backfill Machine Decision Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic machine-decision vector for alignment rows so one-detected-seed MS1 backfill rows can be kept as provisional research features without entering `alignment_matrix.tsv`.

**Architecture:** Add a pure projection helper in the alignment decision layer, fed by existing `alignment_review.tsv` rows and optional `alignment_cells.tsv` rows. Keep `alignment_matrix.tsv` primary-only, keep the existing review TSV schema stable, and extend one existing diagnostic consumer to display the projected vector instead of adding a new sidecar.

**Tech Stack:** Python, dataclasses, `pytest`, existing alignment TSV writers, existing `tools/diagnostics/analyze_matrix_identity_blast_radius.py`.

---

## Execution Status

Implemented on branch `codex/tiered-backfill-machine-decision`. The checkbox
steps below are the original agent execution script and remain as historical
instructions; the current shipped scope, verification commands, and residual
risk are recorded in
`docs/superpowers/notes/2026-05-28-tiered-backfill-machine-decision-implementation-note.md`.

## Scope Guard

Current CodeGraph status on 2026-05-28 was up to date. The current branch is
`codex/tiered-backfill-machine-decision`; `git status --short --branch` showed
no dirty source files before this plan was written.

This plan implements only the first PR scope from
`docs/superpowers/specs/2026-05-28-tiered-backfill-machine-decision-contract-spec.md`:

- one-detected-seed provisional retention state expressed through existing row
  fields and row flags;
- a pure projection helper for `matrix_role` and `recommended_action`;
- synthetic tests and one existing diagnostic consumer;
- no Tier 2 routing, no `provisional-candidates` execution scope, no skipped
  evidence ledger, no new sidecar, and no `alignment_matrix.tsv` schema change.

The implementation verdict after this plan should remain `diagnostic_only`
after focused synthetic tests pass. It can become `shadow_ready` only after a
current existing-artifact smoke classification, or an explicitly hash-pinned
8RAW gate artifact, proves the projection can split primary / provisional /
audit / excluded rows without new evidence collection. It is not
`production_ready` unless a later PR changes production behavior and runs the
matching RAW validation gate.

## File Structure

- Create: `xic_extractor/alignment/machine_decision.py`
  - Owns the machine-decision vector dataclass, role/action literals, pure
    projection from review/cell TSV row mappings, and TSV serialization helpers.
  - Must not import CLI, writers, GUI, RAW readers, workbook code, or
    diagnostics.
- Create: `tests/test_alignment_machine_decision.py`
  - Unit tests for the projection helper independent of pipeline objects.
- Modify: `xic_extractor/alignment/matrix_identity.py`
  - Add explicit row flags for one-detected provisional retention candidates.
  - Preserve the existing `include_in_primary_matrix=False` behavior for
    one-detected-seed rows.
- Modify: `tests/test_alignment_matrix_identity.py`
  - Add regression coverage proving one-detected supported rescue evidence is
    retained as provisional and not promoted.
- Modify: `tests/test_alignment_tsv_writer.py`
  - Add contract coverage proving `alignment_review.tsv` schema stays stable
    while row flags express the provisional-retention candidate.
  - Prove `alignment_matrix.tsv` remains primary-only.
- Modify: `tools/diagnostics/analyze_matrix_identity_blast_radius.py`
  - Add projected `matrix_role`, `evidence_tier`, `support_reasons`, `blockers`,
    `confidence`, and `recommended_action` columns to this diagnostic output.
  - Do not create a new diagnostic entry-point.
- Modify: `tests/test_matrix_identity_blast_radius.py`
  - Prove the diagnostic includes one-detected provisional rows and projects
    `recommended_action=keep_provisional`.
- Modify: `tools/diagnostics/INDEX.md`
  - Update the existing `analyze_matrix_identity_blast_radius.py` purpose to
    mention the projected machine-decision vector.
- Create: `docs/superpowers/notes/2026-05-28-tiered-backfill-machine-decision-implementation-note.md`
  - Short handoff note with scope, verification, and residual risk.

## Now

### Task 0: Preflight Scope

**Files:**
- Read: `docs/superpowers/specs/2026-05-28-tiered-backfill-machine-decision-contract-spec.md`
- Read: `docs/agent-parameter-settings.md`
- Read: `tools/diagnostics/INDEX.md`

- [ ] **Step 1: Confirm branch and dirty scope**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## codex/tiered-backfill-machine-decision
```

If other dirty files appear, classify them before editing. Do not overwrite
unrelated user changes.

- [ ] **Step 2: Confirm CodeGraph index health**

Run:

```powershell
codegraph status
```

Expected: output contains `[OK] Index is up to date`.

If the output says the index is stale, run:

```powershell
codegraph sync .
```

Then re-run:

```powershell
codegraph status
```

Expected: output contains `[OK] Index is up to date`.

- [ ] **Step 3: Reconfirm no RAW gate is required for this PR**

Read:

```powershell
Get-Content -Raw docs\agent-parameter-settings.md
```

Expected decision: this plan does not launch RAW because it only adds
projection/row-flag/diagnostic behavior. Fresh 8RAW or 85RAW becomes required
only if implementation changes RAW-backed evidence execution, final matrix
inclusion, or Tier 2 evidence scope.

- [ ] **Step 4: Commit preflight plan checkpoint**

Run only after Task 0 has no blockers:

```powershell
git add docs\superpowers\plans\2026-05-28-tiered-backfill-machine-decision-contract-implementation-plan.md
git commit -m "docs: plan tiered backfill machine decision contract"
```

Expected: commit succeeds on the feature branch. If the execution policy for the
session does not allow commits, leave the plan unstaged and record that in the
handoff.

### Task 1: Pure Machine-Decision Projection Tests

**Files:**
- Create: `tests/test_alignment_machine_decision.py`
- Test: `tests/test_alignment_machine_decision.py`

- [ ] **Step 1: Write failing projection tests**

Create `tests/test_alignment_machine_decision.py` with this content:

```python
from __future__ import annotations

from xic_extractor.alignment.machine_decision import (
    machine_decision_as_row,
    project_machine_decision,
)


def test_primary_review_row_projects_to_use() -> None:
    vector = project_machine_decision(
        _review_row(
            include="TRUE",
            decision="production_family",
            confidence="high",
            reason="owner_complete_link",
            primary_evidence="owner_complete_link",
            detected=2,
            rescued=1,
        ),
        _cell_rows(detected=2, rescued=1),
    )

    assert vector.feature_family_id == "FAM001"
    assert vector.matrix_role == "primary"
    assert vector.evidence_tier == 1
    assert vector.support_reasons == (
        "detected_seed",
        "ms1_backfill_supported",
        "rt_coherent",
        "owner_complete_link",
    )
    assert vector.blockers == ()
    assert vector.confidence == "high"
    assert vector.recommended_action == "use"

    row = machine_decision_as_row(vector)
    assert row == {
        "matrix_role": "primary",
        "evidence_tier": "1",
        "support_reasons": "detected_seed;ms1_backfill_supported;rt_coherent;owner_complete_link",
        "blockers": "",
        "confidence": "high",
        "recommended_action": "use",
    }


def test_one_detected_seed_supported_rescue_projects_keep_provisional() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="provisional_discovery",
            confidence="review",
            reason="insufficient_detected_identity_support",
            primary_evidence="owner_complete_link",
            detected=1,
            rescued=2,
            flags="single_detected_seed;provisional_retention_candidate;skip_expensive_evidence",
        ),
        _cell_rows(detected=1, rescued=2),
    )

    assert vector.matrix_role == "provisional"
    assert vector.evidence_tier == 1
    assert vector.support_reasons == (
        "detected_seed",
        "ms1_backfill_supported",
        "rt_coherent",
        "owner_complete_link",
    )
    assert vector.blockers == (
        "single_detected_seed",
        "insufficient_detected_identity_support",
        "skip_expensive_evidence",
    )
    assert vector.confidence == "review"
    assert vector.recommended_action == "keep_provisional"


def test_rescue_only_row_projects_to_exclude_with_explicit_blocker() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="audit_family",
            confidence="review",
            reason="rescue_only_blocked",
            primary_evidence="owner_complete_link",
            detected=0,
            rescued=2,
            flags="rescue_only;rescue_only_review",
        ),
        _cell_rows(detected=0, rescued=2),
    )

    assert vector.matrix_role == "excluded"
    assert vector.recommended_action == "exclude"
    assert vector.blockers == ("rescue_only_blocked", "rescue_only")


def test_ambiguous_owner_row_projects_to_audit_review() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="audit_family",
            confidence="review",
            reason="ambiguous_only",
            primary_evidence="none",
            detected=0,
            rescued=0,
            ambiguous=2,
            flags="ambiguous_only;ambiguous_ms1_owner_pressure;zero_present",
        ),
        _cell_rows(detected=0, rescued=0, ambiguous=2),
    )

    assert vector.matrix_role == "audit"
    assert vector.recommended_action == "review"
    assert vector.blockers == (
        "ambiguous_only",
        "ambiguous_ms1_owner_pressure",
        "zero_present",
    )


def test_area_only_rescue_does_not_claim_ms1_backfill_support() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="provisional_discovery",
            confidence="review",
            reason="insufficient_detected_identity_support",
            primary_evidence="owner_complete_link",
            detected=1,
            rescued=2,
            flags="single_detected_seed",
        ),
        _cell_rows(
            detected=1,
            rescued=2,
            rescue_trace_quality="owner_backfill",
            rescue_scan_support_score="",
        ),
    )

    assert vector.matrix_role == "audit"
    assert vector.recommended_action == "review"
    assert "ms1_backfill_supported" not in vector.support_reasons
    assert "low_ms1_assessable_coverage_blocked" in vector.blockers


def test_neighboring_interference_rescue_does_not_claim_ms1_backfill_support() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="provisional_discovery",
            confidence="review",
            reason="insufficient_detected_identity_support",
            primary_evidence="owner_complete_link",
            detected=1,
            rescued=2,
            flags="single_detected_seed",
        ),
        _cell_rows(
            detected=1,
            rescued=2,
            rescue_region_review_reason="neighboring_ms1_interference",
        ),
    )

    assert vector.matrix_role == "audit"
    assert vector.recommended_action == "review"
    assert "ms1_backfill_supported" not in vector.support_reasons
    assert "neighboring_ms1_interference_blocked" in vector.blockers


def test_low_scan_support_rescue_does_not_claim_ms1_backfill_support() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="provisional_discovery",
            confidence="review",
            reason="insufficient_detected_identity_support",
            primary_evidence="owner_complete_link",
            detected=1,
            rescued=2,
            flags="single_detected_seed",
        ),
        _cell_rows(detected=1, rescued=2, rescue_scan_support_score="0.1"),
    )

    assert vector.matrix_role == "audit"
    assert vector.recommended_action == "review"
    assert "ms1_backfill_supported" not in vector.support_reasons
    assert "low_ms1_assessable_coverage_blocked" in vector.blockers


def test_generic_provisional_label_gets_explicit_missing_support_blocker() -> None:
    vector = project_machine_decision(
        _review_row(
            include="FALSE",
            decision="provisional_discovery",
            confidence="review",
            reason="",
            primary_evidence="single_sample_local_owner",
            detected=1,
            rescued=0,
        ),
        _cell_rows(detected=1, rescued=0),
    )

    assert vector.matrix_role == "provisional"
    assert vector.recommended_action == "keep_provisional"
    assert vector.blockers == ("single_detected_seed", "insufficient_identity_support")


def _review_row(
    *,
    include: str,
    decision: str,
    confidence: str,
    reason: str,
    primary_evidence: str,
    detected: int,
    rescued: int,
    duplicate: int = 0,
    ambiguous: int = 0,
    flags: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "include_in_primary_matrix": include,
        "identity_decision": decision,
        "identity_confidence": confidence,
        "identity_reason": reason,
        "primary_evidence": primary_evidence,
        "quantifiable_detected_count": str(detected),
        "quantifiable_rescue_count": str(rescued),
        "accepted_rescue_count": str(rescued),
        "duplicate_assigned_count": str(duplicate),
        "ambiguous_ms1_owner_count": str(ambiguous),
        "row_flags": flags,
    }


def _cell_rows(
    *,
    detected: int,
    rescued: int,
    duplicate: int = 0,
    ambiguous: int = 0,
    rescue_trace_quality: str = "clean",
    rescue_scan_support_score: str = "0.8",
    rescue_reason: str = "rescued",
    rescue_region_review_reason: str = "",
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index in range(detected):
        rows.append(_cell_row(index, "detected", "1000"))
    for index in range(detected, detected + rescued):
        rows.append(
            _cell_row(
                index,
                "rescued",
                "500",
                trace_quality=rescue_trace_quality,
                scan_support_score=rescue_scan_support_score,
                reason=rescue_reason,
                region_review_reason=rescue_region_review_reason,
            ),
        )
    for index in range(detected + rescued, detected + rescued + duplicate):
        rows.append(_cell_row(index, "duplicate_assigned", ""))
    for index in range(
        detected + rescued + duplicate,
        detected + rescued + duplicate + ambiguous,
    ):
        rows.append(_cell_row(index, "ambiguous_ms1_owner", ""))
    return tuple(rows)


def _cell_row(
    index: int,
    status: str,
    area: str,
    *,
    trace_quality: str | None = None,
    scan_support_score: str | None = None,
    reason: str | None = None,
    region_review_reason: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "sample_stem": f"S{index + 1:03d}",
        "status": status,
        "area": area,
        "apex_rt": "8.0" if area else "",
        "height": "100" if area else "",
        "peak_start_rt": "7.95" if area else "",
        "peak_end_rt": "8.05" if area else "",
        "rt_delta_sec": "0.0" if area else "",
        "trace_quality": (
            trace_quality
            if trace_quality is not None
            else ("clean" if area else status)
        ),
        "scan_support_score": (
            scan_support_score
            if scan_support_score is not None
            else ("0.8" if area else "")
        ),
        "reason": reason if reason is not None else status,
        "region_review_reason": region_review_reason,
    }
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_machine_decision.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.machine_decision'`.

- [ ] **Step 3: Commit failing tests**

Run:

```powershell
git add tests\test_alignment_machine_decision.py
git commit -m "test: specify alignment machine decision projection"
```

Expected: commit succeeds if the execution mode permits test-first commits.

### Task 2: Implement Pure Projection Helper

**Files:**
- Create: `xic_extractor/alignment/machine_decision.py`
- Test: `tests/test_alignment_machine_decision.py`

- [ ] **Step 1: Add the projection module**

Create `xic_extractor/alignment/machine_decision.py` with this content:

```python
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from xic_extractor.alignment.promotion_policy import (
    LOW_MS1_COVERAGE_BLOCKED_REASON,
    NEIGHBOR_INTERFERENCE_BLOCKED_REASON,
    BackfillPromotionEvidence,
    evidence_from_tsv_rows,
)

MatrixRole = Literal["primary", "provisional", "audit", "excluded"]
EvidenceTier = Literal[0, 1, 2, 3]
RecommendedAction = Literal["use", "keep_provisional", "exclude", "review"]
MachineConfidence = Literal["high", "medium", "review", "none"]

_EXCLUDE_BLOCKERS = {
    "family_consolidation_loser",
    "duplicate_only",
    "zero_present",
    "rescue_only",
    "rescue_only_blocked",
}
_AUDIT_BLOCKERS = {
    "review_only",
    "ambiguous_only",
    "ambiguous_ms1_owner_pressure",
    "duplicate_claim_pressure",
    "low_ms1_assessable_coverage",
    "low_ms1_assessable_coverage_blocked",
    "neighboring_ms1_interference",
    "neighboring_ms1_interference_blocked",
}
_SUPPORT_PRIMARY_EVIDENCE = {
    "owner_complete_link",
    "owner_identity",
    "cid_nl_only",
    "multi_sample_detected",
    "anchored_family",
}
_NON_BLOCKING_IDENTITY_REASONS = {
    *_SUPPORT_PRIMARY_EVIDENCE,
    "cell_evidence_supported_backfill",
    "dda_limited_ms2_but_ms1_shape_supported",
    "weak_seed_tolerated",
}
_GENERIC_PROVISIONAL_REASONS = {"", "provisional_discovery"}


@dataclass(frozen=True)
class MachineDecisionVector:
    feature_family_id: str
    matrix_role: MatrixRole
    evidence_tier: EvidenceTier
    support_reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    confidence: MachineConfidence
    recommended_action: RecommendedAction


def project_machine_decision(
    review_row: Mapping[str, object],
    cell_rows: Sequence[Mapping[str, object]] = (),
) -> MachineDecisionVector:
    feature_family_id = _text(review_row.get("feature_family_id"))
    include_primary = _is_trueish(review_row.get("include_in_primary_matrix"))
    identity_decision = _text(review_row.get("identity_decision"))
    identity_reason = _text(review_row.get("identity_reason"))
    primary_evidence = _text(review_row.get("primary_evidence"))
    confidence = _confidence(review_row.get("identity_confidence"))
    flags = _split_tokens(review_row.get("row_flags"))
    q_detected = _int_value(
        review_row.get("quantifiable_detected_count")
        or review_row.get("detected_count")
    )
    q_rescue = _int_value(
        review_row.get("quantifiable_rescue_count")
        or review_row.get("accepted_rescue_count")
    )
    promotion_evidence = evidence_from_tsv_rows(
        _string_row(review_row),
        _string_rows(cell_rows),
        seed_quality=None,
        sample_count=len(cell_rows),
    )

    blockers = _blockers(
        identity_reason=identity_reason,
        flags=flags,
        q_detected=q_detected,
        identity_decision=identity_decision,
        cell_evidence_blockers=_cell_evidence_blockers(promotion_evidence),
    )
    support_reasons = _support_reasons(
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        promotion_evidence=promotion_evidence,
    )
    matrix_role = _matrix_role(
        include_primary=include_primary,
        identity_decision=identity_decision,
        blockers=blockers,
    )
    if matrix_role == "provisional" and not blockers:
        blockers = ("insufficient_identity_support",)

    return MachineDecisionVector(
        feature_family_id=feature_family_id,
        matrix_role=matrix_role,
        evidence_tier=_evidence_tier(cell_rows),
        support_reasons=support_reasons,
        blockers=blockers,
        confidence=confidence,
        recommended_action=_recommended_action(matrix_role),
    )


def machine_decision_as_row(vector: MachineDecisionVector) -> dict[str, str]:
    return {
        "matrix_role": vector.matrix_role,
        "evidence_tier": str(vector.evidence_tier),
        "support_reasons": ";".join(vector.support_reasons),
        "blockers": ";".join(vector.blockers),
        "confidence": vector.confidence,
        "recommended_action": vector.recommended_action,
    }


def _matrix_role(
    *,
    include_primary: bool,
    identity_decision: str,
    blockers: tuple[str, ...],
) -> MatrixRole:
    blocker_set = set(blockers)
    if include_primary and identity_decision == "production_family":
        return "primary"
    if identity_decision == "audit_family":
        if blocker_set & _AUDIT_BLOCKERS:
            return "audit"
        if blocker_set & _EXCLUDE_BLOCKERS:
            return "excluded"
        return "audit"
    if blocker_set & _AUDIT_BLOCKERS:
        return "audit"
    if blocker_set & _EXCLUDE_BLOCKERS:
        return "excluded"
    if identity_decision == "provisional_discovery":
        return "provisional"
    return "audit"


def _recommended_action(matrix_role: MatrixRole) -> RecommendedAction:
    if matrix_role == "primary":
        return "use"
    if matrix_role == "provisional":
        return "keep_provisional"
    if matrix_role == "excluded":
        return "exclude"
    return "review"


def _support_reasons(
    *,
    primary_evidence: str,
    q_detected: int,
    q_rescue: int,
    promotion_evidence: BackfillPromotionEvidence,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if q_detected > 0:
        reasons.append("detected_seed")
    if q_rescue > 0 and _has_supported_rescue_cell(promotion_evidence):
        reasons.append("ms1_backfill_supported")
    if _has_rt_coherent_cell(promotion_evidence):
        reasons.append("rt_coherent")
    if primary_evidence in _SUPPORT_PRIMARY_EVIDENCE:
        reasons.append(primary_evidence)
    return tuple(dict.fromkeys(reasons))


def _blockers(
    *,
    identity_reason: str,
    flags: tuple[str, ...],
    q_detected: int,
    identity_decision: str,
    cell_evidence_blockers: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if q_detected == 1:
        blockers.append("single_detected_seed")
    if (
        identity_reason not in _GENERIC_PROVISIONAL_REASONS
        and identity_reason not in _NON_BLOCKING_IDENTITY_REASONS
    ):
        blockers.append(identity_reason)
    for flag in flags:
        if flag in _EXCLUDE_BLOCKERS or flag in _AUDIT_BLOCKERS:
            blockers.append(flag)
        elif flag in {"skip_expensive_evidence", "single_detected_seed"}:
            blockers.append(flag)
    blockers.extend(cell_evidence_blockers)
    if (
        identity_decision == "provisional_discovery"
        and identity_reason in _GENERIC_PROVISIONAL_REASONS
        and "insufficient_identity_support" not in blockers
    ):
        blockers.append("insufficient_identity_support")
    return tuple(dict.fromkeys(blockers))


def _evidence_tier(cell_rows: Sequence[Mapping[str, object]]) -> EvidenceTier:
    if cell_rows:
        return 1
    return 0


def _has_supported_rescue_cell(evidence: BackfillPromotionEvidence) -> bool:
    return any(
        cell.status == "rescued"
        and cell.is_rescued_quantifiable
        and cell.supported_for_backfill
        for cell in evidence.cells
    )


def _cell_evidence_blockers(
    evidence: BackfillPromotionEvidence,
) -> tuple[str, ...]:
    rescued = tuple(cell for cell in evidence.cells if cell.status == "rescued")
    if not rescued:
        return ()

    blockers: list[str] = []
    if any(cell.high_neighbor_interference for cell in rescued):
        blockers.append(NEIGHBOR_INTERFERENCE_BLOCKED_REASON)
    elif any(
        cell.low_assessable_coverage or not cell.local_apex_supported
        for cell in rescued
    ):
        blockers.append(LOW_MS1_COVERAGE_BLOCKED_REASON)
    elif not any(
        cell.is_rescued_quantifiable and cell.supported_for_backfill
        for cell in rescued
    ):
        blockers.append(LOW_MS1_COVERAGE_BLOCKED_REASON)
    return tuple(dict.fromkeys(blockers))


def _has_rt_coherent_cell(evidence: BackfillPromotionEvidence) -> bool:
    return any(cell.local_apex_supported for cell in evidence.cells)


def _confidence(value: object) -> MachineConfidence:
    text = _text(value)
    if text in {"high", "medium", "review", "none"}:
        return text  # type: ignore[return-value]
    return "review"


def _split_tokens(value: object) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in _text(value).split(";")
        if part and part.strip()
    )


def _is_trueish(value: object) -> bool:
    return _text(value).lower() in {"1", "true", "t", "yes", "y"}


def _int_value(value: object) -> int:
    number = _positive_or_zero_float(value)
    return 0 if number is None else int(number)


def _positive_float(value: object) -> float | None:
    number = _positive_or_zero_float(value)
    if number is None or number <= 0.0:
        return None
    return number


def _positive_or_zero_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("'"):
        text = text[1:]
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _string_rows(
    rows: Sequence[Mapping[str, object]],
) -> tuple[dict[str, str], ...]:
    return tuple(_string_row(row) for row in rows)


def _string_row(row: Mapping[str, object]) -> dict[str, str]:
    return {str(key): _text(value) for key, value in row.items()}
```

- [ ] **Step 2: Run projection tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_machine_decision.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit projection helper**

Run:

```powershell
git add xic_extractor\alignment\machine_decision.py tests\test_alignment_machine_decision.py
git commit -m "feat: add alignment machine decision projection"
```

Expected: commit succeeds.

### Task 3: Mark One-Detected Provisional Retention In Existing Row Fields

**Files:**
- Modify: `xic_extractor/alignment/matrix_identity.py`
- Modify: `tests/test_alignment_matrix_identity.py`
- Test: `tests/test_alignment_matrix_identity.py`

- [ ] **Step 1: Add the failing matrix-identity regression**

Add this test near `test_single_detected_seed_does_not_enter_policy_promotion`
in `tests/test_alignment_matrix_identity.py`:

```python
def test_one_detected_seed_with_supported_rescue_is_provisional_retention_candidate() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=1"),
        (
            _cell("seed1", "FAM001", "detected", 100.0),
            _cell("rescue1", "FAM001", "rescued", 90.0),
            _cell("rescue2", "FAM001", "rescued", 80.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.quantifiable_detected_count == 1
    assert decision.quantifiable_rescue_count == 2
    assert "single_detected_seed" in decision.row_flags
    assert "provisional_retention_candidate" in decision.row_flags
    assert "skip_expensive_evidence" in decision.row_flags


def test_one_detected_area_only_rescue_is_not_provisional_retention_candidate() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=1"),
        (
            _cell("seed1", "FAM001", "detected", 100.0),
            _cell(
                "rescue1",
                "FAM001",
                "rescued",
                90.0,
                trace_quality="owner_backfill",
                scan_support_score=None,
            ),
            _cell(
                "rescue2",
                "FAM001",
                "rescued",
                80.0,
                trace_quality="owner_backfill",
                scan_support_score=None,
            ),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert "single_detected_seed" in decision.row_flags
    assert "provisional_retention_candidate" not in decision.row_flags
    assert "skip_expensive_evidence" not in decision.row_flags


def test_review_only_one_detected_rescue_is_not_provisional_retention_candidate() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="owner_complete_link;owner_count=1",
            review_only=True,
        ),
        (
            _cell("seed1", "FAM001", "detected", 100.0),
            _cell("rescue1", "FAM001", "rescued", 90.0),
            _cell("rescue2", "FAM001", "rescued", 80.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.identity_decision == "audit_family"
    assert decision.identity_reason == "review_only"
    assert "single_detected_seed" in decision.row_flags
    assert "provisional_retention_candidate" not in decision.row_flags
    assert "skip_expensive_evidence" not in decision.row_flags
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_matrix_identity.py -q
```

Expected: FAIL because the supported-retention row flags are not present.

- [ ] **Step 3: Add row flags without changing primary promotion**

In `xic_extractor/alignment/matrix_identity.py`, add `BackfillPromotionEvidence`
to the existing `promotion_policy` import:

```python
from xic_extractor.alignment.promotion_policy import (
    RESCUE_ONLY_BLOCKED_REASON,
    BackfillPromotionDecision,
    BackfillPromotionEvidence,
    classify_backfill_promotion,
    evidence_from_alignment,
)
```

Add this helper after `_row_flags()`:

```python
def _is_provisional_retention_candidate(
    *,
    cluster: Any,
    q_detected: int,
    q_rescue: int,
    duplicate_count: int,
    ambiguous_count: int,
    primary_evidence: str,
    policy_evidence: BackfillPromotionEvidence,
) -> bool:
    if bool(getattr(cluster, "review_only", False)):
        return False
    if primary_evidence in {"none", "single_sample_local_owner"}:
        return False
    if q_detected != 1 or q_rescue <= 0:
        return False
    if duplicate_count != 0 or ambiguous_count != 0:
        return False

    supported_rescue_count = sum(
        1
        for cell in policy_evidence.cells
        if cell.status == "rescued"
        and cell.is_rescued_quantifiable
        and cell.supported_for_backfill
    )
    return supported_rescue_count == q_rescue
```

Inside `_row_flags()`, after the existing `anchored_single_detected` block,
add only the explicit one-detected marker:

```python
    if q_detected == 1:
        flags.append("single_detected_seed")
```

Inside `decide_matrix_identity_row()`, after
`promotion_policy = classify_backfill_promotion(policy_evidence)` and before
`flags.extend(promotion_policy.flags)`, add the supported provisional-retention
flags:

```python
    if _is_provisional_retention_candidate(
        cluster=cluster,
        q_detected=q_detected,
        q_rescue=q_rescue,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
        primary_evidence=primary_evidence,
        policy_evidence=policy_evidence,
    ):
        flags.append("provisional_retention_candidate")
        flags.append("skip_expensive_evidence")
```

Do not change `_promotion_decision()` in this task. The expected behavior is
still `include_in_primary_matrix=False` for one-detected-seed rows. The
candidate flag must depend on the existing `promotion_policy` cell-support
oracle; do not use area-only rescue evidence as support.

- [ ] **Step 4: Run focused matrix identity tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_matrix_identity.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit row-flag behavior**

Run:

```powershell
git add xic_extractor\alignment\matrix_identity.py tests\test_alignment_matrix_identity.py
git commit -m "feat: mark one detected provisional retention candidates"
```

Expected: commit succeeds.

### Task 4: Preserve TSV Contracts And Primary Matrix Filtering

**Files:**
- Modify: `tests/test_alignment_tsv_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Add TSV regression coverage**

Add this test after
`test_write_alignment_review_tsv_includes_production_decision_columns` in
`tests/test_alignment_tsv_writer.py`:

```python
def test_one_detected_provisional_retention_stays_out_of_primary_matrix(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import (
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

    review_rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))
    matrix_rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert list(review_rows[0]) == REVIEW_COLUMNS
    assert review_rows[0]["identity_decision"] == "provisional_discovery"
    assert review_rows[0]["include_in_primary_matrix"] == "FALSE"
    assert review_rows[0]["quantifiable_detected_count"] == "1"
    assert review_rows[0]["quantifiable_rescue_count"] == "2"
    assert set(review_rows[0]["row_flags"].split(";")) >= {
        "single_detected_seed",
        "provisional_retention_candidate",
        "skip_expensive_evidence",
    }
    assert matrix_rows == []
```

- [ ] **Step 2: Run TSV writer tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_tsv_writer.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit TSV contract coverage**

Run:

```powershell
git add tests\test_alignment_tsv_writer.py
git commit -m "test: keep provisional retention out of primary matrix"
```

Expected: commit succeeds.

### Task 5: Expose Projection In Existing Blast-Radius Diagnostic

**Files:**
- Modify: `tools/diagnostics/analyze_matrix_identity_blast_radius.py`
- Modify: `tests/test_matrix_identity_blast_radius.py`
- Modify: `tools/diagnostics/INDEX.md`
- Test: `tests/test_matrix_identity_blast_radius.py`

- [ ] **Step 1: Add failing diagnostic regression**

Add this test after
`test_blast_radius_reports_complete_identity_changes_and_benchmark_join` in
`tests/test_matrix_identity_blast_radius.py`:

```python
def test_blast_radius_projects_one_detected_provisional_action(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_run(
        tmp_path / "alignment",
        review_rows=[
            _review_row("FAM_ONE", "FALSE", "owner_complete_link;owner_count=1"),
        ],
        cell_rows=[
            _cell_row("FAM_ONE", "sample-a", "detected", 100.0),
            _cell_row(
                "FAM_ONE",
                "sample-b",
                "rescued",
                90.0,
                trace_quality="clean",
                scan_support_score=0.8,
            ),
            _cell_row(
                "FAM_ONE",
                "sample-c",
                "rescued",
                80.0,
                trace_quality="clean",
                scan_support_score=0.8,
            ),
        ],
    )

    code = blast.main(
        [
            "--alignment-run",
            str(alignment_dir),
            "--output-dir",
            str(tmp_path / "blast"),
        ],
    )

    assert code == 0
    rows = _read_tsv(tmp_path / "blast" / "matrix_identity_blast_radius.tsv")
    by_id = {row["feature_family_id"]: row for row in rows}

    assert by_id["FAM_ONE"]["identity_decision"] == "provisional_discovery"
    assert by_id["FAM_ONE"]["matrix_role"] == "provisional"
    assert by_id["FAM_ONE"]["recommended_action"] == "keep_provisional"
    assert by_id["FAM_ONE"]["evidence_tier"] == "1"
    assert "single_detected_seed" in by_id["FAM_ONE"]["blockers"]
    assert "ms1_backfill_supported" in by_id["FAM_ONE"]["support_reasons"]
```

In the same file, replace the `_cell_row()` helper with this version so the
diagnostic fixture can express independent support instead of area-only
owner-backfill provenance:

```python
def _cell_row(
    family_id: str,
    sample: str,
    status: str,
    area: float,
    *,
    trace_quality: str = "",
    scan_support_score: float | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": status,
        "area": area,
        "apex_rt": 8.5,
        "height": 100.0,
        "peak_start_rt": 8.4,
        "peak_end_rt": 8.6,
        "rt_delta_sec": 0.0,
        "trace_quality": trace_quality,
        "scan_support_score": scan_support_score,
        "reason": reason if reason is not None else status,
    }
```

- [ ] **Step 2: Run diagnostic test and verify it fails**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_matrix_identity_blast_radius.py::test_blast_radius_projects_one_detected_provisional_action -q
```

Expected: FAIL because the diagnostic does not emit `matrix_role` or
`recommended_action`.

- [ ] **Step 3: Add projection columns to the diagnostic**

In `tools/diagnostics/analyze_matrix_identity_blast_radius.py`, add this import:

```python
from xic_extractor.alignment.machine_decision import (
    machine_decision_as_row,
    project_machine_decision,
)
```

Add these names to `OUTPUT_COLUMNS` immediately after `"row_flags"`:

```python
    "matrix_role",
    "evidence_tier",
    "support_reasons",
    "blockers",
    "confidence",
    "recommended_action",
```

Inside `run_blast_radius()`, after `current_by_family` is built, add:

```python
    cell_rows_by_family = _cell_rows_by_family(cell_rows)
```

Inside the `for family_id in sorted(decisions.rows):` loop, before
`rows.append(...)`, add:

```python
        projected_review_row = {
            "feature_family_id": family_id,
            "include_in_primary_matrix": proposed_include,
            "identity_decision": row_decision.identity_decision,
            "identity_confidence": row_decision.identity_confidence,
            "identity_reason": row_decision.identity_reason,
            "primary_evidence": row_decision.primary_evidence,
            "quantifiable_detected_count": row_decision.quantifiable_detected_count,
            "quantifiable_rescue_count": row_decision.quantifiable_rescue_count,
            "accepted_rescue_count": row_decision.quantifiable_rescue_count,
            "duplicate_assigned_count": row_decision.duplicate_assigned_count,
            "ambiguous_ms1_owner_count": row_decision.ambiguous_ms1_owner_count,
            "row_flags": ";".join(row_decision.row_flags),
        }
        machine_decision = project_machine_decision(
            projected_review_row,
            cell_rows_by_family.get(family_id, ()),
        )
```

In the dict passed to `rows.append(...)`, add:

```python
                **machine_decision_as_row(machine_decision),
```

Add these empty values to `_incomplete_rows()` after `"row_flags": ""`:

```python
                "matrix_role": "",
                "evidence_tier": "",
                "support_reasons": "",
                "blockers": "",
                "confidence": "",
                "recommended_action": "",
```

Add this helper near `_alignment_matrix_from_tsv()`:

```python
def _cell_rows_by_family(
    cell_rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for row in cell_rows:
        grouped.setdefault(row.get("feature_family_id", ""), []).append(row)
    return {family_id: tuple(rows) for family_id, rows in grouped.items()}
```

- [ ] **Step 4: Update the diagnostic index entry**

In `tools/diagnostics/INDEX.md`, update the `analyze_matrix_identity_blast_radius.py`
purpose line to:

```markdown
**Purpose**: Analyze matrix identity blast radius for alignment outputs, including projected machine-decision role/action columns from existing review and cell artifacts.
```

- [ ] **Step 5: Run diagnostic tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_matrix_identity_blast_radius.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit diagnostic consumer**

Run:

```powershell
git add tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py tools\diagnostics\INDEX.md
git commit -m "feat: project machine decisions in matrix identity diagnostic"
```

Expected: commit succeeds.

### Task 6: Add Implementation Note

**Files:**
- Create: `docs/superpowers/notes/2026-05-28-tiered-backfill-machine-decision-implementation-note.md`

- [ ] **Step 1: Write the implementation note**

Create `docs/superpowers/notes/2026-05-28-tiered-backfill-machine-decision-implementation-note.md`
with this content after code and diagnostic tests pass:

```markdown
# Tiered Backfill Machine Decision Implementation Note

## Verdict

`diagnostic_only`

The first tiered-backfill machine-decision contract is implemented as a pure
projection over existing alignment review/cell artifacts. It does not change
`alignment_matrix.tsv` schema or primary inclusion semantics.

## Scope Implemented

- One-detected-seed rows with supported rescue evidence stay
  `identity_decision=provisional_discovery`.
- Such rows receive explicit row flags:
  `single_detected_seed`, `provisional_retention_candidate`, and
  `skip_expensive_evidence`.
- `xic_extractor.alignment.machine_decision.project_machine_decision()` maps
  existing review/cell fields to `matrix_role`, `evidence_tier`,
  `support_reasons`, `blockers`, `confidence`, and `recommended_action`.
- `tools/diagnostics/analyze_matrix_identity_blast_radius.py` displays the
  projected vector for machine gate review.

## Out Of Scope

- Tier 2 evidence routing.
- New `provisional-candidates` execution scope.
- Skipped-evidence ledger.
- New sidecar schema.
- `alignment_matrix.tsv` schema or primary-matrix inclusion changes.
- Fresh RAW validation.

## Verification

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_machine_decision.py tests\test_alignment_matrix_identity.py tests\test_alignment_tsv_writer.py tests\test_matrix_identity_blast_radius.py -q
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_untargeted_final_matrix_contract.py tests\test_targeted_gt_alignment_audit.py tests\test_targeted_istd_benchmark.py -q
```

```powershell
git diff --check
```

## Remaining Risk

The vector is currently a projection contract, not a new production schema.
Downstream correction/statistics tools remain protected because
`alignment_matrix.tsv` stays primary-only. If a later PR needs durable external
consumption of provisional rows, it should add a versioned sidecar with schema
tests and named consumers.

The implementation can be relabeled `shadow_ready` only after a current
existing-artifact smoke classification, or an explicitly hash-pinned 8RAW gate
artifact, proves the projection can split primary / provisional / audit /
excluded rows without new evidence collection.
```

- [ ] **Step 2: Commit the implementation note**

Run:

```powershell
git add docs\superpowers\notes\2026-05-28-tiered-backfill-machine-decision-implementation-note.md
git commit -m "docs: record tiered backfill machine decision status"
```

Expected: commit succeeds.

### Task 7: Focused Verification And Review

**Files:**
- Verify: all files changed by Tasks 1-6

- [ ] **Step 1: Run focused synthetic verification**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_machine_decision.py tests\test_alignment_matrix_identity.py tests\test_alignment_tsv_writer.py tests\test_matrix_identity_blast_radius.py -q
```

Expected: PASS.

- [ ] **Step 2: Run downstream primary-filter guard tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_untargeted_final_matrix_contract.py tests\test_targeted_gt_alignment_audit.py tests\test_targeted_istd_benchmark.py -q
```

Expected: PASS.

- [ ] **Step 3: Run ruff on changed Python files**

Run:

```powershell
$pyFiles = @(
  'xic_extractor\alignment\machine_decision.py',
  'xic_extractor\alignment\matrix_identity.py',
  'tools\diagnostics\analyze_matrix_identity_blast_radius.py',
  'tests\test_alignment_machine_decision.py',
  'tests\test_alignment_matrix_identity.py',
  'tests\test_alignment_tsv_writer.py',
  'tests\test_matrix_identity_blast_radius.py'
)
python -m ruff check $pyFiles
```

Expected: PASS. If commits were not created during execution, use:

```powershell
$pyFiles = git ls-files --modified --others --exclude-standard -- '*.py'
python -m ruff check $pyFiles
```

Expected: PASS.

- [ ] **Step 4: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 5: Review public contract drift**

Check these facts manually from the diff:

```powershell
git diff -- xic_extractor\alignment\tsv_writer.py
git diff -- tools\diagnostics\analyze_matrix_identity_blast_radius.py
git diff -- xic_extractor\alignment\matrix_identity.py
```

Expected:

- `ALIGNMENT_REVIEW_COLUMNS` is unchanged.
- `ALIGNMENT_CELLS_COLUMNS` is unchanged.
- `write_alignment_matrix_tsv()` schema and row filter are unchanged.
- Only the blast-radius diagnostic output schema grows.
- No Tier 2 scope or RAW runner is introduced.

- [ ] **Step 6: Confirm readiness label**

Check the implementation note and final handoff wording.

Expected:

- The default implementation verdict is `diagnostic_only`.
- The work is not called `shadow_ready` unless a current existing-artifact smoke
  classification or explicitly hash-pinned 8RAW gate artifact is cited.
- The work is not called `production_ready`.

- [ ] **Step 7: Final commit if verification fixes were needed**

If Task 7 required fixes, commit them:

```powershell
git add xic_extractor\alignment\machine_decision.py xic_extractor\alignment\matrix_identity.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_alignment_machine_decision.py tests\test_alignment_matrix_identity.py tests\test_alignment_tsv_writer.py tests\test_matrix_identity_blast_radius.py tools\diagnostics\INDEX.md docs\superpowers\notes\2026-05-28-tiered-backfill-machine-decision-implementation-note.md
git commit -m "fix: harden tiered backfill machine decision contract"
```

Expected: commit succeeds only if there are verification fixes to record.

## Later

- Add a versioned sidecar only if downstream consumers need durable
  `matrix_role` / `recommended_action` fields outside diagnostics.
- Add a `provisional-candidates` scope only after a named validation gate can
  consume it.
- Add skipped-evidence ledger only with a schema/header test and named gate
  consumer.
- Revisit ASLS / boundary behavior after this row-role contract is stable.

## Not In Scope

- Rewriting the alignment pipeline into multiple pipeline paths.
- Changing `alignment_matrix.tsv` schema, values, or inclusion semantics.
- Promoting one-detected-seed rows to primary output.
- Running Tier 2 overlays, re-extracted XIC windows, or targeted benchmark
  context by default.
- Adding new HTML/XLSX review outputs.
- Creating a new diagnostic entry-point.
- Changing targeted extractor scoring or targeted workbook behavior.

## Stop Rules

Stop and report before continuing if:

- `project_machine_decision()` cannot produce deterministic role/action values
  from existing review/cell fields;
- the projection cannot reuse the existing `promotion_policy` cell-support
  oracle, or an equivalent local wrapper, to distinguish supported rescue cells
  from area-only owner-backfill provenance;
- one-detected provisional retention requires changing `alignment_matrix.tsv`;
- implementation needs Tier 2 evidence routing to pass synthetic tests;
- a provisional row would be emitted with only a generic
  `provisional_discovery` label and no explicit blocker or missing-evidence
  reason;
- diagnostic implementation starts recomputing RAW evidence or rescanning RAW
  files;
- public review/cell TSV schema changes appear necessary;
- focused tests show downstream targeted benchmark consumers count provisional
  rows as primary.

## Acceptance

- `project_machine_decision()` maps:
  - primary row -> `matrix_role=primary`, `recommended_action=use`;
  - one detected seed plus supported rescue evidence ->
    `matrix_role=provisional`, `recommended_action=keep_provisional`;
  - one detected seed plus area-only, low-coverage, or neighboring-interference
    rescue evidence -> `matrix_role=audit`, `recommended_action=review`;
  - rescue-only / duplicate-only / structural zero-present /
    consolidation-loser rows -> `matrix_role=excluded`,
    `recommended_action=exclude`;
  - ambiguous or review-only rows -> `matrix_role=audit`,
    `recommended_action=review`.
- One-detected supported rescue rows remain
  `include_in_primary_matrix=FALSE`.
- `alignment_matrix.tsv` remains primary-only.
- `ALIGNMENT_REVIEW_COLUMNS` and `ALIGNMENT_CELLS_COLUMNS` remain unchanged.
- The blast-radius diagnostic includes one-detected provisional rows even though
  they are outside the current single-dR gate report focus.
- All focused verification commands pass.

## Self-Review Record

- Spec coverage: the plan covers first-PR scope, one-detected retention,
  projection helper, primary-only matrix preservation, diagnostic visibility,
  tests, docs, and stop rules. Tier 2 routing, sidecars, broad pipeline splits,
  skipped-evidence ledger, and RAW reruns are explicitly out of scope.
- Placeholder scan: the plan contains concrete files, commands, code snippets,
  expected outcomes, and no deferred implementation labels.
- Type consistency: `MachineDecisionVector`, `project_machine_decision()`, and
  `machine_decision_as_row()` are introduced in Task 2 and referenced with the
  same names in later tests and diagnostic wiring.
- Sub-agent review fixes: the plan now reuses the existing
  `promotion_policy` cell-support oracle, keeps ambiguous/review-only rows in
  audit precedence, excludes `review_only` from provisional-retention flags,
  and keeps the default implementation verdict at `diagnostic_only`.
