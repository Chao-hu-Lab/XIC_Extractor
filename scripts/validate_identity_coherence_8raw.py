from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


IDENTITY_COHERENCE_FILES = {
    "requests_tsv": "untargeted_identity_coherence_requests.tsv",
    "decisions_tsv": "untargeted_identity_coherence_decisions.tsv",
    "cell_evidence_tsv": "untargeted_identity_coherence_cell_evidence.tsv",
    "controls_tsv": "untargeted_identity_coherence_controls.tsv",
    "summary_md": "untargeted_identity_coherence_summary.md",
}

VALIDATION_SUMMARY_COLUMNS = (
    "check_name",
    "status",
    "serial_value",
    "process_value",
    "details",
)


@dataclass(frozen=True)
class DiagnosticBundle:
    requests_tsv: Path
    decisions_tsv: Path
    cell_evidence_tsv: Path
    controls_tsv: Path
    summary_md: Path


@dataclass(frozen=True)
class TsvRows:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ValidationRow:
    check_name: str
    status: str
    serial_value: str
    process_value: str
    details: str


@dataclass(frozen=True)
class RunMetadata:
    mode: str
    command_line: str
    output_dir: Path
    returncode: int


@dataclass(frozen=True)
class ValidationResult:
    rows: tuple[ValidationRow, ...]
    run_metadata: tuple[RunMetadata, ...] = ()

    @property
    def failed_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "fail")


def bundle_from_output_dir(output_dir: Path) -> DiagnosticBundle:
    identity_dir = output_dir / "identity_coherence"
    return DiagnosticBundle(
        requests_tsv=identity_dir / IDENTITY_COHERENCE_FILES["requests_tsv"],
        decisions_tsv=identity_dir / IDENTITY_COHERENCE_FILES["decisions_tsv"],
        cell_evidence_tsv=identity_dir
        / IDENTITY_COHERENCE_FILES["cell_evidence_tsv"],
        controls_tsv=identity_dir / IDENTITY_COHERENCE_FILES["controls_tsv"],
        summary_md=identity_dir / IDENTITY_COHERENCE_FILES["summary_md"],
    )


def read_tsv_rows(path: Path) -> TsvRows:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, dialect="excel-tab")
        rows = tuple(tuple(row) for row in reader)
    if not rows:
        raise ValueError(f"{path}: empty TSV")
    return TsvRows(header=rows[0], rows=rows[1:])


def compare_identity_coherence_bundles(
    serial: DiagnosticBundle,
    process: DiagnosticBundle,
    *,
    controls_manifest: Path | None = None,
) -> ValidationResult:
    rows = [
        _compare_tsv("requests_tsv_exact", serial.requests_tsv, process.requests_tsv),
        _compare_tsv("decisions_tsv_exact", serial.decisions_tsv, process.decisions_tsv),
        _compare_tsv(
            "cell_evidence_tsv_exact",
            serial.cell_evidence_tsv,
            process.cell_evidence_tsv,
        ),
        _compare_tsv(
            "controls_tsv_parity_only",
            serial.controls_tsv,
            process.controls_tsv,
            success_details=(
                "controls file parity only; no biological controls assessed here"
            ),
        ),
        _controls_manifest_row(controls_manifest),
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
        serial_value=_tsv_digest(serial_rows),
        process_value=_tsv_digest(process_rows),
        details="TSV differs; row order is part of the frozen contract",
    )


def _controls_manifest_row(controls_manifest: Path | None) -> ValidationRow:
    if controls_manifest is None:
        return ValidationRow(
            check_name="controls_manifest_assessment",
            status="not_assessed",
            serial_value="not_provided",
            process_value="not_provided",
            details=(
                "serial/process parity only; no positive-control or decoy "
                "method validation"
            ),
        )
    return ValidationRow(
        check_name="controls_manifest_assessment",
        status="not_assessed",
        serial_value="provided",
        process_value="provided",
        details=(
            "manifest passed through; this runner reports artifact parity, not "
            "positive-control sensitivity or decoy specificity"
        ),
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


def _tsv_digest(rows: TsvRows) -> str:
    return f"header={len(rows.header)} rows={len(rows.rows)}"
