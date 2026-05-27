from pathlib import Path
from types import SimpleNamespace

from tools.diagnostics import backfill_scope_probe
from xic_extractor.alignment.config import AlignmentConfig


def test_locality_summary_uses_actual_backfill_seed_centers(tmp_path: Path) -> None:
    features = (
        _feature(
            "FAM000001",
            seed_centers=((100.0, 5.0), (101.0, 5.0)),
        ),
        _feature(
            "FAM000002",
            seed_centers=((200.0, 8.0),),
        ),
    )

    summary = backfill_scope_probe._locality_summary(
        features,
        sample_order=("sample-a", "sample-b"),
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        alignment_config=AlignmentConfig(),
        raw_xic_batch_size=2,
        open_raw_func=fake_open_raw,
    )

    assert summary["totals"]["extract_request_count"] == 3
    assert summary["totals"]["scan_window_aware_chunk_count"] == 2
    assert summary["totals"]["chunked_raw_chromatogram_call_count"] == 2
    assert summary["totals"]["unique_scan_window_count"] == 2
    assert summary["totals"]["mean_xic_per_chunked_raw_call"] == 1.5
    assert summary["totals"]["overlap_component_count"] == 1
    assert summary["totals"]["max_overlap_component_scan_span"] == 90
    assert summary["totals"]["superwindow_call_count_span_x1"] == 2
    assert summary["totals"]["superwindow_call_count_span_x2"] == 1
    assert summary["totals"]["superwindow_call_count_span_x4"] == 1
    assert summary["sample_rows"] == [
        {
            "sample_stem": "sample-a",
            "extract_request_count": 0,
            "scan_window_aware_chunk_count": 0,
            "chunked_raw_chromatogram_call_count": 0,
            "unique_scan_window_count": 0,
            "mean_xic_per_chunked_raw_call": "",
        },
        {
            "sample_stem": "sample-b",
            "extract_request_count": 3,
            "scan_window_aware_chunk_count": 2,
            "chunked_raw_chromatogram_call_count": 2,
            "unique_scan_window_count": 2,
            "mean_xic_per_chunked_raw_call": 1.5,
        },
    ]


def _feature(
    family_id: str,
    *,
    seed_centers: tuple[tuple[float, float], ...],
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=seed_centers[0][0],
        family_center_rt=seed_centers[0][1],
        family_product_mz=384.0,
        family_observed_neutral_loss_da=116.0,
        review_only=False,
        confirm_local_owners_with_backfill=False,
        backfill_seed_centers=seed_centers,
        owners=(SimpleNamespace(sample_stem="sample-a", owner_area=100.0),),
    )


class FakeRaw:
    def __enter__(self) -> "FakeRaw":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def scan_window_for_request(self, request) -> tuple[int, int]:
        return (int(request.rt_min * 10), int(request.rt_max * 10))


def fake_open_raw(_path: Path, _dll_dir: Path) -> FakeRaw:
    return FakeRaw()
