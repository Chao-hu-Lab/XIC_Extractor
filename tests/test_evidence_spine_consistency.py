import csv
from pathlib import Path

import pytest

from tools.diagnostics import evidence_spine_consistency as report


def test_evidence_spine_consistency_matches_shared_semantics(tmp_path: Path) -> None:
    targeted_dir = tmp_path / "targeted"
    alignment_dir = tmp_path / "alignment"
    targeted_dir.mkdir()
    alignment_dir.mkdir()
    _write_tsv(
        targeted_dir / "peak_candidates.tsv",
        [
            {
                "sample_name": "sample-a",
                "target_label": "15N5-8-oxodG",
                "role": "ISTD",
                "candidate_id": "sample-a|15N5-8-oxodG|0",
                "selected": "TRUE",
                "rt_apex_min": "25.0",
                "rt_left_min": "24.9",
                "rt_right_min": "25.1",
                "area_raw_counts_seconds": "1000",
                "area_baseline_corrected": "950",
                "region_scan_count": "5",
            },
        ],
        fields=(
            "sample_name",
            "target_label",
            "role",
            "candidate_id",
            "selected",
            "rt_apex_min",
            "rt_left_min",
            "rt_right_min",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "region_scan_count",
        ),
    )
    _write_tsv(
        targeted_dir / "peak_candidate_boundaries.tsv",
        [
            {
                "sample_name": "sample-a",
                "target_label": "15N5-8-oxodG",
                "candidate_id": "sample-a|15N5-8-oxodG|0",
                "target_mz": "289.0841",
            },
        ],
        fields=("sample_name", "target_label", "candidate_id", "target_mz"),
    )
    _write_tsv(
        targeted_dir / "peak_region_selection_shadow_summary.tsv",
        [
            {
                "sample_name": "sample-a",
                "target_label": "15N5-8-oxodG",
                "shadow_verdict": "current_supported",
                "local_mixture_diagnostic": "current_single_envelope",
            },
        ],
        fields=(
            "sample_name",
            "target_label",
            "shadow_verdict",
            "local_mixture_diagnostic",
        ),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            {
                "sample_stem": "sample-a",
                "feature_family_id": "FAM000001",
                "status": "detected",
                "area": "1100",
                "apex_rt": "25.02",
                "peak_start_rt": "24.91",
                "peak_end_rt": "25.09",
                "family_center_mz": "289.0842",
                "region_shadow_verdict": "current_supported",
                "region_local_mixture_diagnostic": "current_single_envelope",
            },
        ],
        fields=(
            "sample_stem",
            "feature_family_id",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "family_center_mz",
            "region_shadow_verdict",
            "region_local_mixture_diagnostic",
        ),
    )

    outputs, result = report.run_evidence_spine_consistency(
        targeted_dir=targeted_dir,
        alignment_dir=alignment_dir,
        output_dir=tmp_path / "out",
    )

    assert outputs.rows_tsv.is_file()
    assert result.summary.rows_checked == 1
    assert result.summary.consistent_rows == 1
    row = result.rows[0]
    assert row.untargeted_family_id == "FAM000001"
    assert row.mismatch_reason == "consistent"
    assert row.baseline_corrected_area_available is True


def test_evidence_spine_consistency_reports_missing_alignment(tmp_path: Path) -> None:
    targeted_dir = tmp_path / "targeted"
    alignment_dir = tmp_path / "alignment"
    targeted_dir.mkdir()
    alignment_dir.mkdir()
    _write_minimal_targeted(targeted_dir, mz="289.0841")
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            {
                "sample_stem": "sample-a",
                "feature_family_id": "FAM000002",
                "status": "detected",
                "area": "1100",
                "apex_rt": "28.0",
                "peak_start_rt": "27.9",
                "peak_end_rt": "28.1",
                "family_center_mz": "300.0",
                "region_shadow_verdict": "current_supported",
                "region_local_mixture_diagnostic": "current_single_envelope",
            },
        ],
        fields=(
            "sample_stem",
            "feature_family_id",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "family_center_mz",
            "region_shadow_verdict",
            "region_local_mixture_diagnostic",
        ),
    )

    _outputs, result = report.run_evidence_spine_consistency(
        targeted_dir=targeted_dir,
        alignment_dir=alignment_dir,
        output_dir=tmp_path / "out",
    )

    assert result.summary.missing_alignment_rows == 1
    assert "no_alignment_mz_rt_match" in result.rows[0].mismatch_reason


def test_evidence_spine_consistency_fails_on_missing_columns(tmp_path: Path) -> None:
    targeted_dir = tmp_path / "targeted"
    alignment_dir = tmp_path / "alignment"
    targeted_dir.mkdir()
    alignment_dir.mkdir()
    (targeted_dir / "peak_candidates.tsv").write_text(
        "sample_name\ttarget_label\nsample-a\t15N5-8-oxodG\n",
        encoding="utf-8",
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [],
        fields=(
            "sample_stem",
            "feature_family_id",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "family_center_mz",
            "region_shadow_verdict",
            "region_local_mixture_diagnostic",
        ),
    )

    with pytest.raises(ValueError, match="missing required columns"):
        report.run_evidence_spine_consistency(
            targeted_dir=targeted_dir,
            alignment_dir=alignment_dir,
            output_dir=tmp_path / "out",
        )


def _write_minimal_targeted(targeted_dir: Path, *, mz: str) -> None:
    _write_tsv(
        targeted_dir / "peak_candidates.tsv",
        [
            {
                "sample_name": "sample-a",
                "target_label": "15N5-8-oxodG",
                "role": "ISTD",
                "candidate_id": "sample-a|15N5-8-oxodG|0",
                "selected": "TRUE",
                "rt_apex_min": "25.0",
                "rt_left_min": "24.9",
                "rt_right_min": "25.1",
                "area_raw_counts_seconds": "1000",
                "area_baseline_corrected": "",
                "region_scan_count": "5",
            },
        ],
        fields=(
            "sample_name",
            "target_label",
            "role",
            "candidate_id",
            "selected",
            "rt_apex_min",
            "rt_left_min",
            "rt_right_min",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "region_scan_count",
        ),
    )
    _write_tsv(
        targeted_dir / "peak_candidate_boundaries.tsv",
        [
            {
                "sample_name": "sample-a",
                "target_label": "15N5-8-oxodG",
                "candidate_id": "sample-a|15N5-8-oxodG|0",
                "target_mz": mz,
            },
        ],
        fields=("sample_name", "target_label", "candidate_id", "target_mz"),
    )
    _write_tsv(
        targeted_dir / "peak_region_selection_shadow_summary.tsv",
        [],
        fields=(
            "sample_name",
            "target_label",
            "shadow_verdict",
            "local_mixture_diagnostic",
        ),
    )


def _write_tsv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fields: tuple[str, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
