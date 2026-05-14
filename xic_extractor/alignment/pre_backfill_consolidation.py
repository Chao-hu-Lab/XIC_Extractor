from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from statistics import mean, median

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, row_id
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature

_MAX_BACKFILL_SEED_CENTERS = 2
_PRESENT_STATUSES = {"detected", "rescued"}


def consolidate_pre_backfill_identity_families(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    config: AlignmentConfig,
) -> tuple[OwnerAlignedFeature, ...]:
    groups = _identity_groups(features, config)
    if not any(len(group) > 1 for group in groups):
        return features

    replacements: dict[str, OwnerAlignedFeature] = {}
    for group in groups:
        if len(group) == 1:
            continue
        winner = _winner_feature(group)
        replacements[winner.feature_family_id] = _primary_feature(winner, group)
        for feature in group:
            if feature.feature_family_id != winner.feature_family_id:
                replacements[feature.feature_family_id] = _loser_feature(
                    feature,
                    winner_id=winner.feature_family_id,
                )
    return tuple(
        replacements.get(feature.feature_family_id, feature)
        for feature in features
    )


def recenter_pre_backfill_identity_families(
    matrix: AlignmentMatrix,
) -> AlignmentMatrix:
    grouped_cells = cells_by_cluster(matrix)
    centers_by_id: dict[str, float] = {}
    clusters: list[OwnerAlignedFeature] = []
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        if not _is_pre_backfill_consolidated(cluster):
            clusters.append(cluster)
            continue
        present_rts = [
            cell.apex_rt
            for cell in grouped_cells.get(cluster_id, ())
            if cell.status in _PRESENT_STATUSES and cell.apex_rt is not None
        ]
        if not present_rts:
            clusters.append(cluster)
            continue
        center_rt = mean(present_rts)
        centers_by_id[cluster_id] = center_rt
        clusters.append(replace(cluster, family_center_rt=center_rt))
    if not centers_by_id:
        return matrix
    return AlignmentMatrix(
        clusters=tuple(clusters),
        cells=tuple(_recenter_cell(cell, centers_by_id) for cell in matrix.cells),
        sample_order=matrix.sample_order,
    )


def _identity_groups(
    features: tuple[OwnerAlignedFeature, ...],
    config: AlignmentConfig,
) -> tuple[tuple[OwnerAlignedFeature, ...], ...]:
    groups: list[list[OwnerAlignedFeature]] = []
    for feature in sorted(features, key=_feature_sort_key):
        if feature.review_only:
            groups.append([feature])
            continue
        compatible_indexes = [
            index
            for index, group in enumerate(groups)
            if all(
                not existing.review_only
                and _sample_stems_disjoint(feature, existing)
                and _compatible_identity(feature, existing, config)
                for existing in group
            )
        ]
        if not compatible_indexes:
            groups.append([feature])
            continue
        best_index = min(
            compatible_indexes,
            key=lambda index: _group_match_score(feature, groups[index]),
        )
        groups[best_index].append(feature)
    return tuple(tuple(group) for group in groups)


def _primary_feature(
    winner: OwnerAlignedFeature,
    group: tuple[OwnerAlignedFeature, ...],
) -> OwnerAlignedFeature:
    owners = tuple(owner for feature in group for owner in feature.owners)
    family_count = len(group)
    evidence = (
        f"owner_complete_link;owner_count={len(owners)};"
        f"pre_backfill_identity_consolidated;family_count={family_count}"
    )
    return replace(
        winner,
        family_center_mz=median(feature.family_center_mz for feature in group),
        family_center_rt=median(feature.family_center_rt for feature in group),
        family_product_mz=median(feature.family_product_mz for feature in group),
        family_observed_neutral_loss_da=median(
            feature.family_observed_neutral_loss_da for feature in group
        ),
        has_anchor=any(feature.has_anchor for feature in group),
        owners=owners,
        evidence=evidence,
        identity_conflict=False,
        review_only=False,
        confirm_local_owners_with_backfill=True,
        backfill_seed_centers=_seed_centers(group),
        ambiguous_sample_stem=None,
        ambiguous_candidate_ids=(),
    )


def _loser_feature(
    feature: OwnerAlignedFeature,
    *,
    winner_id: str,
) -> OwnerAlignedFeature:
    suffix = f"pre_backfill_identity_consolidation_loser;winner={winner_id}"
    evidence = f"{feature.evidence};{suffix}" if feature.evidence else suffix
    return replace(feature, evidence=evidence, review_only=True)


def _winner_feature(
    group: tuple[OwnerAlignedFeature, ...],
) -> OwnerAlignedFeature:
    center_rt = median(feature.family_center_rt for feature in group)
    return min(
        group,
        key=lambda feature: (
            -len(feature.owners),
            0 if feature.has_anchor else 1,
            abs(feature.family_center_rt - center_rt),
            feature.feature_family_id,
        ),
    )


def _seed_centers(
    group: tuple[OwnerAlignedFeature, ...],
) -> tuple[tuple[float, float], ...]:
    ordered = tuple(
        sorted(
            {
                (feature.family_center_mz, feature.family_center_rt)
                for feature in group
            },
            key=lambda item: (item[1], item[0]),
        )
    )
    if len(ordered) <= _MAX_BACKFILL_SEED_CENTERS:
        return ordered
    indexes = {0, len(ordered) - 1}
    return tuple(ordered[index] for index in sorted(indexes))


def _compatible_identity(
    left: OwnerAlignedFeature,
    right: OwnerAlignedFeature,
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    if _ppm(left.family_center_mz, right.family_center_mz) > config.max_ppm:
        return False
    if (
        abs(left.family_center_rt - right.family_center_rt) * 60.0
        > config.identity_rt_candidate_window_sec
    ):
        return False
    if (
        _ppm(left.family_product_mz, right.family_product_mz)
        > config.product_mz_tolerance_ppm
    ):
        return False
    return (
        _ppm(
            left.family_observed_neutral_loss_da,
            right.family_observed_neutral_loss_da,
        )
        <= config.observed_loss_tolerance_ppm
    )


def _is_pre_backfill_consolidated(feature: object) -> bool:
    evidence = getattr(feature, "evidence", getattr(feature, "fold_evidence", ""))
    return "pre_backfill_identity_consolidated" in str(evidence).split(";")


def _recenter_cell(
    cell: AlignedCell,
    centers_by_id: dict[str, float],
) -> AlignedCell:
    center_rt = centers_by_id.get(cell.cluster_id)
    if center_rt is None or cell.apex_rt is None:
        return cell
    return replace(cell, rt_delta_sec=(cell.apex_rt - center_rt) * 60.0)


def _sample_stems_disjoint(
    left: OwnerAlignedFeature,
    right: OwnerAlignedFeature,
) -> bool:
    return _sample_stems(left).isdisjoint(_sample_stems(right))


def _sample_stems(feature: OwnerAlignedFeature) -> set[str]:
    return {owner.sample_stem for owner in feature.owners}


def _group_match_score(
    feature: OwnerAlignedFeature,
    group: Iterable[OwnerAlignedFeature],
) -> tuple[float, float, str]:
    members = tuple(group)
    return (
        min(
            _ppm(feature.family_center_mz, member.family_center_mz)
            for member in members
        ),
        min(
            abs(feature.family_center_rt - member.family_center_rt)
            for member in members
        ),
        members[0].feature_family_id,
    )


def _feature_sort_key(feature: OwnerAlignedFeature) -> tuple[object, ...]:
    return (
        feature.neutral_loss_tag,
        feature.family_center_mz,
        feature.family_center_rt,
        feature.family_product_mz,
        feature.family_observed_neutral_loss_da,
        feature.feature_family_id,
    )


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0
