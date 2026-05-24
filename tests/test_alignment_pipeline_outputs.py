from pathlib import Path
from types import SimpleNamespace

import xic_extractor.alignment.pipeline as pipeline_module
from tests.alignment_pipeline_helpers import FakeRawOpener
from tests.alignment_pipeline_helpers import matrix as _matrix
from tests.alignment_pipeline_helpers import owner_edge_evidence as _edge_evidence
from tests.alignment_pipeline_helpers import (
    patch_owner_pipeline_to_matrix as _patch_owner_pipeline_to_matrix,
)
from tests.alignment_pipeline_helpers import peak_config as _peak_config
from tests.alignment_pipeline_helpers import write_batch as _write_batch
from xic_extractor.alignment import AlignmentConfig


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
        emit_alignment_integration_audit=True,
        emit_alignment_backfill_seed_audit=True,
        emit_alignment_status_matrix=True,
        raw_opener=FakeRawOpener(),
    )

    assert outputs.cells_tsv == tmp_path / "out" / "alignment_cells.tsv"
    assert (
        outputs.integration_audit_tsv
        == tmp_path / "out" / "alignment_cell_integration_audit.tsv"
    )
    assert (
        outputs.backfill_seed_audit_tsv
        == tmp_path / "out" / "alignment_owner_backfill_seed_audit.tsv"
    )
    assert outputs.status_matrix_tsv == tmp_path / "out" / "alignment_matrix_status.tsv"
    assert outputs.cells_tsv.exists()
    assert outputs.integration_audit_tsv.exists()
    assert outputs.backfill_seed_audit_tsv.exists()
    assert outputs.status_matrix_tsv.exists()


def test_pipeline_enables_region_audit_only_when_alignment_cells_are_emitted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

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

    def fake_owner_backfill(features, **kwargs):
        calls["emit_region_audit"] = kwargs["emit_region_audit"]
        return ()

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
        emit_alignment_cells=True,
        raw_opener=FakeRawOpener(),
    )

    assert calls["emit_region_audit"] is True


def test_pipeline_enables_region_audit_when_integration_sidecar_is_emitted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

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

    def fake_owner_backfill(features, **kwargs):
        calls["emit_region_audit"] = kwargs["emit_region_audit"]
        return ()

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

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        emit_alignment_integration_audit=True,
        raw_opener=FakeRawOpener(),
    )

    assert outputs.cells_tsv is None
    assert outputs.integration_audit_tsv is not None
    assert calls["emit_region_audit"] is True


def test_pipeline_backfill_seed_sidecar_does_not_force_alignment_cells_or_region_audit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

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

    def fake_owner_backfill(features, **kwargs):
        calls["emit_region_audit"] = kwargs["emit_region_audit"]
        return ()

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

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        emit_alignment_backfill_seed_audit=True,
        raw_opener=FakeRawOpener(),
    )

    assert outputs.cells_tsv is None
    assert outputs.backfill_seed_audit_tsv is not None
    assert outputs.backfill_seed_audit_tsv.exists()
    assert calls["emit_region_audit"] is False


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


def test_run_alignment_output_level_does_not_emit_integration_audit_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outputs = _run_minimal_alignment(tmp_path, monkeypatch, output_level="validation")

    names = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert "alignment_cell_integration_audit.tsv" not in names
    assert "alignment_owner_backfill_seed_audit.tsv" not in names
    assert outputs.integration_audit_tsv is None
    assert outputs.backfill_seed_audit_tsv is None


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
