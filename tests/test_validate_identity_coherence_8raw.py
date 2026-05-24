from __future__ import annotations

from pathlib import Path

from scripts.validate_identity_coherence_8raw import (
    DiagnosticBundle,
    compare_identity_coherence_bundles,
    read_tsv_rows,
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
