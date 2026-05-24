from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.validate_identity_coherence_8raw import (
    DiagnosticBundle,
    build_alignment_command,
    compare_identity_coherence_bundles,
    read_tsv_rows,
    run_validation,
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
