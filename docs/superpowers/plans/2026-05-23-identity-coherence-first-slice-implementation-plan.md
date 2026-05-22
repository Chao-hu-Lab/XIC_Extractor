# Identity Coherence First Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first domain-only identity coherence slice: schema constants, `FragmentIdentity` request models, tag normalization, and a duck-typed request builder.

**Architecture:** The slice creates a small `xic_extractor.alignment.identity_coherence` domain package. It does not connect RAW/XIC extraction, alignment orchestration, Backfill, TSV writers, CLI, workbook, or report surfaces.

**Tech Stack:** Python dataclasses, `enum.StrEnum`, pytest, Markdown schema marker parsing.

**Version note:** This plan follows the repo's current `StrEnum` pattern. If CI
or packaging still claims Python 3.10 support, correct that Python-version
contract in a separate task; do not hide the version decision inside this slice.

---

## Scope

Create or modify only these files:

```text
xic_extractor/alignment/identity_coherence/__init__.py
xic_extractor/alignment/identity_coherence/models.py
xic_extractor/alignment/identity_coherence/schema.py
xic_extractor/alignment/identity_coherence/request_builder.py
tests/alignment/identity_coherence/test_schema_contract.py
tests/alignment/identity_coherence/test_fragment_identity_request_builder.py
```

Do not modify:

```text
scripts/run_alignment.py
xic_extractor/alignment/owner_backfill.py
xic_extractor/alignment/ownership.py
xic_extractor/alignment/tsv_writer.py
xic_extractor/alignment/xlsx_writer.py
tools/diagnostics/*
```

The implementation contract is:

```text
docs/superpowers/specs/2026-05-22-untargeted-identity-coherence-implementation-contract.md
```

## File Responsibilities

- `schema.py`: ordered tuple constants for frozen TSV schemas and `StrEnum` categorical values.
- `models.py`: domain dataclasses only. No IO, no RAW, no `DiscoveryCandidate` import.
- `request_builder.py`: adapter from duck-typed candidate-like object to `IdentityCoherenceRequest`.
- `__init__.py`: thin facade re-exporting stable domain API.
- `test_schema_contract.py`: schema marker parity and enum contract tests.
- `test_fragment_identity_request_builder.py`: request builder and tag normalization behavior.

## Task 1: Add Schema Constants And Enums

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/schema.py`
- Create: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Write failing schema tests**

```python
from pathlib import Path

from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-05-22-untargeted-identity-coherence-implementation-contract.md"
)


def _schema_block(name: str) -> tuple[str, ...]:
    start = f"<!-- schema:{name}:start -->"
    end = f"<!-- schema:{name}:end -->"
    in_block = False
    values: list[str] = []
    for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines():
        if line == start:
            in_block = True
            continue
        if line == end:
            break
        if in_block and line:
            values.append(line)
    assert values, f"schema marker block not found: {name}"
    return tuple(values)


def test_schema_constants_match_contract_marker_blocks():
    assert IDENTITY_COHERENCE_REQUEST_COLUMNS == _schema_block(
        "identity_coherence_requests.tsv"
    )
    assert IDENTITY_COHERENCE_DECISION_COLUMNS == _schema_block(
        "identity_coherence_decisions.tsv"
    )
    assert IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS == _schema_block(
        "identity_coherence_cell_evidence.tsv"
    )
    assert IDENTITY_COHERENCE_CONTROL_COLUMNS == _schema_block(
        "identity_coherence_controls.tsv"
    )


def test_schema_constants_have_no_duplicates():
    for columns in (
        IDENTITY_COHERENCE_REQUEST_COLUMNS,
        IDENTITY_COHERENCE_DECISION_COLUMNS,
        IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
        IDENTITY_COHERENCE_CONTROL_COLUMNS,
    ):
        assert len(columns) == len(set(columns))


def test_request_status_enum_values_are_stable_strings():
    assert {value.value for value in RequestIdentityCompletenessStatus} == {
        "complete",
        "missing_fragment_observation_mode",
        "missing_precursor_mz",
        "missing_product_mz",
        "missing_fragment_tags",
        "missing_mode_specific_constraint",
    }
    assert {value.value for value in RequestCandidateIdentityStatus} == {
        "not_assessed",
        "match",
        "missing_discovery_candidate_join",
        "missing_diagnostic_fragment_evidence",
        "request_candidate_identity_mismatch",
        "unsupported_fragment_observation_mode",
    }
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: fail because `identity_coherence.schema` does not exist.

- [ ] **Step 3: Implement schema constants and enums**

```python
from __future__ import annotations

from enum import StrEnum


class RequestIdentityCompletenessStatus(StrEnum):
    COMPLETE = "complete"
    MISSING_FRAGMENT_OBSERVATION_MODE = "missing_fragment_observation_mode"
    MISSING_PRECURSOR_MZ = "missing_precursor_mz"
    MISSING_PRODUCT_MZ = "missing_product_mz"
    MISSING_FRAGMENT_TAGS = "missing_fragment_tags"
    MISSING_MODE_SPECIFIC_CONSTRAINT = "missing_mode_specific_constraint"


class RequestCandidateIdentityStatus(StrEnum):
    NOT_ASSESSED = "not_assessed"
    MATCH = "match"
    MISSING_DISCOVERY_CANDIDATE_JOIN = "missing_discovery_candidate_join"
    MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE = "missing_diagnostic_fragment_evidence"
    REQUEST_CANDIDATE_IDENTITY_MISMATCH = "request_candidate_identity_mismatch"
    UNSUPPORTED_FRAGMENT_OBSERVATION_MODE = "unsupported_fragment_observation_mode"


class FragmentObservationMode(StrEnum):
    CID_NEUTRAL_LOSS = "cid_neutral_loss"


class FragmentTagMatchPolicy(StrEnum):
    ALL_REQUEST_TAGS_SUPPORTED = "all_request_tags_supported"


IDENTITY_COHERENCE_REQUEST_COLUMNS: tuple[str, ...] = (
    "request_id",
    "decision_id",
    "seed_candidate_id",
    "seed_sample",
    "fragment_observation_mode",
    "precursor_mz",
    "product_mz",
    "fragment_tags",
    "fragment_tag_match_policy",
    "fragment_profile_id",
    "fragment_profile_hash",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_da",
    "cid_observed_loss_tolerance_ppm",
    "request_identity_completeness_status",
    "request_candidate_identity_status",
    "precursor_error_ppm",
    "product_error_ppm",
    "cid_observed_loss_error_ppm",
    "cid_observed_loss_error_da",
    "request_builder_flags",
)

IDENTITY_COHERENCE_DECISION_COLUMNS: tuple[str, ...] = (
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "seed_sample",
    "seed_gate_class",
    "decision",
    "decision_reason",
    "request_identity_completeness_status",
    "request_candidate_identity_status",
    "total_coherent_sample_count",
    "non_seed_coherent_sample_count",
    "tier12_non_seed_identity_sample_count",
    "tier1_fragment_confirmed_sample_count",
    "tier2_shape_supported_sample_count",
    "tier2_seed_shape_fallback_sample_count",
    "tier3_width_only_sample_count",
    "min_total_coherent_samples",
    "min_non_seed_tier12_identity_samples",
    "weak_basis_reason",
    "shape_reference_basis",
    "shape_reference_candidate_id",
    "prototype_width_sec",
    "center_rt_sec",
    "center_rt_source",
    "coherent_fraction",
    "infrastructure_blocked_sample_count",
    "data_quality_reject_sample_count",
    "forbidden_evidence_used",
)

IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "decision_id",
    "identity_family_id",
    "sample_id",
    "candidate_id",
    "cell_assessment_status",
    "cell_identity_tier",
    "cell_identity_basis",
    "fragment_observation_mode",
    "fragment_match_status",
    "fragment_tags_supported",
    "rt_delta_center_sec",
    "rt_gate_status",
    "shape_status",
    "shape_similarity_cosine",
    "shape_reference_basis",
    "shape_reference_candidate_id",
    "shape_fallback_used",
    "shape_audit_status",
    "width_status",
    "width_ratio_to_prototype",
    "baseline_audit_status",
    "area_height_status",
    "non_rt_identity_result",
    "coherent_count_contribution",
    "tier12_count_contribution",
    "blocked_reason",
    "data_quality_reason",
    "forbidden_evidence_seen",
)

IDENTITY_COHERENCE_CONTROL_COLUMNS: tuple[str, ...] = (
    "control_id",
    "control_type",
    "control_name",
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "control_status",
    "control_expected_behavior",
    "control_observed_behavior",
    "control_pass",
    "control_failure_reason",
    "fragment_observation_mode",
    "decoy_generation_method",
    "decoy_source_request_id",
    "decoy_shift_value",
    "decoy_identity_constraint_changed",
    "positive_control_mapping_status",
    "positive_control_target_name",
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
    "control_notes",
)
```

- [ ] **Step 4: Run schema tests**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\schema.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: add identity coherence schema constants"
```

## Task 2: Add Fragment Identity Models

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/models.py`
- Modify: `tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`

- [ ] **Step 1: Write failing model test**

```python
from xic_extractor.alignment.identity_coherence.models import (
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceRequest,
)
from xic_extractor.alignment.identity_coherence.schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


def test_fragment_identity_request_model_can_hold_complete_cid_request():
    identity = FragmentIdentity(
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_mz=500.0,
        product_mz=384.0,
        fragment_tags=("dR", "MeR"),
        fragment_tag_match_policy=FragmentTagMatchPolicy.ALL_REQUEST_TAGS_SUPPORTED,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
        fragment_profile_hash="hash-a",
        mode_constraint=CidNeutralLossConstraint(
            cid_observed_loss_da=116.0,
            cid_observed_loss_tolerance_ppm=10.0,
        ),
    )

    request = IdentityCoherenceRequest(
        request_id="REQ-1",
        decision_id="DEC-1",
        seed_candidate_id="CAND-1",
        seed_sample="RAW-1",
        identity=identity,
        request_identity_completeness_status=RequestIdentityCompletenessStatus.COMPLETE,
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
        request_builder_flags=(),
    )

    assert request.identity.fragment_tags == ("dR", "MeR")
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_fragment_identity_request_builder.py::test_fragment_identity_request_model_can_hold_complete_cid_request -q
```

Expected: fail because `identity_coherence.models` does not exist.

- [ ] **Step 3: Implement dataclasses**

```python
from __future__ import annotations

from dataclasses import dataclass

from .schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


@dataclass(frozen=True)
class CidNeutralLossConstraint:
    cid_observed_loss_da: float | None
    cid_observed_loss_tolerance_ppm: float | None


@dataclass(frozen=True)
class FragmentIdentity:
    fragment_observation_mode: FragmentObservationMode | None
    precursor_mz: float | None
    product_mz: float | None
    fragment_tags: tuple[str, ...]
    fragment_tag_match_policy: FragmentTagMatchPolicy
    precursor_tolerance_ppm: float | None
    product_tolerance_ppm: float | None
    fragment_profile_id: str
    fragment_profile_hash: str
    mode_constraint: CidNeutralLossConstraint


@dataclass(frozen=True)
class IdentityCoherenceRequest:
    request_id: str
    decision_id: str
    seed_candidate_id: str
    seed_sample: str | None
    identity: FragmentIdentity
    request_identity_completeness_status: RequestIdentityCompletenessStatus
    request_candidate_identity_status: RequestCandidateIdentityStatus
    request_builder_flags: tuple[str, ...] = ()
```

- [ ] **Step 4: Run model test**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_fragment_identity_request_builder.py::test_fragment_identity_request_model_can_hold_complete_cid_request -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\models.py tests\alignment\identity_coherence\test_fragment_identity_request_builder.py
git commit -m "feat: add identity coherence request models"
```

## Task 3: Add Request Builder And Tag Normalization

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/request_builder.py`
- Modify: `tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`

- [ ] **Step 1: Write failing builder tests**

```python
from dataclasses import dataclass

import pytest

from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    format_fragment_tags,
)
from xic_extractor.alignment.identity_coherence.schema import (
    FragmentObservationMode,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float | None = 500.0
    product_mz: float | None = 384.0
    observed_neutral_loss_da: float | None = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str | None = "dR"


def _build(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def test_builder_creates_complete_cid_neutral_loss_request():
    request = _build(CandidateLike())

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.COMPLETE
    )
    assert request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )
    # Builder output is pre-gate; this object must not be emitted directly as
    # a frozen requests.tsv row until seed-gate matching resolves the status.
    assert request.identity.fragment_observation_mode is (
        FragmentObservationMode.CID_NEUTRAL_LOSS
    )
    assert request.identity.fragment_tags == ("MeR", "dR")
    assert request.identity.fragment_profile_hash == "unavailable"
    assert "fragment_profile_hash_unavailable" in request.request_builder_flags


@pytest.mark.parametrize(
    ("raw_tags", "expected"),
    [
        ("dR;MeR", ("MeR", "dR")),
        ("dR|MeR", ("MeR", "dR")),
        ("dR,MeR", ("MeR", "dR")),
        (["dR", "MeR"], ("MeR", "dR")),
        (("dR", "MeR"), ("MeR", "dR")),
        ({"dR", "MeR"}, ("MeR", "dR")),
    ],
)
def test_builder_accepts_common_tag_shapes_and_canonicalizes(raw_tags, expected):
    request = _build(CandidateLike(matched_tag_names=raw_tags, neutral_loss_tag=None))

    assert request.identity.fragment_tags == expected


def test_format_fragment_tags_uses_semicolon_for_tsv_projection():
    assert format_fragment_tags(("MeR", "dR")) == "MeR;dR"


def test_builder_preserves_case_variants_and_flags_them():
    request = _build(CandidateLike(matched_tag_names="base;BASE"))

    assert request.identity.fragment_tags == ("BASE", "base")
    assert "fragment_tag_case_variant_seen" in request.request_builder_flags


def test_matched_tags_win_over_legacy_single_tag_and_flag_disagreement():
    request = _build(CandidateLike(matched_tag_names=("MeR",), neutral_loss_tag="dR"))

    assert request.identity.fragment_tags == ("MeR",)
    assert "legacy_single_tag_disagrees_with_matched_tags" in (
        request.request_builder_flags
    )


def test_missing_product_mz_builds_incomplete_request():
    request = _build(CandidateLike(product_mz=None))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ
    )
    assert "missing_product_mz" in request.request_builder_flags


def test_missing_tags_builds_incomplete_request():
    request = _build(CandidateLike(matched_tag_names=None, neutral_loss_tag=None))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_FRAGMENT_TAGS
    )


def test_missing_tolerance_builds_incomplete_request():
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=None,
        fragment_profile_id="profile-a",
    )

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_MODE_SPECIFIC_CONSTRAINT
    )


@pytest.mark.parametrize("field", ["request_id", "decision_id", "fragment_profile_id"])
def test_missing_required_request_metadata_raises_value_error(field):
    kwargs = {
        "request_id": "REQ-1",
        "decision_id": "DEC-1",
        "precursor_tolerance_ppm": 10.0,
        "product_tolerance_ppm": 10.0,
        "cid_observed_loss_tolerance_ppm": 10.0,
        "fragment_profile_id": "profile-a",
    }
    kwargs[field] = ""

    with pytest.raises(ValueError):
        build_identity_coherence_request(CandidateLike(), **kwargs)


def test_missing_candidate_id_raises_value_error():
    with pytest.raises(ValueError):
        _build(CandidateLike(candidate_id=""))
```

- [ ] **Step 2: Run the failing builder tests**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_fragment_identity_request_builder.py -q
```

Expected: fail because `build_identity_coherence_request` does not exist.

- [ ] **Step 3: Implement request builder**

```python
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from .models import CidNeutralLossConstraint, FragmentIdentity, IdentityCoherenceRequest
from .schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


_TAG_SPLIT_RE = re.compile(r"[;|,]")
_MISSING_STATUS_ORDER: Sequence[tuple[str, RequestIdentityCompletenessStatus]] = (
    ("missing_fragment_observation_mode", RequestIdentityCompletenessStatus.MISSING_FRAGMENT_OBSERVATION_MODE),
    ("missing_precursor_mz", RequestIdentityCompletenessStatus.MISSING_PRECURSOR_MZ),
    ("missing_product_mz", RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ),
    ("missing_fragment_tags", RequestIdentityCompletenessStatus.MISSING_FRAGMENT_TAGS),
    (
        "missing_mode_specific_constraint",
        RequestIdentityCompletenessStatus.MISSING_MODE_SPECIFIC_CONSTRAINT,
    ),
)


def build_identity_coherence_request(
    candidate_like: object,
    *,
    request_id: str,
    decision_id: str,
    precursor_tolerance_ppm: float | None,
    product_tolerance_ppm: float | None,
    cid_observed_loss_tolerance_ppm: float | None,
    fragment_profile_id: str,
    fragment_profile_hash: str = "unavailable",
) -> IdentityCoherenceRequest:
    request_id = _require_nonempty_text(request_id, "request_id")
    decision_id = _require_nonempty_text(decision_id, "decision_id")
    fragment_profile_id = _require_nonempty_text(
        fragment_profile_id,
        "fragment_profile_id",
    )
    seed_candidate_id = _require_nonempty_text(
        _getattr_or_none(candidate_like, "candidate_id"),
        "candidate_id",
    )

    flags: list[str] = []
    seed_sample = _first_nonempty_text(
        _getattr_or_none(candidate_like, "sample_name"),
        _getattr_or_none(candidate_like, "sample_stem"),
    )
    if seed_sample is None:
        flags.append("missing_seed_sample")

    matched_tag_names = _getattr_or_none(candidate_like, "matched_tag_names")
    neutral_loss_tag = _getattr_or_none(candidate_like, "neutral_loss_tag")
    tag_source = matched_tag_names if _has_tags(matched_tag_names) else neutral_loss_tag
    fragment_tags, tag_flags = _normalize_fragment_tags(tag_source)
    flags.extend(tag_flags)
    if _has_tags(matched_tag_names) and _has_tags(neutral_loss_tag):
        fallback_tags, _ = _normalize_fragment_tags(neutral_loss_tag)
        if fallback_tags and fallback_tags != fragment_tags:
            flags.append("legacy_single_tag_disagrees_with_matched_tags")

    if fragment_profile_hash == "unavailable":
        flags.append("fragment_profile_hash_unavailable")

    precursor_mz = _getattr_or_none(candidate_like, "precursor_mz")
    product_mz = _getattr_or_none(candidate_like, "product_mz")
    cid_observed_loss_da = _getattr_or_none(candidate_like, "observed_neutral_loss_da")

    missing_flags: list[str] = []
    if precursor_mz is None:
        missing_flags.append("missing_precursor_mz")
    if product_mz is None:
        missing_flags.append("missing_product_mz")
    if not fragment_tags:
        missing_flags.append("missing_fragment_tags")
    if (
        precursor_tolerance_ppm is None
        or product_tolerance_ppm is None
        or cid_observed_loss_tolerance_ppm is None
        or cid_observed_loss_da is None
    ):
        missing_flags.append("missing_mode_specific_constraint")

    flags.extend(missing_flags)
    completeness_status = _completeness_status(missing_flags)

    identity = FragmentIdentity(
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        fragment_tags=fragment_tags,
        fragment_tag_match_policy=FragmentTagMatchPolicy.ALL_REQUEST_TAGS_SUPPORTED,
        precursor_tolerance_ppm=precursor_tolerance_ppm,
        product_tolerance_ppm=product_tolerance_ppm,
        fragment_profile_id=fragment_profile_id,
        fragment_profile_hash=fragment_profile_hash,
        mode_constraint=CidNeutralLossConstraint(
            cid_observed_loss_da=cid_observed_loss_da,
            cid_observed_loss_tolerance_ppm=cid_observed_loss_tolerance_ppm,
        ),
    )

    return IdentityCoherenceRequest(
        request_id=request_id,
        decision_id=decision_id,
        seed_candidate_id=seed_candidate_id,
        seed_sample=seed_sample,
        identity=identity,
        request_identity_completeness_status=completeness_status,
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
        request_builder_flags=tuple(dict.fromkeys(flags)),
    )


def format_fragment_tags(tags: tuple[str, ...]) -> str:
    return ";".join(tags)


def _getattr_or_none(value: object, name: str) -> Any:
    return getattr(value, name, None)


def _require_nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _first_nonempty_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_tags(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Iterable):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def _normalize_fragment_tags(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    flags: list[str] = []
    raw_parts: list[str] = []
    if value is None:
        return (), ()
    if isinstance(value, str):
        raw_parts.extend(_TAG_SPLIT_RE.split(value))
    elif isinstance(value, Iterable):
        for item in value:
            raw_parts.extend(_TAG_SPLIT_RE.split(str(item)))
    else:
        raw_parts.extend(_TAG_SPLIT_RE.split(str(value)))

    tags = tuple(sorted({part.strip() for part in raw_parts if part.strip()}))
    lowered = {}
    for tag in tags:
        lowered.setdefault(tag.lower(), set()).add(tag)
    if any(len(variants) > 1 for variants in lowered.values()):
        flags.append("fragment_tag_case_variant_seen")
    return tags, tuple(flags)


def _completeness_status(
    missing_flags: list[str],
) -> RequestIdentityCompletenessStatus:
    missing = set(missing_flags)
    for flag, status in _MISSING_STATUS_ORDER:
        if flag in missing:
            return status
    return RequestIdentityCompletenessStatus.COMPLETE
```

This implementation intentionally leaves
`request_candidate_identity_status = not_assessed`; request-vs-candidate
matching is a later slice. The returned request is a pre-gate object and must
not be emitted as a final `requests.tsv` row until that status is resolved by
the seed gate.

The public signature is:

```python
def build_identity_coherence_request(
    candidate_like: object,
    *,
    request_id: str,
    decision_id: str,
    precursor_tolerance_ppm: float | None,
    product_tolerance_ppm: float | None,
    cid_observed_loss_tolerance_ppm: float | None,
    fragment_profile_id: str,
    fragment_profile_hash: str = "unavailable",
) -> IdentityCoherenceRequest:
```

- [ ] **Step 4: Run builder tests**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_fragment_identity_request_builder.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\request_builder.py tests\alignment\identity_coherence\test_fragment_identity_request_builder.py
git commit -m "feat: build identity coherence requests"
```

## Task 4: Add Thin Facade And Final Verification

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/__init__.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Write facade import smoke test**

```python
def test_identity_coherence_facade_exports_stable_contract():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.FragmentIdentity is not None
    assert identity_coherence.CidNeutralLossConstraint is not None
    assert identity_coherence.IdentityCoherenceRequest is not None
    assert identity_coherence.build_identity_coherence_request is not None
    assert identity_coherence.format_fragment_tags is not None
    assert identity_coherence.IDENTITY_COHERENCE_REQUEST_COLUMNS
```

- [ ] **Step 2: Run the failing facade test**

Run:

```powershell
pytest tests\alignment\identity_coherence\test_schema_contract.py::test_identity_coherence_facade_exports_stable_contract -q
```

Expected: fail until facade exports are added.

- [ ] **Step 3: Implement thin facade**

```python
from .models import (
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceRequest,
)
from .request_builder import build_identity_coherence_request
from .request_builder import format_fragment_tags
from .schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)

__all__ = [
    "CidNeutralLossConstraint",
    "FragmentIdentity",
    "FragmentObservationMode",
    "FragmentTagMatchPolicy",
    "IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS",
    "IDENTITY_COHERENCE_CONTROL_COLUMNS",
    "IDENTITY_COHERENCE_DECISION_COLUMNS",
    "IDENTITY_COHERENCE_REQUEST_COLUMNS",
    "IdentityCoherenceRequest",
    "RequestCandidateIdentityStatus",
    "RequestIdentityCompletenessStatus",
    "build_identity_coherence_request",
    "format_fragment_tags",
]
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
pytest tests\alignment\identity_coherence -q
```

Expected: pass.

- [ ] **Step 5: Run import smoke compile**

Run:

```powershell
python -m py_compile `
  xic_extractor\alignment\identity_coherence\__init__.py `
  xic_extractor\alignment\identity_coherence\models.py `
  xic_extractor\alignment\identity_coherence\schema.py `
  xic_extractor\alignment\identity_coherence\request_builder.py
```

Expected: exit code 0.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence tests\alignment\identity_coherence
git commit -m "feat: expose identity coherence domain contract"
```

## Self-Review Checklist

- [ ] No production alignment flow imports the new package.
- [ ] No RAW/XIC adapters are imported by domain modules.
- [ ] No TSV writer exists in this slice.
- [ ] `FragmentIdentity` is the only normalized identity object used by the builder output.
- [ ] Legacy names appear only in `request_builder.py` tests or adapter code.
- [ ] All tests under `tests\alignment\identity_coherence` pass.
