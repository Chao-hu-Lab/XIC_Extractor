from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.edge_scoring import (
    DriftLookupProtocol,
    OwnerEdgeEvidence,
    evaluate_owner_edge,
)
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    SampleLocalMS1Owner,
)


@dataclass(frozen=True)
class OwnerAlignedFeature:
    feature_family_id: str
    neutral_loss_tag: str
    family_center_mz: float
    family_center_rt: float
    family_product_mz: float
    family_observed_neutral_loss_da: float
    has_anchor: bool
    owners: tuple[SampleLocalMS1Owner, ...]
    evidence: str
    identity_conflict: bool = False
    review_only: bool = False
    confirm_local_owners_with_backfill: bool = False
    backfill_seed_centers: tuple[tuple[float, float], ...] = ()
    ambiguous_sample_stem: str | None = None
    ambiguous_candidate_ids: tuple[str, ...] = ()

    @property
    def cluster_id(self) -> str:
        return self.feature_family_id

    @property
    def members(self) -> tuple[SampleLocalMS1Owner, ...]:
        return self.owners

    @property
    def event_cluster_ids(self) -> tuple[str, ...]:
        return tuple(owner.owner_id for owner in self.owners)

    @property
    def event_member_count(self) -> int:
        return sum(len(owner.all_events) for owner in self.owners)


@dataclass(frozen=True)
class _GroupHardGateEnvelope:
    neutral_loss_tag: str
    sample_stems: frozenset[str]
    precursor_mz_min: float
    precursor_mz_max: float
    product_mz_min: float
    product_mz_max: float
    observed_loss_min: float
    observed_loss_max: float


def cluster_sample_local_owners(
    owners: tuple[SampleLocalMS1Owner, ...] | list[SampleLocalMS1Owner],
    *,
    config: AlignmentConfig,
    drift_lookup: DriftLookupProtocol | None = None,
    edge_evidence_sink: list[OwnerEdgeEvidence] | None = None,
) -> tuple[OwnerAlignedFeature, ...]:
    clean = tuple(owner for owner in owners if not owner.identity_conflict)
    conflict_features = tuple(
        _feature_from_group(
            (owner,),
            feature_family_id=f"FAM{index:06d}",
            evidence="identity_conflict_review_only",
            identity_conflict=True,
            review_only=True,
        )
        for index, owner in enumerate(
            sorted(
                (owner for owner in owners if owner.identity_conflict),
                key=_owner_sort_key,
            ),
            start=1,
        )
    )
    edge_cache: dict[tuple[str, str], OwnerEdgeEvidence] = {}
    groups = _complete_link_groups(
        sorted(clean, key=_owner_sort_key),
        config,
        drift_lookup=drift_lookup,
        edge_evidence_sink=edge_evidence_sink,
        edge_cache=edge_cache,
    )
    clean_features = tuple(
        _feature_from_group(
            tuple(group),
            feature_family_id=f"FAM{index + len(conflict_features):06d}",
            evidence=_group_evidence(group),
        )
        for index, group in enumerate(groups, start=1)
    )
    return (*conflict_features, *clean_features)


def review_only_features_from_ambiguous_records(
    records: tuple[AmbiguousOwnerRecord, ...],
    *,
    start_index: int,
) -> tuple[OwnerAlignedFeature, ...]:
    features: list[OwnerAlignedFeature] = []
    for offset, record in enumerate(records):
        if (
            record.neutral_loss_tag is None
            or record.precursor_mz is None
            or record.apex_rt is None
            or record.product_mz is None
            or record.observed_neutral_loss_da is None
        ):
            continue
        features.append(
            OwnerAlignedFeature(
                feature_family_id=f"FAM{start_index + offset:06d}",
                neutral_loss_tag=record.neutral_loss_tag,
                family_center_mz=record.precursor_mz,
                family_center_rt=record.apex_rt,
                family_product_mz=record.product_mz,
                family_observed_neutral_loss_da=record.observed_neutral_loss_da,
                has_anchor=False,
                owners=(),
                evidence="ambiguous_ms1_owner_review_only",
                review_only=True,
                ambiguous_sample_stem=record.sample_stem,
                ambiguous_candidate_ids=record.candidate_ids,
            ),
        )
    return tuple(features)


def _complete_link_groups(
    owners: list[SampleLocalMS1Owner],
    config: AlignmentConfig,
    *,
    drift_lookup: DriftLookupProtocol | None,
    edge_evidence_sink: list[OwnerEdgeEvidence] | None,
    edge_cache: dict[tuple[str, str], OwnerEdgeEvidence],
) -> tuple[tuple[SampleLocalMS1Owner, ...], ...]:
    groups: list[list[SampleLocalMS1Owner]] = []
    envelopes: list[_GroupHardGateEnvelope] = []
    use_group_prefilter = edge_evidence_sink is None
    for owner in owners:
        compatible_group_indexes = [
            index
            for index, group in enumerate(groups)
            if (
                not use_group_prefilter
                or _group_can_pass_hard_gates(owner, envelopes[index], config)
            )
            and all(
                _edge_for_pair(
                    owner,
                    existing,
                    config=config,
                    drift_lookup=drift_lookup,
                    edge_evidence_sink=edge_evidence_sink,
                    edge_cache=edge_cache,
                ).decision
                == "strong_edge"
                for existing in group
            )
        ]
        if not compatible_group_indexes:
            groups.append([owner])
            envelopes.append(_group_envelope_for_owner(owner))
            continue
        best_index = min(
            compatible_group_indexes,
            key=lambda index: _group_match_score(owner, groups[index], config),
        )
        groups[best_index].append(owner)
        envelopes[best_index] = _extend_group_envelope(envelopes[best_index], owner)
    return tuple(tuple(group) for group in groups)


def _group_can_pass_hard_gates(
    owner: SampleLocalMS1Owner,
    envelope: _GroupHardGateEnvelope,
    config: AlignmentConfig,
) -> bool:
    if owner.sample_stem in envelope.sample_stems:
        return False
    if (
        not owner.neutral_loss_tag
        or owner.neutral_loss_tag != envelope.neutral_loss_tag
    ):
        return False
    if _range_exceeds_ppm(
        owner.precursor_mz,
        envelope.precursor_mz_min,
        envelope.precursor_mz_max,
        config.max_ppm,
    ):
        return False

    event = owner.primary_identity_event
    if _range_exceeds_ppm(
        event.product_mz,
        envelope.product_mz_min,
        envelope.product_mz_max,
        config.product_mz_tolerance_ppm,
    ):
        return False
    return not _range_exceeds_ppm(
        event.observed_neutral_loss_da,
        envelope.observed_loss_min,
        envelope.observed_loss_max,
        config.observed_loss_tolerance_ppm,
    )


def _range_exceeds_ppm(
    reference: float,
    lower: float,
    upper: float,
    max_ppm: float,
) -> bool:
    return _ppm(reference, lower) > max_ppm or _ppm(reference, upper) > max_ppm


def _group_envelope_for_owner(
    owner: SampleLocalMS1Owner,
) -> _GroupHardGateEnvelope:
    event = owner.primary_identity_event
    return _GroupHardGateEnvelope(
        neutral_loss_tag=owner.neutral_loss_tag,
        sample_stems=frozenset((owner.sample_stem,)),
        precursor_mz_min=owner.precursor_mz,
        precursor_mz_max=owner.precursor_mz,
        product_mz_min=event.product_mz,
        product_mz_max=event.product_mz,
        observed_loss_min=event.observed_neutral_loss_da,
        observed_loss_max=event.observed_neutral_loss_da,
    )


def _extend_group_envelope(
    envelope: _GroupHardGateEnvelope,
    owner: SampleLocalMS1Owner,
) -> _GroupHardGateEnvelope:
    event = owner.primary_identity_event
    return _GroupHardGateEnvelope(
        neutral_loss_tag=envelope.neutral_loss_tag,
        sample_stems=envelope.sample_stems | frozenset((owner.sample_stem,)),
        precursor_mz_min=min(envelope.precursor_mz_min, owner.precursor_mz),
        precursor_mz_max=max(envelope.precursor_mz_max, owner.precursor_mz),
        product_mz_min=min(envelope.product_mz_min, event.product_mz),
        product_mz_max=max(envelope.product_mz_max, event.product_mz),
        observed_loss_min=min(
            envelope.observed_loss_min,
            event.observed_neutral_loss_da,
        ),
        observed_loss_max=max(
            envelope.observed_loss_max,
            event.observed_neutral_loss_da,
        ),
    )


def _edge_for_pair(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    *,
    config: AlignmentConfig,
    drift_lookup: DriftLookupProtocol | None,
    edge_evidence_sink: list[OwnerEdgeEvidence] | None,
    edge_cache: dict[tuple[str, str], OwnerEdgeEvidence],
) -> OwnerEdgeEvidence:
    key = cast(tuple[str, str], tuple(sorted((left.owner_id, right.owner_id))))
    edge = edge_cache.get(key)
    if edge is not None:
        return edge

    edge = evaluate_owner_edge(
        left,
        right,
        config=config,
        drift_lookup=drift_lookup,
    )
    edge_cache[key] = edge
    if edge_evidence_sink is not None:
        edge_evidence_sink.append(edge)
    return edge


def _group_match_score(
    owner: SampleLocalMS1Owner,
    group: list[SampleLocalMS1Owner],
    config: AlignmentConfig,
) -> tuple[float, float, float]:
    return max(_owner_match_score(owner, existing, config) for existing in group)


def _owner_match_score(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> tuple[float, float, float]:
    mz_score = _ppm(left.precursor_mz, right.precursor_mz) / config.max_ppm
    rt_score = (
        abs(left.owner_apex_rt - right.owner_apex_rt)
        * 60.0
        / config.identity_rt_candidate_window_sec
    )
    product_ppm = _ppm(
        left.primary_identity_event.product_mz,
        right.primary_identity_event.product_mz,
    )
    product_score = (
        product_ppm / config.product_mz_tolerance_ppm
    )
    return (mz_score + rt_score + product_score, mz_score, rt_score)


def _feature_from_group(
    group: tuple[SampleLocalMS1Owner, ...],
    *,
    feature_family_id: str,
    evidence: str,
    identity_conflict: bool = False,
    review_only: bool = False,
) -> OwnerAlignedFeature:
    center_mz = sum(owner.precursor_mz for owner in group) / len(group)
    center_rt = sum(owner.owner_apex_rt for owner in group) / len(group)
    center_product_mz = sum(
        owner.primary_identity_event.product_mz for owner in group
    ) / len(group)
    center_loss = sum(
        owner.primary_identity_event.observed_neutral_loss_da for owner in group
    ) / len(group)
    return OwnerAlignedFeature(
        feature_family_id=feature_family_id,
        neutral_loss_tag=group[0].neutral_loss_tag,
        family_center_mz=center_mz,
        family_center_rt=center_rt,
        family_product_mz=center_product_mz,
        family_observed_neutral_loss_da=center_loss,
        has_anchor=True,
        owners=group,
        evidence=evidence,
        identity_conflict=identity_conflict,
        review_only=review_only,
    )


def _group_evidence(group: tuple[SampleLocalMS1Owner, ...]) -> str:
    if len(group) == 1:
        return "single_sample_local_owner"
    return f"owner_complete_link;owner_count={len(group)}"


def _owner_sort_key(owner: SampleLocalMS1Owner) -> tuple[object, ...]:
    event = owner.primary_identity_event
    return (
        owner.neutral_loss_tag,
        owner.precursor_mz,
        owner.owner_apex_rt,
        owner.sample_stem,
        -event.evidence_score,
        -event.seed_event_count,
        owner.owner_id,
    )


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0
