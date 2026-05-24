from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.bundle import (
    read_tsv_dict_rows,
)
from xic_extractor.alignment.identity_coherence_validation.models import ValidationRow


def controls_manifest_row(controls_manifest: Path | None) -> ValidationRow:
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


def control_method_rows(
    serial_controls_tsv: Path,
    process_controls_tsv: Path,
    controls_manifest: Path | None,
    *,
    controls_parity_pass: bool,
) -> tuple[ValidationRow, ...]:
    if controls_manifest is None:
        return (
            ValidationRow(
                check_name="positive_control_pass_fraction",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
            ValidationRow(
                check_name="decoy_coherent_seed_count",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
            ValidationRow(
                check_name="decoy_correctly_rejected_count",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
        )
    if not controls_parity_pass:
        return (
            ValidationRow(
                check_name="positive_control_pass_fraction",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
            ValidationRow(
                check_name="decoy_coherent_seed_count",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
            ValidationRow(
                check_name="decoy_correctly_rejected_count",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
        )
    serial_rows = read_tsv_dict_rows(serial_controls_tsv)
    process_rows = read_tsv_dict_rows(process_controls_tsv)
    serial_positive = _positive_control_fraction_row(
        _rows_by_control_type(serial_rows, "positive_targeted_istd"),
    )
    process_positive = _positive_control_fraction_row(
        _rows_by_control_type(process_rows, "positive_targeted_istd"),
    )
    serial_coherent = _decoy_coherent_count_row(
        _rows_by_control_type(serial_rows, "identity_decoy"),
    )
    process_coherent = _decoy_coherent_count_row(
        _rows_by_control_type(process_rows, "identity_decoy"),
    )
    serial_rejected = _decoy_rejected_count_row(
        _rows_by_control_type(serial_rows, "identity_decoy"),
    )
    process_rejected = _decoy_rejected_count_row(
        _rows_by_control_type(process_rows, "identity_decoy"),
    )
    return (
        merge_method_row(serial_positive, process_positive),
        merge_method_row(serial_coherent, process_coherent),
        merge_method_row(serial_rejected, process_rejected),
    )


def merge_method_row(serial: ValidationRow, process: ValidationRow) -> ValidationRow:
    status = "pass" if serial.status == process.status == "pass" else "fail"
    if serial.status == process.status == "not_assessed":
        status = "not_assessed"
    return ValidationRow(
        check_name=serial.check_name,
        status=status,
        serial_value=serial.serial_value,
        process_value=process.process_value,
        details=f"serial: {serial.details}; process: {process.details}",
    )


def _rows_by_control_type(
    rows: tuple[dict[str, str], ...],
    control_type: str,
) -> list[dict[str, str]]:
    return [row for row in rows if row.get("control_type") == control_type]


def _positive_control_fraction_row(
    rows: list[dict[str, str]],
) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="positive_control_pass_fraction",
            status="not_assessed",
            serial_value="0/0",
            process_value="0/0",
            details="no positive_targeted_istd controls in controls.tsv",
        )
    passed = sum(1 for row in rows if _control_pass_is_true(row))
    fraction = passed / len(rows)
    value = f"{fraction:.3f}"
    return ValidationRow(
        check_name="positive_control_pass_fraction",
        status="pass" if passed == len(rows) else "fail",
        serial_value=value,
        process_value=value,
        details=f"{passed}/{len(rows)} positive controls passed",
    )


def _decoy_coherent_count_row(rows: list[dict[str, str]]) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="decoy_coherent_seed_count",
            status="not_assessed",
            serial_value="0",
            process_value="0",
            details="no identity_decoy controls in controls.tsv",
        )
    coherent = sum(
        1
        for row in rows
        if row.get("control_failure_reason") == "decoy_seed_gate_coherent"
    )
    return ValidationRow(
        check_name="decoy_coherent_seed_count",
        status="pass" if coherent == 0 else "fail",
        serial_value=str(coherent),
        process_value=str(coherent),
        details="decoy controls that reached coherent_seed",
    )


def _decoy_rejected_count_row(rows: list[dict[str, str]]) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="decoy_correctly_rejected_count",
            status="not_assessed",
            serial_value="0/0",
            process_value="0/0",
            details="no identity_decoy controls in controls.tsv",
        )
    passed = sum(1 for row in rows if _control_pass_is_true(row))
    value = f"{passed}/{len(rows)}"
    return ValidationRow(
        check_name="decoy_correctly_rejected_count",
        status="pass" if passed == len(rows) else "fail",
        serial_value=value,
        process_value=value,
        details="identity decoys rejected before false promotion",
    )


def _control_pass_is_true(row: dict[str, str]) -> bool:
    # Intentional duplication: validator must not import alignment internals,
    # and independent controls summary computation is the cross-check.
    return row.get("control_pass", "").strip().lower() == "true"
