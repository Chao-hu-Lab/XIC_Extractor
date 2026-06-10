from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics import shift_aware_backfill_calibration_pack as pack


def test_build_calibration_rows_selects_high_similarity_cases(tmp_path: Path) -> None:
    shift_summary = tmp_path / "shift_summary.tsv"
    _write_tsv(
        shift_summary,
        [
            {
                "feature_family_id": "FAM002",
                "nonref_source_families": "FAM002A",
                "nonref_group_count": "1",
                "min_shape_r_after_best_shift": "0.9100",
                "max_shape_r_after_best_shift": "0.9200",
                "max_abs_shift_sec": "6.00",
            },
            {
                "feature_family_id": "FAM001",
                "nonref_source_families": "FAM001A;FAM001B",
                "nonref_group_count": "2",
                "min_shape_r_after_best_shift": "0.9830",
                "max_shape_r_after_best_shift": "0.9910",
                "max_abs_shift_sec": "2.40",
            },
        ],
    )
    groups = tmp_path / "groups.tsv"
    _write_tsv(
        groups,
        [
            {
                "feature_family_id": "FAM001",
                "product_behavior_state": "product_rescued_context_only",
                "evidence_authority_state": "review_only_visual_support",
                "reconciliation_class": "product_rejects_but_visual_supports",
                "detected_cell_count": "2",
                "rescued_cell_count": "83",
                "top_support_component": (
                    "shift_aware_same_pattern_support_review_only"
                ),
                "top_blocker": "",
                "missing_evidence": "",
            },
            {
                "feature_family_id": "FAM002",
                "product_behavior_state": "product_rescued_context_only",
                "evidence_authority_state": "evidence_blocks_backfill",
                "reconciliation_class": "product_rejects_and_evidence_blocks",
                "detected_cell_count": "2",
                "rescued_cell_count": "10",
                "top_support_component": "",
                "top_blocker": "neighboring_ms1_review",
                "missing_evidence": "",
            },
        ],
    )
    overlays = tmp_path / "overlay.tsv"
    _write_tsv(
        overlays,
        [
            {
                "feature_family_id": "FAM001",
                "family_verdict": "review_required_neighboring_ms1_interference",
                "png_path": str(tmp_path / "fam001_context.png"),
                "shape_supported_fraction": "0.5",
                "absolute_own_max_shape_supported_fraction": "0.9",
                "absolute_trace_apex_cluster_fraction": "0.8",
            },
        ],
    )
    shift_output_dir = tmp_path / "shift"
    shift_output_dir.mkdir()
    best_png = (
        shift_output_dir
        / "001_fam001_shift_aware_source_family_best_shift_alignment.png"
    )
    best_tsv = (
        shift_output_dir
        / "001_fam001_shift_aware_source_family_best_shift_summary.tsv"
    )
    best_png.write_bytes(b"png")
    best_tsv.write_text("feature_family_id\nFAM001\n", encoding="utf-8")

    rows = pack.build_calibration_rows(
        shift_aware_summary_tsv=shift_summary,
        reconciliation_groups_tsv=groups,
        overlay_batch_summary_tsv=overlays,
        shift_aware_output_dir=shift_output_dir,
        reconciliation_gallery_html=tmp_path / "gallery.html",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["feature_family_id"] == "FAM001"
    assert row["review_rank"] == "1"
    assert row["machine_shift_aware_call"] == (
        "shift_aware_same_pattern_support_review_only"
    )
    assert row["manual_same_peak_call"] == ""
    assert row["manual_standard_peak_call"] == ""
    assert row["manual_backfill_authority_call"] == ""
    assert row["shift_best_alignment_png_path"] == str(best_png)
    assert row["shift_best_summary_tsv_path"] == str(best_tsv)


def test_cli_writes_manual_review_tsv_and_html(tmp_path: Path) -> None:
    shift_summary = tmp_path / "shift_summary.tsv"
    _write_tsv(
        shift_summary,
        [
            {
                "feature_family_id": "FAM001",
                "nonref_source_families": "FAM001A",
                "nonref_group_count": "1",
                "min_shape_r_after_best_shift": "0.9900",
                "max_shape_r_after_best_shift": "0.9900",
                "max_abs_shift_sec": "1.20",
            },
        ],
    )
    groups = tmp_path / "groups.tsv"
    _write_tsv(
        groups,
        [
            {
                "feature_family_id": "FAM001",
                "product_behavior_state": "product_rescued_context_only",
                "evidence_authority_state": "review_only_visual_support",
                "reconciliation_class": "product_rejects_but_visual_supports",
                "detected_cell_count": "2",
                "rescued_cell_count": "83",
                "top_support_component": (
                    "shift_aware_same_pattern_support_review_only"
                ),
                "top_blocker": "",
                "missing_evidence": "",
            },
        ],
    )
    overlays = tmp_path / "overlay.tsv"
    _write_tsv(
        overlays,
        [
            {
                "feature_family_id": "FAM001",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "png_path": str(tmp_path / "fam001.png"),
                "shape_supported_fraction": "1",
                "absolute_own_max_shape_supported_fraction": "1",
                "absolute_trace_apex_cluster_fraction": "1",
            },
        ],
    )
    shift_output_dir = tmp_path / "shift"
    shift_output_dir.mkdir()
    (
        shift_output_dir
        / "001_fam001_shift_aware_source_family_best_shift_alignment.png"
    ).write_bytes(
        b"png",
    )
    output_dir = tmp_path / "out"

    assert (
        pack.main(
            [
                "--shift-aware-summary-tsv",
                str(shift_summary),
                "--reconciliation-groups-tsv",
                str(groups),
                "--overlay-batch-summary-tsv",
                str(overlays),
                "--shift-aware-output-dir",
                str(shift_output_dir),
                "--reconciliation-gallery-html",
                str(tmp_path / "gallery.html"),
                "--output-dir",
                str(output_dir),
            ],
        )
        == 0
    )

    tsv = output_dir / "shift_aware_backfill_calibration_pack.tsv"
    html = output_dir / "shift_aware_backfill_calibration_pack.html"
    assert tsv.exists()
    assert html.exists()
    content = tsv.read_text(encoding="utf-8")
    assert "manual_same_peak_call" in content
    assert "manual_standard_peak_call" in content
    assert "shift_aware_same_pattern_support_review_only" in content
    assert "Shift-aware same-pattern calibration" in html.read_text(encoding="utf-8")


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    assert rows
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(rows[0]),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
