import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import xic_extractor.alignment.pipeline as pipeline_module
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.timing import TimingRecorder
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_pipeline_records_alignment_timing_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    recorder = TimingRecorder("alignment", run_id="test-alignment")

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        timing_recorder=recorder,
    )

    stages = [record.stage for record in recorder.records]
    assert stages == [
        "alignment.run_config",
        "alignment.read_batch_index",
        "alignment.read_candidates",
        "alignment.open_raw_sources",
        "alignment.build_owners",
        "alignment.cluster_owners",
        "alignment.owner_backfill",
        "alignment.build_matrix",
        "alignment.claim_registry",
        "alignment.primary_consolidation",
        "alignment.pre_backfill_recenter",
        "alignment.write_outputs",
    ]
    records_by_stage = {record.stage: record for record in recorder.records}
    assert records_by_stage["alignment.run_config"].elapsed_sec == 0.0
    assert records_by_stage["alignment.run_config"].metrics == {
        "raw_workers": 1,
        "raw_xic_batch_size": 1,
        "owner_backfill_xic_backend": "raw",
        "preconsolidate_owner_families": False,
        "output_level": "machine",
        "drift_prior_source": "none",
    }
    assert records_by_stage["alignment.read_candidates"].metrics["candidate_count"] == 1
    assert records_by_stage["alignment.open_raw_sources"].metrics["raw_count"] == 1


def test_pipeline_records_alignment_extract_xic_inner_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_partial_batch(
        tmp_path,
        sample_order=("Sample_A", "Sample_B"),
        candidate_samples=("Sample_A",),
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    monkeypatch.setattr(
        "xic_extractor.alignment.ownership.find_peak_and_area",
        _ok_alignment_peak,
    )
    monkeypatch.setattr(
        "xic_extractor.alignment.owner_backfill.find_peak_and_area",
        _ok_alignment_peak,
    )
    monkeypatch.setattr(
        pipeline_module,
        "_write_outputs_atomic",
        lambda *args, **kwargs: None,
    )
    recorder = TimingRecorder("alignment", run_id="test-inner-timing")

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=TraceRawOpener(),
        timing_recorder=recorder,
    )

    records_by_stage_sample = {
        (record.stage, record.sample_stem): record for record in recorder.records
    }
    build_record = records_by_stage_sample[
        ("alignment.build_owners.extract_xic", "Sample_A")
    ]
    backfill_record = records_by_stage_sample[
        ("alignment.owner_backfill.extract_xic", "Sample_B")
    ]
    expected_metrics = {
        "extract_xic_count": 1,
        "extract_xic_batch_count": 1,
        "raw_chromatogram_call_count": 0,
        "point_count": 3,
    }
    assert build_record.metrics == expected_metrics
    assert backfill_record.metrics == expected_metrics


def test_timed_raw_source_records_batch_calls() -> None:
    from xic_extractor.xic_models import XICRequest, XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.raw_chromatogram_call_count = 0

        def extract_xic_many(self, requests):
            self.raw_chromatogram_call_count += 1
            return tuple(
                XICTrace.from_arrays([request.rt_min], [request.mz])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            self.raw_chromatogram_call_count += 1
            return [rt_min], [mz]

    stats = pipeline_module._RawSourceTimingStats(
        sample_stem="Sample_A",
        stage="alignment.build_owners.extract_xic",
    )
    source = pipeline_module._TimedRawSource(BatchSource(), stats=stats)

    traces = source.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
        )
    )

    assert [trace.intensity.tolist() for trace in traces] == [[258.0], [259.0]]
    assert stats.extract_xic_count == 2
    assert stats.extract_xic_batch_count == 1
    assert stats.raw_chromatogram_call_count == 1
    assert stats.point_count == 2


def test_timed_raw_source_records_batch_failure_metrics() -> None:
    from xic_extractor.xic_models import XICRequest

    class FailingBatchSource:
        def __init__(self) -> None:
            self.raw_chromatogram_call_count = 0

        def extract_xic_many(self, requests):
            self.raw_chromatogram_call_count += 1
            raise RuntimeError("batch failed")

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("fallback should not be used")

    stats = pipeline_module._RawSourceTimingStats(
        sample_stem="Sample_A",
        stage="alignment.build_owners.extract_xic",
    )
    source = pipeline_module._TimedRawSource(FailingBatchSource(), stats=stats)

    with pytest.raises(RuntimeError, match="batch failed"):
        source.extract_xic_many(
            (
                XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
                XICRequest(mz=259.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
            )
        )

    assert stats.extract_xic_count == 2
    assert stats.extract_xic_batch_count == 1
    assert stats.raw_chromatogram_call_count == 1
    assert stats.point_count == 0
    assert stats.elapsed_sec >= 0


def test_timed_raw_source_delegates_scan_window_lookup() -> None:
    from xic_extractor.xic_models import XICRequest

    class WindowSource:
        def scan_window_for_request(self, request):
            return (int(request.rt_min), int(request.rt_max))

    stats = pipeline_module._RawSourceTimingStats(
        sample_stem="Sample_A",
        stage="alignment.build_owners.extract_xic",
    )
    source = pipeline_module._TimedRawSource(WindowSource(), stats=stats)

    window = source.scan_window_for_request(
        XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0)
    )

    assert window == (8, 9)


def _patch_owner_pipeline_to_matrix(monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline_module,
        "build_sample_local_owners",
        lambda candidates, **kwargs: SimpleNamespace(
            owners=(),
            assignments=(),
            ambiguous_records=(),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        lambda owners, *, config, drift_lookup=None, edge_evidence_sink=None: (),
    )
    monkeypatch.setattr(
        pipeline_module,
        "review_only_features_from_ambiguous_records",
        lambda records, *, start_index: (),
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_backfill_cells",
        lambda features, *, sample_order, raw_sources, **kwargs: (),
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        lambda features, *, sample_order, **kwargs: _matrix(sample_order),
    )


class FakeRawOpener:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []
        self.handles: list[FakeRawContext] = []

    def __call__(self, raw_path: Path, dll_dir: Path):
        self.calls.append((raw_path, dll_dir))
        handle = FakeRawContext(raw_path)
        self.handles.append(handle)
        return handle


class FakeRawContext:
    def __init__(self, raw_path: Path) -> None:
        self.raw_path = raw_path
        self.entered = False
        self.closed = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        raise AssertionError("fake pipeline tests monkeypatch backfill")


class TraceRawOpener:
    def __call__(self, raw_path: Path, dll_dir: Path):
        return TraceRawContext(raw_path)


class TraceRawContext:
    def __init__(self, raw_path: Path) -> None:
        self.raw_path = raw_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        return np.asarray([7.9, 8.0, 8.1]), np.asarray([10.0, 100.0, 10.0])


def _ok_alignment_peak(*args, **kwargs):
    peak = SimpleNamespace(
        rt=8.0,
        intensity=100.0,
        area=25.0,
        peak_start=7.9,
        peak_end=8.1,
    )
    return SimpleNamespace(status="OK", peak=peak)


def _write_batch(
    tmp_path: Path,
    sample_order: tuple[str, ...],
    *,
    raw_files: dict[str, str] | None = None,
) -> Path:
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir(exist_ok=True)
    raw_files = raw_files or {}
    rows = []
    for sample_stem in sample_order:
        sample_dir = batch_dir / sample_stem
        sample_dir.mkdir(exist_ok=True)
        candidates_csv = sample_dir / "discovery_candidates.csv"
        _write_csv(
            candidates_csv,
            DISCOVERY_CANDIDATE_COLUMNS,
            [_candidate_row(sample_stem)],
        )
        rows.append(
            {
                "sample_stem": sample_stem,
                "raw_file": raw_files.get(sample_stem, f"C:/stale/{sample_stem}.raw"),
                "candidate_csv": str(candidates_csv.relative_to(batch_dir)),
                "review_csv": "",
            }
        )
    batch_index = batch_dir / "discovery_batch_index.csv"
    _write_csv(
        batch_index,
        ("sample_stem", "raw_file", "candidate_csv", "review_csv"),
        rows,
    )
    return batch_index


def _write_partial_batch(
    tmp_path: Path,
    *,
    sample_order: tuple[str, ...],
    candidate_samples: tuple[str, ...],
) -> Path:
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir(exist_ok=True)
    rows = []
    for sample_stem in sample_order:
        sample_dir = batch_dir / sample_stem
        sample_dir.mkdir(exist_ok=True)
        candidates_csv = sample_dir / "discovery_candidates.csv"
        candidate_rows = (
            [_candidate_row(sample_stem)]
            if sample_stem in candidate_samples
            else []
        )
        _write_csv(candidates_csv, DISCOVERY_CANDIDATE_COLUMNS, candidate_rows)
        rows.append(
            {
                "sample_stem": sample_stem,
                "raw_file": f"C:/stale/{sample_stem}.raw",
                "candidate_csv": str(candidates_csv.relative_to(batch_dir)),
                "review_csv": "",
            }
        )
    batch_index = batch_dir / "discovery_batch_index.csv"
    _write_csv(
        batch_index,
        ("sample_stem", "raw_file", "candidate_csv", "review_csv"),
        rows,
    )
    return batch_index


def _write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _candidate_row(sample_stem: str) -> dict[str, str]:
    return {
        "review_priority": "HIGH",
        "evidence_tier": "A",
        "evidence_score": "80",
        "ms2_support": "strong",
        "ms1_support": "clean",
        "rt_alignment": "aligned",
        "family_context": "singleton",
        "candidate_id": f"{sample_stem}#1",
        "feature_family_id": f"{sample_stem}@F0001",
        "feature_family_size": "1",
        "feature_superfamily_id": f"{sample_stem}@SF0001",
        "feature_superfamily_size": "1",
        "feature_superfamily_role": "representative",
        "feature_superfamily_confidence": "LOW",
        "feature_superfamily_evidence": "single_candidate",
        "precursor_mz": "500.0",
        "product_mz": "384.0",
        "observed_neutral_loss_da": "116.0",
        "best_seed_rt": "8.5",
        "seed_event_count": "2",
        "ms1_peak_found": "TRUE",
        "ms1_apex_rt": "8.5",
        "ms1_area": "1000.0",
        "ms2_product_max_intensity": "500.0",
        "reason": "seed",
        "raw_file": f"C:/stale/{sample_stem}.raw",
        "sample_stem": sample_stem,
        "best_ms2_scan_id": "1",
        "seed_scan_ids": "1;2",
        "neutral_loss_tag": "DNA_dR",
        "configured_neutral_loss_da": "116.0",
        "neutral_loss_mass_error_ppm": "1.0",
        "rt_seed_min": "8.4",
        "rt_seed_max": "8.6",
        "ms1_search_rt_min": "8.2",
        "ms1_search_rt_max": "8.8",
        "ms1_seed_delta_min": "",
        "ms1_peak_rt_start": "8.4",
        "ms1_peak_rt_end": "8.6",
        "ms1_height": "100.0",
        "ms1_trace_quality": "clean",
        "ms1_scan_support_score": "0.8",
        "selected_tag_count": "1",
        "matched_tag_count": "1",
        "matched_tag_names": "DNA_dR",
        "primary_tag_name": "DNA_dR",
        "tag_combine_mode": "single",
        "tag_intersection_status": "not_required",
        "tag_evidence_json": '{"DNA_dR":{"scan_count":2}}',
    }


def _cluster(cluster_id: str = "ALN000001") -> AlignmentCluster:
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=500.0,
        cluster_center_rt=8.5,
        cluster_product_mz=384.0,
        cluster_observed_neutral_loss_da=116.0,
        has_anchor=True,
        members=(),
        anchor_members=(),
    )


def _matrix(sample_order: tuple[str, ...]) -> AlignmentMatrix:
    return AlignmentMatrix(
        clusters=(_cluster(),),
        cells=tuple(
            AlignedCell(
                sample_stem=sample_stem,
                cluster_id="ALN000001",
                status="detected",
                area=100.0,
                apex_rt=8.5,
                height=50.0,
                peak_start_rt=8.4,
                peak_end_rt=8.6,
                rt_delta_sec=0.0,
                trace_quality="clean",
                scan_support_score=0.8,
                source_candidate_id=f"{sample_stem}#1",
                source_raw_file=Path(f"{sample_stem}.raw"),
                reason="detected",
            )
            for sample_stem in sample_order
        ),
        sample_order=sample_order,
    )


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("output.csv"),
        diagnostics_csv=Path("diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
    )
