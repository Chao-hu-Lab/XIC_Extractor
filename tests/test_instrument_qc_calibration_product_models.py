from pathlib import Path

from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactInventoryItem,
    CalibrationBundleManifest,
    CalibrationEvidenceRow,
    CalibrationEvidenceSummary,
    CorrectionStatus,
    CoverageStatus,
    MatrixResponsePreviewRow,
    MatrixRTPreviewRow,
    ProductSupportStatus,
    ResponseTransferStatus,
)


def test_manifest_records_entrypoint_metadata() -> None:
    manifest = CalibrationBundleManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        run_id="run-001",
        product_maturity_level="level_0",
        overall_verdict="diagnostic_only",
        artifact_inventory=(
            ArtifactInventoryItem(
                artifact_id="evidence",
                path=Path("instrument_qc_calibration_evidence.tsv"),
                role="row_contract",
                required=True,
                schema_version=ARTIFACT_SCHEMA_VERSION,
                status="present",
            ),
        ),
        source_artifacts={},
        source_contracts={},
        generation_command="python tool.py",
        created_at_utc="2026-05-21T00:00:00Z",
        created_by="instrument_qc_matrix_calibration_preview.py",
        status_counts={"coverage_status": {"covered": 1}},
        first_human_file="",
        first_machine_file="instrument_qc_calibration_evidence.tsv",
    )

    assert manifest.product_maturity_level == "level_0"
    assert manifest.overall_verdict == "diagnostic_only"
    assert manifest.artifact_inventory[0].path == Path(
        "instrument_qc_calibration_evidence.tsv"
    )


def test_evidence_rows_use_explicit_status_taxonomy() -> None:
    row = CalibrationEvidenceRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        evidence_row_id="evidence-001",
        source_artifact_id="sdolek_trend",
        source_artifact_hash="abc",
        source_type="sdolek",
        matrix_context="clean",
        sample_name="SDOLEK_1",
        raw_stem="SDOLEK_1",
        source_raw_file="SDOLEK_1.raw",
        raw_path_kind="basename",
        injection_order=1,
        compound="SDO",
        compound_group="SDO",
        precursor_mz=311.0814,
        observed_mz=None,
        mz_ppm_error=None,
        reference_rt_min=6.26,
        observed_rt_min=6.27,
        rt_delta_min=0.01,
        rt_region="rt_06_07",
        area=1000.0,
        height=100.0,
        log2_area_delta=0.0,
        log2_height_delta=0.0,
        peak_width_min=0.83,
        activation_method="wHCD",
        product_support_status=ProductSupportStatus.SUPPORTED,
        neutral_loss_support_status=ProductSupportStatus.NOT_APPLICABLE,
        evidence_confidence="high",
        calibration_eligible=True,
        coverage_status=CoverageStatus.COVERED,
        exclusion_reason="",
    )

    assert row.matrix_context == "clean"
    assert row.product_support_status == "supported"
    assert row.neutral_loss_support_status == "not_applicable"


def test_evidence_summary_records_status_counts() -> None:
    summary = CalibrationEvidenceSummary(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        total_rows=2,
        counts_by_source_type={"sdolek": 1, "mixstds": 1},
        counts_by_matrix_context={"clean": 2},
        counts_by_coverage_status={"covered": 2},
        counts_by_product_support_status={"supported": 1, "not_triggered": 1},
        counts_by_calibration_eligible={"true": 1, "false": 1},
        missing_artifacts=("instrument_qc_hcd_audit.tsv",),
    )

    assert summary.counts_by_product_support_status["not_triggered"] == 1
    assert summary.missing_artifacts == ("instrument_qc_hcd_audit.tsv",)


def test_matrix_preview_rows_carry_stable_rejoin_keys() -> None:
    rt_row = MatrixRTPreviewRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        matrix_source="alignment_cells.tsv",
        matrix_source_hash="hash",
        matrix_schema_version="unknown",
        source_row_id="1",
        source_cell_key="FAM001|SampleA",
        feature_id="FAM001",
        matrix_column_name="SampleA",
        sample_name="SampleA",
        sample_stem="SampleA",
        raw_file_stem="SampleA",
        feature_mz=300.0,
        raw_feature_rt_min=12.0,
        injection_order=5,
        model_id="rt-clean-summary",
        predicted_rt_delta_min=0.05,
        rt_uncertainty_min=0.02,
        rt_if_standard_corrected_min=11.95,
        correction_status=CorrectionStatus.APPLIED_PREVIEW,
        correction_block_reason="",
        review_reason="Preview only.",
    )

    assert rt_row.source_cell_key == "FAM001|SampleA"
    assert rt_row.correction_status == "applied_preview"


def test_response_preview_blocks_missing_values_without_imputation() -> None:
    row = MatrixResponsePreviewRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        matrix_source="alignment_cells.tsv",
        matrix_source_hash="hash",
        matrix_schema_version="unknown",
        source_row_id="row-1",
        source_cell_key="FAM001|SampleA",
        feature_id="FAM001",
        matrix_column_name="SampleA",
        sample_name="SampleA",
        sample_stem="SampleA",
        raw_file_stem="SampleA",
        feature_mz=300.0,
        raw_feature_rt_min=12.0,
        injection_order=5,
        raw_area=None,
        raw_area_status="missing",
        raw_height=None,
        raw_height_status="missing",
        model_id="response-clean-summary",
        predicted_log2_response_delta=None,
        area_if_response_corrected=None,
        height_if_response_corrected=None,
        preview_area_status="blocked",
        preview_height_status="blocked",
        response_uncertainty_log2=None,
        transfer_status=ResponseTransferStatus.CLEAN_ONLY,
        correction_status=CorrectionStatus.BLOCKED_MISSING_VALUE,
        correction_block_reason="raw area is missing",
        review_reason="No imputation in response preview.",
    )

    assert row.area_if_response_corrected is None
    assert row.correction_status == "blocked_missing_value"


def test_status_literals_are_string_compatible() -> None:
    assert CoverageStatus.COVERED == "covered"
    assert ProductSupportStatus.NOT_TRIGGERED == "not_triggered"
    assert CorrectionStatus.APPLIED_PREVIEW == "applied_preview"
