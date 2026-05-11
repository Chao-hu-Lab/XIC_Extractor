import numpy as np

from tests.test_alignment_owner_clustering import _owner
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.config import ExtractionConfig


def test_owner_backfill_rescues_missing_sample_from_feature_center() -> None:
    source = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 50.0, 120.0, 50.0, 0.0]),
    )
    feature = _feature()

    cells = build_owner_backfill_cells(
        (feature,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=_peak_config(),
    )

    assert len(cells) == 1
    cell = cells[0]
    assert cell.sample_stem == "sample-b"
    assert cell.cluster_id == feature.feature_family_id
    assert cell.status == "rescued"
    assert cell.area is not None and cell.area > 0
    assert cell.reason == "owner-centered MS1 backfill"
    assert source.calls == [(500.0, 7.5, 9.5, 20.0)]


def test_owner_backfill_skips_review_only_identity_conflicts() -> None:
    source = FakeBackfillSource(
        rt=np.array([8.4, 8.5, 8.6]),
        intensity=np.array([0.0, 100.0, 0.0]),
    )

    cells = build_owner_backfill_cells(
        (_feature(review_only=True),),
        sample_order=("sample-b",),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert cells == ()
    assert source.calls == []


def test_owner_backfill_treats_non_finite_trace_as_unchecked() -> None:
    source = FakeBackfillSource(
        rt=np.array([8.4, 8.5, np.nan]),
        intensity=np.array([0.0, 100.0, 0.0]),
    )

    cells = build_owner_backfill_cells(
        (_feature(),),
        sample_order=("sample-b",),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert cells == ()


class FakeBackfillSource:
    def __init__(self, *, rt, intensity) -> None:
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


def _feature(*, review_only: bool = False) -> OwnerAlignedFeature:
    return OwnerAlignedFeature(
        feature_family_id="FAM000001",
        neutral_loss_tag="NL116",
        family_center_mz=500.0,
        family_center_rt=8.5,
        family_product_mz=383.9526,
        family_observed_neutral_loss_da=116.0474,
        has_anchor=True,
        owners=(_owner("sample-a", "a", apex_rt=8.5),),
        evidence="single_sample_local_owner",
        review_only=review_only,
        identity_conflict=review_only,
    )


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=".",
        dll_dir=".",
        output_csv="output.csv",
        diagnostics_csv="diagnostics.csv",
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.01,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
    )
