from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.compare import (
    compare_identity_coherence_bundles,
)
from xic_extractor.alignment.identity_coherence_validation.models import (
    DiagnosticBundle,
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
    rows = {row.check_name: row for row in result.rows}
    assert rows["decisions_tsv_exact"].status == "pass"
    assert rows["controls_manifest_assessment"].status == "not_assessed"
    assert rows["controls_tsv_parity_only"].details.startswith(
        "controls file parity only",
    )


def test_compare_bundles_fails_when_row_order_changes(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows=(
            "ICD-1\twould_primary_provisional_identity_family_support\n"
            "ICD-2\tinsufficient_evidence\n"
        ),
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows=(
            "ICD-2\tinsufficient_evidence\n"
            "ICD-1\twould_primary_provisional_identity_family_support\n"
        ),
    )

    result = compare_identity_coherence_bundles(serial, process)

    rows = {row.check_name: row for row in result.rows}
    assert rows["decisions_tsv_exact"].status == "fail"
    assert rows["decisions_tsv_exact"].details.startswith("TSV differs")


def test_compare_bundles_fails_when_summary_missing(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    process.summary_md.unlink()

    result = compare_identity_coherence_bundles(serial, process)

    rows = {row.check_name: row for row in result.rows}
    assert rows["summary_md_presence"].status == "fail"
    assert rows["summary_md_presence"].serial_value == "true"
    assert rows["summary_md_presence"].process_value == "false"
