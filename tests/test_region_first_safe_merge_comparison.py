from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.diagnostics import region_first_safe_merge_comparison as comparison


def test_comparison_reports_changed_safe_merge_rows(tmp_path: Path) -> None:
    default_dir = tmp_path / "default"
    safe_dir = tmp_path / "safe"
    output_dir = tmp_path / "comparison"
    targets_csv = tmp_path / "targets.csv"
    _write_targets(targets_csv)
    _write_results(
        default_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1000.00",
                "d3-N6-medA_PeakStart": "25.70",
                "d3-N6-medA_PeakEnd": "25.80",
                "d3-N6-medA_NL": "OK",
                "5-medC_RT": "12.30",
                "5-medC_Area": "2000.00",
                "5-medC_PeakStart": "12.20",
                "5-medC_PeakEnd": "12.40",
                "5-medC_NL": "OK",
            }
        ],
    )
    _write_results(
        safe_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1120.00",
                "d3-N6-medA_PeakStart": "25.65",
                "d3-N6-medA_PeakEnd": "26.10",
                "d3-N6-medA_NL": "OK",
                "5-medC_RT": "12.30",
                "5-medC_Area": "2000.00",
                "5-medC_PeakStart": "12.20",
                "5-medC_PeakEnd": "12.40",
                "5-medC_NL": "OK",
            }
        ],
    )
    _write_candidates(
        safe_dir / "peak_candidates.tsv",
        [
            {
                "sample_name": "S1",
                "target_label": "d3-N6-medA",
                "target_mz": "269.13390",
                "role": "ISTD",
                "selected": "TRUE",
                "merge_note": (
                    "region_first_safe_merge;"
                    "adjacent_wis_local_minimum_merge"
                ),
            }
        ],
    )
    _write_shadow_summary(
        safe_dir / "peak_region_selection_shadow_summary.tsv",
        [
            {
                "sample_name": "S1",
                "target_label": "d3-N6-medA",
                "shadow_verdict": "merge_suggested",
                "merge_suggestion_source": "adjacent_wis_local_minimum_merge",
                "selected_interval_count": "2",
                "selected_interval_gap_max_min": "0.041",
            }
        ],
    )

    outputs = comparison.run_region_first_safe_merge_comparison(
        default_dir=default_dir,
        safe_merge_dir=safe_dir,
        targets_csv=targets_csv,
        output_dir=output_dir,
    )

    rows = _read_tsv(outputs.comparison_tsv)
    assert rows == [
        {
            "sample_name": "S1",
            "target_label": "d3-N6-medA",
            "target_mz": "269.13390",
            "is_istd": "TRUE",
            "default_rt_min": "25.74",
            "safe_merge_rt_min": "25.74",
            "rt_delta_min": "0.00000",
            "default_area": "1000.00",
            "safe_merge_area": "1120.00",
            "area_ratio": "1.12000",
            "default_peak_start": "25.70",
            "safe_merge_peak_start": "25.65",
            "default_peak_end": "25.80",
            "safe_merge_peak_end": "26.10",
            "default_nl": "OK",
            "safe_merge_nl": "OK",
            "promotion_reason": "region_first_safe_merge",
            "safe_merge_note": (
                "region_first_safe_merge;"
                "adjacent_wis_local_minimum_merge"
            ),
            "shadow_verdict": "merge_suggested",
            "merge_suggestion_source": "adjacent_wis_local_minimum_merge",
            "selected_interval_count": "2",
            "selected_interval_gap_max_min": "0.041",
        }
    ]
    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["compared_rows"] == "2"
    assert summary["changed_rows"] == "1"
    assert summary["promoted_rows"] == "1"
    assert summary["changed_istd_rows"] == "1"
    assert summary["affected_target_labels"] == "d3-N6-medA"
    assert summary["area_ratio_median"] == "1.12000"
    assert "d3-N6-medA" in outputs.markdown.read_text(encoding="utf-8")


def test_comparison_prefers_persisted_promotion_source_over_post_merge_shadow(
    tmp_path: Path,
) -> None:
    default_dir = tmp_path / "default"
    safe_dir = tmp_path / "safe"
    output_dir = tmp_path / "comparison"
    targets_csv = tmp_path / "targets.csv"
    _write_targets(targets_csv)
    _write_results(
        default_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1000.00",
                "d3-N6-medA_PeakStart": "25.70",
                "d3-N6-medA_PeakEnd": "25.80",
                "d3-N6-medA_NL": "OK",
            }
        ],
    )
    _write_results(
        safe_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1120.00",
                "d3-N6-medA_PeakStart": "25.65",
                "d3-N6-medA_PeakEnd": "26.10",
                "d3-N6-medA_NL": "OK",
            }
        ],
    )
    _write_candidates(
        safe_dir / "peak_candidates.tsv",
        [
            {
                "sample_name": "S1",
                "target_label": "d3-N6-medA",
                "target_mz": "269.13390",
                "role": "ISTD",
                "selected": "TRUE",
                "merge_note": (
                    "region_first_safe_merge;"
                    "adjacent_wis_local_minimum_merge"
                ),
            }
        ],
    )
    _write_shadow_summary(
        safe_dir / "peak_region_selection_shadow_summary.tsv",
        [
            {
                "sample_name": "S1",
                "target_label": "d3-N6-medA",
                "shadow_verdict": "split_supported",
                "merge_suggestion_source": "",
                "selected_interval_count": "3",
                "selected_interval_gap_max_min": "0.090",
            }
        ],
    )

    outputs = comparison.run_region_first_safe_merge_comparison(
        default_dir=default_dir,
        safe_merge_dir=safe_dir,
        targets_csv=targets_csv,
        output_dir=output_dir,
    )

    row = _read_tsv(outputs.comparison_tsv)[0]
    assert row["shadow_verdict"] == "split_supported"
    assert row["merge_suggestion_source"] == "adjacent_wis_local_minimum_merge"


def test_comparison_fails_clearly_for_missing_required_columns(
    tmp_path: Path,
) -> None:
    default_dir = tmp_path / "default"
    safe_dir = tmp_path / "safe"
    default_dir.mkdir()
    safe_dir.mkdir()
    targets_csv = tmp_path / "targets.csv"
    _write_targets(targets_csv)
    (default_dir / "xic_results.csv").write_text("bad\n1\n", encoding="utf-8")
    (safe_dir / "xic_results.csv").write_text("SampleName\nS1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SampleName"):
        comparison.run_region_first_safe_merge_comparison(
            default_dir=default_dir,
            safe_merge_dir=safe_dir,
            targets_csv=targets_csv,
            output_dir=tmp_path / "out",
        )


def test_comparison_counts_only_rows_present_in_both_runs(tmp_path: Path) -> None:
    default_dir = tmp_path / "default"
    safe_dir = tmp_path / "safe"
    output_dir = tmp_path / "comparison"
    targets_csv = tmp_path / "targets.csv"
    _write_targets(targets_csv)
    _write_results(
        default_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1000.00",
                "d3-N6-medA_PeakStart": "25.70",
                "d3-N6-medA_PeakEnd": "25.80",
                "d3-N6-medA_NL": "OK",
            }
        ],
    )
    _write_results(
        safe_dir / "xic_results.csv",
        [
            {
                "SampleName": "S1",
                "d3-N6-medA_RT": "25.74",
                "d3-N6-medA_Area": "1000.00",
                "d3-N6-medA_PeakStart": "25.70",
                "d3-N6-medA_PeakEnd": "25.80",
                "d3-N6-medA_NL": "OK",
            },
            {
                "SampleName": "S2",
                "d3-N6-medA_RT": "25.75",
                "d3-N6-medA_Area": "1100.00",
                "d3-N6-medA_PeakStart": "25.70",
                "d3-N6-medA_PeakEnd": "25.82",
                "d3-N6-medA_NL": "OK",
            },
        ],
    )

    outputs = comparison.run_region_first_safe_merge_comparison(
        default_dir=default_dir,
        safe_merge_dir=safe_dir,
        targets_csv=targets_csv,
        output_dir=output_dir,
    )

    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["compared_rows"] == "1"
    assert summary["changed_rows"] == "0"


def _write_targets(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["label", "mz", "is_istd"], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow({"label": "d3-N6-medA", "mz": "269.13390", "is_istd": "TRUE"})
        writer.writerow({"label": "5-medC", "mz": "242.11360", "is_istd": "FALSE"})


def _write_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_candidates(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "sample_name",
        "target_label",
        "target_mz",
        "role",
        "selected",
        "merge_note",
    ]
    _write_tsv(path, fieldnames, rows)


def _write_shadow_summary(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "sample_name",
        "target_label",
        "shadow_verdict",
        "merge_suggestion_source",
        "selected_interval_count",
        "selected_interval_gap_max_min",
    ]
    _write_tsv(path, fieldnames, rows)


def _write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
