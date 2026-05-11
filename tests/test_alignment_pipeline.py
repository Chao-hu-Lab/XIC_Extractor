import csv
from pathlib import Path

import pytest

import xic_extractor.alignment.pipeline as pipeline_module
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_pipeline_loads_candidates_clusters_backfills_and_writes_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A", "Sample_B"))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_cluster(candidates, *, config):
        calls["candidates"] = tuple(candidate.sample_stem for candidate in candidates)
        calls["cluster_config"] = config
        return (_cluster(),)

    def fake_backfill(clusters, *, sample_order, raw_sources, alignment_config, peak_config):
        calls["clusters"] = clusters
        calls["sample_order"] = sample_order
        calls["raw_sources"] = raw_sources
        calls["alignment_config"] = alignment_config
        calls["peak_config"] = peak_config
        return _matrix(sample_order)

    monkeypatch.setattr(pipeline_module, "cluster_candidates", fake_cluster)
    monkeypatch.setattr(pipeline_module, "backfill_alignment_matrix", fake_backfill)

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
    assert calls["sample_order"] == ("Sample_A", "Sample_B")
    assert set(calls["raw_sources"]) == {"Sample_A", "Sample_B"}
    assert outputs.review_tsv == tmp_path / "out" / "alignment_review.tsv"
    assert outputs.matrix_tsv == tmp_path / "out" / "alignment_matrix.tsv"
    assert outputs.cells_tsv is None
    assert outputs.status_matrix_tsv is None
    assert outputs.review_tsv.exists()
    assert outputs.matrix_tsv.exists()
    assert not (tmp_path / "out" / "alignment_cells.tsv").exists()
    assert not (tmp_path / "out" / "alignment_matrix_status.tsv").exists()


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

    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (_cluster(),),
    )

    def fake_backfill(clusters, *, sample_order, raw_sources, **kwargs):
        captured_sources.update(raw_sources)
        return _matrix(sample_order)

    monkeypatch.setattr(pipeline_module, "backfill_alignment_matrix", fake_backfill)

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

    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (_cluster(),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "backfill_alignment_matrix",
        lambda clusters, *, sample_order, raw_sources, **kwargs: _matrix(sample_order),
    )

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

    def fail_matrix_writer(path, matrix):
        raise RuntimeError("writer failed")

    monkeypatch.setattr(pipeline_module, "write_alignment_matrix_tsv", fail_matrix_writer)
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


def test_pipeline_debug_flags_write_optional_outputs(tmp_path: Path, monkeypatch) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (_cluster(),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "backfill_alignment_matrix",
        lambda clusters, *, sample_order, raw_sources, **kwargs: _matrix(sample_order),
    )

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

    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (_cluster(),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "backfill_alignment_matrix",
        lambda clusters, *, sample_order, raw_sources, **kwargs: _matrix(sample_order),
    )

    def fail_matrix_writer(path, matrix):
        Path(path).write_text("partial matrix", encoding="utf-8")
        raise RuntimeError("matrix failed")

    monkeypatch.setattr(pipeline_module, "write_alignment_matrix_tsv", fail_matrix_writer)

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
        _write_csv(candidates_csv, DISCOVERY_CANDIDATE_COLUMNS, [_candidate_row(sample_stem)])
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


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
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
    }


def _cluster() -> AlignmentCluster:
    return AlignmentCluster(
        cluster_id="ALN000001",
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
