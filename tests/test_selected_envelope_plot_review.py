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
from xic_extractor.configuration.models import Target
from xic_extractor.peak_detection.chrom_peak_segments import (
    ChromPeakSegment,
    enumerate_chrom_peak_segments,
)
from xic_extractor.peak_detection.selected_envelope import TraceInterval
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


def test_select_selected_envelope_plot_requests_adds_chrom_review_rows() -> None:
    rows = [
        _diagnostic_row(
            sample_name="sample-review",
            target_label="8-oxodG",
            selected_candidate_id="candidate-review",
            row_boundary_decision="accept_candidate",
            area_delta_ratio="0",
        ),
        _diagnostic_row(
            sample_name="sample-other",
            target_label="8-oxo-Guo",
            selected_candidate_id="candidate-other",
            row_boundary_decision="accept_candidate",
            area_delta_ratio="0",
        ),
    ]

    requests = select_selected_envelope_plot_requests(
        rows,
        chrom_peak_segment_review_rows=[
            {
                "sample_name": "sample-review",
                "target_label": "8-oxodG",
                "role": "Analyte",
            }
        ],
        max_high_risk=0,
        max_accepted_increase=0,
        max_accepted_decrease=0,
    )

    assert [request.plot_group for request in requests] == [
        "chrom_peak_segment_review_only"
    ]
    assert requests[0].row["selected_candidate_id"] == "candidate-review"


def test_select_plot_requests_fails_on_missing_chrom_review_row() -> None:
    with pytest.raises(ValueError, match="chrom review row not found"):
        select_selected_envelope_plot_requests(
            [
                _diagnostic_row(
                    sample_name="sample-a",
                    target_label="8-oxodG",
                )
            ],
            chrom_peak_segment_review_rows=[
                {
                    "sample_name": "missing",
                    "target_label": "8-oxodG",
                    "role": "Analyte",
                }
            ],
            max_high_risk=0,
            max_accepted_increase=0,
            max_accepted_decrease=0,
        )


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


def test_write_selected_envelope_boundary_plot_draws_chrom_segments(
    tmp_path: Path,
) -> None:
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
    segments = enumerate_chrom_peak_segments(
        rt,
        intensity,
        baseline,
        quantitation_context_rt_start=10.0,
        quantitation_context_rt_end=14.0,
    ).segments
    selected_segment = plot_review._select_chrom_peak_segment_for_row(row, segments)
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
        chrom_peak_segments=segments,
        selected_chrom_peak_segment=selected_segment,
    )

    assert selected_segment is not None
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


def test_plot_index_row_records_projected_chrom_segment(tmp_path: Path) -> None:
    row = _diagnostic_row()
    rt = np.linspace(10.0, 14.0, 41)
    baseline = np.full_like(rt, 10.0)
    intensity = baseline + 200.0 * np.exp(-((rt - 12.0) ** 2) / 0.08)
    segments = enumerate_chrom_peak_segments(
        rt,
        intensity,
        baseline,
        quantitation_context_rt_start=10.0,
        quantitation_context_rt_end=14.0,
    ).segments
    selected_segment = plot_review._select_chrom_peak_segment_for_row(row, segments)

    index_row = plot_review._plot_index_row(
        rank=1,
        request=plot_review.SelectedEnvelopePlotRequest(
            row=row,
            plot_group="accepted_area_increase",
        ),
        boundary_oracle=None,
        chrom_peak_segment_status="OK",
        chrom_peak_segments=segments,
        selected_chrom_peak_segment=selected_segment,
        png_path=tmp_path / "plot.png",
        pdf_path=tmp_path / "plot.pdf",
    )

    assert index_row["chrom_peak_segment_status"] == "OK"
    assert index_row["chrom_peak_segment_count"] == "1"
    assert index_row["selected_chrom_peak_segment_id"] == "chrom_peak_segment_001"
    assert index_row["selected_chrom_peak_segment_class"] == "isolated_peak"
    assert (
        index_row["selected_chrom_peak_segment_projection"]
        == "resolver_midpoint_contains"
    )


def test_review_gallery_html_marks_active_interval_and_escapes(
    tmp_path: Path,
) -> None:
    gallery_dir = tmp_path / "review"
    plot_path = gallery_dir / "plots" / "plot.png"
    plot_path.parent.mkdir(parents=True)
    plot_path.write_bytes(b"fake-png")
    row = {header: "" for header in PLOT_INDEX_HEADERS}
    row.update(
        {
            "plot_rank": "1",
            "plot_group": "high_risk_externalized",
            "sample_name": "<sample-a>",
            "target_label": "8-oxodG",
            "role": "Analyte",
            "row_boundary_decision": "externalize",
            "boundary_change_class": "context_apex_conflict",
            "resolver_rt_start": "16.06619",
            "resolver_rt_end": "17.17301",
            "envelope_rt_start": "15.37481",
            "envelope_rt_end": "17.20159",
            "png_path": str(plot_path),
        }
    )
    gallery_path = gallery_dir / "review_gallery.html"

    plot_review._write_review_gallery_html(
        gallery_path,
        [row],
        index_tsv=gallery_dir / "selected_envelope_plot_index.tsv",
    )

    html_text = gallery_path.read_text(encoding="utf-8")
    assert "green = ACTIVE selected/product interval" in html_text
    assert "&lt;sample-a&gt;" in html_text
    assert 'src="plots/plot.png"' in html_text
    assert "16.06619-17.17301" in html_text


def test_select_chrom_peak_segment_prefers_selected_apex_over_wide_envelope() -> None:
    row = _diagnostic_row(
        selected_candidate_id=(
            "sample|8-oxodG|region_first_safe_merge|local_minimum|"
            "16.36568|16.21219|16.40116"
        )
    )
    row["resolver_rt_start"] = "16.21219"
    row["resolver_rt_end"] = "16.40116"
    row["envelope_rt_start"] = "15.29182"
    row["envelope_rt_end"] = "17.20159"
    segments = (
        _segment("chrom_peak_segment_001", 15.29182, 16.06619, apex=15.86155),
        _segment("chrom_peak_segment_002", 16.06619, 16.60743, apex=16.50198),
        _segment("chrom_peak_segment_003", 16.60743, 17.10889, apex=16.88434),
    )

    selected_segment = plot_review._select_chrom_peak_segment_for_row(row, segments)

    assert selected_segment is not None
    assert selected_segment.segment_id == "chrom_peak_segment_002"
    assert (
        plot_review._chrom_peak_segment_projection_basis(row, selected_segment)
        == "selected_apex_contains"
    )


def test_plot_extraction_bounds_include_target_window() -> None:
    row = _diagnostic_row()
    row["quantitation_context_rt_start"] = "17.34502"
    row["quantitation_context_rt_end"] = "19.28695"
    target = Target(
        label="8-oxodG",
        mz=284.0989,
        rt_min=16.0,
        rt_max=18.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=False,
        istd_pair="15N5-8-oxodG",
    )

    bounds = plot_review._plot_extraction_bounds(row, target)

    assert bounds == pytest.approx((16.0, 19.28695))


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
        "chrom_peak_segment_status",
        "chrom_peak_segment_count",
        "selected_chrom_peak_segment_id",
        "selected_chrom_peak_segment_class",
        "selected_chrom_peak_segment_rt_start",
        "selected_chrom_peak_segment_rt_end",
        "selected_chrom_peak_segment_area_asls",
        "selected_chrom_peak_segment_stop_reason",
        "selected_chrom_peak_segment_projection",
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


def _segment(
    segment_id: str,
    start: float,
    end: float,
    *,
    apex: float,
) -> ChromPeakSegment:
    return ChromPeakSegment(
        segment_id=segment_id,
        interval=TraceInterval(
            start_index=0,
            end_index=1,
            rt_start_min=start,
            rt_end_min=end,
            scan_count=3,
        ),
        apex_index=0,
        apex_rt_min=apex,
        raw_apex_residual=100.0,
        morphology_apex_residual=100.0,
        area_baseline_corrected=1000.0,
        morphology_area_shadow=1000.0,
        segment_class="separate_peak",
        boundary_stop_reason="baseline_valley_split",
        evidence_sources=("morphology_trace",),
    )
