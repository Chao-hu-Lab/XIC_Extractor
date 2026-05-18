from pathlib import Path
from types import SimpleNamespace

import numpy as np

import xic_extractor.alignment.family_integration as family_integration_module
from xic_extractor.alignment.family_integration import integrate_feature_family_matrix
from xic_extractor.alignment.feature_family import build_ms1_feature_family
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.region_audit import PeakRegionAuditSummary


def test_family_integration_uses_family_center_not_event_cluster_area():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(
            _cluster("ALN000001", mz=242.114, rt=12.5927),
            _cluster("ALN000002", mz=242.115, rt=12.5916),
        ),
        evidence="cid_nl_only",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )
    alignment_config = _alignment_config()

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=alignment_config,
        peak_config=_peak_config(),
    )

    assert matrix.clusters[0].feature_family_id == "FAM000001"
    rt_padding_min = alignment_config.max_rt_sec / 60.0
    assert source.calls == [
        (
            family.family_center_mz,
            family.family_center_rt - rt_padding_min,
            family.family_center_rt + rt_padding_min,
            alignment_config.preferred_ppm,
        )
    ]
    assert matrix.cells[0].cluster_id == "FAM000001"
    assert matrix.cells[0].status == "detected"
    assert matrix.cells[0].area is not None
    assert matrix.cells[0].reason == (
        "family-centered MS1 integration from original detection"
    )


def test_family_integration_region_audit_is_opt_in(monkeypatch):
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001"),),
        evidence="cid_nl_only",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    def fail_region_audit(*args, **kwargs):
        raise AssertionError("region audit should be debug/validation opt-in")

    monkeypatch.setattr(
        family_integration_module,
        "build_peak_region_audit_summary",
        fail_region_audit,
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.cells[0].region_candidate_count is None
    assert matrix.cells[0].region_shadow_status == ""


def test_family_integration_emits_region_audit_when_requested():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001"),),
        evidence="cid_nl_only",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
        emit_region_audit=True,
    )

    assert matrix.cells[0].region_candidate_count is not None
    assert matrix.cells[0].region_shadow_status == "evaluated"


def test_family_integration_region_audit_receives_trace_group(monkeypatch):
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001"),),
        evidence="cid_nl_only",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )
    captured = {}

    def fake_region_audit(*args, **kwargs):
        captured["trace_group"] = kwargs["trace_group"]
        return PeakRegionAuditSummary(
            candidate_count=1,
            shadow_status="evaluated",
        )

    monkeypatch.setattr(
        family_integration_module,
        "build_peak_region_audit_summary",
        fake_region_audit,
    )

    integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
        emit_region_audit=True,
    )

    trace_group = captured["trace_group"]
    assert trace_group.analysis_mode == "untargeted"
    assert trace_group.context_id == "FAM000001"
    assert trace_group.neutral_loss_tag == "DNA_dR"


def test_family_integration_missing_raw_source_is_unchecked():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001"),),
        evidence="single_event_cluster",
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.cells[0].status == "unchecked"
    assert matrix.cells[0].reason == "missing raw source for family integration"


def test_non_anchor_family_integrates_detected_samples_only():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", has_anchor=False),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1", "s2"),
        raw_sources={"s1": source, "s2": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert [cell.status for cell in matrix.cells] == ["detected", "unchecked"]
    assert matrix.cells[1].reason == "family integration skipped for non-anchor family"
    assert len(source.calls) == 1


def test_family_integration_marks_original_member_peak_as_detected():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", has_anchor=True),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.cells[0].status == "detected"
    assert matrix.cells[0].reason == (
        "family-centered MS1 integration from original detection"
    )


def test_family_integration_marks_anchor_backfill_peak_as_rescued():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", has_anchor=True),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1", "s2"),
        raw_sources={"s1": source, "s2": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    cells = {cell.sample_stem: cell for cell in matrix.cells}
    assert cells["s1"].status == "detected"
    assert cells["s2"].status == "rescued"
    assert cells["s2"].reason == "family-centered MS1 backfill"


def test_family_integration_assigns_duplicate_ms1_peak_to_nearest_family():
    left = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", rt=12.0, has_anchor=False),),
        evidence="single_event_cluster",
    )
    right = build_ms1_feature_family(
        family_id="FAM000002",
        event_clusters=(_cluster("ALN000002", rt=12.6, has_anchor=False),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (left, right),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    cells = {cell.cluster_id: cell for cell in matrix.cells}
    assert cells["FAM000001"].status == "duplicate_assigned"
    assert cells["FAM000001"].area is None
    assert cells["FAM000001"].trace_quality == "assigned_duplicate"
    assert cells["FAM000001"].reason == (
        "MS1 peak assigned to selected feature family FAM000002"
    )
    assert cells["FAM000002"].status == "detected"
    assert cells["FAM000002"].area is not None


def test_family_integration_protects_anchor_family_when_duplicate_peak_conflicts():
    non_anchor = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", rt=12.58, has_anchor=False),),
        evidence="single_event_cluster",
    )
    anchor = build_ms1_feature_family(
        family_id="FAM000002",
        event_clusters=(_cluster("ALN000002", rt=12.0, has_anchor=True),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (non_anchor, anchor),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    cells = {cell.cluster_id: cell for cell in matrix.cells}
    assert cells["FAM000001"].status == "duplicate_assigned"
    assert cells["FAM000001"].area is None
    assert cells["FAM000001"].trace_quality == "assigned_duplicate"
    assert cells["FAM000001"].reason == (
        "MS1 peak assigned to selected feature family FAM000002"
    )
    assert cells["FAM000002"].status == "detected"


class FakeXICSource:
    def __init__(self, *, rt, intensity):
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


def _cluster(
    cluster_id: str,
    *,
    mz: float = 242.114,
    rt: float = 12.5927,
    has_anchor: bool = True,
) -> AlignmentCluster:
    member = SimpleNamespace(sample_stem="s1", candidate_id=f"{cluster_id}#s1")
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=126.066,
        cluster_observed_neutral_loss_da=116.048,
        has_anchor=has_anchor,
        members=(member,),
        anchor_members=(member,) if has_anchor else (),
    )


def _alignment_config():
    from xic_extractor.alignment.config import AlignmentConfig

    return AlignmentConfig(max_rt_sec=180.0, preferred_ppm=20.0)


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("out.csv"),
        diagnostics_csv=Path("diag.csv"),
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.01,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
        resolver_chrom_threshold=0.0,
        resolver_min_search_range_min=0.04,
        resolver_min_relative_height=0.0,
        resolver_min_absolute_height=0.0,
        resolver_min_ratio_top_edge=0.0,
        resolver_peak_duration_min=0.0,
        resolver_peak_duration_max=2.0,
        resolver_min_scans=1,
    )
