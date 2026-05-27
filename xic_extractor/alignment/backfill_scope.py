from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.family_compatibility import (
    family_center_mz,
    family_center_rt,
    loose_compatible_primary_family,
)
from xic_extractor.alignment.owner_area import median_owner_area, positive_finite
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner

BackfillScope = Literal["full-audit", "production-equivalent", "selected-families"]
PREDICATE_VERSION = "p7-backfill-scope-v1"
REQUEST_PLAN_VERSION = "p7-owner-backfill-request-plan-v1"

SKIPPED_EVIDENCE_LEDGER_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "family_center_mz",
    "family_center_rt",
    "rt_window_start",
    "rt_window_end",
    "pre_backfill_category",
    "skipped_stage",
    "skip_reason",
    "backfill_scope",
    "predicate_version",
    "raw_xic_requests_skipped",
    "would_emit_in_full_audit",
    "full_audit_available",
    "source_artifact",
)


@dataclass(frozen=True)
class SkippedEvidenceRecord:
    feature_family_id: str
    sample_stem: str
    family_center_mz: float
    family_center_rt: float
    rt_window_start: float
    rt_window_end: float
    pre_backfill_category: str
    skipped_stage: str
    skip_reason: str
    backfill_scope: str
    predicate_version: str
    raw_xic_requests_skipped: int
    would_emit_in_full_audit: bool
    full_audit_available: bool
    source_artifact: str


@dataclass(frozen=True)
class BackfillScopeSelection:
    scope: BackfillScope
    features: tuple[OwnerAlignedFeature, ...]
    skipped: tuple[SkippedEvidenceRecord, ...]
    selected_family_ids: frozenset[str]


def select_backfill_features(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
    scope: BackfillScope,
    selected_family_ids: frozenset[str] = frozenset(),
) -> BackfillScopeSelection:
    if scope == "full-audit":
        return BackfillScopeSelection(
            scope=scope,
            features=features,
            skipped=(),
            selected_family_ids=frozenset(),
        )
    if scope == "selected-families" and not selected_family_ids:
        raise ValueError("selected-families backfill scope requires selected families")
    if scope not in {"production-equivalent", "selected-families"}:
        raise ValueError(
            "backfill scope must be full-audit, production-equivalent, "
            "or selected-families"
        )

    selected: list[OwnerAlignedFeature] = []
    skipped: list[SkippedEvidenceRecord] = []
    for feature in features:
        if scope == "selected-families":
            if feature.feature_family_id in selected_family_ids:
                selected.append(feature)
                continue
            skipped.extend(
                _skipped_records(
                    feature,
                    sample_order=sample_order,
                    raw_sample_stems=raw_sample_stems,
                    alignment_config=alignment_config,
                    scope=scope,
                    category="selected_family_excluded",
                    reason="not_in_selected_family_allowlist",
                )
            )
            continue

        if _can_skip_for_production_equivalence(
            feature,
            features,
            alignment_config=alignment_config,
        ):
            skipped.extend(
                _skipped_records(
                    feature,
                    sample_order=sample_order,
                    raw_sample_stems=raw_sample_stems,
                    alignment_config=alignment_config,
                    scope=scope,
                    category="single_detected_no_consolidation_candidate",
                    reason="single_detected_no_consolidation_candidate",
                )
            )
            continue
        selected.append(feature)

    return BackfillScopeSelection(
        scope=scope,
        features=tuple(selected),
        skipped=tuple(skipped),
        selected_family_ids=frozenset(selected_family_ids),
    )


def backfill_request_sample_stems(
    feature: OwnerAlignedFeature,
    *,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
) -> tuple[str, ...]:
    if bool(getattr(feature, "review_only", False)):
        return ()
    detected_samples = {owner.sample_stem for owner in feature.owners}
    if len(detected_samples) < alignment_config.owner_backfill_min_detected_samples:
        return ()
    owners_by_sample: dict[str, list[SampleLocalMS1Owner]] = defaultdict(list)
    for owner in feature.owners:
        owners_by_sample[owner.sample_stem].append(owner)

    requested: list[str] = []
    for sample_stem in sample_order:
        if sample_stem not in raw_sample_stems:
            continue
        if (
            sample_stem in detected_samples
            and not feature.confirm_local_owners_with_backfill
        ):
            continue
        if sample_stem in detected_samples and not any_detected_owner_can_be_superseded(
            feature,
            owners_by_sample.get(sample_stem),
        ):
            continue
        requested.append(sample_stem)
    return tuple(requested)


def backfill_features_for_sample(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_stem: str,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
) -> tuple[OwnerAlignedFeature, ...]:
    return tuple(
        feature
        for feature in features
        if sample_stem
        in backfill_request_sample_stems(
            feature,
            sample_order=sample_order,
            raw_sample_stems=raw_sample_stems,
            alignment_config=alignment_config,
        )
    )


def backfill_seed_centers(
    feature: OwnerAlignedFeature,
) -> tuple[tuple[float, float], ...]:
    return feature.backfill_seed_centers or (
        (feature.family_center_mz, feature.family_center_rt),
    )


def any_detected_owner_can_be_superseded(
    feature: OwnerAlignedFeature,
    owners: Sequence[SampleLocalMS1Owner] | None,
) -> bool:
    return any(
        detected_owner_can_be_superseded(feature, owner) for owner in owners or ()
    )


def detected_owner_can_be_superseded(
    feature: OwnerAlignedFeature,
    owner: SampleLocalMS1Owner,
) -> bool:
    detected_area = positive_finite(owner.owner_area)
    if detected_area is None:
        return False
    family_area = median_owner_area(feature)
    if family_area is None:
        return False
    return detected_area <= family_area * 0.25


def read_family_allowlist_tsv(
    path: Path,
    *,
    family_id_column: str,
) -> frozenset[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or family_id_column not in reader.fieldnames:
            raise ValueError(f"{path}: missing required column {family_id_column!r}")
        family_ids = frozenset(
            str(row.get(family_id_column, "")).strip()
            for row in reader
            if str(row.get(family_id_column, "")).strip()
        )
    if not family_ids:
        raise ValueError(f"{path}: no selected family ids found")
    return family_ids


def write_skipped_evidence_ledger_tsv(
    path: Path,
    rows: Sequence[SkippedEvidenceRecord],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SKIPPED_EVIDENCE_LEDGER_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    return path


def skipped_evidence_summary(rows: Sequence[SkippedEvidenceRecord]) -> dict[str, int]:
    return {
        "skipped_evidence_row_count": len(rows),
        "raw_xic_requests_skipped": sum(row.raw_xic_requests_skipped for row in rows),
    }


def _can_skip_for_production_equivalence(
    feature: OwnerAlignedFeature,
    features: tuple[OwnerAlignedFeature, ...],
    *,
    alignment_config: AlignmentConfig,
) -> bool:
    if bool(getattr(feature, "review_only", False)):
        return True
    if bool(getattr(feature, "confirm_local_owners_with_backfill", False)):
        return False
    if len({owner.sample_stem for owner in feature.owners}) != 1:
        return False
    return not any(
        other is not feature
        and not bool(getattr(other, "review_only", False))
        and loose_compatible_primary_family(feature, other, alignment_config)
        for other in features
    )


def _skipped_records(
    feature: OwnerAlignedFeature,
    *,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
    scope: BackfillScope,
    category: str,
    reason: str,
) -> tuple[SkippedEvidenceRecord, ...]:
    request_samples = backfill_request_sample_stems(
        feature,
        sample_order=sample_order,
        raw_sample_stems=raw_sample_stems,
        alignment_config=alignment_config,
    )
    if not request_samples:
        return ()
    seed_centers = backfill_seed_centers(feature)
    seed_rt_values = [seed_rt for _seed_mz, seed_rt in seed_centers]
    rt_window_min = alignment_config.max_rt_sec / 60.0
    rt_window_start = min(seed_rt_values) - rt_window_min
    rt_window_end = max(seed_rt_values) + rt_window_min
    return tuple(
        SkippedEvidenceRecord(
            feature_family_id=feature.feature_family_id,
            sample_stem=sample_stem,
            family_center_mz=family_center_mz(feature),
            family_center_rt=family_center_rt(feature),
            rt_window_start=rt_window_start,
            rt_window_end=rt_window_end,
            pre_backfill_category=category,
            skipped_stage="owner_backfill",
            skip_reason=reason,
            backfill_scope=scope,
            predicate_version=PREDICATE_VERSION,
            raw_xic_requests_skipped=len(seed_centers),
            would_emit_in_full_audit=True,
            full_audit_available=True,
            source_artifact="owner_backfill",
        )
        for sample_stem in request_samples
    )
