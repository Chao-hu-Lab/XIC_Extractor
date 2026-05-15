import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import xic_extractor.alignment.pipeline as pipeline_module
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.process_backend import (
    OwnerBackfillProcessOutput,
    OwnerBackfillTimingStats,
    OwnerBuildProcessOutput,
    OwnerBuildTimingStats,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.timing import TimingRecorder
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_pipeline_loads_candidates_builds_owners_backfills_and_writes_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A", "Sample_B"))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_build_owners(
        candidates,
        *,
        raw_sources,
        alignment_config,
        peak_config,
        raw_xic_batch_size,
    ):
        calls["candidates"] = tuple(candidate.sample_stem for candidate in candidates)
        calls["owner_raw_sources"] = raw_sources
        calls["alignment_config"] = alignment_config
        calls["peak_config"] = peak_config
        calls["owner_raw_xic_batch_size"] = raw_xic_batch_size
        return SimpleNamespace(owners=("owner",), ambiguous_records=())

    def fake_cluster_owners(owners, *, config):
        calls["owners"] = owners
        calls["cluster_config"] = config
        return ("feature",)

    def fake_owner_backfill(
        features,
        *,
        sample_order,
        raw_sources,
        alignment_config,
        peak_config,
        raw_xic_batch_size,
    ):
        calls["features"] = features
        calls["sample_order"] = sample_order
        calls["raw_sources"] = raw_sources
        calls["backfill_raw_xic_batch_size"] = raw_xic_batch_size
        return ("rescued",)

    def fake_owner_matrix(
        features,
        *,
        sample_order,
        ambiguous_by_sample,
        rescued_cells,
    ):
        calls["matrix_features"] = features
        calls["ambiguous_by_sample"] = ambiguous_by_sample
        calls["rescued_cells"] = rescued_cells
        return _matrix(sample_order)

    monkeypatch.setattr(pipeline_module, "build_sample_local_owners", fake_build_owners)
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        fake_cluster_owners,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_backfill_cells",
        fake_owner_backfill,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        fake_owner_matrix,
    )

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )

    assert calls["candidates"] == ("Sample_A", "Sample_B")
    assert calls["owners"] == ("owner",)
    assert calls["features"] == ("feature",)
    assert calls["sample_order"] == ("Sample_A", "Sample_B")
    assert set(calls["raw_sources"]) == {"Sample_A", "Sample_B"}
    assert calls["owner_raw_xic_batch_size"] == 1
    assert calls["backfill_raw_xic_batch_size"] == 1
    assert calls["matrix_features"] == ("feature",)
    assert calls["ambiguous_by_sample"] == {}
    assert calls["rescued_cells"] == ("rescued",)
    assert outputs.review_tsv == tmp_path / "out" / "alignment_review.tsv"
    assert outputs.matrix_tsv == tmp_path / "out" / "alignment_matrix.tsv"
    assert outputs.workbook == tmp_path / "out" / "alignment_results.xlsx"
    assert outputs.review_html == tmp_path / "out" / "review_report.html"
    assert outputs.cells_tsv is None
    assert outputs.status_matrix_tsv is None
    assert outputs.workbook.exists()
    assert outputs.review_html.exists()
    assert outputs.review_tsv.exists()
    assert outputs.matrix_tsv.exists()
    assert not (tmp_path / "out" / "alignment_cells.tsv").exists()
    assert not (tmp_path / "out" / "alignment_matrix_status.tsv").exists()


def test_pipeline_applies_single_worker_hybrid_owner_backfill_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        pipeline_module,
        "build_sample_local_owners",
        lambda candidates, **kwargs: SimpleNamespace(
            owners=("owner",),
            assignments=(),
            ambiguous_records=(),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        lambda owners, *, config, drift_lookup=None, edge_evidence_sink=None: (
            "feature",
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "review_only_features_from_ambiguous_records",
        lambda records, *, start_index: (),
    )

    def fake_source_for_owner_backfill_backend(source, backend):
        calls["backend"] = backend
        return SimpleNamespace(kind="indexed", source=source)

    def fake_owner_backfill(
        features,
        *,
        sample_order,
        raw_sources,
        validation_raw_sources=None,
        **kwargs,
    ):
        calls["backfill_raw_sources"] = raw_sources
        calls["validation_raw_sources"] = validation_raw_sources
        return ()

    monkeypatch.setattr(
        pipeline_module,
        "source_for_owner_backfill_backend",
        fake_source_for_owner_backfill_backend,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_backfill_cells",
        fake_owner_backfill,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        lambda features, *, sample_order, **kwargs: _matrix(sample_order),
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        owner_backfill_xic_backend="ms1_index_hybrid",
    )

    assert calls["backend"] == "ms1_index_hybrid"
    assert set(calls["backfill_raw_sources"]) == {"Sample_A"}
    assert set(calls["validation_raw_sources"]) == {"Sample_A"}
    assert (
        calls["backfill_raw_sources"]["Sample_A"]
        is not calls["validation_raw_sources"]["Sample_A"]
    )


def test_pipeline_preconsolidates_owner_families_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        pipeline_module,
        "build_sample_local_owners",
        lambda candidates, **kwargs: SimpleNamespace(
            owners=("owner",),
            assignments=(),
            ambiguous_records=(),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        lambda owners, *, config, drift_lookup=None, edge_evidence_sink=None: (
            "feature",
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "review_only_features_from_ambiguous_records",
        lambda records, *, start_index: (),
    )

    def fake_preconsolidate(features, *, config):
        calls["preconsolidate_features"] = features
        return ("consolidated",)

    def fake_owner_backfill(features, **kwargs):
        calls["backfill_features"] = features
        return ()

    monkeypatch.setattr(
        pipeline_module,
        "consolidate_pre_backfill_identity_families",
        fake_preconsolidate,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_backfill_cells",
        fake_owner_backfill,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        lambda features, *, sample_order, **kwargs: _matrix(sample_order),
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        preconsolidate_owner_families=True,
    )

    assert calls["preconsolidate_features"] == ("feature",)
    assert calls["backfill_features"] == ("consolidated",)


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


def test_pipeline_uses_process_owner_backfill_when_raw_workers_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    opener = FakeRawOpener()
    calls = {}
    rescued = _cell("Sample_A", cluster_id="ALN000001")
    recorder = TimingRecorder("alignment", run_id="test-process-backfill")

    def fake_process_backfill(features, **kwargs):
        calls["features"] = features
        calls.update(kwargs)
        assert opener.calls == []
        return OwnerBackfillProcessOutput(
            cells=(rescued,),
            timing_stats=(
                OwnerBackfillTimingStats(
                    sample_stem="Sample_A",
                    elapsed_sec=1.5,
                    extract_xic_count=4,
                    point_count=40,
                ),
            ),
        )

    def fake_process_build(candidates, **kwargs):
        calls["build_candidates"] = tuple(
            candidate.sample_stem for candidate in candidates
        )
        calls["build_kwargs"] = kwargs
        return OwnerBuildProcessOutput(
            ownership=OwnershipBuildResult(
                owners=(),
                assignments=(),
                ambiguous_records=(),
            ),
            timing_stats=(
                OwnerBuildTimingStats(
                    sample_stem="Sample_A",
                    elapsed_sec=2.5,
                    extract_xic_count=5,
                    point_count=50,
                ),
            ),
        )

    monkeypatch.setattr(
        pipeline_module,
        "run_owner_build_process",
        fake_process_build,
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
        "run_owner_backfill_process",
        fake_process_backfill,
    )
    def fake_owner_matrix(features, *, sample_order, rescued_cells, **kwargs):
        calls["rescued_cells"] = rescued_cells
        return _matrix(sample_order)

    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        fake_owner_matrix,
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=opener,
        raw_workers=2,
        owner_backfill_xic_backend="ms1_index",
        timing_recorder=recorder,
    )

    assert calls["max_workers"] == 2
    assert calls["raw_paths"] == {"Sample_A": raw_dir / "Sample_A.raw"}
    assert calls["rescued_cells"] == (rescued,)
    assert calls["build_kwargs"]["max_workers"] == 2
    assert calls["raw_xic_batch_size"] == 1
    assert calls["owner_backfill_xic_backend"] == "ms1_index"
    assert calls["build_kwargs"]["raw_xic_batch_size"] == 1
    assert "owner_backfill_xic_backend" not in calls["build_kwargs"]
    records_by_stage_sample = {
        (record.stage, record.sample_stem): record for record in recorder.records
    }
    assert records_by_stage_sample[
        ("alignment.build_owners.extract_xic", "Sample_A")
    ].metrics == {
        "extract_xic_count": 5,
        "extract_xic_batch_count": 0,
        "raw_chromatogram_call_count": 0,
        "point_count": 50,
    }
    assert records_by_stage_sample[
        ("alignment.owner_backfill.extract_xic", "Sample_A")
    ].metrics == {
        "extract_xic_count": 4,
        "extract_xic_batch_count": 0,
        "raw_chromatogram_call_count": 0,
        "point_count": 40,
    }


def test_pipeline_uses_raw_dir_as_authority_and_fallbacks_to_sample_stem(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(
        tmp_path,
        ("Sample_A", "Sample_B", "Sample_C"),
        raw_files={
            "Sample_A": "C:/stale/renamed.raw",
            "Sample_B": "",
            "Sample_C": "C:/stale/missing.raw",
        },
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "renamed.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    opener = FakeRawOpener()
    captured_sources = {}

    def fake_build_owners(candidates, *, raw_sources, **kwargs):
        captured_sources.update(raw_sources)
        return SimpleNamespace(owners=(), ambiguous_records=())

    monkeypatch.setattr(pipeline_module, "build_sample_local_owners", fake_build_owners)
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        lambda owners, *, config, drift_lookup=None, edge_evidence_sink=None: (),
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

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=opener,
    )

    assert [call[0] for call in opener.calls] == [
        raw_dir / "renamed.raw",
        raw_dir / "Sample_B.raw",
    ]
    assert set(captured_sources) == {"Sample_A", "Sample_B"}


def test_pipeline_enters_and_closes_raw_handles_on_success_and_write_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    opener = FakeRawOpener()

    _patch_owner_pipeline_to_matrix(monkeypatch)

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out_success",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=opener,
    )
    assert opener.handles[0].entered is True
    assert opener.handles[0].closed is True

    def fail_matrix_writer(path, matrix, *, alignment_config=None):
        raise RuntimeError("writer failed")

    monkeypatch.setattr(
        pipeline_module,
        "write_alignment_matrix_tsv",
        fail_matrix_writer,
    )
    with pytest.raises(RuntimeError, match="writer failed"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=tmp_path / "out_failure",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=opener,
        )
    assert opener.handles[-1].entered is True
    assert opener.handles[-1].closed is True


def test_pipeline_debug_flags_write_optional_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        emit_alignment_cells=True,
        emit_alignment_status_matrix=True,
        raw_opener=FakeRawOpener(),
    )

    assert outputs.cells_tsv == tmp_path / "out" / "alignment_cells.tsv"
    assert outputs.status_matrix_tsv == tmp_path / "out" / "alignment_matrix_status.tsv"
    assert outputs.cells_tsv.exists()
    assert outputs.status_matrix_tsv.exists()


def test_pipeline_default_path_no_longer_uses_legacy_near_duplicate_folding() -> None:
    assert not hasattr(pipeline_module, "fold_near_duplicate_clusters")


def test_pipeline_builds_owner_features_before_owner_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}
    owner = SimpleNamespace(owner_id="OWN-Sample_A-000001")
    feature = SimpleNamespace(
        feature_family_id="FAM000001",
        neutral_loss_tag="DNA_dR",
        family_center_mz=500.0,
        family_center_rt=8.5,
        family_product_mz=384.0,
        family_observed_neutral_loss_da=116.0,
        has_anchor=True,
        event_cluster_ids=("ALN000001",),
        event_member_count=1,
        evidence="single_sample_local_owner",
    )
    owner_matrix = AlignmentMatrix(
        clusters=(feature,),
        cells=(),
        sample_order=("Sample_A",),
    )

    def fake_build_owners(candidates, **kwargs):
        calls["candidates"] = tuple(candidate.candidate_id for candidate in candidates)
        return SimpleNamespace(owners=(owner,), ambiguous_records=("ambiguous",))

    def fake_cluster_owners(
        owners,
        *,
        config,
        drift_lookup=None,
        edge_evidence_sink=None,
    ):
        calls["owners"] = owners
        return (feature,)

    def fake_backfill(features, *, sample_order, raw_sources, **kwargs):
        calls["backfill_features"] = features
        calls["sample_order"] = sample_order
        calls["raw_sources"] = raw_sources
        return ("rescued",)

    def fake_owner_matrix(features, *, ambiguous_by_sample, rescued_cells, **kwargs):
        calls["matrix_features"] = features
        calls["ambiguous_by_sample"] = ambiguous_by_sample
        calls["rescued_cells"] = rescued_cells
        return owner_matrix

    monkeypatch.setattr(
        pipeline_module,
        "build_sample_local_owners",
        fake_build_owners,
    )
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        fake_cluster_owners,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_backfill_cells",
        fake_backfill,
    )
    monkeypatch.setattr(
        pipeline_module,
        "review_only_features_from_ambiguous_records",
        lambda records, *, start_index: ("ambiguous-feature",),
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        fake_owner_matrix,
    )
    monkeypatch.setattr(
        pipeline_module,
        "_write_outputs_atomic",
        lambda outputs, matrix, **kwargs: calls.setdefault("written_matrix", matrix),
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )

    assert calls["owners"] == (owner,)
    assert calls["backfill_features"] == (feature, "ambiguous-feature")
    assert calls["matrix_features"] == (feature, "ambiguous-feature")
    assert calls["ambiguous_by_sample"] == {}
    assert calls["rescued_cells"] == ("rescued",)
    assert calls["written_matrix"] is owner_matrix


def test_pipeline_applies_claim_registry_before_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    owner_matrix = _matrix(("Sample_A",))
    claimed_matrix = _matrix(("Sample_A",))
    calls = {}

    _patch_owner_pipeline_to_matrix(monkeypatch)
    monkeypatch.setattr(
        pipeline_module,
        "build_owner_alignment_matrix",
        lambda features, *, sample_order, **kwargs: owner_matrix,
    )

    def fake_claim_registry(matrix, config):
        calls["claim_matrix"] = matrix
        calls["claim_config"] = config
        return claimed_matrix

    monkeypatch.setattr(
        pipeline_module,
        "apply_ms1_peak_claim_registry",
        fake_claim_registry,
    )
    monkeypatch.setattr(
        pipeline_module,
        "_write_outputs_atomic",
        lambda outputs, matrix, **kwargs: calls.setdefault("written_matrix", matrix),
    )

    alignment_config = AlignmentConfig()
    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=alignment_config,
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )

    assert calls["claim_matrix"] is owner_matrix
    assert calls["claim_config"] is alignment_config
    assert calls["written_matrix"] is claimed_matrix


def test_pipeline_keeps_stale_output_pair_when_requested_write_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    review = output_dir / "alignment_review.tsv"
    matrix = output_dir / "alignment_matrix.tsv"
    review.write_text("old review", encoding="utf-8")
    matrix.write_text("old matrix", encoding="utf-8")

    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fail_matrix_writer(path, matrix, *, alignment_config=None):
        Path(path).write_text("partial matrix", encoding="utf-8")
        raise RuntimeError("matrix failed")

    monkeypatch.setattr(
        pipeline_module,
        "write_alignment_matrix_tsv",
        fail_matrix_writer,
    )

    with pytest.raises(RuntimeError, match="matrix failed"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=output_dir,
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=FakeRawOpener(),
        )

    assert review.read_text(encoding="utf-8") == "old review"
    assert matrix.read_text(encoding="utf-8") == "old matrix"
    assert not (output_dir / "alignment_review.tsv.tmp").exists()
    assert not (output_dir / "alignment_matrix.tsv.tmp").exists()


def test_pipeline_rolls_back_stale_output_pair_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    review = output_dir / "alignment_review.tsv"
    matrix = output_dir / "alignment_matrix.tsv"
    review.write_text("old review", encoding="utf-8")
    matrix.write_text("old matrix", encoding="utf-8")

    _patch_owner_pipeline_to_matrix(monkeypatch)
    original_replace = Path.replace

    def fail_second_replace(self: Path, target: Path):
        if self.name == "alignment_matrix.tsv.tmp":
            raise PermissionError("locked matrix")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)

    with pytest.raises(PermissionError, match="locked matrix"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=output_dir,
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=FakeRawOpener(),
        )

    assert review.read_text(encoding="utf-8") == "old review"
    assert matrix.read_text(encoding="utf-8") == "old matrix"


def test_run_alignment_production_level_writes_xlsx_and_html_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outputs = _run_minimal_alignment(
        tmp_path,
        monkeypatch,
        output_level="production",
    )

    names = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert names == ["alignment_results.xlsx", "review_report.html"]
    assert outputs.workbook == tmp_path / "out" / "alignment_results.xlsx"
    assert outputs.review_html == tmp_path / "out" / "review_report.html"
    assert outputs.matrix_tsv is None
    assert outputs.review_tsv is None


def test_run_alignment_debug_level_writes_machine_and_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outputs = _run_minimal_alignment(tmp_path, monkeypatch, output_level="debug")

    names = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert names == [
        "alignment_cells.tsv",
        "alignment_matrix.tsv",
        "alignment_matrix_status.tsv",
        "alignment_results.xlsx",
        "alignment_review.tsv",
        "ambiguous_ms1_owners.tsv",
        "event_to_ms1_owner.tsv",
        "owner_edge_evidence.tsv",
        "review_report.html",
    ]
    assert outputs.event_to_owner_tsv is not None
    assert outputs.ambiguous_owners_tsv is not None
    assert outputs.edge_evidence_tsv is not None


def test_run_alignment_passes_drift_lookup_to_owner_clustering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    drift_lookup = _DriftLookup()
    calls = {}
    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fake_cluster_owners(
        owners,
        *,
        config,
        drift_lookup=None,
        edge_evidence_sink=None,
    ):
        calls["drift_lookup"] = drift_lookup
        calls["edge_evidence_sink"] = edge_evidence_sink
        return ()

    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        fake_cluster_owners,
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        drift_lookup=drift_lookup,
    )

    assert calls["drift_lookup"] is drift_lookup
    assert calls["edge_evidence_sink"] == []


def test_run_alignment_validation_level_writes_owner_edge_evidence_tsv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fake_cluster_owners(
        owners,
        *,
        config,
        drift_lookup=None,
        edge_evidence_sink=None,
    ):
        edge_evidence_sink.append(_edge_evidence())
        return ()

    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        fake_cluster_owners,
    )

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        output_level="validation",
        raw_opener=FakeRawOpener(),
    )

    assert outputs.edge_evidence_tsv == tmp_path / "out" / "owner_edge_evidence.tsv"
    lines = outputs.edge_evidence_tsv.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("left_owner_id\tright_owner_id\t")
    assert lines[1].startswith("OWN-Sample_A-000001\tOWN-Sample_B-000001\t")


def test_run_alignment_owner_edge_evidence_replace_failure_rolls_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    workbook = output_dir / "alignment_results.xlsx"
    edge_evidence = output_dir / "owner_edge_evidence.tsv"
    workbook.write_text("old workbook", encoding="utf-8")
    edge_evidence.write_text("old edge evidence", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fake_cluster_owners(
        owners,
        *,
        config,
        drift_lookup=None,
        edge_evidence_sink=None,
    ):
        edge_evidence_sink.append(_edge_evidence())
        return ()

    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        fake_cluster_owners,
    )
    original_replace = Path.replace

    def fail_edge_evidence_replace(self: Path, target: Path):
        if self.name == "owner_edge_evidence.tsv.tmp":
            raise PermissionError("locked owner edge evidence")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_edge_evidence_replace)

    with pytest.raises(PermissionError, match="locked owner edge evidence"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=output_dir,
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            output_level="validation",
            raw_opener=FakeRawOpener(),
        )

    assert workbook.read_text(encoding="utf-8") == "old workbook"
    assert edge_evidence.read_text(encoding="utf-8") == "old edge evidence"
    assert not (output_dir / "owner_edge_evidence.tsv.tmp").exists()
    assert not (output_dir / "owner_edge_evidence.tsv.bak").exists()


def test_run_alignment_default_stays_machine_until_owner_validation_acceptance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _run_minimal_alignment(tmp_path, monkeypatch)

    names = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert names == [
        "alignment_matrix.tsv",
        "alignment_results.xlsx",
        "alignment_review.tsv",
        "review_report.html",
    ]


def test_run_alignment_rolls_back_artifact_set_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    workbook = output_dir / "alignment_results.xlsx"
    html = output_dir / "review_report.html"
    workbook.write_text("old workbook", encoding="utf-8")
    html.write_text("old html", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    original_replace = Path.replace

    def fail_html_replace(self: Path, target: Path):
        if self.name == "review_report.html.tmp":
            raise PermissionError("locked by browser")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_html_replace)

    with pytest.raises(PermissionError, match="locked by browser"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=output_dir,
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            output_level="production",
            raw_opener=FakeRawOpener(),
        )

    assert workbook.read_text(encoding="utf-8") == "old workbook"
    assert html.read_text(encoding="utf-8") == "old html"


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


def _run_minimal_alignment(
    tmp_path: Path,
    monkeypatch,
    *,
    output_level: str | None = None,
) -> pipeline_module.AlignmentRunOutputs:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    kwargs = {}
    if output_level is not None:
        kwargs["output_level"] = output_level
    return pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        **kwargs,
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


class _DriftLookup:
    source = "targeted_istd_trend"

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return {"Sample_A": 0.1}.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return {"Sample_A": 1}.get(sample_stem)


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


def _edge_evidence() -> OwnerEdgeEvidence:
    return OwnerEdgeEvidence(
        left_owner_id="OWN-Sample_A-000001",
        right_owner_id="OWN-Sample_B-000001",
        left_sample_stem="Sample_A",
        right_sample_stem="Sample_B",
        neutral_loss_tag="DNA_dR",
        left_precursor_mz=500.0,
        right_precursor_mz=500.1,
        left_rt_min=8.5,
        right_rt_min=8.6,
        decision="strong_edge",
        failure_reason="",
        rt_raw_delta_sec=6.0,
        rt_drift_corrected_delta_sec=1.0,
        drift_prior_source="targeted_istd_trend",
        injection_order_gap=1,
        owner_quality="clean",
        seed_support_level="strong",
        duplicate_context="none",
        score=100,
        reason="strong_edge: score=100",
    )


def _ok_alignment_peak(*args, **kwargs):
    peak = SimpleNamespace(
        rt=8.0,
        intensity=100.0,
        area=25.0,
        peak_start=7.9,
        peak_end=8.1,
    )
    return SimpleNamespace(status="OK", peak=peak)


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


def _cell(sample_stem: str, *, cluster_id: str) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status="rescued",
        area=100.0,
        apex_rt=8.5,
        height=50.0,
        peak_start_rt=8.4,
        peak_end_rt=8.6,
        rt_delta_sec=0.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
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


def _empty_ownership():
    from xic_extractor.alignment.ownership import OwnershipBuildResult

    return OwnershipBuildResult(assignments=(), ambiguous_records=(), owners=())


def test_pipeline_passes_alignment_config_to_production_writers(monkeypatch, tmp_path):
    from xic_extractor.alignment import pipeline as alignment_pipeline
    from xic_extractor.alignment.config import AlignmentConfig
    from xic_extractor.alignment.matrix import AlignmentMatrix

    seen = {"xlsx": None, "matrix_tsv": None, "review_tsv": None}
    matrix = AlignmentMatrix(clusters=(), cells=(), sample_order=())
    config = AlignmentConfig(max_rt_sec=77.0)
    outputs = alignment_pipeline.AlignmentRunOutputs(
        workbook=tmp_path / "alignment_results.xlsx",
        matrix_tsv=tmp_path / "alignment_matrix.tsv",
        review_tsv=tmp_path / "alignment_review.tsv",
    )

    def fake_xlsx(path, matrix_arg, *, metadata, alignment_config=None):
        seen["xlsx"] = alignment_config
        path.write_text("xlsx", encoding="utf-8")
        return path

    def fake_matrix_tsv(path, matrix_arg, *, alignment_config=None):
        seen["matrix_tsv"] = alignment_config
        path.write_text("matrix", encoding="utf-8")
        return path

    def fake_review_tsv(path, matrix_arg, *, alignment_config=None):
        seen["review_tsv"] = alignment_config
        path.write_text("review", encoding="utf-8")
        return path

    monkeypatch.setattr(alignment_pipeline, "write_alignment_results_xlsx", fake_xlsx)
    monkeypatch.setattr(
        alignment_pipeline,
        "write_alignment_matrix_tsv",
        fake_matrix_tsv,
    )
    monkeypatch.setattr(
        alignment_pipeline,
        "write_alignment_review_tsv",
        fake_review_tsv,
    )

    alignment_pipeline._write_outputs_atomic(
        outputs,
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
        ownership=_empty_ownership(),
        alignment_config=config,
    )

    assert seen == {"xlsx": config, "matrix_tsv": config, "review_tsv": config}
