import csv
import json
from pathlib import Path

from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactInventoryItem,
    CalibrationBundleManifest,
    CalibrationEvidenceRow,
    CalibrationEvidenceSummary,
    CoverageStatus,
    ProductSupportStatus,
)
from xic_extractor.instrument_qc.calibration_product_writers import (
    CALIBRATION_EVIDENCE_COLUMNS,
    write_calibration_evidence_summary_json,
    write_calibration_evidence_tsv,
    write_calibration_manifest_json,
)


def _evidence_row() -> CalibrationEvidenceRow:
    return CalibrationEvidenceRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        evidence_row_id="evidence-001",
        source_artifact_id="instrument_qc_sdolek_trend.tsv",
        source_artifact_hash="hash",
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
        height=None,
        log2_area_delta=None,
        log2_height_delta=None,
        peak_width_min=0.83,
        activation_method="wHCD",
        product_support_status=ProductSupportStatus.SUPPORTED,
        neutral_loss_support_status=ProductSupportStatus.NOT_APPLICABLE,
        evidence_confidence="high",
        calibration_eligible=True,
        coverage_status=CoverageStatus.COVERED,
        exclusion_reason="",
    )


def test_write_calibration_manifest_json_round_trips_paths(tmp_path: Path) -> None:
    path = tmp_path / "instrument_qc_calibration_manifest.json"
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
        source_artifacts={"instrument_qc_sdolek_trend.tsv": "abc"},
        source_contracts={"instrument_qc": "sdolek_trend_v1"},
        generation_command="cmd",
        created_at_utc="2026-05-21T00:00:00Z",
        created_by="tool",
        status_counts={"evidence_rows": {"total": 1}},
        first_human_file="",
        first_machine_file="instrument_qc_calibration_evidence.tsv",
    )

    write_calibration_manifest_json(path, manifest)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["artifact_inventory"][0]["path"] == (
        "instrument_qc_calibration_evidence.tsv"
    )
    assert payload["overall_verdict"] == "diagnostic_only"


def test_write_calibration_evidence_tsv_uses_stable_columns(tmp_path: Path) -> None:
    path = tmp_path / "instrument_qc_calibration_evidence.tsv"
    write_calibration_evidence_tsv(path, [_evidence_row()])

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)

    assert reader.fieldnames == CALIBRATION_EVIDENCE_COLUMNS
    assert rows[0]["product_support_status"] == "supported"
    assert rows[0]["calibration_eligible"] == "true"


def test_write_calibration_evidence_summary_json(tmp_path: Path) -> None:
    path = tmp_path / "instrument_qc_calibration_evidence_summary.json"
    summary = CalibrationEvidenceSummary(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id="bundle-001",
        total_rows=1,
        counts_by_source_type={"sdolek": 1},
        counts_by_matrix_context={"clean": 1},
        counts_by_coverage_status={"covered": 1},
        counts_by_product_support_status={"supported": 1},
        counts_by_calibration_eligible={"true": 1},
        missing_artifacts=(),
    )

    write_calibration_evidence_summary_json(path, summary)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["total_rows"] == 1
    assert payload["counts_by_source_type"] == {"sdolek": 1}
