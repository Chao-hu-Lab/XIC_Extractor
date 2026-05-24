from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import validate_identity_coherence_8raw as validation_script
from scripts.validate_identity_coherence_8raw import (
    DiagnosticBundle,
    ValidationResult,
    ValidationRow,
    build_alignment_command,
    compare_identity_coherence_bundles,
    read_tsv_rows,
    run_validation,
    write_validation_outputs,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _bundle(root: Path, *, suffix: str = "") -> DiagnosticBundle:
    return DiagnosticBundle(
        requests_tsv=root / f"untargeted_identity_coherence_requests{suffix}.tsv",
        decisions_tsv=root / f"untargeted_identity_coherence_decisions{suffix}.tsv",
        cell_evidence_tsv=(
            root / f"untargeted_identity_coherence_cell_evidence{suffix}.tsv"
        ),
        controls_tsv=root / f"untargeted_identity_coherence_controls{suffix}.tsv",
        summary_md=root / f"untargeted_identity_coherence_summary{suffix}.md",
    )


def _write_bundle(root: Path, *, decision_rows: str) -> DiagnosticBundle:
    bundle = _bundle(root)
    _write(bundle.requests_tsv, "request_id\tseed_candidate_id\nICR-1\tC1\n")
    _write(bundle.decisions_tsv, "decision_id\tdecision\n" + decision_rows)
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(bundle.controls_tsv, "control_id\tcontrol_pass\n")
    _write(bundle.summary_md, "# Summary\n")
    return bundle


def _write_controls_bundle(
    root: Path,
    *,
    controls_rows: str,
) -> DiagnosticBundle:
    # Minimal fixture for method-row calculation. Frozen output schema parity is
    # covered by the existing writer tests; this validator only consumes these
    # five controls.tsv fields for summary metrics.
    bundle = _bundle(root)
    _write(bundle.requests_tsv, "request_id\tseed_candidate_id\nICR-1\tC1\n")
    _write(
        bundle.decisions_tsv,
        "decision_id\tdecision\n"
        "ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(
        bundle.controls_tsv,
        "control_id\tcontrol_type\tcontrol_pass\tcontrol_status\t"
        "control_failure_reason\n"
        + controls_rows,
    )
    _write(bundle.summary_md, "# Summary\n")
    return bundle


def test_read_tsv_rows_preserves_header_and_order(tmp_path: Path) -> None:
    path = _write(tmp_path / "rows.tsv", "a\tb\n1\t2\n3\t4\n")

    rows = read_tsv_rows(path)

    assert rows.header == ("a", "b")
    assert rows.rows == (("1", "2"), ("3", "4"))


def test_compare_bundles_passes_identical_tsvs(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )

    result = compare_identity_coherence_bundles(serial, process)

    assert result.failed_count == 0
    assert {row.check_name: row.status for row in result.rows}[
        "decisions_tsv_exact"
    ] == "pass"
    assert {row.check_name: row.status for row in result.rows}[
        "controls_manifest_assessment"
    ] == "not_assessed"
    assert {row.check_name: row.details for row in result.rows}[
        "controls_tsv_parity_only"
    ].startswith("controls file parity only")


def test_controls_rows_remain_not_assessed_without_manifest(
    tmp_path: Path,
) -> None:
    serial = _write_controls_bundle(
        tmp_path / "serial",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )
    process = _write_controls_bundle(
        tmp_path / "process",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=None,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["controls_manifest_assessment"].status == "not_assessed"
    assert rows["positive_control_pass_fraction"].status == "not_assessed"
    assert rows["decoy_coherent_seed_count"].status == "not_assessed"


def test_controls_rows_report_positive_and_decoy_metrics(tmp_path: Path) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "PC-1\tpositive_targeted_istd\ttrue\tassessed\t\n"
        "IDC-1\tidentity_decoy\ttrue\tassessed\t\n"
    )
    serial = _write_controls_bundle(tmp_path / "serial", controls_rows=controls)
    process = _write_controls_bundle(tmp_path / "process", controls_rows=controls)

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["positive_control_pass_fraction"].status == "pass"
    assert rows["positive_control_pass_fraction"].serial_value == "1.000"
    assert rows["decoy_coherent_seed_count"].status == "pass"
    assert rows["decoy_coherent_seed_count"].serial_value == "0"
    assert rows["decoy_correctly_rejected_count"].serial_value == "1/1"


def test_controls_rows_fail_when_decoy_reaches_coherent_seed(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "IDC-1\tidentity_decoy\tfalse\tassessed\tdecoy_seed_gate_coherent\n"
    )
    serial = _write_controls_bundle(tmp_path / "serial", controls_rows=controls)
    process = _write_controls_bundle(tmp_path / "process", controls_rows=controls)

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["decoy_coherent_seed_count"].status == "fail"
    assert rows["decoy_coherent_seed_count"].serial_value == "1"


def test_controls_rows_do_not_interpret_when_controls_parity_fails(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    serial = _write_controls_bundle(
        tmp_path / "serial",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )
    process = _write_controls_bundle(
        tmp_path / "process",
        controls_rows="IDC-1\tidentity_decoy\tfalse\tassessed\t"
        "decoy_seed_gate_coherent\n",
    )

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["controls_tsv_parity_only"].status == "fail"
    assert rows["decoy_coherent_seed_count"].status == "fail"
    assert rows["decoy_coherent_seed_count"].serial_value == "not_assessed"
    assert rows["decoy_coherent_seed_count"].process_value == "not_assessed"


def test_compare_bundles_fails_when_row_order_changes(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\treview_only_insufficient_identity_support\n"
        "ICD-2\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-2\twould_primary_provisional_identity_family_support\n"
        "ICD-1\treview_only_insufficient_identity_support\n",
    )

    result = compare_identity_coherence_bundles(serial, process)

    assert result.failed_count == 1
    assert {row.check_name: row.status for row in result.rows}[
        "decisions_tsv_exact"
    ] == "fail"


def test_compare_bundles_fails_when_summary_missing(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    serial.summary_md.unlink()

    result = compare_identity_coherence_bundles(serial, process)

    assert {row.check_name: row.status for row in result.rows}[
        "summary_md_presence"
    ] == "fail"


def test_build_serial_command_omits_validation_fast_profile(tmp_path: Path) -> None:
    command = build_alignment_command(
        mode="serial",
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out" / "serial",
        controls_manifest=None,
    )

    joined = " ".join(str(part) for part in command)
    assert "--emit-identity-coherence-diagnostic" in joined
    assert "--identity-coherence-output-dir" not in command
    assert "--emit-alignment-cells" not in command
    assert "--timing-output" not in command
    assert "--performance-profile" not in command
    assert "validation-fast" not in command
    assert command[command.index("--raw-workers") + 1] == "1"
    assert command[command.index("--raw-xic-batch-size") + 1] == "1"


def test_build_process_command_uses_validation_fast_profile(tmp_path: Path) -> None:
    command = build_alignment_command(
        mode="process",
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out" / "process",
        controls_manifest=tmp_path / "controls.tsv",
    )

    assert "--performance-profile" in command
    assert "validation-fast" in command
    assert "--identity-coherence-output-dir" not in command
    assert "--emit-alignment-cells" not in command
    assert "--timing-output" not in command
    assert "--identity-coherence-controls-manifest" in command
    assert str(tmp_path / "controls.tsv") in command


def test_run_validation_uses_fake_runner_and_compares_outputs(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        output_dir = Path(command[command.index("--output-dir") + 1])
        _write_bundle(
            output_dir / "identity_coherence",
            decision_rows=(
                "ICD-1\twould_primary_provisional_identity_family_support\n"
            ),
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_root=tmp_path / "validation",
        controls_manifest=None,
        runner=fake_runner,
    )

    assert result.failed_count == 0
    assert [command[command.index("--output-dir") + 1] for command in commands] == [
        str(tmp_path / "validation" / "serial"),
        str(tmp_path / "validation" / "process"),
    ]
    assert result.run_metadata[0].mode == "serial"
    assert result.run_metadata[1].mode == "process"


def test_run_validation_raises_when_child_fails(tmp_path: Path) -> None:
    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            13,
            stdout="partial stdout",
            stderr="boom",
        )

    try:
        run_validation(
            discovery_batch_index=tmp_path / "batch.csv",
            raw_dir=tmp_path / "raw",
            dll_dir=tmp_path / "dll",
            output_root=tmp_path / "validation",
            controls_manifest=None,
            runner=fake_runner,
        )
    except RuntimeError as exc:
        assert "serial alignment failed with exit code 13" in str(exc)
        assert "boom" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_run_validation_clears_previous_mode_outputs(tmp_path: Path) -> None:
    stale = (
        tmp_path
        / "validation"
        / "serial"
        / "identity_coherence"
        / "untargeted_identity_coherence_decisions.tsv"
    )
    stale.parent.mkdir(parents=True)
    stale.write_text("decision_id\tdecision\nSTALE\told\n", encoding="utf-8")

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        output_dir = Path(command[command.index("--output-dir") + 1])
        _write_bundle(
            output_dir / "identity_coherence",
            decision_rows=(
                "ICD-1\twould_primary_provisional_identity_family_support\n"
            ),
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_root=tmp_path / "validation",
        controls_manifest=None,
        runner=fake_runner,
    )

    assert result.failed_count == 0
    assert "STALE" not in stale.read_text(encoding="utf-8")


def test_write_validation_outputs_labels_controls_not_assessed(
    tmp_path: Path,
) -> None:
    result = ValidationResult(
        rows=(
            ValidationRow(
                check_name="requests_tsv_exact",
                status="pass",
                serial_value="1",
                process_value="1",
                details="ok",
            ),
        )
    )

    write_validation_outputs(
        output_root=tmp_path,
        result=result,
        controls_manifest=None,
    )

    report = (
        tmp_path / "identity_coherence_8raw_validation_report.md"
    ).read_text(encoding="utf-8")
    assert "Controls: not_assessed" in report
    assert "diagnostic-only" in report
    assert "does not validate final matrix filtering" in report
    assert "not final retained feature inclusion" in report
    summary = (
        tmp_path / "identity_coherence_8raw_validation_summary.tsv"
    ).read_text(encoding="utf-8")
    assert "controls_manifest_assessment\tnot_assessed" in summary


def test_main_rejects_missing_controls_manifest(tmp_path: Path, capsys) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
            "--controls-manifest",
            str(tmp_path / "missing.tsv"),
        ]
    )

    assert code == 2
    assert "controls manifest does not exist" in capsys.readouterr().err


def test_main_returns_one_when_parity_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    def fake_run_validation(**kwargs) -> ValidationResult:
        return ValidationResult(
            rows=(
                ValidationRow(
                    check_name="decisions_tsv_exact",
                    status="fail",
                    serial_value="a",
                    process_value="b",
                    details="different",
                ),
            )
        )

    monkeypatch.setattr(validation_script, "run_validation", fake_run_validation)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
        ]
    )

    assert code == 1


def test_main_returns_two_when_validation_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    def fake_run_validation(**kwargs) -> ValidationResult:
        raise RuntimeError("serial alignment failed")

    monkeypatch.setattr(validation_script, "run_validation", fake_run_validation)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
        ]
    )

    assert code == 2
