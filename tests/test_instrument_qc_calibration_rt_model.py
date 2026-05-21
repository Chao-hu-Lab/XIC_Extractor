import pytest

from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    CalibrationEvidenceRow,
    CoverageStatus,
    ProductSupportStatus,
)
from xic_extractor.instrument_qc.calibration_rt_model import (
    build_rt_model_bundle,
)


def test_compound_aware_leave_one_anchor_out_uses_same_standard_trend() -> None:
    bundle = build_rt_model_bundle(
        bundle_id="bundle",
        evidence_rows=(
            _row("A-1", compound="A", order=1, reference_rt=10.0, delta=0.00),
            _row("A-2", compound="A", order=2, reference_rt=10.0, delta=0.05),
            _row("A-3", compound="A", order=3, reference_rt=10.0, delta=0.10),
            _row("B-1", compound="B", order=2, reference_rt=22.0, delta=1.20),
        ),
    )

    rows_by_id = {row.evidence_row_id: row for row in bundle.leave_one_anchor_out_rows}

    assert rows_by_id["A-2"].abs_prediction_error_min == pytest.approx(0.0)
    assert rows_by_id["A-2"].status == "PASS"


def test_matrix_prediction_exposes_irt_scope_and_coverage_label() -> None:
    bundle = build_rt_model_bundle(
        bundle_id="bundle",
        evidence_rows=(
            _row("low", compound="low", order=1, reference_rt=12.0, delta=0.05),
            _row("mid", compound="mid", order=10, reference_rt=15.0, delta=0.10),
            _row("high", compound="high", order=20, reference_rt=18.0, delta=0.15),
        ),
    )

    prediction = bundle.predict(feature_rt_min=15.0, injection_order=10)

    assert prediction.coverage_status == CoverageStatus.COVERED
    assert prediction.rt_alignment_support_status == "local_rt_supported"
    assert prediction.irt_anchor_scope == "inside_anchor_range"
    assert prediction.irt_position == pytest.approx(50.0)
    assert prediction.predicted_rt_delta_min == pytest.approx(0.10, abs=1e-3)


def test_prediction_blocks_without_docs_derived_injection_order() -> None:
    bundle = build_rt_model_bundle(
        bundle_id="bundle",
        evidence_rows=(
            _row("low", compound="low", order=1, reference_rt=5.0, delta=0.05),
            _row("mid", compound="mid", order=10, reference_rt=15.0, delta=0.10),
        ),
    )

    prediction = bundle.predict(feature_rt_min=15.0, injection_order=None)

    assert prediction.coverage_status == CoverageStatus.INCOMPLETE
    assert prediction.rt_alignment_support_status == (
        "incomplete_missing_injection_order"
    )
    assert prediction.predicted_rt_delta_min is None


def _row(
    evidence_id: str,
    *,
    compound: str,
    order: int,
    reference_rt: float,
    delta: float,
) -> CalibrationEvidenceRow:
    return CalibrationEvidenceRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle",
        evidence_row_id=evidence_id,
        source_artifact_id="instrument_qc_mixstds_trend.tsv",
        source_artifact_hash="hash",
        source_type="mixstds",
        matrix_context="clean",
        sample_name=f"{compound}_{order}",
        raw_stem=f"{compound}_{order}",
        source_raw_file=f"{compound}_{order}.raw",
        raw_path_kind="basename",
        injection_order=order,
        compound=compound,
        compound_group=compound,
        precursor_mz=100.0,
        observed_mz=None,
        mz_ppm_error=None,
        reference_rt_min=reference_rt,
        observed_rt_min=reference_rt + delta,
        rt_delta_min=delta,
        rt_region=f"rt_{int(reference_rt):02d}_{int(reference_rt) + 1:02d}",
        area=1000.0,
        height=None,
        log2_area_delta=None,
        log2_height_delta=None,
        peak_width_min=0.5,
        activation_method="unknown",
        product_support_status=ProductSupportStatus.NOT_APPLICABLE,
        neutral_loss_support_status=ProductSupportStatus.NOT_APPLICABLE,
        evidence_confidence="high",
        calibration_eligible=True,
        coverage_status=CoverageStatus.COVERED,
        exclusion_reason="",
    )
