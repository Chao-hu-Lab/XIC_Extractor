from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from xic_extractor.instrument_qc.calibration_product_loaders import (
    parse_optional_float,
    parse_optional_int,
    read_tsv_rows,
)
from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactInventoryItem,
    CalibrationBundleManifest,
    CalibrationEvidenceRow,
    CalibrationEvidenceSummary,
    CorrectionStatus,
    CoverageStatus,
    MatrixRTPreviewRow,
    ProductSupportStatus,
)
from xic_extractor.instrument_qc.calibration_product_writers import (
    write_calibration_evidence_summary_json,
    write_calibration_evidence_tsv,
    write_calibration_manifest_json,
    write_matrix_rt_preview_tsv,
    write_preview_summary_json,
)

TREND_REQUIRED_COLUMNS = {
    "sample_name",
    "raw_path",
    "injection_order",
    "compound",
    "precursor_mz",
    "reference_rt_min",
    "rt_delta_to_reference_min",
    "apex_rt_min",
    "area",
    "base_width_min",
    "status",
    "reason",
}

HCD_REQUIRED_COLUMNS = {
    "sample_name",
    "raw_path",
    "injection_order",
    "compound",
    "precursor_mz",
    "ms1_apex_rt_min",
    "ms1_status",
    "instrument_method",
    "activation_method",
    "hcd_mapping_source",
    "hcd_product_group",
    "hcd_status",
    "trigger_scan_count",
    "expected_product_count",
    "matched_product_count",
    "best_product_ppm",
    "best_product_base_ratio",
    "review_reason",
}

ALIGNMENT_CELLS_REQUIRED_COLUMNS = {
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "source_raw_file",
    "family_center_mz",
    "family_center_rt",
}


@dataclass(frozen=True)
class CalibrationBundleResult:
    manifest_json: Path
    evidence_tsv: Path
    evidence_summary_json: Path
    rt_preview_tsv: Path | None = None
    rt_preview_summary_json: Path | None = None
    response_preview_tsv: Path | None = None
    response_preview_summary_json: Path | None = None


@dataclass(frozen=True)
class _CollectedEvidence:
    rows: tuple[CalibrationEvidenceRow, ...]
    summary: CalibrationEvidenceSummary
    source_artifacts: dict[str, str]
    missing_artifacts: tuple[str, ...]


def build_level0_calibration_bundle(
    *,
    instrument_qc_dir: Path,
    output_dir: Path,
    generation_command: str,
) -> CalibrationBundleResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_id = output_dir.name or "calibration_bundle"
    collected = _collect_level0_evidence(
        instrument_qc_dir=instrument_qc_dir,
        bundle_id=bundle_id,
    )
    evidence_tsv = output_dir / "instrument_qc_calibration_evidence.tsv"
    evidence_summary_json = output_dir / "instrument_qc_calibration_evidence_summary.json"
    manifest_json = output_dir / "instrument_qc_calibration_manifest.json"

    write_calibration_evidence_tsv(evidence_tsv, collected.rows)
    write_calibration_evidence_summary_json(evidence_summary_json, collected.summary)

    manifest = CalibrationBundleManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id=bundle_id,
        run_id=bundle_id,
        product_maturity_level="level_0",
        overall_verdict="diagnostic_only",
        artifact_inventory=_base_artifact_inventory(
            manifest_json=manifest_json,
            evidence_tsv=evidence_tsv,
            evidence_summary_json=evidence_summary_json,
        ),
        source_artifacts=collected.source_artifacts,
        source_contracts={
            "instrument_qc_sdolek_trend.tsv": "trend_v1",
            "instrument_qc_mixstds_trend.tsv": "trend_v1_optional",
            "instrument_qc_hcd_audit.tsv": "hcd_audit_v1_optional",
        },
        generation_command=generation_command,
        created_at_utc=datetime.now(UTC).replace(microsecond=0).isoformat(),
        created_by="instrument_qc_matrix_calibration_preview.py",
        status_counts={
            "source_type": collected.summary.counts_by_source_type,
            "coverage_status": collected.summary.counts_by_coverage_status,
            "product_support_status": collected.summary.counts_by_product_support_status,
            "calibration_eligible": collected.summary.counts_by_calibration_eligible,
        },
        first_human_file="",
        first_machine_file=evidence_tsv.name,
    )
    write_calibration_manifest_json(manifest_json, manifest)
    return CalibrationBundleResult(
        manifest_json=manifest_json,
        evidence_tsv=evidence_tsv,
        evidence_summary_json=evidence_summary_json,
    )


def build_level1_rt_calibration_preview(
    *,
    instrument_qc_dir: Path,
    matrix_input: Path,
    matrix_input_role: str,
    output_dir: Path,
    generation_command: str,
) -> CalibrationBundleResult:
    if matrix_input_role != "untargeted_cell_table":
        raise ValueError(f"unsupported matrix input role: {matrix_input_role}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_id = output_dir.name or "calibration_bundle"
    matrix_hash_before = _file_hash(matrix_input)
    collected = _collect_level0_evidence(
        instrument_qc_dir=instrument_qc_dir,
        bundle_id=bundle_id,
    )

    evidence_tsv = output_dir / "instrument_qc_calibration_evidence.tsv"
    evidence_summary_json = output_dir / "instrument_qc_calibration_evidence_summary.json"
    rt_preview_tsv = output_dir / "matrix_rt_calibration_preview.tsv"
    rt_preview_summary_json = output_dir / "matrix_rt_calibration_preview_summary.json"
    manifest_json = output_dir / "instrument_qc_calibration_manifest.json"

    rt_rows = _build_rt_preview_rows(
        bundle_id=bundle_id,
        matrix_input=matrix_input,
        matrix_hash=matrix_hash_before,
        evidence_rows=collected.rows,
    )
    rt_summary = _preview_summary(
        bundle_id=bundle_id,
        matrix_source=matrix_input.name,
        matrix_source_hash=matrix_hash_before,
        rows=rt_rows,
    )

    write_calibration_evidence_tsv(evidence_tsv, collected.rows)
    write_calibration_evidence_summary_json(evidence_summary_json, collected.summary)
    write_matrix_rt_preview_tsv(rt_preview_tsv, rt_rows)
    write_preview_summary_json(rt_preview_summary_json, rt_summary)

    matrix_hash_after = _file_hash(matrix_input)
    if matrix_hash_after != matrix_hash_before:
        raise ValueError(f"matrix input changed during preview generation: {matrix_input}")

    source_artifacts = {
        **collected.source_artifacts,
        matrix_input.name: matrix_hash_before,
    }
    manifest = CalibrationBundleManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id=bundle_id,
        run_id=bundle_id,
        product_maturity_level="level_1",
        overall_verdict="preview_ready",
        artifact_inventory=(
            *_base_artifact_inventory(
                manifest_json=manifest_json,
                evidence_tsv=evidence_tsv,
                evidence_summary_json=evidence_summary_json,
            ),
            ArtifactInventoryItem(
                artifact_id="rt_preview",
                path=rt_preview_tsv.name,
                role="matrix_preview",
                required=True,
                schema_version=ARTIFACT_SCHEMA_VERSION,
                status="present",
            ),
            ArtifactInventoryItem(
                artifact_id="rt_preview_summary",
                path=rt_preview_summary_json.name,
                role="summary",
                required=True,
                schema_version=ARTIFACT_SCHEMA_VERSION,
                status="present",
            ),
        ),
        source_artifacts=source_artifacts,
        source_contracts={
            "instrument_qc_sdolek_trend.tsv": "trend_v1",
            "instrument_qc_mixstds_trend.tsv": "trend_v1_optional",
            "instrument_qc_hcd_audit.tsv": "hcd_audit_v1_optional",
            matrix_input.name: matrix_input_role,
        },
        generation_command=generation_command,
        created_at_utc=datetime.now(UTC).replace(microsecond=0).isoformat(),
        created_by="instrument_qc_matrix_calibration_preview.py",
        status_counts={
            "source_type": collected.summary.counts_by_source_type,
            "coverage_status": collected.summary.counts_by_coverage_status,
            "product_support_status": collected.summary.counts_by_product_support_status,
            "calibration_eligible": collected.summary.counts_by_calibration_eligible,
            "rt_preview_status": rt_summary["counts_by_correction_status"],
        },
        first_human_file="",
        first_machine_file=rt_preview_tsv.name,
    )
    write_calibration_manifest_json(manifest_json, manifest)
    return CalibrationBundleResult(
        manifest_json=manifest_json,
        evidence_tsv=evidence_tsv,
        evidence_summary_json=evidence_summary_json,
        rt_preview_tsv=rt_preview_tsv,
        rt_preview_summary_json=rt_preview_summary_json,
    )


def _collect_level0_evidence(
    *,
    instrument_qc_dir: Path,
    bundle_id: str,
) -> _CollectedEvidence:
    evidence_rows: list[CalibrationEvidenceRow] = []
    source_artifacts: dict[str, str] = {}
    missing_artifacts: list[str] = []

    evidence_rows.extend(
        _append_trend_rows(
            instrument_qc_dir=instrument_qc_dir,
            filename="instrument_qc_sdolek_trend.tsv",
            source_type="sdolek",
            bundle_id=bundle_id,
            source_artifacts=source_artifacts,
            missing_artifacts=missing_artifacts,
            required=True,
        )
    )
    evidence_rows.extend(
        _append_trend_rows(
            instrument_qc_dir=instrument_qc_dir,
            filename="instrument_qc_mixstds_trend.tsv",
            source_type="mixstds",
            bundle_id=bundle_id,
            source_artifacts=source_artifacts,
            missing_artifacts=missing_artifacts,
            required=False,
        )
    )
    evidence_rows.extend(
        _append_hcd_rows(
            instrument_qc_dir=instrument_qc_dir,
            filename="instrument_qc_hcd_audit.tsv",
            bundle_id=bundle_id,
            source_artifacts=source_artifacts,
            missing_artifacts=missing_artifacts,
        )
    )

    rows = tuple(evidence_rows)
    summary = _build_summary(
        bundle_id=bundle_id,
        rows=rows,
        missing_artifacts=tuple(missing_artifacts),
    )
    return _CollectedEvidence(
        rows=rows,
        summary=summary,
        source_artifacts=source_artifacts,
        missing_artifacts=tuple(missing_artifacts),
    )


def _append_trend_rows(
    *,
    instrument_qc_dir: Path,
    filename: str,
    source_type: str,
    bundle_id: str,
    source_artifacts: dict[str, str],
    missing_artifacts: list[str],
    required: bool,
) -> tuple[CalibrationEvidenceRow, ...]:
    path = instrument_qc_dir / filename
    if not path.exists():
        if required:
            raise ValueError(f"missing required instrument QC artifact: {path}")
        missing_artifacts.append(filename)
        return ()
    source_hash = _file_hash(path)
    source_artifacts[filename] = source_hash
    output: list[CalibrationEvidenceRow] = []
    for index, row in enumerate(
        read_tsv_rows(path, required_columns=TREND_REQUIRED_COLUMNS),
        start=2,
    ):
        status = (row.get("status") or "").strip()
        detected = status == "detected"
        observed_rt = parse_optional_float(
            row,
            "apex_rt_min",
            path=path,
            row_number=index,
        )
        reference_rt = parse_optional_float(
            row,
            "reference_rt_min",
            path=path,
            row_number=index,
        )
        rt_delta = parse_optional_float(
            row,
            "rt_delta_to_reference_min",
            path=path,
            row_number=index,
        )
        if rt_delta is None and observed_rt is not None and reference_rt is not None:
            rt_delta = observed_rt - reference_rt
        compound = (row.get("compound") or "").strip()
        output.append(
            CalibrationEvidenceRow(
                schema_version=ARTIFACT_SCHEMA_VERSION,
                bundle_id=bundle_id,
                evidence_row_id=f"{source_type}-{index - 1:04d}",
                source_artifact_id=filename,
                source_artifact_hash=source_hash,
                source_type=source_type,
                matrix_context="clean",
                sample_name=(row.get("sample_name") or "").strip(),
                raw_stem=Path(row.get("raw_path") or row.get("sample_name") or "").stem,
                source_raw_file=Path(row.get("raw_path") or "").name,
                raw_path_kind="basename",
                injection_order=parse_optional_int(
                    row,
                    "injection_order",
                    path=path,
                    row_number=index,
                ),
                compound=compound,
                compound_group=compound,
                precursor_mz=parse_optional_float(
                    row,
                    "precursor_mz",
                    path=path,
                    row_number=index,
                ),
                observed_mz=None,
                mz_ppm_error=None,
                reference_rt_min=reference_rt,
                observed_rt_min=observed_rt,
                rt_delta_min=rt_delta,
                rt_region=_rt_region(observed_rt or reference_rt),
                area=parse_optional_float(row, "area", path=path, row_number=index),
                height=None,
                log2_area_delta=None,
                log2_height_delta=None,
                peak_width_min=parse_optional_float(
                    row,
                    "base_width_min",
                    path=path,
                    row_number=index,
                ),
                activation_method="unknown",
                product_support_status=ProductSupportStatus.NOT_APPLICABLE,
                neutral_loss_support_status=ProductSupportStatus.NOT_APPLICABLE,
                evidence_confidence=(row.get("trend_confidence") or "review").strip(),
                calibration_eligible=detected,
                coverage_status=(
                    CoverageStatus.COVERED if detected else CoverageStatus.NOT_ASSESSABLE
                ),
                exclusion_reason="" if detected else (row.get("reason") or ""),
            )
        )
    return tuple(output)


def _base_artifact_inventory(
    *,
    manifest_json: Path,
    evidence_tsv: Path,
    evidence_summary_json: Path,
) -> tuple[ArtifactInventoryItem, ...]:
    return (
        ArtifactInventoryItem(
            artifact_id="manifest",
            path=manifest_json.name,
            role="entrypoint",
            required=True,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            status="present",
        ),
        ArtifactInventoryItem(
            artifact_id="evidence",
            path=evidence_tsv.name,
            role="row_contract",
            required=True,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            status="present",
        ),
        ArtifactInventoryItem(
            artifact_id="evidence_summary",
            path=evidence_summary_json.name,
            role="summary",
            required=True,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            status="present",
        ),
    )


def _build_rt_preview_rows(
    *,
    bundle_id: str,
    matrix_input: Path,
    matrix_hash: str,
    evidence_rows: tuple[CalibrationEvidenceRow, ...],
) -> tuple[MatrixRTPreviewRow, ...]:
    predicted_delta, uncertainty, model_id = _rt_preview_model(evidence_rows)
    rows: list[MatrixRTPreviewRow] = []
    for row_number, row in enumerate(
        read_tsv_rows(matrix_input, required_columns=ALIGNMENT_CELLS_REQUIRED_COLUMNS),
        start=1,
    ):
        tsv_row_number = row_number + 1
        raw_rt = parse_optional_float(
            row,
            "apex_rt",
            path=matrix_input,
            row_number=tsv_row_number,
        )
        family_center_rt = parse_optional_float(
            row,
            "family_center_rt",
            path=matrix_input,
            row_number=tsv_row_number,
        )
        feature_id = (row.get("feature_family_id") or "").strip()
        sample_stem = (row.get("sample_stem") or "").strip()
        status = (row.get("status") or "").strip()
        correction_status = CorrectionStatus.APPLIED_PREVIEW
        corrected_rt = None
        block_reason = ""
        review_reason = "RT preview subtracts clean-standard median RT delta."
        if predicted_delta is None:
            correction_status = CorrectionStatus.BLOCKED_NOT_COVERED
            block_reason = "no eligible standard RT evidence"
            review_reason = "No eligible clean-standard RT evidence is available."
        elif raw_rt is None:
            correction_status = CorrectionStatus.BLOCKED_MISSING_VALUE
            block_reason = "raw feature RT is missing"
            review_reason = "No imputation in RT preview."
        elif status not in {"detected", "rescued"}:
            correction_status = CorrectionStatus.NOT_APPLICABLE
            block_reason = f"cell status is {status or 'blank'}"
            review_reason = "RT preview is only informative for measured cells."
        else:
            corrected_rt = raw_rt - predicted_delta
        rows.append(
            MatrixRTPreviewRow(
                schema_version=ARTIFACT_SCHEMA_VERSION,
                bundle_id=bundle_id,
                matrix_source=matrix_input.name,
                matrix_source_hash=matrix_hash,
                matrix_schema_version="alignment_cells.tsv",
                source_row_id=str(tsv_row_number),
                source_cell_key=f"{feature_id}|{sample_stem}",
                feature_id=feature_id,
                matrix_column_name=sample_stem,
                sample_name=sample_stem,
                sample_stem=sample_stem,
                raw_file_stem=_raw_file_stem(row.get("source_raw_file"), sample_stem),
                feature_mz=parse_optional_float(
                    row,
                    "family_center_mz",
                    path=matrix_input,
                    row_number=tsv_row_number,
                ),
                raw_feature_rt_min=raw_rt or family_center_rt,
                injection_order=None,
                model_id=model_id,
                predicted_rt_delta_min=predicted_delta,
                rt_uncertainty_min=uncertainty,
                rt_if_standard_corrected_min=corrected_rt,
                correction_status=correction_status,
                correction_block_reason=block_reason,
                review_reason=review_reason,
            )
        )
    return tuple(rows)


def _rt_preview_model(
    evidence_rows: tuple[CalibrationEvidenceRow, ...],
) -> tuple[float | None, float | None, str]:
    deltas = [
        row.rt_delta_min
        for row in evidence_rows
        if row.calibration_eligible
        and row.matrix_context == "clean"
        and row.rt_delta_min is not None
    ]
    if not deltas:
        return None, None, "clean-standard-median-unavailable"
    prediction = median(deltas)
    uncertainty = median(abs(delta - prediction) for delta in deltas)
    return prediction, uncertainty, "clean-standard-median-rt"


def _preview_summary(
    *,
    bundle_id: str,
    matrix_source: str,
    matrix_source_hash: str,
    rows: tuple[MatrixRTPreviewRow, ...],
) -> dict[str, object]:
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "matrix_source": matrix_source,
        "matrix_source_hash": matrix_source_hash,
        "total_rows": len(rows),
        "counts_by_correction_status": _counts(
            str(row.correction_status) for row in rows
        ),
    }


def _raw_file_stem(raw_file: str | None, sample_stem: str) -> str:
    value = (raw_file or "").strip()
    if not value:
        return sample_stem
    return Path(value).stem or sample_stem


def _append_hcd_rows(
    *,
    instrument_qc_dir: Path,
    filename: str,
    bundle_id: str,
    source_artifacts: dict[str, str],
    missing_artifacts: list[str],
) -> tuple[CalibrationEvidenceRow, ...]:
    path = instrument_qc_dir / filename
    if not path.exists():
        missing_artifacts.append(filename)
        return ()
    source_hash = _file_hash(path)
    source_artifacts[filename] = source_hash
    output: list[CalibrationEvidenceRow] = []
    for index, row in enumerate(
        read_tsv_rows(path, required_columns=HCD_REQUIRED_COLUMNS),
        start=2,
    ):
        status = (row.get("hcd_status") or "").strip()
        product_status = _product_status_from_hcd(status)
        ms1_status = (row.get("ms1_status") or "").strip()
        output.append(
            CalibrationEvidenceRow(
                schema_version=ARTIFACT_SCHEMA_VERSION,
                bundle_id=bundle_id,
                evidence_row_id=f"hcd-{index - 1:04d}",
                source_artifact_id=filename,
                source_artifact_hash=source_hash,
                source_type="hcd_audit",
                matrix_context="clean",
                sample_name=(row.get("sample_name") or "").strip(),
                raw_stem=Path(row.get("raw_path") or row.get("sample_name") or "").stem,
                source_raw_file=Path(row.get("raw_path") or "").name,
                raw_path_kind="basename",
                injection_order=parse_optional_int(
                    row,
                    "injection_order",
                    path=path,
                    row_number=index,
                ),
                compound=(row.get("compound") or "").strip(),
                compound_group=(row.get("hcd_product_group") or "").strip(),
                precursor_mz=parse_optional_float(
                    row,
                    "precursor_mz",
                    path=path,
                    row_number=index,
                ),
                observed_mz=None,
                mz_ppm_error=parse_optional_float(
                    row,
                    "best_product_ppm",
                    path=path,
                    row_number=index,
                ),
                reference_rt_min=None,
                observed_rt_min=parse_optional_float(
                    row,
                    "ms1_apex_rt_min",
                    path=path,
                    row_number=index,
                ),
                rt_delta_min=None,
                rt_region=_rt_region(
                    parse_optional_float(
                        row,
                        "ms1_apex_rt_min",
                        path=path,
                        row_number=index,
                    )
                ),
                area=None,
                height=None,
                log2_area_delta=None,
                log2_height_delta=None,
                peak_width_min=None,
                activation_method=(row.get("activation_method") or "unknown").strip(),
                product_support_status=product_status,
                neutral_loss_support_status=ProductSupportStatus.NOT_APPLICABLE,
                evidence_confidence=(
                    "high" if product_status == ProductSupportStatus.SUPPORTED else "review"
                ),
                calibration_eligible=(
                    ms1_status == "detected"
                    and product_status == ProductSupportStatus.SUPPORTED
                ),
                coverage_status=(
                    CoverageStatus.COVERED
                    if product_status == ProductSupportStatus.SUPPORTED
                    else CoverageStatus.NOT_ASSESSABLE
                ),
                exclusion_reason=(row.get("review_reason") or ""),
            )
        )
    return tuple(output)


def _build_summary(
    *,
    bundle_id: str,
    rows: tuple[CalibrationEvidenceRow, ...],
    missing_artifacts: tuple[str, ...],
) -> CalibrationEvidenceSummary:
    return CalibrationEvidenceSummary(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id=bundle_id,
        total_rows=len(rows),
        counts_by_source_type=_counts(row.source_type for row in rows),
        counts_by_matrix_context=_counts(row.matrix_context for row in rows),
        counts_by_coverage_status=_counts(str(row.coverage_status) for row in rows),
        counts_by_product_support_status=_counts(
            str(row.product_support_status) for row in rows
        ),
        counts_by_calibration_eligible=_counts(
            "true" if row.calibration_eligible else "false" for row in rows
        ),
        missing_artifacts=tuple(missing_artifacts),
    )


def _product_status_from_hcd(status: str) -> ProductSupportStatus:
    if status == "hcd_supported":
        return ProductSupportStatus.SUPPORTED
    if status == "hcd_partial":
        return ProductSupportStatus.PARTIAL
    if status == "no_ms2_trigger":
        return ProductSupportStatus.NOT_TRIGGERED
    if status == "no_product_match":
        return ProductSupportStatus.PRODUCT_MISSING
    if status == "hcd_group_unmapped":
        return ProductSupportStatus.UNMAPPED
    if status == "ms2_parse_error":
        return ProductSupportStatus.PARSE_ERROR
    return ProductSupportStatus.NOT_APPLICABLE


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _rt_region(rt: float | None) -> str:
    if rt is None:
        return "rt_unknown"
    start = int(rt)
    return f"rt_{start:02d}_{start + 1:02d}"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
