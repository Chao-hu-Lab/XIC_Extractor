import csv
import sys
from pathlib import Path

from tools.diagnostics import gaussian15_area_pressure_audit as audit
from tools.diagnostics.gaussian15_area_pressure_audit import (
    gaussian15_area_pressure_rows,
    summarize_gaussian15_area_pressure,
)


def test_gaussian15_area_pressure_audit_reports_area_and_scan_rate_pressure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "peak_candidates.tsv"
    _write_candidates(
        path,
        [
            _row(
                "S1",
                "5-medC",
                "c1",
                selected="TRUE",
                raw_area="100",
                morphology_area="90",
                scan_count="31",
                duration_min="0.5",
            ),
            _row(
                "S2",
                "8-oxodG",
                "c2",
                selected="TRUE",
                raw_area="100",
                morphology_area="260",
                scan_count="16",
                duration_min="1.0",
            ),
            _row(
                "S3",
                "8-oxo-Guo",
                "c3",
                raw_area="100",
                morphology_area="",
                scan_count="",
                duration_min="",
            ),
        ],
    )

    summary = summarize_gaussian15_area_pressure(path)
    rows = gaussian15_area_pressure_rows(path)

    assert summary["readiness_label"] == "diagnostic_pressure_test_surface"
    assert summary["product_action"] == "diagnostic_only_no_product_mutation"
    assert summary["candidate_row_count"] == 3
    assert summary["selected_candidate_count"] == 2
    assert summary["comparable_area_count"] == 2
    assert summary["large_area_delta_count"] == 1
    assert summary["selected_large_area_delta_count"] == 1
    assert summary["missing_gaussian_area_count"] == 1
    assert summary["fixed_window_wide_count"] == 1
    assert summary["median_gaussian_to_raw_ratio"] == 1.75

    assert rows[0]["gaussian_to_raw_area_ratio"] == 0.9
    assert rows[0]["area_pressure_class"] == "within_20pct"
    assert rows[0]["estimated_scan_interval_sec"] == 1.0
    assert rows[0]["estimated_gaussian15_window_sec"] == 15.0
    assert rows[0]["scan_rate_pressure_class"] == "nominal_observed"
    assert rows[1]["area_pressure_class"] == "large_delta"
    assert rows[1]["estimated_gaussian15_window_sec"] == 60.0
    assert rows[1]["scan_rate_pressure_class"] == "wide_fixed_point_window"
    assert rows[2]["area_pressure_class"] == "missing_gaussian_area"
    assert rows[2]["scan_rate_pressure_class"] == "unknown_scan_rate"


def test_gaussian15_area_pressure_cli_reads_candidates_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "peak_candidates.tsv"
    output_dir = tmp_path / "out"
    _write_candidates(
        path,
        [
            _row(
                "S1",
                "5-medC",
                "c1",
                selected="TRUE",
                raw_area="100",
                morphology_area="90",
                scan_count="31",
                duration_min="0.5",
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
            "gaussian15_area_pressure_audit.py",
            "--peak-candidates-tsv",
            str(path),
            "--output-dir",
            str(output_dir),
        ],
    )

    audit.main()

    assert read_paths == [path]
    assert (output_dir / "gaussian15_area_pressure_summary.tsv").exists()
    assert _read_tsv(output_dir / "gaussian15_area_pressure_rows.tsv")[0][
        "scan_rate_pressure_class"
    ] == "nominal_observed"


def _row(
    sample: str,
    target: str,
    candidate_id: str,
    *,
    selected: str = "FALSE",
    raw_area: str,
    morphology_area: str,
    scan_count: str,
    duration_min: str,
) -> dict[str, str]:
    return {
        "sample_name": sample,
        "target_label": target,
        "candidate_id": candidate_id,
        "selected": selected,
        "area_raw_counts_seconds": raw_area,
        "area_ms1_morphology": morphology_area,
        "ms1_morphology_area_source": "gaussian15_positive_asls_residual",
        "ms1_morphology_trace_method": "gaussian_15",
        "ms1_morphology_trace_window_points": "15",
        "ms1_morphology_trace_effective_points": "15",
        "region_scan_count": scan_count,
        "region_duration_min": duration_min,
    }


def _write_candidates(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
