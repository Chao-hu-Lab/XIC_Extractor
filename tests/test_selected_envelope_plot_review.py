from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from tools.diagnostics import selected_envelope_plot_review as plot_review
from tools.diagnostics.selected_envelope_plot_review import (
    PLOT_INDEX_HEADERS,
    main,
    select_selected_envelope_plot_requests,
    selected_boundary_oracles_by_candidate_id,
    write_selected_envelope_boundary_plot,
)
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
)
from xic_extractor.peak_detection.selected_envelope_oracle import BoundaryOracle


def test_select_selected_envelope_plot_requests_prioritizes_boundary_risks() -> None:
    rows = [
        _diagnostic_row(
            sample_name="sample-low",
            target_label="8-oxodG",
            selected_candidate_id="candidate-low",
            row_boundary_decision="externalize",
            boundary_change_class="low_scan",
            area_delta_ratio="-0.54",
        ),
        _diagnostic_row(
            sample_name="sample-overmerge",
            target_label="8-oxo-Guo",
            selected_candidate_id="candidate-overmerge",
            row_boundary_decision="externalize",
            boundary_change_class="overmerge_rejected",
            area_delta_ratio="-0.18",
        ),
        _diagnostic_row(
            sample_name="sample-increase",
            target_label="dG-C8-MeIQx",
            selected_candidate_id="candidate-increase",
            row_boundary_decision="accept_candidate",
            boundary_change_class="flank_recovered",
            area_delta_ratio="0.56",
        ),
        _diagnostic_row(
            sample_name="sample-decrease",
            target_label="5-medC",
            selected_candidate_id="candidate-decrease",
            row_boundary_decision="accept_candidate",
            boundary_change_class="flank_recovered",
            area_delta_ratio="-0.04",
        ),
    ]

    requests = select_selected_envelope_plot_requests(
        rows,
        max_high_risk=1,
        max_accepted_increase=1,
        max_accepted_decrease=1,
    )

    assert [request.plot_group for request in requests] == [
        "high_risk_externalized",
        "accepted_area_increase",
        "accepted_area_decrease",
    ]
    assert requests[0].row["sample_name"] == "sample-low"
    assert requests[1].row["sample_name"] == "sample-increase"
    assert requests[2].row["sample_name"] == "sample-decrease"


def test_select_selected_envelope_plot_requests_skips_positive_decrease() -> None:
    rows = [
        _diagnostic_row(
            sample_name="sample-increase",
            selected_candidate_id="candidate-increase",
            row_boundary_decision="accept_candidate",
            area_delta_ratio="0.25",
        ),
    ]

    requests = select_selected_envelope_plot_requests(
        rows,
        max_high_risk=0,
        max_accepted_increase=0,
        max_accepted_decrease=2,
    )

    assert requests == ()


def test_write_selected_envelope_boundary_plot_writes_files(tmp_path: Path) -> None:
    row = _diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        row_boundary_decision="externalize",
        boundary_change_class="low_scan",
        area_delta_ratio="-0.50",
    )
    rt = np.linspace(10.0, 14.0, 41)
    baseline = np.full_like(rt, 10.0)
    intensity = baseline + 200.0 * np.exp(-((rt - 12.0) ** 2) / 0.08)
    png_path = tmp_path / "plot.png"
    pdf_path = tmp_path / "plot.pdf"

    write_selected_envelope_boundary_plot(
        png_path=png_path,
        pdf_path=pdf_path,
        row=row,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        plot_group="high_risk_externalized",
    )

    assert png_path.exists()
    assert pdf_path.exists()
    assert png_path.stat().st_size > 0
    assert pdf_path.stat().st_size > 0


def test_write_selected_envelope_boundary_plot_draws_oracle_overlay(
    tmp_path: Path,
) -> None:
    row = _diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        selected_candidate_id="candidate-001",
        row_boundary_decision="accept_candidate",
        boundary_change_class="flank_recovered",
    )
    oracle = BoundaryOracle(
        oracle_row_id="oracle-001",
        selected_candidate_id="candidate-001",
        oracle_status="expert_reviewed",
        oracle_source="manual_overlay",
        rt_start_min=11.85,
        rt_end_min=12.15,
        area_baseline_corrected=150.0,
        shape_class="clean_single_peak",
    )
    rt = np.linspace(10.0, 14.0, 41)
    baseline = np.full_like(rt, 10.0)
    intensity = baseline + 200.0 * np.exp(-((rt - 12.0) ** 2) / 0.08)
    png_path = tmp_path / "plot.png"
    pdf_path = tmp_path / "plot.pdf"

    write_selected_envelope_boundary_plot(
        png_path=png_path,
        pdf_path=pdf_path,
        row=row,
        boundary_oracle=oracle,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        plot_group="accepted_area_increase",
    )

    assert png_path.exists()
    assert pdf_path.exists()
    assert png_path.stat().st_size > 0
    assert pdf_path.stat().st_size > 0


def test_plot_review_gaussian15_overlay_residual_uses_weighted_kernel() -> None:
    baseline = np.zeros(31, dtype=float)
    intensity = np.zeros(31, dtype=float)
    intensity[15] = 100.0

    smoothed = plot_review.gaussian15_smoothed_residual(intensity, baseline)

    assert smoothed.shape == intensity.shape
    assert smoothed[15] > smoothed[14] > smoothed[10] > 0.0
    assert smoothed[15] < intensity[15]
    assert float(np.sum(smoothed)) == pytest.approx(float(np.sum(intensity)))


def test_boundary_oracle_lookup_rejects_duplicate_candidate_ids() -> None:
    oracle_a = BoundaryOracle(
        oracle_row_id="oracle-001",
        selected_candidate_id="candidate-001",
        oracle_status="expert_reviewed",
        oracle_source="manual_overlay",
        rt_start_min=11.85,
        rt_end_min=12.15,
        area_baseline_corrected=150.0,
        shape_class="clean_single_peak",
    )
    oracle_b = BoundaryOracle(
        oracle_row_id="oracle-002",
        selected_candidate_id="candidate-001",
        oracle_status="expert_reviewed",
        oracle_source="expert_overlay",
        rt_start_min=11.90,
        rt_end_min=12.10,
        area_baseline_corrected=148.0,
        shape_class="clean_single_peak",
    )

    with pytest.raises(ValueError, match="unique by selected_candidate_id"):
        selected_boundary_oracles_by_candidate_id((oracle_a, oracle_b))


def test_boundary_oracle_lookup_rejects_benchmark_controls_for_plot_overlay() -> None:
    oracle = BoundaryOracle(
        oracle_row_id="targeted-control-001",
        selected_candidate_id="candidate-001",
        oracle_status="benchmark_control_only",
        oracle_source="targeted_workbook_control",
        rt_start_min=11.85,
        rt_end_min=12.15,
        area_baseline_corrected=None,
        shape_class="clean_single_peak",
    )

    with pytest.raises(ValueError, match="expert_reviewed"):
        selected_boundary_oracles_by_candidate_id((oracle,))


def test_selected_envelope_plot_review_cli_fails_on_missing_columns(
    tmp_path: Path,
) -> None:
    bad_tsv = tmp_path / "bad.tsv"
    _write_tsv(bad_tsv, [{"sample_name": "sample-a"}])

    code = main(
        [
            "--selected-envelope-diagnostics-tsv",
            str(bad_tsv),
            "--raw-dir",
            str(tmp_path),
            "--dll-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "plots"),
        ]
    )

    assert code == 2


def test_plot_index_headers_are_stable() -> None:
    assert PLOT_INDEX_HEADERS == (
        "plot_rank",
        "plot_group",
        "sample_name",
        "target_label",
        "role",
        "selected_candidate_id",
        "row_boundary_decision",
        "boundary_change_class",
        "boundary_stop_reason",
        "area_delta_ratio",
        "resolver_rt_start",
        "resolver_rt_end",
        "envelope_rt_start",
        "envelope_rt_end",
        "quantitation_context_rt_start",
        "quantitation_context_rt_end",
        "oracle_row_id",
        "oracle_status",
        "oracle_source",
        "oracle_rt_start",
        "oracle_rt_end",
        "png_path",
        "pdf_path",
    )


def _diagnostic_row(
    *,
    sample_name: str = "sample-a",
    target_label: str = "5-medC",
    selected_candidate_id: str = "candidate-001",
    row_boundary_decision: str = "accept_candidate",
    boundary_change_class: str = "flank_recovered",
    boundary_stop_reason: str = "baseline_return_reached",
    area_delta_ratio: str = "0.60",
) -> dict[str, str]:
    row = {header: "" for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS}
    row.update(
        {
            "sample_name": sample_name,
            "target_label": target_label,
            "role": "Analyte",
            "selected_candidate_id": selected_candidate_id,
            "selected_boundary_mode": "selected_full_envelope",
            "row_boundary_decision": row_boundary_decision,
            "legacy_resolver_provenance": "local_minimum",
            "resolver_rt_start": "11.80000",
            "resolver_rt_end": "12.20000",
            "envelope_rt_start": "11.90000",
            "envelope_rt_end": "12.10000",
            "quantitation_context_rt_start": "10.00000",
            "quantitation_context_rt_end": "14.00000",
            "boundary_change_class": boundary_change_class,
            "boundary_stop_reason": boundary_stop_reason,
            "asls_area_old_interval": "100.00",
            "asls_area_selected_envelope": "150.00",
            "area_delta_ratio": area_delta_ratio,
        }
    )
    return row


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
