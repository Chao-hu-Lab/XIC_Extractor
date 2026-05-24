import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

import xic_extractor.alignment.pipeline as pipeline_module
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.ownership_models import (
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.alignment.process_backend import (
    OwnerBackfillProcessOutput,
    OwnerBuildProcessOutput,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in(
    tmp_path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    calls = {}

    def fake_build_owners(candidates, **kwargs):
        candidate = tuple(candidates)[0]
        event = IdentityEvent(
            candidate_id=candidate.candidate_id,
            sample_stem=candidate.sample_stem,
            raw_file=str(candidate.raw_file),
            neutral_loss_tag=candidate.neutral_loss_tag,
            precursor_mz=candidate.precursor_mz,
            product_mz=candidate.product_mz,
            observed_neutral_loss_da=candidate.observed_neutral_loss_da,
            seed_rt=candidate.best_seed_rt,
            evidence_score=candidate.evidence_score,
            seed_event_count=candidate.seed_event_count,
        )
        owner = SampleLocalMS1Owner(
            owner_id="OWN-1",
            sample_stem=candidate.sample_stem,
            raw_file=str(candidate.raw_file),
            precursor_mz=candidate.precursor_mz,
            owner_apex_rt=float(candidate.ms1_apex_rt),
            owner_peak_start_rt=float(candidate.ms1_peak_rt_start),
            owner_peak_end_rt=float(candidate.ms1_peak_rt_end),
            owner_area=float(candidate.ms1_area),
            owner_height=float(candidate.ms1_height),
            primary_identity_event=event,
            supporting_events=(),
            identity_conflict=False,
            assignment_reason="primary_identity_event",
        )
        return OwnershipBuildResult(
            owners=(owner,),
            assignments=(
                OwnerAssignment(
                    candidate_id=candidate.candidate_id,
                    owner_id="OWN-1",
                    assignment_status="primary",
                    reason="primary_identity_event",
                ),
            ),
            ambiguous_records=(),
        )

    def fake_diagnostic(**kwargs):
        calls.update(kwargs)

        class Result:
            records = ()
            context = type(
                "Context",
                (),
                {"raw_xic_request_count": 0, "xic_point_count": 0},
            )()

        return Result()

    monkeypatch.setattr(pipeline_module, "build_sample_local_owners", fake_build_owners)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        fake_diagnostic,
    )

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        emit_identity_coherence_diagnostic=True,
        identity_coherence_output_dir=tmp_path / "identity",
    )

    assert calls["output_dir"] == tmp_path / "identity"
    assert calls["fragment_profile_id"] == "alignment-cid-neutral-loss-v0.4"
    assert outputs.identity_coherence_output_dir == tmp_path / "identity"


def test_run_alignment_passes_identity_coherence_worker_policy(
    tmp_path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

    def fake_build_owners(*args, **kwargs):
        return OwnerBuildProcessOutput(
            ownership=OwnershipBuildResult(
                owners=(),
                assignments=(),
                ambiguous_records=(),
            ),
            timing_stats=(),
        )

    def fake_backfill(*args, **kwargs):
        return OwnerBackfillProcessOutput(cells=(), timing_stats=())

    def fake_diagnostic(**kwargs):
        calls.update(kwargs)

        class Result:
            records = ()
            context = type(
                "Context",
                (),
                {"raw_xic_request_count": 0, "xic_point_count": 0},
            )()

        return Result()

    monkeypatch.setattr(pipeline_module, "run_owner_build_process", fake_build_owners)
    monkeypatch.setattr(pipeline_module, "run_owner_backfill_process", fake_backfill)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        fake_diagnostic,
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_workers=8,
        raw_xic_batch_size=64,
        emit_identity_coherence_diagnostic=True,
    )

    assert calls["raw_workers"] == 8
    assert calls["raw_xic_batch_size"] == 64


def test_identity_coherence_diagnostic_does_not_change_backfill_inputs(
    tmp_path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    captured_features = []

    _patch_owner_pipeline_to_matrix(monkeypatch)
    expected_features = ("sentinel-family",)
    sentinel_feature = SimpleNamespace(feature_family_id=expected_features[0])
    monkeypatch.setattr(
        pipeline_module,
        "cluster_sample_local_owners",
        lambda owners, *, config, drift_lookup=None, edge_evidence_sink=None: (
            sentinel_feature,
        ),
    )

    def fake_backfill(features, *, sample_order, raw_sources, **kwargs):
        captured_features.append(
            tuple(feature.feature_family_id for feature in features)
        )
        return ()

    monkeypatch.setattr(pipeline_module, "build_owner_backfill_cells", fake_backfill)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("diagnostic must not run when disabled")
        ),
    )

    disabled = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "disabled",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )
    disabled_features = captured_features[-1]
    assert disabled_features == expected_features
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        lambda **kwargs: type(
            "DiagnosticRun",
            (),
            {
                "records": (),
                "context": type(
                    "Context",
                    (),
                    {"raw_xic_request_count": 0, "xic_point_count": 0},
                )(),
            },
        )(),
    )
    enabled = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "enabled",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        emit_identity_coherence_diagnostic=True,
    )

    assert captured_features == [expected_features, expected_features]
    assert disabled.identity_coherence_output_dir is None
    assert enabled.identity_coherence_output_dir == (
        tmp_path / "enabled" / "identity_coherence"
    )


def test_run_alignment_propagates_identity_coherence_diagnostic_errors(
    tmp_path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    def failing_diagnostic(**kwargs):
        raise RuntimeError("identity diagnostic failed")

    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        failing_diagnostic,
    )

    with pytest.raises(RuntimeError, match="identity diagnostic failed"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path,
            output_dir=tmp_path / "out",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=FakeRawOpener(),
            emit_identity_coherence_diagnostic=True,
        )


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
