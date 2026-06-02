from __future__ import annotations

from typing import Protocol, TypeAlias

from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner


class OwnerGroupDeliveryFeature(Protocol):
    @property
    def feature_family_id(self) -> str: ...

    @property
    def cluster_id(self) -> str: ...

    @property
    def neutral_loss_tag(self) -> str: ...

    @property
    def family_center_mz(self) -> float: ...

    @property
    def family_center_rt(self) -> float: ...

    @property
    def family_product_mz(self) -> float: ...

    @property
    def family_observed_neutral_loss_da(self) -> float: ...

    @property
    def has_anchor(self) -> bool: ...

    @property
    def owners(self) -> tuple[SampleLocalMS1Owner, ...]: ...

    @property
    def members(self) -> tuple[SampleLocalMS1Owner, ...]: ...

    @property
    def event_cluster_ids(self) -> tuple[str, ...]: ...

    @property
    def event_member_count(self) -> int: ...

    @property
    def evidence(self) -> str: ...

    @property
    def identity_conflict(self) -> bool: ...

    @property
    def review_only(self) -> bool: ...

    @property
    def confirm_local_owners_with_backfill(self) -> bool: ...

    @property
    def backfill_seed_centers(self) -> tuple[tuple[float, float], ...]: ...

    @property
    def ambiguous_sample_stem(self) -> str | None: ...

    @property
    def ambiguous_candidate_ids(self) -> tuple[str, ...]: ...


OwnerGroupDeliveryFeatures: TypeAlias = tuple[OwnerGroupDeliveryFeature, ...]
