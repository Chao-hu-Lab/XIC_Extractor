
from pathlib import Path
from types import SimpleNamespace

import xic_extractor.alignment.pipeline as pipeline_module
from tests.alignment_pipeline_helpers import FakeRawOpener
from tests.alignment_pipeline_helpers import matrix as _matrix
from tests.alignment_pipeline_helpers import (
    patch_owner_pipeline_to_matrix as _patch_owner_pipeline_to_matrix,
)
from tests.alignment_pipeline_helpers import peak_config as _peak_config
from tests.alignment_pipeline_helpers import write_batch as _write_batch
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.matrix import AlignmentMatrix


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
        emit_region_audit,
    ):
        calls["candidates"] = tuple(candidate.sample_stem for candidate in candidates)
        calls["owner_raw_sources"] = raw_sources
        calls["alignment_config"] = alignment_config
        calls["peak_config"] = peak_config
        calls["owner_raw_xic_batch_size"] = raw_xic_batch_size
        calls["owner_emit_region_audit"] = emit_region_audit
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
        emit_region_audit,
    ):
        calls["features"] = features
        calls["sample_order"] = sample_order
        calls["raw_sources"] = raw_sources
        calls["backfill_raw_xic_batch_size"] = raw_xic_batch_size
        calls["emit_region_audit"] = emit_region_audit
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
    assert calls["owner_emit_region_audit"] is False
    assert calls["backfill_raw_xic_batch_size"] == 1
    assert calls["emit_region_audit"] is False
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


class _DriftLookup:
    source = "targeted_istd_trend"

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return {"Sample_A": 0.1}.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return {"Sample_A": 1}.get(sample_stem)
