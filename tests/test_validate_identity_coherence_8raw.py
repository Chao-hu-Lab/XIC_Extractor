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
    write_decoy_manifest_proposal,
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


# This fixture intentionally uses the proposal writer's minimum input surface.
# Do not consolidate it with _write_bundle(); this test needs seed_gate_class.
def _write_proposal_source_bundle(root: Path) -> DiagnosticBundle:
    bundle = _bundle(root)
    _write(
        bundle.requests_tsv,
        "request_id\tdecision_id\tseed_candidate_id\tseed_sample\t"
        "fragment_observation_mode\tprecursor_mz\tproduct_mz\tfragment_tags\t"
        "fragment_tag_match_policy\tfragment_profile_id\tfragment_profile_hash\t"
        "precursor_tolerance_ppm\tproduct_tolerance_ppm\tcid_observed_loss_da\t"
        "cid_observed_loss_tolerance_ppm\trequest_identity_completeness_status\t"
        "request_candidate_identity_status\tprecursor_error_ppm\tproduct_error_ppm\t"
        "cid_observed_loss_error_ppm\tcid_observed_loss_error_da\t"
        "request_builder_flags\n"
        "ICR-1\tICD-1\tC1\tS1\tcid_neutral_loss\t500.0\t384.0\tDNA_dR\t"
        "all_request_tags_supported\tdefault\tunavailable\t20.0\t20.0\t"
        "116.0474\t20.0\tcomplete\tmatch\t0.1\t0.2\t0.3\t0.0001\t\n",
    )
    _write(
        bundle.decisions_tsv,
        "decision_id\tidentity_family_id\tseed_candidate_id\tseed_sample\t"
        "seed_gate_class\tdecision\n"
        "ICD-1\tICF-1\tC1\tS1\tcoherent_seed\t"
        "would_primary_provisional_identity_family_support\n",
    )
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(bundle.controls_tsv, "control_id\tcontrol_type\tcontrol_pass\n")
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


def test_write_decoy_manifest_proposal_from_serial_bundle(tmp_path: Path) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "identity_coherence_controls_manifest_8raw.proposed.tsv"

    count = write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

    assert count == 1
    text = proposal.read_text(encoding="utf-8")
    assert "control_id\tcontrol_type\tcontrol_name" in text
    assert "IDC-001\tidentity_decoy\tAuto-proposed rt_shift decoy for ICR-1" in text
    assert "\tnot_applicable\t" in text
    assert "\tseed_rt_outside_owner_peak\t" in text
    assert "\tICR-1\t" in text
    assert "\trt_shift\t" in text


def test_write_decoy_manifest_proposal_writes_header_when_no_sources(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    _write(
        bundle.decisions_tsv,
        "decision_id\tidentity_family_id\tseed_candidate_id\tseed_sample\t"
        "seed_gate_class\tdecision\n"
        "ICD-1\tICF-1\tC1\tS1\treview_only_seed_gate_failed\t"
        "review_only_seed_gate_failed\n",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=3)

    assert count == 0
    lines = proposal.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("control_id\tcontrol_type\tcontrol_name")


def test_write_decoy_manifest_proposal_respects_zero_limit(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=0)

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_joins_by_decision_id(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    original = bundle.requests_tsv.read_text(encoding="utf-8")
    header, row = original.splitlines()
    wrong = row.replace("ICR-1\tICD-1\tC1\tS1", "ICR-WRONG\tICD-OTHER\tC1\tS9")
    right = row.replace("ICR-1\tICD-1\tC1\tS1", "ICR-RIGHT\tICD-1\tC1\tS1")
    bundle.requests_tsv.write_text(
        f"{header}\n{wrong}\n{right}\n",
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    assert count == 1
    text = proposal.read_text(encoding="utf-8")
    assert "\tICR-RIGHT\t" in text
    assert "\tICR-WRONG\t" not in text


def test_write_decoy_manifest_proposal_skips_incomplete_tolerances(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    bundle.requests_tsv.write_text(
        bundle.requests_tsv.read_text(encoding="utf-8").replace(
            "\t20.0\t20.0\t116.0474\t20.0\t",
            "\t20.0\t\t116.0474\t20.0\t",
        ),
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_round_trips_through_manifest_reader(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.identity_coherence.controls import (
        read_identity_controls_manifest,
    )

    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "proposal.tsv"

    write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    entries = read_identity_controls_manifest(proposal)
    assert len(entries) == 1
    assert entries[0].control_type.value == "identity_decoy"
    assert entries[0].expected_mapping_status.value == "not_applicable"
    assert entries[0].decoy_generation_method.value == "rt_shift"
    assert entries[0].decoy_source_request_id == "ICR-1"


def test_run_validation_does_not_write_proposal_when_parity_fails(
    tmp_path: Path,
) -> None:
    proposal = tmp_path / "proposal.tsv"
    proposal.write_text("stale\n", encoding="utf-8")

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        output_dir = Path(command[command.index("--output-dir") + 1])
        _write_proposal_source_bundle(output_dir / "identity_coherence")
        if output_dir.name == "process":
            (output_dir / "identity_coherence" / bundle_name()).write_text(
                "different\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    def bundle_name() -> str:
        return "untargeted_identity_coherence_decisions.tsv"

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path,
        dll_dir=tmp_path,
        output_root=tmp_path / "out",
        controls_manifest=None,
        controls_manifest_proposal=proposal,
        runner=fake_runner,
    )

    assert result.failed_count > 0
    assert not proposal.exists()


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


def test_main_passes_controls_manifest_proposal_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    proposal = tmp_path / "proposal.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    seen: dict[str, object] = {}

    def fake_run_validation(**kwargs) -> ValidationResult:
        seen.update(kwargs)
        return ValidationResult(
            rows=(
                ValidationRow(
                    check_name="decisions_tsv_exact",
                    status="pass",
                    serial_value="1",
                    process_value="1",
                    details="same",
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
            "--write-controls-manifest-proposal",
            str(proposal),
        ]
    )

    assert code == 0
    assert seen["controls_manifest_proposal"] == proposal


def test_main_rejects_proposed_controls_manifest(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    proposed = tmp_path / "identity_coherence_controls_manifest.proposed.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    proposed.write_text("control_id\n", encoding="utf-8")
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
            str(proposed),
        ]
    )

    assert code == 2
    assert "must be reviewed and renamed" in capsys.readouterr().err


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
