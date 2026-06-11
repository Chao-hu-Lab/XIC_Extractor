from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NamedTuple

from xic_extractor.alignment.backfill_scope import (
    backfill_request_sample_stems,
    backfill_seed_centers,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.owner_group_delivery import (
    OwnerGroupDeliveryFeature,
    OwnerGroupDeliveryFeatures,
)
from xic_extractor.xic_models import XICRequest


class OwnerBackfillRequestItem(NamedTuple):
    feature: OwnerGroupDeliveryFeature
    sample_stem: str
    request: XICRequest
    preferred_rt: float


@dataclass(frozen=True)
class OwnerBackfillRequestPlan:
    requests_by_sample: Mapping[str, tuple[OwnerBackfillRequestItem, ...]]

    def requests_for_sample(
        self,
        sample_stem: str,
    ) -> tuple[OwnerBackfillRequestItem, ...]:
        return self.requests_by_sample.get(sample_stem, ())

    def features_for_sample(
        self,
        sample_stem: str,
    ) -> OwnerGroupDeliveryFeatures:
        features: list[OwnerGroupDeliveryFeature] = []
        seen_feature_ids: set[int] = set()
        for item in self.requests_for_sample(sample_stem):
            feature_id = id(item.feature)
            if feature_id in seen_feature_ids:
                continue
            seen_feature_ids.add(feature_id)
            features.append(item.feature)
        return tuple(features)

    def request_count_for_sample(self, sample_stem: str) -> int:
        return len(self.requests_for_sample(sample_stem))


def build_owner_backfill_request_plan(
    features: OwnerGroupDeliveryFeatures,
    *,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
) -> OwnerBackfillRequestPlan:
    pending: dict[str, list[OwnerBackfillRequestItem]] = defaultdict(list)
    rt_window_min = alignment_config.max_rt_sec / 60.0
    for feature in features:
        seed_centers = backfill_seed_centers(feature)
        for sample_stem in backfill_request_sample_stems(
            feature,
            sample_order=sample_order,
            raw_sample_stems=raw_sample_stems,
            alignment_config=alignment_config,
        ):
            for seed_mz, seed_rt in seed_centers:
                pending[sample_stem].append(
                    OwnerBackfillRequestItem(
                        feature=feature,
                        sample_stem=sample_stem,
                        request=XICRequest(
                            mz=seed_mz,
                            rt_min=seed_rt - rt_window_min,
                            rt_max=seed_rt + rt_window_min,
                            ppm_tol=alignment_config.preferred_ppm,
                        ),
                        preferred_rt=seed_rt,
                    )
                )
    return OwnerBackfillRequestPlan(
        requests_by_sample={
            sample_stem: tuple(sample_requests)
            for sample_stem, sample_requests in pending.items()
        },
    )
