from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.bundle import (
    read_tsv_rows,
    tsv_digest,
)
from xic_extractor.alignment.identity_coherence_validation.controls_summary import (
    control_method_rows,
    controls_manifest_row,
)
from xic_extractor.alignment.identity_coherence_validation.models import (
    DiagnosticBundle,
    ValidationResult,
    ValidationRow,
)


def compare_identity_coherence_bundles(
    serial: DiagnosticBundle,
    process: DiagnosticBundle,
    *,
    controls_manifest: Path | None = None,
) -> ValidationResult:
    controls_parity = _compare_tsv(
        "controls_tsv_parity_only",
        serial.controls_tsv,
        process.controls_tsv,
        success_details=(
            "controls file parity only; method controls summarized separately"
        ),
    )
    rows = [
        _compare_tsv("requests_tsv_exact", serial.requests_tsv, process.requests_tsv),
        _compare_tsv(
            "decisions_tsv_exact",
            serial.decisions_tsv,
            process.decisions_tsv,
        ),
        _compare_tsv(
            "cell_evidence_tsv_exact",
            serial.cell_evidence_tsv,
            process.cell_evidence_tsv,
        ),
        controls_parity,
        controls_manifest_row(controls_manifest),
        *control_method_rows(
            serial.controls_tsv,
            process.controls_tsv,
            controls_manifest,
            controls_parity_pass=controls_parity.status == "pass",
        ),
        _compare_summary_presence(serial.summary_md, process.summary_md),
    ]
    return ValidationResult(rows=tuple(rows))


def _compare_tsv(
    check_name: str,
    serial_path: Path,
    process_path: Path,
    *,
    success_details: str = "exact header and row-order match",
) -> ValidationRow:
    serial_rows = read_tsv_rows(serial_path)
    process_rows = read_tsv_rows(process_path)
    if serial_rows == process_rows:
        return ValidationRow(
            check_name=check_name,
            status="pass",
            serial_value=str(len(serial_rows.rows)),
            process_value=str(len(process_rows.rows)),
            details=success_details,
        )
    return ValidationRow(
        check_name=check_name,
        status="fail",
        serial_value=tsv_digest(serial_rows),
        process_value=tsv_digest(process_rows),
        details="TSV differs; row order is part of the frozen contract",
    )


def _compare_summary_presence(serial_path: Path, process_path: Path) -> ValidationRow:
    serial_exists = serial_path.is_file()
    process_exists = process_path.is_file()
    return ValidationRow(
        check_name="summary_md_presence",
        status="pass" if serial_exists and process_exists else "fail",
        serial_value=str(serial_exists).lower(),
        process_value=str(process_exists).lower(),
        details="summary markdown is reviewed manually; TSVs are exact-compared",
    )
