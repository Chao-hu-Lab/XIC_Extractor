# Identity Coherence Seed Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the second identity coherence slice: request-vs-candidate identity matching plus the pre-Backfill seed coherence gate.

**Architecture:** This slice stays inside `xic_extractor.alignment.identity_coherence`. It resolves first-slice `IdentityCoherenceRequest` objects against joined pre-Backfill `DiscoveryCandidate`-like evidence and sample-local owner evidence, but it still does not perform XIC retrieval, tiered cross-sample evidence, TSV writing, CLI wiring, Backfill, workbook, or report work.

**Tech Stack:** Python dataclasses, `enum.StrEnum`, duck-typed candidate/owner fixtures, pytest.

---

## Preflight

Before implementing any task:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset `
  status --short
```

Expected: the command succeeds. `.codegraph/` may remain untracked and must not be staged.

If Git reports dubious ownership, stop and set the local safe-directory rule, or ask for approval before continuing:

```powershell
git config --global --add safe.directory `
  C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset
```

All commit and hygiene commands in this plan may alternatively use the explicit `-c safe.directory=...` form above.

## Scope

Create or modify only these files:

```text
xic_extractor/alignment/identity_coherence/__init__.py
xic_extractor/alignment/identity_coherence/models.py
xic_extractor/alignment/identity_coherence/schema.py
xic_extractor/alignment/identity_coherence/request_builder.py
xic_extractor/alignment/identity_coherence/tags.py
xic_extractor/alignment/identity_coherence/candidate_matcher.py
xic_extractor/alignment/identity_coherence/seed_gate.py
tests/alignment/identity_coherence/test_fragment_tags.py
tests/alignment/identity_coherence/test_candidate_matcher.py
tests/alignment/identity_coherence/test_seed_gate.py
tests/alignment/identity_coherence/test_schema_contract.py
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

## File Responsibilities

- `tags.py`: shared fragment-tag parsing, canonical ordering, and TSV formatting. It is used by both request builder and candidate matcher.
- `request_builder.py`: adapter edge for legacy `DiscoveryCandidate`-like fields. It builds both normalized `IdentityCoherenceRequest` and normalized `SeedCandidateEvidence`.
- `candidate_matcher.py`: pure request-vs-candidate identity comparison. It reads normalized `FragmentIdentity` plus normalized `SeedCandidateEvidence` and returns match status/errors. No owner logic and no legacy field reads.
- `seed_gate.py`: Layer 1 seed coherence gate. It combines request completeness, candidate identity match, pre-Backfill provenance, sample-local owner geometry, owner assignment state, and scan support. No cross-sample XIC.
- `models.py`: domain dataclasses only.
- `schema.py`: stable categorical enums and frozen TSV column constants.
- `__init__.py`: thin facade exports.

## Task 1: Extract Shared Fragment Tag Helpers

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/tags.py`
- Modify: `xic_extractor/alignment/identity_coherence/request_builder.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Create: `tests/alignment/identity_coherence/test_fragment_tags.py`
- Modify: `tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`

- [ ] **Step 1: Write failing shared-tag tests**

```python
import pytest

from xic_extractor.alignment.identity_coherence.tags import (
    format_fragment_tags,
    has_fragment_tags,
    normalize_fragment_tags,
)


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
def test_normalize_fragment_tags_accepts_supported_shapes(raw_tags, expected):
    tags, flags = normalize_fragment_tags(raw_tags)

    assert tags == expected
    assert flags == ()


def test_normalize_fragment_tags_preserves_case_variants():
    tags, flags = normalize_fragment_tags("base;BASE")

    assert tags == ("BASE", "base")
    assert flags == ("fragment_tag_case_variant_seen",)


def test_format_fragment_tags_uses_semicolon():
    assert format_fragment_tags(("MeR", "dR")) == "MeR;dR"


def test_has_fragment_tags_treats_empty_values_as_absent():
    assert has_fragment_tags(None) is False
    assert has_fragment_tags("") is False
    assert has_fragment_tags(["", "  "]) is False
    assert has_fragment_tags("dR") is True


def test_normalize_fragment_tags_ignores_empty_separator_slots():
    tags, flags = normalize_fragment_tags("dR;;MeR")

    assert tags == ("MeR", "dR")
    assert flags == ()
```

- [ ] **Step 2: Run the failing tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_fragment_tags.py -q
```

Expected: fail because `identity_coherence.tags` does not exist.

- [ ] **Step 3: Implement `tags.py`**

```python
from __future__ import annotations

import re
from collections.abc import Iterable

_TAG_SPLIT_RE = re.compile(r"[;|,]")


def format_fragment_tags(tags: tuple[str, ...]) -> str:
    return ";".join(tags)


def has_fragment_tags(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Iterable):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def normalize_fragment_tags(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
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
    lowered: dict[str, set[str]] = {}
    for tag in tags:
        lowered.setdefault(tag.lower(), set()).add(tag)
    if any(len(variants) > 1 for variants in lowered.values()):
        flags.append("fragment_tag_case_variant_seen")
    return tags, tuple(flags)
```

- [ ] **Step 4: Update `request_builder.py` to import shared helpers**

Remove its private `_TAG_SPLIT_RE`, `_has_tags`, `_normalize_fragment_tags`,
and local `format_fragment_tags`. `request_builder.py` uses only the parsing
helpers:

```python
from .tags import has_fragment_tags, normalize_fragment_tags
```

Then replace calls:

```python
tag_source = (
    matched_tag_names
    if has_fragment_tags(matched_tag_names)
    else neutral_loss_tag
)
fragment_tags, tag_flags = normalize_fragment_tags(tag_source)
if has_fragment_tags(matched_tag_names) and has_fragment_tags(neutral_loss_tag):
    fallback_tags, _ = normalize_fragment_tags(neutral_loss_tag)
    if any(tag not in fragment_tags for tag in fallback_tags):
        flags.append("legacy_single_tag_disagrees_with_matched_tags")
```

Update `tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`
so `format_fragment_tags` is imported from `.tags`, not from `request_builder`:

```python
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.tags import format_fragment_tags
```

- [ ] **Step 5: Export `tags.py` helpers from facade**

Add these direct imports to `__init__.py` and `__all__`; do not re-export them through `request_builder.py`:

```python
from .request_builder import build_identity_coherence_request
from .tags import format_fragment_tags, has_fragment_tags, normalize_fragment_tags
```

Remove `format_fragment_tags` from the existing `.request_builder` facade import.

- [ ] **Step 6: Run tag and builder tests**

```powershell
uv run pytest `
  tests\alignment\identity_coherence\test_fragment_tags.py `
  tests\alignment\identity_coherence\test_fragment_identity_request_builder.py `
  -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git status --short
git add xic_extractor\alignment\identity_coherence\tags.py `
  xic_extractor\alignment\identity_coherence\request_builder.py `
  xic_extractor\alignment\identity_coherence\__init__.py `
  tests\alignment\identity_coherence\test_fragment_tags.py `
  tests\alignment\identity_coherence\test_fragment_identity_request_builder.py
git commit -m "refactor: share identity coherence tag parsing"
```

## Task 2: Add Seed Gate Enums And Result Models

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence/schema.py`
- Modify: `xic_extractor/alignment/identity_coherence/models.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Write failing enum/model tests**

Append to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
from dataclasses import dataclass

from xic_extractor.alignment.identity_coherence.models import (
    CandidateIdentityMatch,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    RequestCandidateIdentityStatus,
    SeedGateClass,
    SeedRejectReason,
)


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float = 500.0
    product_mz: float = 384.0
    observed_neutral_loss_da: float = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str = "dR"


def _request():
    return build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def test_seed_gate_enum_values_are_stable_strings():
    assert {value.value for value in EvidenceStage} == {
        "pre_backfill",
        "backfill_only",
        "post_backfill",
    }
    assert {value.value for value in SeedGateClass} == {
        "coherent_seed",
        "review_only_seed_gate_failed",
        "blocked_seed",
    }
    assert {value.value for value in SeedRejectReason} == {
        "missing_request_identity_constraint",
        "no_quantifiable_owner",
        "missing_discovery_candidate_join",
        "missing_diagnostic_fragment_evidence",
        "ambiguous_owner",
        "duplicate_loser",
        "backfill_only_evidence",
        "nonfinite_peak",
        "seed_rt_outside_owner_peak",
        "low_ms1_scan_support",
        "request_candidate_identity_mismatch",
        "unsupported_fragment_observation_mode",
        "multi_seed_requires_phase2",
    }


def test_seed_gate_models_hold_a_resolved_gate_result():
    evidence = SeedCandidateEvidence(
        candidate_id="CAND-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.83,
        ms1_scan_support_score=0.80,
    )
    match = CandidateIdentityMatch(
        request_candidate_identity_status=RequestCandidateIdentityStatus.MATCH,
        precursor_error_ppm=0.0,
        product_error_ppm=0.0,
        cid_observed_loss_error_ppm=0.0,
        cid_observed_loss_error_da=0.0,
        missing_fields=(),
        mismatch_fields=(),
        fragment_tags_supported=("dR",),
    )

    result = SeedGateResult(
        resolved_request=_request(),
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=match,
        review_flags=(),
    )

    assert evidence.evidence_stage is EvidenceStage.PRE_BACKFILL
    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert result.resolved_request.seed_candidate_id == "CAND-1"
    assert SeedGateConfig().min_ms1_scan_support_score == 0.5
```

- [ ] **Step 2: Run the failing tests**

```powershell
uv run pytest `
  tests\alignment\identity_coherence\test_schema_contract.py::test_seed_gate_enum_values_are_stable_strings `
  tests\alignment\identity_coherence\test_schema_contract.py::test_seed_gate_models_hold_a_resolved_gate_result `
  -q
```

Expected: fail because enums/models do not exist.

- [ ] **Step 3: Add enums to `schema.py`**

```python
class EvidenceStage(StrEnum):
    PRE_BACKFILL = "pre_backfill"
    BACKFILL_ONLY = "backfill_only"
    POST_BACKFILL = "post_backfill"


class SeedGateClass(StrEnum):
    COHERENT_SEED = "coherent_seed"
    REVIEW_ONLY_SEED_GATE_FAILED = "review_only_seed_gate_failed"
    BLOCKED_SEED = "blocked_seed"


class SeedRejectReason(StrEnum):
    MISSING_REQUEST_IDENTITY_CONSTRAINT = "missing_request_identity_constraint"
    NO_QUANTIFIABLE_OWNER = "no_quantifiable_owner"
    MISSING_DISCOVERY_CANDIDATE_JOIN = "missing_discovery_candidate_join"
    MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE = "missing_diagnostic_fragment_evidence"
    AMBIGUOUS_OWNER = "ambiguous_owner"
    DUPLICATE_LOSER = "duplicate_loser"
    BACKFILL_ONLY_EVIDENCE = "backfill_only_evidence"
    NONFINITE_PEAK = "nonfinite_peak"
    SEED_RT_OUTSIDE_OWNER_PEAK = "seed_rt_outside_owner_peak"
    LOW_MS1_SCAN_SUPPORT = "low_ms1_scan_support"
    REQUEST_CANDIDATE_IDENTITY_MISMATCH = "request_candidate_identity_mismatch"
    UNSUPPORTED_FRAGMENT_OBSERVATION_MODE = "unsupported_fragment_observation_mode"
    MULTI_SEED_REQUIRES_PHASE2 = "multi_seed_requires_phase2"
```

- [ ] **Step 4: Add result models to `models.py`**

```python
@dataclass(frozen=True)
class CandidateIdentityMatch:
    request_candidate_identity_status: RequestCandidateIdentityStatus
    precursor_error_ppm: float | None
    product_error_ppm: float | None
    cid_observed_loss_error_ppm: float | None
    cid_observed_loss_error_da: float | None
    missing_fields: tuple[str, ...] = ()
    mismatch_fields: tuple[str, ...] = ()
    fragment_tags_supported: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedCandidateEvidence:
    candidate_id: str
    precursor_mz: float | None
    product_mz: float | None
    cid_observed_loss_da: float | None
    fragment_tags: tuple[str, ...]
    best_seed_rt: float | None
    ms1_scan_support_score: float | None
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL


@dataclass(frozen=True)
class SeedGateConfig:
    min_ms1_scan_support_score: float = 0.50
    require_seed_rt_inside_owner_peak: bool = True


@dataclass(frozen=True)
class SeedGateResult:
    resolved_request: IdentityCoherenceRequest
    seed_gate_class: SeedGateClass
    seed_reject_reason: SeedRejectReason | None
    candidate_match: CandidateIdentityMatch
    review_flags: tuple[str, ...] = ()
```

Import `EvidenceStage`, `SeedGateClass`, and `SeedRejectReason` from `.schema`.

`SeedGateClass.BLOCKED_SEED` and
`SeedRejectReason.MULTI_SEED_REQUIRES_PHASE2` are stable enum values reserved
for later infrastructure/multi-seed slices. This seed-gate slice defines and
exports them for schema stability but does not produce them.

- [ ] **Step 5: Update facade exports**

Export `CandidateIdentityMatch`, `SeedCandidateEvidence`, `SeedGateConfig`, `SeedGateResult`, `EvidenceStage`, `SeedGateClass`, and `SeedRejectReason` from `__init__.py`.

- [ ] **Step 6: Run schema tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git status --short
git add xic_extractor\alignment\identity_coherence\schema.py `
  xic_extractor\alignment\identity_coherence\models.py `
  xic_extractor\alignment\identity_coherence\__init__.py `
  tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: add identity coherence seed gate models"
```

## Task 3: Implement Request-Vs-Candidate Identity Matching

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence/request_builder.py`
- Create: `xic_extractor/alignment/identity_coherence/candidate_matcher.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Create: `tests/alignment/identity_coherence/test_candidate_matcher.py`
- Modify: `tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`

- [ ] **Step 1: Write failing matcher tests**

```python
from dataclasses import dataclass
from dataclasses import replace

from xic_extractor.alignment.identity_coherence.candidate_matcher import (
    match_request_to_candidate,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.schema import (
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
    best_seed_rt: float | None = 7.83
    ms1_scan_support_score: float | None = 0.80


def _request(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _evidence(candidate: CandidateLike):
    return build_seed_candidate_evidence(candidate)


def test_match_request_to_candidate_accepts_matching_cid_neutral_loss():
    candidate = CandidateLike()
    match = match_request_to_candidate(_request(candidate), _evidence(candidate))

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
    assert match.precursor_error_ppm == 0.0
    assert match.product_error_ppm == 0.0
    assert match.cid_observed_loss_error_ppm == 0.0
    assert match.cid_observed_loss_error_da == 0.0
    assert match.fragment_tags_supported == ("MeR", "dR")


def test_match_request_to_candidate_checks_unsupported_mode_before_missing_join():
    request = _request(CandidateLike())
    unsupported_identity = replace(
        request.identity,
        fragment_observation_mode="hcd_product_ion",
    )
    unsupported_request = replace(request, identity=unsupported_identity)

    unsupported_match = match_request_to_candidate(unsupported_request, None)
    missing_join_match = match_request_to_candidate(request, None)

    assert unsupported_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE
    )
    assert missing_join_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    )
    assert missing_join_match.missing_fields == ("candidate",)


def test_match_request_to_candidate_reports_missing_diagnostic_evidence():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(product_mz=None))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE
    )
    assert "product_mz" in match.missing_fields


def test_match_request_to_candidate_rejects_product_mz_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(product_mz=390.0))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "product_mz" in match.mismatch_fields


def test_match_request_to_candidate_rejects_precursor_mz_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(precursor_mz=500.02))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "precursor_mz" in match.mismatch_fields


def test_match_request_to_candidate_rejects_cid_loss_ppm_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(observed_neutral_loss_da=116.01))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "cid_observed_loss_da" in match.mismatch_fields


def test_match_request_to_candidate_accepts_exact_ppm_boundary():
    request = _request(CandidateLike())
    candidate = _evidence(
        CandidateLike(
            precursor_mz=500.005,
            product_mz=384.00384,
            observed_neutral_loss_da=116.00116,
        )
    )
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )


def test_match_request_to_candidate_rejects_missing_request_tag_support():
    request = _request(CandidateLike(matched_tag_names=("MeR", "dR")))
    candidate = _evidence(
        CandidateLike(matched_tag_names=("dR",), neutral_loss_tag="dR"),
    )
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "fragment_tags" in match.mismatch_fields


def test_match_request_to_candidate_leaves_incomplete_request_not_assessed():
    request = _request(CandidateLike(product_mz=None))
    match = match_request_to_candidate(request, _evidence(CandidateLike()))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ
    )
    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )
```

Append these invariant tests to
`tests/alignment/identity_coherence/test_fragment_identity_request_builder.py`.
They make the builder's completeness guarantee match the matcher assumption that
mass/loss values and ppm tolerances are finite positive numbers:

```python
def test_nonfinite_precursor_mz_builds_incomplete_request():
    request = _build(CandidateLike(precursor_mz=float("nan")))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRECURSOR_MZ
    )
    assert "missing_precursor_mz" in request.request_builder_flags


def test_zero_cid_loss_payload_builds_missing_mode_constraint_request():
    request = _build(CandidateLike(observed_neutral_loss_da=0.0))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_MODE_SPECIFIC_CONSTRAINT
    )
    assert "missing_mode_specific_constraint" in request.request_builder_flags


def test_nonfinite_common_tolerance_builds_missing_tolerance_request():
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=float("inf"),
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE
    )
    assert "missing_precursor_tolerance_ppm" in request.request_builder_flags
```

- [ ] **Step 2: Run the failing matcher tests**

```powershell
uv run pytest `
  tests\alignment\identity_coherence\test_fragment_identity_request_builder.py `
  tests\alignment\identity_coherence\test_candidate_matcher.py `
  -q
```

Expected: fail because `candidate_matcher.py` does not exist and the numeric
completeness guards are not implemented yet.

- [ ] **Step 3: Add normalized candidate evidence builder to `request_builder.py`**

Domain matching must not read legacy `matched_tag_names` / `neutral_loss_tag`
directly. Add this adapter helper next to `build_identity_coherence_request()`:

```python
def build_seed_candidate_evidence(
    candidate_like: object,
    *,
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
) -> SeedCandidateEvidence:
    seed_candidate_id = _require_nonempty_text(
        _getattr_or_none(candidate_like, "candidate_id"),
        "candidate_id",
    )
    matched_tag_names = _getattr_or_none(candidate_like, "matched_tag_names")
    neutral_loss_tag = _getattr_or_none(candidate_like, "neutral_loss_tag")
    tag_source = (
        matched_tag_names
        if has_fragment_tags(matched_tag_names)
        else neutral_loss_tag
    )
    fragment_tags, _ = normalize_fragment_tags(tag_source)

    return SeedCandidateEvidence(
        candidate_id=seed_candidate_id,
        precursor_mz=_finite_positive_or_none(
            _getattr_or_none(candidate_like, "precursor_mz"),
        ),
        product_mz=_finite_positive_or_none(
            _getattr_or_none(candidate_like, "product_mz"),
        ),
        cid_observed_loss_da=_finite_positive_or_none(
            _getattr_or_none(candidate_like, "observed_neutral_loss_da"),
        ),
        fragment_tags=fragment_tags,
        best_seed_rt=_getattr_or_none(candidate_like, "best_seed_rt"),
        ms1_scan_support_score=_getattr_or_none(
            candidate_like,
            "ms1_scan_support_score",
        ),
        evidence_stage=evidence_stage,
    )
```

Import `math`, `SeedCandidateEvidence`, `EvidenceStage`, `has_fragment_tags`,
and `normalize_fragment_tags`. Add shared request-builder helpers:

```python
def _finite_positive_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)
```

Use `_finite_positive_or_none()` for `precursor_mz`, `product_mz`,
`cid_observed_loss_da`, and the three ppm tolerances in
`build_identity_coherence_request()`. Invalid values should reuse the existing
missing flags (`missing_precursor_mz`, `missing_product_mz`,
`missing_mode_specific_constraint`, or `missing_*_tolerance_ppm`). This adapter
helper is the only place in this slice that may read legacy candidate tag
fields.

- [ ] **Step 4: Implement `candidate_matcher.py`**

```python
from __future__ import annotations

import math

from .models import (
    CandidateIdentityMatch,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
)
from .schema import (
    FragmentObservationMode,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


def match_request_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
) -> CandidateIdentityMatch:
    if (
        request.request_identity_completeness_status
        is not RequestIdentityCompletenessStatus.COMPLETE
    ):
        return _match(RequestCandidateIdentityStatus.NOT_ASSESSED)

    identity = request.identity
    if (
        identity.fragment_observation_mode
        is not FragmentObservationMode.CID_NEUTRAL_LOSS
    ):
        return _match(
            RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE,
        )

    if candidate_evidence is None:
        return _match(
            RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN,
            missing_fields=("candidate",),
        )

    missing_fields: list[str] = []
    candidate_precursor_mz = candidate_evidence.precursor_mz
    candidate_product_mz = candidate_evidence.product_mz
    candidate_loss_da = candidate_evidence.cid_observed_loss_da
    candidate_tags = candidate_evidence.fragment_tags

    if candidate_precursor_mz is None:
        missing_fields.append("precursor_mz")
    if candidate_product_mz is None:
        missing_fields.append("product_mz")
    if candidate_loss_da is None:
        missing_fields.append("observed_neutral_loss_da")
    if not candidate_tags:
        missing_fields.append("fragment_tags")
    if missing_fields:
        return _match(
            RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            missing_fields=tuple(missing_fields),
            fragment_tags_supported=candidate_tags,
        )

    if not all(
        _finite_positive_number(value)
        for value in (
            identity.precursor_mz,
            identity.product_mz,
            identity.mode_constraint.cid_observed_loss_da,
            identity.precursor_tolerance_ppm,
            identity.product_tolerance_ppm,
            identity.mode_constraint.cid_observed_loss_tolerance_ppm,
        )
    ):
        return _match(
            RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            missing_fields=("request_identity_numeric_invariant",),
            fragment_tags_supported=candidate_tags,
        )

    precursor_error_ppm = _ppm_error(candidate_precursor_mz, identity.precursor_mz)
    product_error_ppm = _ppm_error(candidate_product_mz, identity.product_mz)
    loss_error_da = (
        candidate_loss_da - identity.mode_constraint.cid_observed_loss_da
    )
    loss_error_ppm = _ppm_error(
        candidate_loss_da,
        identity.mode_constraint.cid_observed_loss_da,
    )

    mismatch_fields: list[str] = []
    if abs(precursor_error_ppm) > identity.precursor_tolerance_ppm:
        mismatch_fields.append("precursor_mz")
    if abs(product_error_ppm) > identity.product_tolerance_ppm:
        mismatch_fields.append("product_mz")
    if (
        abs(loss_error_ppm)
        > identity.mode_constraint.cid_observed_loss_tolerance_ppm
    ):
        mismatch_fields.append("cid_observed_loss_da")
    if any(tag not in candidate_tags for tag in identity.fragment_tags):
        mismatch_fields.append("fragment_tags")

    if mismatch_fields:
        return _match(
            RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH,
            precursor_error_ppm=precursor_error_ppm,
            product_error_ppm=product_error_ppm,
            cid_observed_loss_error_ppm=loss_error_ppm,
            cid_observed_loss_error_da=loss_error_da,
            mismatch_fields=tuple(mismatch_fields),
            fragment_tags_supported=candidate_tags,
        )

    return _match(
        RequestCandidateIdentityStatus.MATCH,
        precursor_error_ppm=precursor_error_ppm,
        product_error_ppm=product_error_ppm,
        cid_observed_loss_error_ppm=loss_error_ppm,
        cid_observed_loss_error_da=loss_error_da,
        fragment_tags_supported=candidate_tags,
    )


def _ppm_error(observed: float, expected: float) -> float:
    return (observed - expected) / expected * 1_000_000.0


def _finite_positive_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _match(
    status: RequestCandidateIdentityStatus,
    *,
    precursor_error_ppm: float | None = None,
    product_error_ppm: float | None = None,
    cid_observed_loss_error_ppm: float | None = None,
    cid_observed_loss_error_da: float | None = None,
    missing_fields: tuple[str, ...] = (),
    mismatch_fields: tuple[str, ...] = (),
    fragment_tags_supported: tuple[str, ...] = (),
) -> CandidateIdentityMatch:
    return CandidateIdentityMatch(
        request_candidate_identity_status=status,
        precursor_error_ppm=precursor_error_ppm,
        product_error_ppm=product_error_ppm,
        cid_observed_loss_error_ppm=cid_observed_loss_error_ppm,
        cid_observed_loss_error_da=cid_observed_loss_error_da,
        missing_fields=missing_fields,
        mismatch_fields=mismatch_fields,
        fragment_tags_supported=fragment_tags_supported,
    )
```

The implementation assumes a complete request has finite positive m/z,
tolerance, and mode payload fields. That invariant is owned by the
request-builder completeness checks.

CID observed-loss ppm is calculated relative to the neutral-loss mass itself
(`cid_observed_loss_da`), not relative to precursor m/z. The Da loss error stays
review context only.

- [ ] **Step 5: Export matcher and evidence builder from facade**

Add `match_request_to_candidate` and `build_seed_candidate_evidence` to `__init__.py` imports and `__all__`.

- [ ] **Step 6: Run matcher tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_candidate_matcher.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git status --short
git add xic_extractor\alignment\identity_coherence\request_builder.py `
  xic_extractor\alignment\identity_coherence\candidate_matcher.py `
  xic_extractor\alignment\identity_coherence\__init__.py `
  tests\alignment\identity_coherence\test_fragment_identity_request_builder.py `
  tests\alignment\identity_coherence\test_candidate_matcher.py
git commit -m "feat: match identity coherence requests to candidates"
```

## Task 4: Implement Seed Coherence Gate

**Files:**
- Create: `xic_extractor/alignment/identity_coherence/seed_gate.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Create: `tests/alignment/identity_coherence/test_seed_gate.py`

- [ ] **Step 1: Write failing seed-gate tests**

```python
from dataclasses import dataclass

from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    RequestCandidateIdentityStatus,
    SeedGateClass,
    SeedRejectReason,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float | None = 500.0
    product_mz: float | None = 384.0
    observed_neutral_loss_da: float | None = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str | None = "dR"
    best_seed_rt: float = 7.83
    ms1_scan_support_score: float | None = 0.80


@dataclass
class OwnerLike:
    owner_apex_rt: float = 7.84
    owner_peak_start_rt: float = 7.70
    owner_peak_end_rt: float = 7.98
    owner_area: float = 1000.0
    owner_height: float = 200.0


def _request(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _evidence(candidate: CandidateLike, *, evidence_stage=EvidenceStage.PRE_BACKFILL):
    return build_seed_candidate_evidence(candidate, evidence_stage=evidence_stage)


def test_evaluate_seed_gate_accepts_matching_candidate_and_owner():
    candidate = CandidateLike()
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert result.seed_reject_reason is None
    assert result.resolved_request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )


def test_evaluate_seed_gate_rejects_incomplete_request_before_candidate_match():
    candidate = CandidateLike(product_mz=None)
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(CandidateLike()),
        OwnerLike(),
    )

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is (
        SeedRejectReason.MISSING_REQUEST_IDENTITY_CONSTRAINT
    )
    assert result.resolved_request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )


def test_evaluate_seed_gate_rejects_candidate_identity_mismatch_before_owner_checks():
    request = _request(CandidateLike())
    candidate = CandidateLike(product_mz=390.0)
    result = evaluate_seed_gate(request, _evidence(candidate), None)

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )


def test_evaluate_seed_gate_rejects_missing_owner():
    candidate = CandidateLike()
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), None)

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.NO_QUANTIFIABLE_OWNER


def test_evaluate_seed_gate_rejects_nonfinite_owner_geometry():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(owner_area=float("nan")),
    )

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.NONFINITE_PEAK


def test_evaluate_seed_gate_rejects_seed_rt_outside_owner_peak():
    candidate = CandidateLike(best_seed_rt=8.10)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK


def test_evaluate_seed_gate_rejects_ambiguous_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="ambiguous",
    )

    assert result.seed_reject_reason is SeedRejectReason.AMBIGUOUS_OWNER


def test_evaluate_seed_gate_rejects_unresolved_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="unresolved",
    )

    assert result.seed_reject_reason is SeedRejectReason.NO_QUANTIFIABLE_OWNER


def test_evaluate_seed_gate_allows_supporting_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="supporting",
    )

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED


def test_evaluate_seed_gate_rejects_unknown_owner_assignment_status():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="ambigous",
    )

    assert result.seed_reject_reason is SeedRejectReason.AMBIGUOUS_OWNER


def test_evaluate_seed_gate_rejects_duplicate_loser():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        duplicate_loser=True,
    )

    assert result.seed_reject_reason is SeedRejectReason.DUPLICATE_LOSER


def test_evaluate_seed_gate_rejects_low_scan_support_when_available():
    candidate = CandidateLike(ms1_scan_support_score=0.25)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_reject_reason is SeedRejectReason.LOW_MS1_SCAN_SUPPORT


def test_evaluate_seed_gate_rejects_nonfinite_scan_support_when_available():
    candidate = CandidateLike(ms1_scan_support_score=float("nan"))
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_reject_reason is SeedRejectReason.LOW_MS1_SCAN_SUPPORT


def test_evaluate_seed_gate_allows_missing_scan_support_as_unassessed():
    candidate = CandidateLike(ms1_scan_support_score=None)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert "ms1_scan_support_unavailable" in result.review_flags


def test_evaluate_seed_gate_rejects_backfill_only_candidate_evidence():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate, evidence_stage=EvidenceStage.BACKFILL_ONLY),
        OwnerLike(),
    )

    assert result.seed_reject_reason is SeedRejectReason.BACKFILL_ONLY_EVIDENCE


def test_evaluate_seed_gate_rejects_post_backfill_owner_evidence():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_evidence_stage=EvidenceStage.POST_BACKFILL,
    )

    assert result.seed_reject_reason is SeedRejectReason.BACKFILL_ONLY_EVIDENCE
```

- [ ] **Step 2: Run the failing seed-gate tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_seed_gate.py -q
```

Expected: fail because `seed_gate.py` does not exist.

- [ ] **Step 3: Implement `seed_gate.py`**

```python
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .candidate_matcher import match_request_to_candidate
from .models import (
    CandidateIdentityMatch,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
)
from .schema import (
    EvidenceStage,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    SeedGateClass,
    SeedRejectReason,
)

_ALLOWED_OWNER_ASSIGNMENT_STATUSES = {
    "primary",
    "supporting",
    "ambiguous",
    "unresolved",
}


def evaluate_seed_gate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
    owner_like: object | None,
    *,
    owner_assignment_status: str = "primary",
    duplicate_loser: bool = False,
    owner_evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
    config: SeedGateConfig = SeedGateConfig(),
) -> SeedGateResult:
    review_flags: list[str] = []
    candidate_match = match_request_to_candidate(request, candidate_evidence)
    candidate_status = candidate_match.request_candidate_identity_status
    resolved_request = replace(
        request,
        request_candidate_identity_status=candidate_status,
    )

    if (
        request.request_identity_completeness_status
        is not RequestIdentityCompletenessStatus.COMPLETE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_REQUEST_IDENTITY_CONSTRAINT,
            review_flags,
        )
    if (
        candidate_status
        is RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE,
            review_flags,
        )
    if (
        candidate_status
        is RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_DISCOVERY_CANDIDATE_JOIN,
            review_flags,
        )
    if (
        candidate_status
        is RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            review_flags,
        )
    if (
        candidate_status
        is RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH,
            review_flags,
        )

    if (
        candidate_evidence.evidence_stage is not EvidenceStage.PRE_BACKFILL
        or owner_evidence_stage is not EvidenceStage.PRE_BACKFILL
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.BACKFILL_ONLY_EVIDENCE,
            review_flags,
        )

    if owner_like is None:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NO_QUANTIFIABLE_OWNER,
            review_flags,
        )

    if owner_assignment_status not in _ALLOWED_OWNER_ASSIGNMENT_STATUSES:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.AMBIGUOUS_OWNER,
            review_flags,
        )
    if owner_assignment_status == "unresolved":
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NO_QUANTIFIABLE_OWNER,
            review_flags,
        )
    if owner_assignment_status == "ambiguous":
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.AMBIGUOUS_OWNER,
            review_flags,
        )
    if duplicate_loser:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.DUPLICATE_LOSER,
            review_flags,
        )

    owner_values = {
        "owner_apex_rt": _getattr_or_none(owner_like, "owner_apex_rt"),
        "owner_peak_start_rt": _getattr_or_none(owner_like, "owner_peak_start_rt"),
        "owner_peak_end_rt": _getattr_or_none(owner_like, "owner_peak_end_rt"),
        "owner_area": _getattr_or_none(owner_like, "owner_area"),
        "owner_height": _getattr_or_none(owner_like, "owner_height"),
    }
    if any(not _finite_number(value) for value in owner_values.values()):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NONFINITE_PEAK,
            review_flags,
        )

    seed_rt = candidate_evidence.best_seed_rt
    if not _finite_number(seed_rt):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NONFINITE_PEAK,
            review_flags,
        )
    if (
        config.require_seed_rt_inside_owner_peak
        and not (
            owner_values["owner_peak_start_rt"]
            <= seed_rt
            <= owner_values["owner_peak_end_rt"]
        )
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK,
            review_flags,
        )

    scan_support = candidate_evidence.ms1_scan_support_score
    if scan_support is None:
        review_flags.append("ms1_scan_support_unavailable")
    elif (
        not _finite_number(scan_support)
        or scan_support < config.min_ms1_scan_support_score
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.LOW_MS1_SCAN_SUPPORT,
            review_flags,
        )

    return SeedGateResult(
        resolved_request=resolved_request,
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=candidate_match,
        review_flags=tuple(review_flags),
    )


def _result(
    resolved_request: IdentityCoherenceRequest,
    candidate_match: CandidateIdentityMatch,
    reason: SeedRejectReason,
    review_flags: list[str],
) -> SeedGateResult:
    return SeedGateResult(
        resolved_request=resolved_request,
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=reason,
        candidate_match=candidate_match,
        review_flags=tuple(review_flags),
    )


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _getattr_or_none(value: object, name: str) -> Any:
    return getattr(value, name, None)
```

- [ ] **Step 4: Export `evaluate_seed_gate` from facade**

Add `evaluate_seed_gate` to `__init__.py` imports and `__all__`.

- [ ] **Step 5: Run seed-gate tests**

```powershell
uv run pytest tests\alignment\identity_coherence\test_seed_gate.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git status --short
git add xic_extractor\alignment\identity_coherence\seed_gate.py `
  xic_extractor\alignment\identity_coherence\__init__.py `
  tests\alignment\identity_coherence\test_seed_gate.py
git commit -m "feat: evaluate identity coherence seed gate"
```

## Task 5: Final Contract Verification

**Files:**
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`

- [ ] **Step 1: Add facade export coverage**

Replace the existing `test_identity_coherence_facade_exports_stable_contract`
body in `tests/alignment/identity_coherence/test_schema_contract.py`; do not
append a second function with the same name:

```python
def test_identity_coherence_facade_exports_stable_contract():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.FragmentIdentity is not None
    assert identity_coherence.CidNeutralLossConstraint is not None
    assert identity_coherence.IdentityCoherenceRequest is not None
    assert identity_coherence.CandidateIdentityMatch is not None
    assert identity_coherence.SeedCandidateEvidence is not None
    assert identity_coherence.SeedGateConfig is not None
    assert identity_coherence.SeedGateResult is not None
    assert identity_coherence.EvidenceStage is not None
    assert identity_coherence.SeedGateClass is not None
    assert identity_coherence.SeedRejectReason is not None
    assert identity_coherence.build_identity_coherence_request is not None
    assert identity_coherence.build_seed_candidate_evidence is not None
    assert identity_coherence.match_request_to_candidate is not None
    assert identity_coherence.evaluate_seed_gate is not None
    assert identity_coherence.format_fragment_tags is not None
    assert identity_coherence.has_fragment_tags is not None
    assert identity_coherence.normalize_fragment_tags is not None
    assert identity_coherence.IDENTITY_COHERENCE_REQUEST_COLUMNS
```

- [ ] **Step 2: Run the full focused suite**

```powershell
uv run pytest tests\alignment\identity_coherence -q
```

Expected: pass.

- [ ] **Step 3: Run import compile smoke**

```powershell
uv run python -m py_compile `
  xic_extractor\alignment\identity_coherence\__init__.py `
  xic_extractor\alignment\identity_coherence\models.py `
  xic_extractor\alignment\identity_coherence\schema.py `
  xic_extractor\alignment\identity_coherence\tags.py `
  xic_extractor\alignment\identity_coherence\request_builder.py `
  xic_extractor\alignment\identity_coherence\candidate_matcher.py `
  xic_extractor\alignment\identity_coherence\seed_gate.py
```

Expected: exit code 0.

- [ ] **Step 4: Check git diff hygiene**

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors. `.codegraph/` may remain untracked and must not be committed.

- [ ] **Step 5: Commit**

```powershell
git status --short
git add xic_extractor\alignment\identity_coherence\__init__.py `
  tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "test: verify identity coherence seed gate contract"
```

## Out Of Scope For This Plan

- Layer 2 cross-sample candidate retrieval.
- Tier 1 non-seed fragment support.
- Tier 2 prototype-medoid shape similarity.
- Tier 3 prototype-width fallback.
- Identity controls/decoys execution.
- TSV writer, summary, CLI, HTML/story updates.
- Backfill or owner_backfill behavior changes.

Those belong in the next plans after this seed-gate slice is reviewed.

## Self-Review Checklist

- [ ] No production alignment flow imports the new seed-gate module.
- [ ] No RAW/XIC adapters are imported by identity coherence domain modules.
- [ ] Candidate matching uses normalized `FragmentIdentity` plus `SeedCandidateEvidence`, not legacy fields carried in parallel.
- [ ] Candidate matching uses ppm gates for precursor, product, and CID observed loss.
- [ ] Seed gate resolves complete joined requests away from `not_assessed`.
- [ ] Seed gate checks candidate identity before owner geometry.
- [ ] Seed gate rejects non-pre-Backfill candidate or owner evidence with `backfill_only_evidence`.
- [ ] Seed gate treats missing scan support as review flag, not as background/specificity evidence.
- [ ] No TSV writer exists in this slice.
- [ ] Focused tests under `tests\alignment\identity_coherence` pass.
