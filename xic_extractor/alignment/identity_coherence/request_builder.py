from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .models import (
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
)
from .schema import (
    EvidenceStage,
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)
from .tags import has_fragment_tags, normalize_fragment_tags

_MISSING_STATUS_ORDER: Sequence[tuple[str, RequestIdentityCompletenessStatus]] = (
    (
        "missing_fragment_observation_mode",
        RequestIdentityCompletenessStatus.MISSING_FRAGMENT_OBSERVATION_MODE,
    ),
    ("missing_precursor_mz", RequestIdentityCompletenessStatus.MISSING_PRECURSOR_MZ),
    ("missing_product_mz", RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ),
    ("missing_fragment_tags", RequestIdentityCompletenessStatus.MISSING_FRAGMENT_TAGS),
    (
        "missing_precursor_tolerance_ppm",
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE,
    ),
    (
        "missing_product_tolerance_ppm",
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE,
    ),
    (
        "missing_cid_observed_loss_tolerance_ppm",
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE,
    ),
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

    precursor_tolerance_ppm = _finite_positive_or_none(precursor_tolerance_ppm)
    product_tolerance_ppm = _finite_positive_or_none(product_tolerance_ppm)
    cid_observed_loss_tolerance_ppm = _finite_positive_or_none(
        cid_observed_loss_tolerance_ppm
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
    tag_source = (
        matched_tag_names
        if has_fragment_tags(matched_tag_names)
        else neutral_loss_tag
    )
    fragment_tags, tag_flags = normalize_fragment_tags(tag_source)
    flags.extend(tag_flags)
    if has_fragment_tags(matched_tag_names) and has_fragment_tags(neutral_loss_tag):
        fallback_tags, _ = normalize_fragment_tags(neutral_loss_tag)
        if any(tag not in fragment_tags for tag in fallback_tags):
            flags.append("legacy_single_tag_disagrees_with_matched_tags")

    if fragment_profile_hash == "unavailable":
        flags.append("fragment_profile_hash_unavailable")

    precursor_mz = _finite_positive_or_none(
        _getattr_or_none(candidate_like, "precursor_mz")
    )
    product_mz = _finite_positive_or_none(
        _getattr_or_none(candidate_like, "product_mz")
    )
    cid_observed_loss_da = _finite_positive_or_none(
        _getattr_or_none(candidate_like, "observed_neutral_loss_da")
    )

    missing_flags: list[str] = []
    if precursor_mz is None:
        missing_flags.append("missing_precursor_mz")
    if product_mz is None:
        missing_flags.append("missing_product_mz")
    if not fragment_tags:
        missing_flags.append("missing_fragment_tags")
    if precursor_tolerance_ppm is None:
        missing_flags.append("missing_precursor_tolerance_ppm")
    if product_tolerance_ppm is None:
        missing_flags.append("missing_product_tolerance_ppm")
    if cid_observed_loss_tolerance_ppm is None:
        missing_flags.append("missing_cid_observed_loss_tolerance_ppm")
    if cid_observed_loss_da is None:
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


def _finite_positive_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _completeness_status(
    missing_flags: list[str],
) -> RequestIdentityCompletenessStatus:
    missing = set(missing_flags)
    for flag, status in _MISSING_STATUS_ORDER:
        if flag in missing:
            return status
    return RequestIdentityCompletenessStatus.COMPLETE
