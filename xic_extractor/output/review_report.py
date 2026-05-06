from __future__ import annotations

from pathlib import Path

from xic_extractor.output.review_metrics import build_review_metrics
from xic_extractor.output.review_report_components import (
    _CSS,
    _batch_overview,
    _detection_rate_chart,
    _flag_burden_chart,
    _heatmap,
    _ordered_values,
    _review_queue,
    _targets_by_detection,
)
from xic_extractor.output.review_report_trend import _istd_rt_trend


def review_report_path_for_excel(excel_path: Path) -> Path:
    return excel_path.with_name(
        excel_path.name.replace("xic_results_", "review_report_")
    ).with_suffix(".html")


def write_review_report(
    path: Path,
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
    injection_order: dict[str, int] | None = None,
) -> Path:
    metrics = build_review_metrics(
        rows,
        diagnostics=diagnostics,
        review_rows=review_rows,
        count_no_ms2_as_detected=count_no_ms2_as_detected,
    )
    samples = _ordered_values(rows, "SampleName")
    targets = _targets_by_detection(metrics)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                "<title>XIC Review Report</title>",
                f"<style>{_CSS}</style>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>XIC Review Report</h1>",
                _batch_overview(metrics),
                _detection_rate_chart(metrics, targets),
                _flag_burden_chart(metrics, targets),
                _istd_rt_trend(rows, injection_order),
                _heatmap(metrics, samples, targets),
                _review_queue(review_rows),
                "</main>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    return path
