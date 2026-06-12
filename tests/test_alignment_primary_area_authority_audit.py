import csv
import sys
from pathlib import Path

from tools.diagnostics import alignment_primary_area_authority_audit as audit
from tools.diagnostics.alignment_primary_area_authority_audit import (
    summarize_primary_area_authority,
)


def test_primary_area_authority_audit_counts_fail_closed_and_leaked_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "alignment_cells.tsv"
    _write_cells(
        path,
        [
            _row(
                "FAM1",
                "S1",
                area="100",
                primary_matrix_area="90",
                primary_matrix_area_source="gaussian15_positive_asls_residual",
            ),
            _row(
                "FAM1",
                "S2",
                area="100",
                primary_matrix_area="",
                primary_matrix_area_reason="missing_ms1_morphology_area",
            ),
            _row(
                "FAM1",
                "S3",
                area="100",
                primary_matrix_area="95",
                primary_matrix_area_source="asls_baseline_corrected",
            ),
        ],
    )

    summary = summarize_primary_area_authority(path)

    assert summary["alignment_cell_count"] == 3
    assert summary["gaussian_primary_area_count"] == 1
    assert summary["fail_closed_missing_morphology_count"] == 1
    assert summary["non_gaussian_primary_area_count"] == 1
    assert summary["gate_decision"] == "fail"


def test_primary_area_authority_audit_fails_non_gaussian_nonblank_primary_area(
    tmp_path: Path,
) -> None:
    path = tmp_path / "alignment_cells.tsv"
    _write_cells(
        path,
        [
            _row(
                "FAM1",
                "S1",
                primary_matrix_area="0",
                primary_matrix_area_source="asls_baseline_corrected",
            ),
            _row(
                "FAM1",
                "S2",
                primary_matrix_area="-10",
                primary_matrix_area_source="raw_area",
            ),
            _row(
                "FAM1",
                "S3",
                primary_matrix_area="not-a-number",
                primary_matrix_area_source="legacy_scalar_area",
            ),
        ],
    )

    summary = summarize_primary_area_authority(path)

    assert summary["non_gaussian_primary_area_count"] == 3
    assert summary["gate_decision"] == "fail"


def test_primary_area_authority_audit_defers_missing_morphology_without_legacy_area(
    tmp_path: Path,
) -> None:
    path = tmp_path / "alignment_cells.tsv"
    _write_cells(
        path,
        [
            _row(
                "FAM1",
                "S1",
                area="",
                primary_matrix_area="",
                primary_matrix_area_reason="missing_ms1_morphology_area",
            ),
            _row(
                "FAM1",
                "S2",
                area="0",
                primary_matrix_area="",
                primary_matrix_area_reason="missing_ms1_morphology_area",
            ),
        ],
    )

    summary = summarize_primary_area_authority(path)

    assert summary["fail_closed_missing_morphology_count"] == 2
    assert summary["gate_decision"] == "defer"


def test_primary_area_authority_cli_reads_cells_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    _write_cells(
        path,
        [
            _row(
                "FAM1",
                "S1",
                area="100",
                primary_matrix_area="90",
                primary_matrix_area_source="gaussian15_positive_asls_residual",
            ),
            _row(
                "FAM1",
                "S2",
                primary_matrix_area="10",
                primary_matrix_area_source="legacy_scalar_area",
            ),
        ],
    )
    read_paths: list[Path] = []
    original_read = audit.read_tsv_required

    def counted_read(path_arg: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
        read_paths.append(path_arg)
        return original_read(path_arg, columns)

    monkeypatch.setattr(audit, "read_tsv_required", counted_read)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alignment_primary_area_authority_audit.py",
            "--alignment-cells-tsv",
            str(path),
            "--output-dir",
            str(output_dir),
        ],
    )

    audit.main()

    assert read_paths == [path]
    assert (output_dir / "alignment_primary_area_authority_summary.tsv").exists()
    flagged_rows = _read_tsv(output_dir / "alignment_primary_area_authority_rows.tsv")
    assert flagged_rows[0]["authority_class"] == "non_gaussian_primary_area"


def _row(
    family_id: str,
    sample: str,
    *,
    area: str = "",
    primary_matrix_area: str = "",
    primary_matrix_area_source: str = "",
    primary_matrix_area_reason: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": "detected",
        "area": area,
        "primary_matrix_area": primary_matrix_area,
        "primary_matrix_area_source": primary_matrix_area_source,
        "primary_matrix_area_reason": primary_matrix_area_reason,
    }


def _write_cells(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
