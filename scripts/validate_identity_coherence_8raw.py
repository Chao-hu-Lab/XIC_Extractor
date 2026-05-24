from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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

# Keep this in sync with controls.py:REQUIRED_MANIFEST_FIELDS plus the optional
# fields read by _entry_from_row(); tests must round-trip proposals through the
# real manifest reader to catch drift.
CONTROL_MANIFEST_COLUMNS = (
    "control_id",
    "control_type",
    "control_name",
    "expected_mapping_status",
    "control_expected_behavior",
    "fragment_observation_mode",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_tolerance_ppm",
    "rt_tolerance_sec",
    "required_failure_reason_when_missed",
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "decoy_generation_method",
    "decoy_source_request_id",
    "decoy_fragment_tags",
    "positive_control_target_name",
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
    "control_notes",
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


ACCEPTANCE_SUMMARY_COLUMNS = (
    "criterion",
    "status",
    "evidence",
    "details",
)

V04_ACCEPTANCE_PASS_PREFIX = (
    "PASS identity_coherence_v04_acceptance "
    "scope=8raw_method_review_only not_85raw_ready"
)

SIDECAR_PARITY_CHECKS = (
    "requests_tsv_exact",
    "decisions_tsv_exact",
    "cell_evidence_tsv_exact",
    "controls_tsv_parity_only",
    "summary_md_presence",
)


@dataclass(frozen=True)
class AcceptanceRow:
    criterion: str
    status: str
    evidence: str
    details: str


@dataclass(frozen=True)
class AcceptanceReport:
    rows: tuple[AcceptanceRow, ...]

    @property
    def accepted(self) -> bool:
        rows = {row.criterion: row for row in self.rows}
        final = rows.get("v04_acceptance")
        return final is not None and final.status == "pass"


class CommandRunner(Protocol):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        ...


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


def build_alignment_command(
    *,
    mode: str,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    controls_manifest: Path | None,
) -> list[str]:
    if mode not in {"serial", "process"}:
        raise ValueError("mode must be 'serial' or 'process'")
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "run_alignment.py"),
        "--discovery-batch-index",
        str(discovery_batch_index),
        "--raw-dir",
        str(raw_dir),
        "--dll-dir",
        str(dll_dir),
        "--output-dir",
        str(output_dir),
        "--emit-identity-coherence-diagnostic",
        "--output-level",
        "validation",
    ]
    if mode == "serial":
        command.extend(
            [
                "--raw-workers",
                "1",
                "--raw-xic-batch-size",
                "1",
            ]
        )
    else:
        command.extend(["--performance-profile", "validation-fast"])
    if controls_manifest is not None:
        command.extend(
            ["--identity-coherence-controls-manifest", str(controls_manifest)]
        )
    return command


def run_validation(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_root: Path,
    controls_manifest: Path | None,
    controls_manifest_proposal: Path | None = None,
    runner: CommandRunner | None = None,
) -> ValidationResult:
    output_root.mkdir(parents=True, exist_ok=True)
    runner = runner or _run_command
    serial_output = output_root / "serial"
    process_output = output_root / "process"
    _reset_run_dir(serial_output)
    _reset_run_dir(process_output)
    metadata: list[RunMetadata] = []
    for mode, output_dir in (
        ("serial", serial_output),
        ("process", process_output),
    ):
        command = build_alignment_command(
            mode=mode,
            discovery_batch_index=discovery_batch_index,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            controls_manifest=controls_manifest,
        )
        completed = runner(command)
        metadata.append(
            RunMetadata(
                mode=mode,
                command_line=subprocess.list2cmdline(command),
                output_dir=output_dir,
                returncode=completed.returncode,
            )
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"{mode} alignment failed with exit code {completed.returncode}: "
                f"command={subprocess.list2cmdline(command)} "
                f"stdout={_tail(completed.stdout)} "
                f"stderr={_tail(completed.stderr)}"
            )
    result = compare_identity_coherence_bundles(
        bundle_from_output_dir(serial_output),
        bundle_from_output_dir(process_output),
        controls_manifest=controls_manifest,
    )
    if controls_manifest_proposal is not None:
        if result.failed_count:
            # Proposal generation stays conservative: if any existing validation
            # row is already failed, do not emit a new proposed controls manifest.
            controls_manifest_proposal.unlink(missing_ok=True)
        else:
            write_decoy_manifest_proposal(
                bundle_from_output_dir(serial_output),
                controls_manifest_proposal,
            )
    return ValidationResult(rows=result.rows, run_metadata=tuple(metadata))


def write_validation_outputs(
    *,
    output_root: Path,
    result: ValidationResult,
    controls_manifest: Path | None,
    run_metadata: tuple[RunMetadata, ...] = (),
) -> AcceptanceReport:
    output_root.mkdir(parents=True, exist_ok=True)
    metadata = run_metadata if run_metadata else result.run_metadata
    result = _with_controls_manifest_row(result, controls_manifest)
    _write_summary_tsv(
        output_root / "identity_coherence_8raw_validation_summary.tsv",
        result,
    )
    _write_report_md(
        output_root / "identity_coherence_8raw_validation_report.md",
        result=result,
        controls_manifest=controls_manifest,
        run_metadata=metadata,
    )
    acceptance = evaluate_v04_acceptance(
        result,
        controls_manifest=controls_manifest,
    )
    _write_acceptance_tsv(
        output_root / "identity_coherence_v04_acceptance.tsv",
        acceptance,
    )
    _write_acceptance_md(
        output_root / "identity_coherence_v04_acceptance.md",
        report=acceptance,
        controls_manifest=controls_manifest,
    )
    return acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run serial-vs-process 8RAW validation for the identity coherence "
            "diagnostic sidecar."
        )
    )
    parser.add_argument("--discovery-batch-index", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--controls-manifest", type=Path)
    parser.add_argument("--write-controls-manifest-proposal", type=Path)
    parser.add_argument(
        "--require-v04-acceptance",
        action="store_true",
        help=(
            "Exit non-zero unless serial/process parity, reviewed controls, "
            "positive controls, and identity decoys pass V0.4 acceptance."
        ),
    )
    args = parser.parse_args(argv)

    if not args.discovery_batch_index.is_file():
        print(
            f"{args.discovery_batch_index}: discovery batch index does not exist",
            file=sys.stderr,
        )
        return 2
    if not args.raw_dir.is_dir():
        print(f"{args.raw_dir}: raw directory does not exist", file=sys.stderr)
        return 2
    if not args.dll_dir.is_dir():
        print(f"{args.dll_dir}: dll directory does not exist", file=sys.stderr)
        return 2
    if (
        args.controls_manifest is not None
        and ".proposed." in args.controls_manifest.name.lower()
    ):
        print(
            "proposal manifests must be reviewed and renamed before use as "
            "--controls-manifest",
            file=sys.stderr,
        )
        return 2
    if args.controls_manifest is not None and not args.controls_manifest.is_file():
        print(
            f"{args.controls_manifest}: controls manifest does not exist",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_validation(
            discovery_batch_index=args.discovery_batch_index,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            output_root=args.output_root,
            controls_manifest=args.controls_manifest,
            controls_manifest_proposal=args.write_controls_manifest_proposal,
        )
        acceptance = write_validation_outputs(
            output_root=args.output_root,
            result=result,
            controls_manifest=args.controls_manifest,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    sidecar_failed_count = sidecar_parity_failed_count(result)
    if sidecar_failed_count:
        print(
            "FAIL identity_coherence_sidecar_parity "
            f"failed={sidecar_failed_count}",
            file=sys.stderr,
        )
        return 1
    acceptance_rows = {row.criterion: row for row in acceptance.rows}
    final_acceptance = acceptance_rows["v04_acceptance"]
    if args.require_v04_acceptance and not acceptance.accepted:
        print(
            "FAIL identity_coherence_v04_acceptance "
            f"reason={final_acceptance.evidence} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}",
            file=sys.stderr,
        )
        return 1
    print(
        "PASS identity_coherence_sidecar_parity "
        f"summary={args.output_root / 'identity_coherence_8raw_validation_report.md'}"
    )
    if acceptance.accepted:
        print(
            f"{V04_ACCEPTANCE_PASS_PREFIX} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}"
        )
    else:
        print(
            "NO-GO identity_coherence_v04_acceptance "
            f"reason={final_acceptance.evidence} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}"
        )
    if args.write_controls_manifest_proposal is not None:
        print(
            "Controls manifest proposal: "
            f"{args.write_controls_manifest_proposal}"
        )
    return 0


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
        _controls_manifest_row(controls_manifest),
        *_control_method_rows(
            serial.controls_tsv,
            process.controls_tsv,
            controls_manifest,
            controls_parity_pass=controls_parity.status == "pass",
        ),
        _compare_summary_presence(serial.summary_md, process.summary_md),
    ]
    return ValidationResult(rows=tuple(rows))


def sidecar_parity_failed_count(result: ValidationResult) -> int:
    return len(_sidecar_parity_failures(result))


def _sidecar_parity_failures(result: ValidationResult) -> tuple[str, ...]:
    rows_by_name = {row.check_name: row for row in result.rows}
    failures: list[str] = []
    for name in SIDECAR_PARITY_CHECKS:
        row = rows_by_name.get(name)
        if row is None or row.status != "pass":
            failures.append(name)
    return tuple(failures)


def evaluate_v04_acceptance(
    result: ValidationResult,
    *,
    controls_manifest: Path | None = None,
) -> AcceptanceReport:
    rows_by_name = {row.check_name: row for row in result.rows}
    parity = _acceptance_sidecar_parity(rows_by_name)
    controls = _acceptance_reviewed_controls(rows_by_name, controls_manifest)
    positives = _acceptance_positive_controls(rows_by_name)
    decoys = _acceptance_identity_decoys(rows_by_name)
    required = (parity, controls, positives, decoys)
    if all(row.status == "pass" for row in required):
        final = AcceptanceRow(
            criterion="v04_acceptance",
            status="pass",
            evidence="all_required_criteria_passed",
            details=(
                "V0.4 diagnostic mechanics and reviewed controls passed for "
                "8RAW method review; this does not clear 85RAW execution."
            ),
        )
    else:
        failing = ",".join(row.criterion for row in required if row.status != "pass")
        final = AcceptanceRow(
            criterion="v04_acceptance",
            status="fail",
            evidence=failing,
            details=(
                "V0.4 acceptance is blocked until all required criteria pass; "
                "do not treat serial/process parity alone as method validation."
            ),
        )
    return AcceptanceReport(rows=(*required, final))


def _acceptance_sidecar_parity(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    required = SIDECAR_PARITY_CHECKS
    missing = [name for name in required if name not in rows_by_name]
    failing = [
        name
        for name in required
        if name in rows_by_name and rows_by_name[name].status != "pass"
    ]
    if not missing and not failing:
        return AcceptanceRow(
            criterion="serial_process_sidecar_parity",
            status="pass",
            evidence=",".join(required),
            details="serial and process frozen sidecars match exactly",
        )
    evidence = ",".join((*missing, *failing))
    return AcceptanceRow(
        criterion="serial_process_sidecar_parity",
        status="fail",
        evidence=evidence,
        details="serial/process sidecar parity must pass before method review",
    )


def _acceptance_reviewed_controls(
    rows_by_name: dict[str, ValidationRow],
    controls_manifest: Path | None,
) -> AcceptanceRow:
    row = rows_by_name.get("controls_manifest_assessment")
    reviewed_path = (
        controls_manifest is not None
        and controls_manifest.name.lower().endswith(".reviewed.tsv")
    )
    if (
        row is not None
        and row.serial_value == row.process_value == "provided"
        and reviewed_path
    ):
        return AcceptanceRow(
            criterion="reviewed_controls_manifest",
            status="pass",
            evidence="provided",
            details="a .reviewed.tsv controls manifest was supplied to the validator",
        )
    return AcceptanceRow(
        criterion="reviewed_controls_manifest",
        status="fail",
        evidence="not_provided_or_not_reviewed",
        details=(
            "a .reviewed.tsv controls manifest is required; proposed manifests "
            "and ad-hoc TSV paths cannot satisfy this criterion"
        ),
    )


def _acceptance_positive_controls(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    row = rows_by_name.get("positive_control_pass_fraction")
    if row is not None and row.status == "pass":
        return AcceptanceRow(
            criterion="positive_control_sensitivity",
            status="pass",
            evidence=f"{row.serial_value}/{row.process_value}",
            details=row.details,
        )
    return AcceptanceRow(
        criterion="positive_control_sensitivity",
        status="fail",
        evidence=_row_evidence(row),
        details="positive controls must be present and pass before V0.4 acceptance",
    )


def _acceptance_identity_decoys(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    coherent = rows_by_name.get("decoy_coherent_seed_count")
    rejected = rows_by_name.get("decoy_correctly_rejected_count")
    if (
        coherent is not None
        and rejected is not None
        and coherent.status == "pass"
        and coherent.serial_value == coherent.process_value == "0"
        and rejected.status == "pass"
    ):
        return AcceptanceRow(
            criterion="identity_decoy_specificity",
            status="pass",
            evidence=f"promoted=0 rejected={rejected.serial_value}",
            details="identity decoys were rejected without coherent-seed promotion",
        )
    return AcceptanceRow(
        criterion="identity_decoy_specificity",
        status="fail",
        evidence=(
            f"promoted={_row_evidence(coherent)} "
            f"rejected={_row_evidence(rejected)}"
        ),
        details="identity decoys must not reach coherent seed or would-primary",
    )


def _row_evidence(row: ValidationRow | None) -> str:
    if row is None:
        return "missing"
    return f"{row.status}:{row.serial_value}/{row.process_value}"


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


def _control_method_rows(
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
    serial_rows = _read_tsv_dict_rows(serial_controls_tsv)
    process_rows = _read_tsv_dict_rows(process_controls_tsv)
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
        _merge_method_row(serial_positive, process_positive),
        _merge_method_row(serial_coherent, process_coherent),
        _merge_method_row(serial_rejected, process_rejected),
    )


def _read_tsv_dict_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        return tuple(dict(row) for row in reader)


def _rows_by_control_type(
    rows: tuple[dict[str, str], ...],
    control_type: str,
) -> list[dict[str, str]]:
    return [row for row in rows if row.get("control_type") == control_type]


def _merge_method_row(serial: ValidationRow, process: ValidationRow) -> ValidationRow:
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


def write_decoy_manifest_proposal(
    serial_bundle: DiagnosticBundle,
    proposal_path: Path,
    *,
    max_decoys: int = 3,
) -> int:
    if max_decoys < 0:
        raise ValueError("max_decoys must be nonnegative")
    request_rows = _read_tsv_dict_rows(serial_bundle.requests_tsv)
    decision_rows = _read_tsv_dict_rows(serial_bundle.decisions_tsv)
    request_by_decision, ambiguous_decision_ids = _unique_requests_by_decision(
        request_rows
    )
    proposal_rows: list[dict[str, str]] = []
    for decision in decision_rows:
        if len(proposal_rows) >= max_decoys:
            break
        decision_id = decision.get("decision_id", "")
        if decision_id in ambiguous_decision_ids:
            continue
        if decision.get("seed_gate_class") != "coherent_seed":
            continue
        request = request_by_decision.get(decision_id)
        if request is None:
            continue
        if request.get("seed_candidate_id") != decision.get("seed_candidate_id"):
            continue
        if request.get("seed_sample") != decision.get("seed_sample"):
            continue
        if not _proposal_request_has_required_values(request):
            continue
        proposal_rows.append(
            _decoy_manifest_row(
                index=len(proposal_rows) + 1,
                request=request,
                decision=decision,
            )
        )
    _write_manifest_rows(proposal_path, proposal_rows)
    return len(proposal_rows)


def _unique_requests_by_decision(
    request_rows: tuple[dict[str, str], ...],
) -> tuple[dict[str, dict[str, str]], set[str]]:
    request_by_decision: dict[str, dict[str, str]] = {}
    ambiguous: set[str] = set()
    for row in request_rows:
        decision_id = row.get("decision_id", "")
        if not decision_id:
            continue
        if decision_id in request_by_decision:
            ambiguous.add(decision_id)
            request_by_decision.pop(decision_id, None)
            continue
        if decision_id not in ambiguous:
            request_by_decision[decision_id] = row
    return request_by_decision, ambiguous


def _proposal_request_has_required_values(request: dict[str, str]) -> bool:
    required = (
        "fragment_observation_mode",
        "precursor_tolerance_ppm",
        "product_tolerance_ppm",
        "cid_observed_loss_tolerance_ppm",
    )
    return all(request.get(field, "").strip() for field in required)


def _decoy_manifest_row(
    *,
    index: int,
    request: dict[str, str],
    decision: dict[str, str],
) -> dict[str, str]:
    request_id = request.get("request_id", "")
    return {
        "control_id": f"IDC-{index:03d}",
        "control_type": "identity_decoy",
        "control_name": f"Auto-proposed rt_shift decoy for {request_id}",
        "expected_mapping_status": "not_applicable",
        "control_expected_behavior": "decoy_rejected_before_promotion",
        "fragment_observation_mode": request.get("fragment_observation_mode", ""),
        "precursor_tolerance_ppm": request.get("precursor_tolerance_ppm", ""),
        "product_tolerance_ppm": request.get("product_tolerance_ppm", ""),
        "cid_observed_loss_tolerance_ppm": request.get(
            "cid_observed_loss_tolerance_ppm", ""
        ),
        "rt_tolerance_sec": "60.0",
        "required_failure_reason_when_missed": "seed_rt_outside_owner_peak",
        "decision_id": decision.get("decision_id", ""),
        "identity_family_id": decision.get("identity_family_id", ""),
        "seed_candidate_id": decision.get("seed_candidate_id", ""),
        "decoy_generation_method": "rt_shift",
        "decoy_source_request_id": request_id,
        "decoy_fragment_tags": "",
        "positive_control_target_name": "",
        "positive_control_target_mz": "",
        "positive_control_target_rt_sec": "",
        "positive_control_mapping_error_ppm": "",
        "positive_control_mapping_delta_rt_sec": "",
        "control_notes": (
            "auto-proposed identity decoy; review and rename to .reviewed.tsv "
            "before using as validation input"
        ),
    }


def _write_manifest_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CONTROL_MANIFEST_COLUMNS,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: row.get(column, "")
                    for column in CONTROL_MANIFEST_COLUMNS
                }
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


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )


def _reset_run_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _tail(text: str | None, *, limit: int = 1000) -> str:
    if not text:
        return ""
    return text[-limit:]


def _with_controls_manifest_row(
    result: ValidationResult,
    controls_manifest: Path | None,
) -> ValidationResult:
    if any(row.check_name == "controls_manifest_assessment" for row in result.rows):
        return result
    return ValidationResult(
        rows=(*result.rows, _controls_manifest_row(controls_manifest)),
        run_metadata=result.run_metadata,
    )


def _write_summary_tsv(path: Path, result: ValidationResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=VALIDATION_SUMMARY_COLUMNS,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in result.rows:
            writer.writerow(
                {
                    "check_name": row.check_name,
                    "status": row.status,
                    "serial_value": row.serial_value,
                    "process_value": row.process_value,
                    "details": row.details,
                }
            )


def _write_acceptance_tsv(path: Path, report: AcceptanceReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ACCEPTANCE_SUMMARY_COLUMNS,
            dialect="excel-tab",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in report.rows:
            writer.writerow(
                {
                    "criterion": row.criterion,
                    "status": row.status,
                    "evidence": row.evidence,
                    "details": row.details,
                }
            )


def _write_acceptance_md(
    path: Path,
    *,
    report: AcceptanceReport,
    controls_manifest: Path | None,
) -> None:
    controls_text = (
        str(controls_manifest) if controls_manifest is not None else "not_provided"
    )
    verdict = "PASS" if report.accepted else "FAIL"
    lines = [
        "# Identity Coherence V0.4 Acceptance",
        "",
        (
            "This report closes the V0.4 8RAW diagnostic acceptance loop. It is "
            "diagnostic-only and does not validate final matrix filtering, "
            "background filtering, normalization, statistics, or 85RAW execution."
        ),
        "",
        f"**Verdict:** `{verdict}`",
        "",
        f"**Reviewed controls manifest:** `{controls_text}`",
        "",
        "| Criterion | Status | Evidence | Details |",
        "| --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(
            f"| `{row.criterion}` | `{row.status}` | "
            f"{_format_markdown_cell(row.evidence)} | "
            f"{_format_markdown_cell(row.details)} |"
        )
    lines.extend(
        [
            "",
            "## Handoff Notes",
            "",
            (
                "- A PASS means the V0.4 diagnostic is ready for human method "
                "review on the 8RAW subset."
            ),
            (
                "- A PASS does not authorize 85RAW execution; 85RAW still "
                "requires a reviewed count/fraction policy and request-budget "
                "ceiling."
            ),
            (
                "- A FAIL with passing serial/process parity usually means "
                "reviewed controls are missing or controls failed; do not "
                "reinterpret that as a retrieval or Backfill failure."
            ),
            (
                "- Contaminants that are chromatographically coherent can "
                "still appear as would-primary diagnostic rows; downstream "
                "filtering owns final-matrix exclusion."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _write_report_md(
    path: Path,
    *,
    result: ValidationResult,
    controls_manifest: Path | None,
    run_metadata: tuple[RunMetadata, ...] = (),
) -> None:
    parity_result = "PASS" if sidecar_parity_failed_count(result) == 0 else "FAIL"
    controls_status = (
        "provided_not_assessed" if controls_manifest is not None else "not_assessed"
    )
    lines = [
        "# Identity Coherence 8RAW Validation",
        "",
        f"Parity result: {parity_result}",
        "",
        "This report is diagnostic-only. It validates identity coherence sidecar "
        "parity and does not validate final matrix filtering. It is not method "
        "validation and does not establish positive-control sensitivity or decoy "
        "specificity unless those checks are explicitly reported.",
        "",
        "`would_primary_provisional_identity_family_support` is a diagnostic "
        "sidecar label, not final retained feature inclusion.",
        "",
        f"Controls: {controls_status}",
        "",
        "## Run Metadata",
        "",
        "| Mode | Return Code | Output Dir | Command |",
        "| --- | ---: | --- | --- |",
    ]
    if not run_metadata:
        lines.append("| `not_assessed` | 0 |  | metadata not supplied |")
    for item in run_metadata:
        lines.append(
            "| "
            f"`{item.mode}` | {item.returncode} | `{item.output_dir}` | "
            f"`{item.command_line}` |"
        )
    lines.extend(
        [
            "",
            "## Parity Checks",
            "",
            "| Check | Status | Serial | Process | Details |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in result.rows:
        lines.append(
            "| "
            f"`{row.check_name}` | `{row.status}` | {row.serial_value} | "
            f"{row.process_value} | {row.details} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
