from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics import analyze_matrix_identity_blast_radius as blast


def test_blast_radius_reports_complete_identity_changes_and_benchmark_join(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_run(
        tmp_path / "alignment",
        review_rows=[
            _review_row("FAM001", "TRUE", "single_sample_local_owner"),
            _review_row("FAM002", "TRUE", "owner_complete_link;owner_count=2"),
        ],
        cell_rows=[
            _cell_row("FAM001", "sample-a", "detected", 100.0),
            _cell_row("FAM001", "sample-b", "rescued", 90.0),
            _cell_row("FAM002", "sample-a", "detected", 100.0),
            _cell_row("FAM002", "sample-b", "detected", 90.0),
        ],
    )
    benchmark_dir = _write_benchmark_dir(tmp_path / "benchmark", "FAM002")

    code = blast.main(
        [
            "--alignment-run",
            str(alignment_dir),
            "--benchmark-dir",
            str(benchmark_dir),
            "--output-dir",
            str(tmp_path / "blast"),
            "--require-targeted-benchmark",
        ],
    )

    assert code == 0
    rows = _read_tsv(tmp_path / "blast" / "matrix_identity_blast_radius.tsv")
    by_id = {row["feature_family_id"]: row for row in rows}
    assert by_id["FAM001"]["evidence_status"] == "complete"
    assert by_id["FAM001"]["would_change_to_audit"] == "TRUE"
    assert by_id["FAM001"]["identity_decision"] == "audit_family"
    assert by_id["FAM002"]["targeted_target_name"] == "d3-5-medC"
    assert by_id["FAM002"]["active_dna_istd_candidate"] == "TRUE"
    payload = json.loads(
        (tmp_path / "blast" / "matrix_identity_blast_radius.json").read_text(
            encoding="utf-8",
        ),
    )
    assert payload["evidence_status"] == "complete"
    assert payload["would_change_to_audit_count"] == 1


def test_blast_radius_missing_peak_columns_outputs_incomplete_summary(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        [_review_row("FAM001", "TRUE", "single_sample_local_owner")],
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "sample-a",
                "status": "detected",
            },
        ],
    )
    _write_tsv(
        alignment_dir / "alignment_matrix.tsv",
        [{"feature_family_id": "FAM001", "sample-a": "100"}],
    )
    benchmark_dir = _write_benchmark_dir(tmp_path / "benchmark", "FAM001")

    code = blast.main(
        [
            "--alignment-run",
            str(alignment_dir),
            "--benchmark-dir",
            str(benchmark_dir),
            "--output-dir",
            str(tmp_path / "blast"),
            "--require-targeted-benchmark",
            "--allow-incomplete-summary",
        ],
    )

    assert code == 0
    rows = _read_tsv(tmp_path / "blast" / "matrix_identity_blast_radius.tsv")
    assert rows[0]["evidence_status"] == "evidence_incomplete"
    assert "alignment_cells.tsv:area" in rows[0]["missing_required_columns"]
    assert "alignment_cells.tsv:peak_start_rt" in rows[0]["missing_required_columns"]


def test_blast_radius_requires_targeted_benchmark_when_enabled(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_run(
        tmp_path / "alignment",
        review_rows=[
            _review_row("FAM001", "TRUE", "owner_complete_link;owner_count=2"),
        ],
        cell_rows=[
            _cell_row("FAM001", "sample-a", "detected", 100.0),
            _cell_row("FAM001", "sample-b", "detected", 90.0),
        ],
    )

    code = blast.main(
        [
            "--alignment-run",
            str(alignment_dir),
            "--benchmark-dir",
            str(tmp_path / "missing-benchmark"),
            "--output-dir",
            str(tmp_path / "blast"),
            "--require-targeted-benchmark",
        ],
    )

    assert code == 2


def _write_alignment_run(
    path: Path,
    *,
    review_rows: list[dict[str, object]],
    cell_rows: list[dict[str, object]],
) -> Path:
    path.mkdir(parents=True)
    _write_tsv(path / "alignment_review.tsv", review_rows)
    _write_tsv(path / "alignment_cells.tsv", cell_rows)
    _write_tsv(path / "alignment_matrix.tsv", [{"feature_family_id": "FAM001"}])
    return path


def _review_row(
    family_id: str,
    include: str,
    evidence: str,
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "include_in_primary_matrix": include,
        "family_evidence": evidence,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": 500.0,
        "family_center_rt": 8.5,
        "has_anchor": "TRUE",
    }


def _cell_row(
    family_id: str,
    sample: str,
    status: str,
    area: float,
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": status,
        "area": area,
        "apex_rt": 8.5,
        "height": 100.0,
        "peak_start_rt": 8.4,
        "peak_end_rt": 8.6,
        "rt_delta_sec": 0.0,
        "reason": status,
    }


def _write_benchmark_dir(path: Path, family_id: str) -> Path:
    path.mkdir(parents=True)
    benchmark_rows = [
        {
            "target_name": "d3-5-medC",
            "role": "ISTD",
            "benchmark_class": "PASS",
            "feature_family_id": family_id,
            "active_dna_istd_candidate": "TRUE",
        },
    ]
    _write_tsv(path / "targeted_istd_benchmark_matches.tsv", benchmark_rows)
    _write_tsv(path / "targeted_istd_benchmark_summary.tsv", benchmark_rows)
    (path / "targeted_istd_benchmark.json").write_text(
        json.dumps({"overall_status": "PASS"}),
        encoding="utf-8",
    )
    return path


def _write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
