from pathlib import Path

import pytest

import xic_extractor.alignment.validation_pipeline as pipeline_module
from xic_extractor.alignment.legacy_io import LoadedFeature, LoadedMatrix
from xic_extractor.alignment.validation_compare import FeatureMatch, SummaryMetric


def test_validation_pipeline_loads_xic_once_and_accepts_all_legacy_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {"xic": 0, "legacy": []}
    xic = _matrix("xic_alignment", "ALN000001")
    legacy = _matrix("fh_alignment", "LEGACY001")

    def fake_load_xic(review: Path, matrix: Path):
        calls["xic"] = int(calls["xic"]) + 1
        return xic

    def fake_legacy_loader(source: str):
        def load(path: Path):
            calls["legacy"].append((source, path))  # type: ignore[union-attr]
            return _matrix(source, f"{source}:000001")

        return load

    monkeypatch.setattr(pipeline_module, "load_xic_alignment", fake_load_xic)
    monkeypatch.setattr(
        pipeline_module,
        "load_fh_alignment_tsv",
        fake_legacy_loader("fh_alignment"),
    )
    monkeypatch.setattr(
        pipeline_module,
        "load_metabcombiner_tsv",
        lambda path: (
            fake_legacy_loader("metabcombiner_fh_block")(path),
            fake_legacy_loader("metabcombiner_mzmine_block")(path),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "load_combine_fix_xlsx",
        fake_legacy_loader("combine_fix"),
    )
    monkeypatch.setattr(
        pipeline_module,
        "match_legacy_source",
        lambda xic_matrix, legacy_matrix, **kwargs: (_match(legacy_matrix.source),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "summarize_legacy_source",
        lambda xic_matrix, legacy_matrix, matches, **kwargs: (
            _metric(legacy_matrix.source, "matched_feature_count", 1),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "summarize_global",
        lambda metrics: (_metric("global", "replacement_readiness", "review"),),
    )

    outputs = pipeline_module.run_alignment_validation(
        alignment_review=tmp_path / "alignment_review.tsv",
        alignment_matrix=tmp_path / "alignment_matrix.tsv",
        output_dir=tmp_path / "out",
        legacy_fh_tsv=tmp_path / "fh.tsv",
        legacy_metabcombiner_tsv=tmp_path / "metab.tsv",
        legacy_combine_fix_xlsx=tmp_path / "fix.xlsx",
    )

    assert calls["xic"] == 1
    assert len(calls["legacy"]) == 4
    assert outputs.summary_tsv == tmp_path / "out" / "alignment_validation_summary.tsv"
    assert outputs.matches_tsv == tmp_path / "out" / "alignment_legacy_matches.tsv"
    assert outputs.summary_tsv.exists()
    assert outputs.matches_tsv.exists()
    assert not (tmp_path / "out" / "alignment_cells.tsv").exists()
    assert legacy.source == "fh_alignment"


def test_validation_pipeline_rejects_zero_legacy_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one legacy source"):
        pipeline_module.run_alignment_validation(
            alignment_review=tmp_path / "alignment_review.tsv",
            alignment_matrix=tmp_path / "alignment_matrix.tsv",
            output_dir=tmp_path / "out",
        )


def test_validation_pipeline_passes_scope_and_thresholds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    xic = _matrix("xic_alignment", "ALN000001")
    legacy = _matrix("fh_alignment", "LEGACY001")

    monkeypatch.setattr(pipeline_module, "load_xic_alignment", lambda *args: xic)
    monkeypatch.setattr(pipeline_module, "load_fh_alignment_tsv", lambda path: legacy)

    def fake_match(xic_matrix, legacy_matrix, **kwargs):
        captured["match_kwargs"] = kwargs
        return (_match(legacy_matrix.source),)

    def fake_summary(xic_matrix, legacy_matrix, matches, **kwargs):
        captured["summary_kwargs"] = kwargs
        return (_metric(legacy_matrix.source, "matched_feature_count", 1),)

    monkeypatch.setattr(pipeline_module, "match_legacy_source", fake_match)
    monkeypatch.setattr(pipeline_module, "summarize_legacy_source", fake_summary)
    monkeypatch.setattr(pipeline_module, "summarize_global", lambda metrics: ())

    pipeline_module.run_alignment_validation(
        alignment_review=tmp_path / "alignment_review.tsv",
        alignment_matrix=tmp_path / "alignment_matrix.tsv",
        output_dir=tmp_path / "out",
        legacy_fh_tsv=tmp_path / "fh.tsv",
        match_ppm=10.0,
        match_rt_sec=30.0,
        sample_scope="legacy",
        match_distance_warn_median=0.25,
        match_distance_warn_p90=0.75,
    )

    assert captured["match_kwargs"] == {
        "match_ppm": 10.0,
        "match_rt_sec": 30.0,
        "sample_scope": "legacy",
    }
    assert captured["summary_kwargs"] == {
        "sample_scope": "legacy",
        "match_ppm": 10.0,
        "match_rt_sec": 30.0,
        "match_distance_warn_median": 0.25,
        "match_distance_warn_p90": 0.75,
    }


def test_validation_pipeline_writer_failure_keeps_stale_output_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    summary = output_dir / "alignment_validation_summary.tsv"
    matches = output_dir / "alignment_legacy_matches.tsv"
    summary.write_text("old summary", encoding="utf-8")
    matches.write_text("old matches", encoding="utf-8")
    xic = _matrix("xic_alignment", "ALN000001")
    legacy = _matrix("fh_alignment", "LEGACY001")

    monkeypatch.setattr(pipeline_module, "load_xic_alignment", lambda *args: xic)
    monkeypatch.setattr(pipeline_module, "load_fh_alignment_tsv", lambda path: legacy)
    monkeypatch.setattr(
        pipeline_module,
        "match_legacy_source",
        lambda *args, **kwargs: (_match("fh_alignment"),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "summarize_legacy_source",
        lambda *args, **kwargs: (_metric("fh_alignment", "matched_feature_count", 1),),
    )
    monkeypatch.setattr(pipeline_module, "summarize_global", lambda metrics: ())

    def fail_matches_writer(path, rows):
        Path(path).write_text("partial", encoding="utf-8")
        raise RuntimeError("matches failed")

    monkeypatch.setattr(
        pipeline_module,
        "write_legacy_matches_tsv",
        fail_matches_writer,
    )

    with pytest.raises(RuntimeError, match="matches failed"):
        pipeline_module.run_alignment_validation(
            alignment_review=tmp_path / "alignment_review.tsv",
            alignment_matrix=tmp_path / "alignment_matrix.tsv",
            output_dir=output_dir,
            legacy_fh_tsv=tmp_path / "fh.tsv",
        )

    assert summary.read_text(encoding="utf-8") == "old summary"
    assert matches.read_text(encoding="utf-8") == "old matches"


def test_validation_pipeline_does_not_import_raw_reader() -> None:
    source = Path("xic_extractor/alignment/validation_pipeline.py").read_text(
        encoding="utf-8"
    )

    assert "raw_reader" not in source
    assert "open_raw" not in source


def _matrix(source: str, feature_id: str) -> LoadedMatrix:
    return LoadedMatrix(
        source=source,
        sample_order=("S1",),
        features=(
            LoadedFeature(
                feature_id=feature_id,
                mz=100.0,
                rt_min=10.0,
                sample_areas={"S1": 1.0},
                metadata={},
            ),
        ),
    )


def _match(source: str) -> FeatureMatch:
    return FeatureMatch(
        source=source,
        xic_cluster_id="ALN000001",
        legacy_feature_id="LEGACY001",
        xic_mz=100.0,
        legacy_mz=100.0,
        mz_delta_ppm=0.0,
        xic_rt=10.0,
        legacy_rt=10.0,
        rt_delta_sec=0.0,
        distance_score=0.0,
        shared_sample_count=1,
        xic_present_count=1,
        legacy_present_count=1,
        both_present_count=1,
        xic_only_count=0,
        legacy_only_count=0,
        both_missing_count=0,
        present_jaccard=1.0,
        log_area_pearson=None,
        status="OK",
        note="",
    )


def _metric(source: str, metric: str, value) -> SummaryMetric:
    return SummaryMetric(
        source=source,
        metric=metric,
        value=value,
        threshold="",
        status="OK",
        note="",
    )
