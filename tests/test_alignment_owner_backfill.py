from dataclasses import replace

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


def test_owner_backfill_skips_features_below_min_detected_sample_gate() -> None:
    source = FakeBackfillSource(
        rt=np.array([8.4, 8.5, 8.6]),
        intensity=np.array([0.0, 100.0, 0.0]),
    )

    cells = build_owner_backfill_cells(
        (_feature(),),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(owner_backfill_min_detected_samples=2),
        peak_config=_peak_config(),
    )

    assert cells == ()
    assert source.calls == []


def test_owner_backfill_skips_detected_confirmation_when_owner_cannot_change() -> None:
    source_a = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 50.0, 100.0, 50.0, 0.0]),
    )
    source_b = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 60.0, 120.0, 60.0, 0.0]),
    )
    feature = replace(_feature(), confirm_local_owners_with_backfill=True)

    cells = build_owner_backfill_cells(
        (feature,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-a": source_a, "sample-b": source_b},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
    ]
    assert source_a.calls == []
    assert source_b.calls == [(500.0, 5.5, 11.5, 20.0)]


def test_owner_backfill_confirms_low_detected_preconsolidated_owner() -> None:
    source_a = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 500.0, 1200.0, 500.0, 0.0]),
    )
    source_b = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 60.0, 120.0, 60.0, 0.0]),
    )
    low_owner = replace(_owner("sample-a", "a"), owner_area=100.0)
    typical_owner = replace(_owner("sample-b", "b"), owner_area=1000.0)
    feature = replace(
        _feature(),
        owners=(low_owner, typical_owner),
        confirm_local_owners_with_backfill=True,
    )

    cells = build_owner_backfill_cells(
        (feature,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-a": source_a, "sample-b": source_b},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-a"),
    ]
    assert source_a.calls == [(500.0, 5.5, 11.5, 20.0)]
    assert source_b.calls == []


def test_owner_backfill_confirms_any_low_owner_for_duplicate_sample() -> None:
    source_a = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 500.0, 1200.0, 500.0, 0.0]),
    )
    source_b = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 60.0, 120.0, 60.0, 0.0]),
    )
    low_owner = replace(_owner("sample-a", "low"), owner_area=100.0)
    typical_owner = replace(_owner("sample-b", "b"), owner_area=1000.0)
    high_owner = replace(_owner("sample-a", "high"), owner_area=1000.0)
    feature = replace(
        _feature(),
        owners=(low_owner, typical_owner, high_owner),
        confirm_local_owners_with_backfill=True,
    )

    cells = build_owner_backfill_cells(
        (feature,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-a": source_a, "sample-b": source_b},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-a"),
    ]
    assert source_a.calls == [(500.0, 5.5, 11.5, 20.0)]
    assert source_b.calls == []


def test_owner_backfill_uses_preconsolidated_seed_centers_and_keeps_best_peak() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.centers: list[float] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            traces = []
            for request in requests:
                center = (request.rt_min + request.rt_max) / 2.0
                self.centers.append(center)
                intensity = 300.0 if round(center, 1) == 8.8 else 100.0
                traces.append(
                    XICTrace.from_arrays(
                        [
                            center - 0.10,
                            center - 0.01,
                            center,
                            center + 0.01,
                            center + 0.10,
                        ],
                        [0.0, intensity / 2.0, intensity, intensity / 2.0, 0.0],
                    )
                )
            return tuple(traces)

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    feature = replace(
        _feature(),
        backfill_seed_centers=((500.0, 8.5), (500.0, 8.8)),
    )

    cells = build_owner_backfill_cells(
        (feature,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_xic_batch_size=64,
    )

    assert source.centers == [8.5, 8.8]
    assert len(cells) == 1
    assert cells[0].sample_stem == "sample-b"
    assert cells[0].area is not None and cells[0].area > 0
    assert cells[0].apex_rt == 8.8


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


def test_owner_backfill_uses_batch_source_and_preserves_feature_major_order() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_sizes.append(len(requests))
            traces = []
            for request in requests:
                center = (request.rt_min + request.rt_max) / 2.0
                traces.append(
                    XICTrace.from_arrays(
                        [
                            center - 0.10,
                            center - 0.01,
                            center,
                            center + 0.01,
                            center + 0.10,
                        ],
                        [0.0, 50.0, 120.0, 50.0, 0.0],
                    )
                )
            return tuple(traces)

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source_b = BatchSource()
    source_c = BatchSource()
    feature_a = _feature()
    feature_b = _feature(feature_family_id="FAM000002", mz=510.0, rt=8.8)

    cells = build_owner_backfill_cells(
        (feature_a, feature_b),
        sample_order=("sample-a", "sample-b", "sample-c"),
        raw_sources={"sample-b": source_b, "sample-c": source_c},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_xic_batch_size=64,
    )

    assert source_b.batch_sizes == [2]
    assert source_c.batch_sizes == [2]
    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
        ("FAM000001", "sample-c"),
        ("FAM000002", "sample-b"),
        ("FAM000002", "sample-c"),
    ]


def test_owner_backfill_deduplicates_identical_xic_requests() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_sizes.append(len(requests))
            return tuple(
                XICTrace.from_arrays(
                    [
                        (request.rt_min + request.rt_max) / 2.0 - 0.10,
                        (request.rt_min + request.rt_max) / 2.0 - 0.01,
                        (request.rt_min + request.rt_max) / 2.0,
                        (request.rt_min + request.rt_max) / 2.0 + 0.01,
                        (request.rt_min + request.rt_max) / 2.0 + 0.10,
                    ],
                    [0.0, 50.0, 120.0, 50.0, 0.0],
                )
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    feature_a = _feature(feature_family_id="FAM000001", mz=500.0, rt=8.5)
    feature_b = _feature(feature_family_id="FAM000002", mz=500.0, rt=8.5)

    cells = build_owner_backfill_cells(
        (feature_a, feature_b),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_xic_batch_size=64,
    )

    assert source.batch_sizes == [1]
    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
        ("FAM000002", "sample-b"),
    ]


def test_owner_backfill_validates_prefilter_hits_with_secondary_source() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self, traces) -> None:
            self.traces = tuple(traces)
            self.requests = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.requests.append(requests)
            return self.traces[: len(requests)]

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    feature_a = _feature(feature_family_id="FAM000001", mz=500.0, rt=8.5)
    feature_b = _feature(feature_family_id="FAM000002", mz=510.0, rt=10.5)
    prefilter = BatchSource(
        (
            XICTrace.from_arrays(
                [8.40, 8.49, 8.50, 8.51, 8.60],
                [0.0, 50.0, 120.0, 50.0, 0.0],
            ),
            XICTrace.from_arrays(
                [10.40, 10.49, 10.50, 10.51, 10.60],
                [0.0, 0.0, 0.0, 0.0, 0.0],
            ),
        )
    )
    validator = BatchSource(
        (
            XICTrace.from_arrays(
                [8.40, 8.49, 8.50, 8.51, 8.60],
                [0.0, 100.0, 240.0, 100.0, 0.0],
            ),
        )
    )

    cells = build_owner_backfill_cells(
        (feature_a, feature_b),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": prefilter},
        validation_raw_sources={"sample-b": validator},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=_peak_config(),
        raw_xic_batch_size=64,
    )

    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
    ]
    assert cells[0].height == 240.0
    assert len(prefilter.requests[0]) == 2
    assert len(validator.requests[0]) == 1
    assert validator.requests[0][0].mz == 500.0


def test_owner_backfill_batches_by_rt_window_without_changing_emit_order() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_centers: list[tuple[float, ...]] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_centers.append(
                tuple(
                    round((request.rt_min + request.rt_max) / 2.0, 3)
                    for request in requests
                )
            )
            traces = []
            for request in requests:
                center = (request.rt_min + request.rt_max) / 2.0
                traces.append(
                    XICTrace.from_arrays(
                        [
                            center - 0.10,
                            center - 0.01,
                            center,
                            center + 0.01,
                            center + 0.10,
                        ],
                        [0.0, 50.0, 120.0, 50.0, 0.0],
                    )
                )
            return tuple(traces)

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    feature_a = _feature(feature_family_id="FAM000001", mz=500.0, rt=8.5)
    feature_b = _feature(feature_family_id="FAM000002", mz=510.0, rt=10.5)
    feature_c = _feature(feature_family_id="FAM000003", mz=520.0, rt=8.5)

    cells = build_owner_backfill_cells(
        (feature_a, feature_b, feature_c),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=_peak_config(),
        raw_xic_batch_size=2,
    )

    assert source.batch_centers == [(8.5, 8.5), (10.5,)]
    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
        ("FAM000002", "sample-b"),
        ("FAM000003", "sample-b"),
    ]


def test_owner_backfill_does_not_split_source_scan_window_groups() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_centers: list[tuple[float, ...]] = []

        def scan_window_for_request(self, _request):
            return (100, 200)

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_centers.append(
                tuple(
                    round((request.rt_min + request.rt_max) / 2.0, 3)
                    for request in requests
                )
            )
            traces = []
            for request in requests:
                center = (request.rt_min + request.rt_max) / 2.0
                traces.append(
                    XICTrace.from_arrays(
                        [
                            center - 0.10,
                            center - 0.01,
                            center,
                            center + 0.01,
                            center + 0.10,
                        ],
                        [0.0, 50.0, 120.0, 50.0, 0.0],
                    )
                )
            return tuple(traces)

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    feature_a = _feature(feature_family_id="FAM000001", mz=500.0, rt=8.50)
    feature_b = _feature(feature_family_id="FAM000002", mz=510.0, rt=8.51)
    feature_c = _feature(feature_family_id="FAM000003", mz=520.0, rt=8.52)

    cells = build_owner_backfill_cells(
        (feature_a, feature_b, feature_c),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=_peak_config(),
        raw_xic_batch_size=2,
    )

    assert source.batch_centers == [(8.5, 8.51, 8.52)]
    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("FAM000001", "sample-b"),
        ("FAM000002", "sample-b"),
        ("FAM000003", "sample-b"),
    ]


def test_owner_backfill_falls_back_when_scan_window_unavailable() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_centers: list[tuple[float, ...]] = []

        def scan_window_for_request(self, _request):
            raise AttributeError("scan window lookup is unavailable")

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_centers.append(
                tuple(
                    round((request.rt_min + request.rt_max) / 2.0, 3)
                    for request in requests
                )
            )
            return tuple(
                XICTrace.from_arrays(
                    [
                        (request.rt_min + request.rt_max) / 2.0 - 0.01,
                        (request.rt_min + request.rt_max) / 2.0,
                        (request.rt_min + request.rt_max) / 2.0 + 0.01,
                    ],
                    [0.0, 120.0, 0.0],
                )
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()

    build_owner_backfill_cells(
        (
            _feature(feature_family_id="FAM000001", mz=500.0, rt=8.5),
            _feature(feature_family_id="FAM000002", mz=510.0, rt=10.5),
            _feature(feature_family_id="FAM000003", mz=520.0, rt=8.5),
        ),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=_peak_config(),
        raw_xic_batch_size=2,
    )

    assert source.batch_centers == [(8.5, 8.5), (10.5,)]


class FakeBackfillSource:
    def __init__(self, *, rt, intensity) -> None:
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


def _feature(
    *,
    review_only: bool = False,
    feature_family_id: str = "FAM000001",
    mz: float = 500.0,
    rt: float = 8.5,
) -> OwnerAlignedFeature:
    return OwnerAlignedFeature(
        feature_family_id=feature_family_id,
        neutral_loss_tag="NL116",
        family_center_mz=mz,
        family_center_rt=rt,
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
