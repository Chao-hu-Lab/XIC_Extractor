from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.instrument_qc.calibration_product_loaders import (
    parse_optional_float,
    parse_optional_int,
    read_tsv_rows,
)
from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    CalibrationEvidenceRow,
    CalibrationEvidenceSummary,
    CoverageStatus,
    ProductSupportStatus,
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


@dataclass(frozen=True)
class CollectedCalibrationEvidence:
    rows: tuple[CalibrationEvidenceRow, ...]
    summary: CalibrationEvidenceSummary
    source_artifacts: dict[str, str]
    missing_artifacts: tuple[str, ...]


def collect_level0_evidence(
    *,
    instrument_qc_dir: Path,
    bundle_id: str,
) -> CollectedCalibrationEvidence:
    evidence_rows: list[CalibrationEvidenceRow] = []
    source_artifacts: dict[str, str] = {}
    missing_artifacts: list[str] = []

    evidence_rows.extend(
        append_trend_rows(
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
        append_trend_rows(
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
        append_hcd_rows(
            instrument_qc_dir=instrument_qc_dir,
            filename="instrument_qc_hcd_audit.tsv",
            bundle_id=bundle_id,
            source_artifacts=source_artifacts,
            missing_artifacts=missing_artifacts,
        )
    )

    rows = tuple(evidence_rows)
    summary = build_evidence_summary(
        bundle_id=bundle_id,
        rows=rows,
        missing_artifacts=tuple(missing_artifacts),
    )
    return CollectedCalibrationEvidence(
        rows=rows,
        summary=summary,
        source_artifacts=source_artifacts,
        missing_artifacts=tuple(missing_artifacts),
    )


def append_trend_rows(
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
    source_hash = file_hash(path)
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
                rt_region=rt_region(observed_rt or reference_rt),
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
                    CoverageStatus.COVERED
                    if detected
                    else CoverageStatus.NOT_ASSESSABLE
                ),
                exclusion_reason="" if detected else (row.get("reason") or ""),
            )
        )
    return tuple(output)


def append_hcd_rows(
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
    source_hash = file_hash(path)
    source_artifacts[filename] = source_hash
    output: list[CalibrationEvidenceRow] = []
    for index, row in enumerate(
        read_tsv_rows(path, required_columns=HCD_REQUIRED_COLUMNS),
        start=2,
    ):
        status = (row.get("hcd_status") or "").strip()
        product_status = product_status_from_hcd(status)
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
                rt_region=rt_region(
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
                    "high"
                    if product_status == ProductSupportStatus.SUPPORTED
                    else "review"
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


def build_evidence_summary(
    *,
    bundle_id: str,
    rows: tuple[CalibrationEvidenceRow, ...],
    missing_artifacts: tuple[str, ...],
) -> CalibrationEvidenceSummary:
    return CalibrationEvidenceSummary(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id=bundle_id,
        total_rows=len(rows),
        counts_by_source_type=counts(row.source_type for row in rows),
        counts_by_matrix_context=counts(row.matrix_context for row in rows),
        counts_by_coverage_status=counts(str(row.coverage_status) for row in rows),
        counts_by_product_support_status=counts(
            str(row.product_support_status) for row in rows
        ),
        counts_by_calibration_eligible=counts(
            "true" if row.calibration_eligible else "false" for row in rows
        ),
        missing_artifacts=tuple(missing_artifacts),
    )


def product_status_from_hcd(status: str) -> ProductSupportStatus:
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


def counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def rt_region(rt: float | None) -> str:
    if rt is None:
        return "rt_unknown"
    start = int(rt)
    return f"rt_{start:02d}_{start + 1:02d}"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
