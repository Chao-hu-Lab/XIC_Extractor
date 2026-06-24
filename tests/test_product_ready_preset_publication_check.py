from __future__ import annotations

import json
from pathlib import Path

from xic_extractor.diagnostics.product_ready_preset_publication_check import (
    check_product_ready_preset_publication,
)
from xic_extractor.tabular_io import file_sha256


def test_product_ready_preset_publication_check_passes_current_run_manifest(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(tmp_path)

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "pass"
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["matrix_cells_written"] == "2"
    assert summary["product_surface_changed"] == "TRUE"


def test_product_ready_preset_publication_check_rejects_fixed_replay_dir(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(tmp_path)
    (alignment_dir / "backfill_expansion_productization_preset").mkdir()

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "fail"
    checks = outputs.checks_tsv.read_text(encoding="utf-8")
    assert "no_fixed_backfill_expansion_replay\tfail" in checks


def test_product_ready_preset_publication_check_requires_manifest_when_queue_exists(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(tmp_path, write_manifest=False)

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "fail"
    checks = outputs.checks_tsv.read_text(encoding="utf-8")
    assert "default_matrix_manifest_presence\tfail" in checks


def test_product_ready_preset_publication_check_allows_noop_no_queue_run(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(
        tmp_path,
        write_manifest=False,
        review_queue_row_count="0",
        matrix_cells_written="",
    )

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "pass"
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["product_surface_changed"] == "FALSE"


def test_product_ready_preset_publication_check_rejects_mismatched_manifest(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(tmp_path)
    manifest_path = alignment_dir / "standard_peak_default_matrix_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["matrix_cells_written"] = "1"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "fail"
    checks = outputs.checks_tsv.read_text(encoding="utf-8")
    assert (
        "default_matrix_manifest_matrix_cells_written_matches_summary\tfail"
        in checks
    )


def test_product_ready_preset_publication_check_rejects_stale_published_matrix(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_publication_artifacts(tmp_path)
    (alignment_dir / "alignment_matrix.tsv").write_text(
        "Mz\tRT\tS1\n1\t2\t999\n",
        encoding="utf-8",
    )

    outputs = check_product_ready_preset_publication(alignment_dir=alignment_dir)

    assert outputs.status == "fail"
    checks = outputs.checks_tsv.read_text(encoding="utf-8")
    assert (
        "default_matrix_manifest_published_alignment_matrix_sha256_matches\tfail"
        in checks
    )


def _write_publication_artifacts(
    root: Path,
    *,
    write_manifest: bool = True,
    review_queue_row_count: str = "3",
    matrix_cells_written: str = "2",
) -> Path:
    alignment_dir = root / "alignment"
    summary_dir = alignment_dir / "standard_peak_backfill_preset"
    summary_dir.mkdir(parents=True)
    (alignment_dir / "alignment_matrix.tsv").write_text(
        "Mz\tRT\tS1\n",
        encoding="utf-8",
    )
    (alignment_dir / "alignment_matrix_identity.tsv").write_text(
        "Mz\tRT\tS1\n",
        encoding="utf-8",
    )
    source_run_id = (
        "alignment-preset:builtin:dna_dr_product_ready:standard-peak-backfill"
    )
    summary = {
        "status": "pass",
        "source_run_id": source_run_id,
        "review_queue_row_count": review_queue_row_count,
        "matrix_cells_written": matrix_cells_written,
    }
    (summary_dir / "standard_peak_backfill_preset_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    if write_manifest:
        matrix_tsv = alignment_dir / "alignment_matrix.tsv"
        identity_tsv = alignment_dir / "alignment_matrix_identity.tsv"
        manifest = {
            "status": "pass",
            "source_run_id": source_run_id,
            "coverage_status": "complete",
            "queue_row_count": review_queue_row_count,
            "missing_queue_rank_count": "0",
            "duplicate_queue_rank_count": "0",
            "matrix_cells_written": matrix_cells_written,
            "published_alignment_matrix_tsv": str(matrix_tsv),
            "published_alignment_matrix_identity_tsv": str(identity_tsv),
            "published_alignment_matrix_sha256": file_sha256(
                matrix_tsv,
                uppercase=False,
            ),
            "published_alignment_matrix_identity_sha256": file_sha256(
                identity_tsv,
                uppercase=False,
            ),
        }
        (alignment_dir / "standard_peak_default_matrix_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
    return alignment_dir
