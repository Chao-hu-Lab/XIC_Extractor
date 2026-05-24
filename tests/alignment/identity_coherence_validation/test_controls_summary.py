from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.controls_summary import (
    control_method_rows,
    controls_manifest_row,
    merge_method_row,
)
from xic_extractor.alignment.identity_coherence_validation.models import ValidationRow


def _write_controls_tsv(path: Path, rows: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "control_id\tcontrol_type\tcontrol_pass\tcontrol_status\t"
        "control_failure_reason\n"
        + rows,
        encoding="utf-8",
    )
    return path


def test_controls_rows_remain_not_assessed_without_manifest(tmp_path: Path) -> None:
    rows = control_method_rows(
        _write_controls_tsv(
            tmp_path / "serial" / "controls.tsv",
            "IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
        ),
        _write_controls_tsv(
            tmp_path / "process" / "controls.tsv",
            "IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
        ),
        controls_manifest=None,
        controls_parity_pass=True,
    )

    rows_by_name = {row.check_name: row for row in rows}
    assert controls_manifest_row(None).status == "not_assessed"
    assert rows_by_name["positive_control_pass_fraction"].status == "not_assessed"
    assert rows_by_name["decoy_coherent_seed_count"].status == "not_assessed"


def test_controls_rows_report_positive_and_decoy_metrics(tmp_path: Path) -> None:
    manifest = tmp_path / "controls.reviewed.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "PC-1\tpositive_targeted_istd\ttrue\tassessed\t\n"
        "IDC-1\tidentity_decoy\ttrue\tassessed\t\n"
    )

    rows = control_method_rows(
        _write_controls_tsv(tmp_path / "serial" / "controls.tsv", controls),
        _write_controls_tsv(tmp_path / "process" / "controls.tsv", controls),
        controls_manifest=manifest,
        controls_parity_pass=True,
    )

    rows_by_name = {row.check_name: row for row in rows}
    assert controls_manifest_row(manifest).serial_value == "provided"
    assert rows_by_name["positive_control_pass_fraction"].status == "pass"
    assert rows_by_name["positive_control_pass_fraction"].serial_value == "1.000"
    assert rows_by_name["decoy_coherent_seed_count"].status == "pass"
    assert rows_by_name["decoy_coherent_seed_count"].serial_value == "0"
    assert rows_by_name["decoy_correctly_rejected_count"].serial_value == "1/1"


def test_controls_rows_fail_when_decoy_reaches_coherent_seed(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "controls.reviewed.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "IDC-1\tidentity_decoy\tfalse\tassessed\tdecoy_seed_gate_coherent\n"
    )

    rows = control_method_rows(
        _write_controls_tsv(tmp_path / "serial" / "controls.tsv", controls),
        _write_controls_tsv(tmp_path / "process" / "controls.tsv", controls),
        controls_manifest=manifest,
        controls_parity_pass=True,
    )

    rows_by_name = {row.check_name: row for row in rows}
    assert rows_by_name["decoy_coherent_seed_count"].status == "fail"
    assert rows_by_name["decoy_coherent_seed_count"].serial_value == "1"


def test_controls_rows_do_not_interpret_when_controls_parity_fails(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "controls.reviewed.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")

    rows = control_method_rows(
        _write_controls_tsv(
            tmp_path / "serial" / "controls.tsv",
            "IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
        ),
        _write_controls_tsv(
            tmp_path / "process" / "controls.tsv",
            "IDC-1\tidentity_decoy\tfalse\tassessed\tdecoy_seed_gate_coherent\n",
        ),
        controls_manifest=manifest,
        controls_parity_pass=False,
    )

    rows_by_name = {row.check_name: row for row in rows}
    assert rows_by_name["decoy_coherent_seed_count"].status == "fail"
    assert rows_by_name["decoy_coherent_seed_count"].serial_value == "not_assessed"
    assert rows_by_name["decoy_coherent_seed_count"].process_value == "not_assessed"


def test_merge_method_row_preserves_process_process_value() -> None:
    merged = merge_method_row(
        ValidationRow("decoy_correctly_rejected_count", "pass", "3/3", "3/3", "s"),
        ValidationRow("decoy_correctly_rejected_count", "pass", "2/3", "2/3", "p"),
    )

    assert merged.serial_value == "3/3"
    assert merged.process_value == "2/3"
