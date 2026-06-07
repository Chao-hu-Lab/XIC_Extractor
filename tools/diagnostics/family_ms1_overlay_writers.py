"""TSV/JSON output writers for family MS1 overlay diagnostics."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from tools.diagnostics.family_ms1_overlay_evidence import (
    _absolute_own_max_shape_similarity,
    _apex_aligned_shape_similarity,
    _global_trace_apex_delta,
    _local_to_global_max_ratio,
    _local_window_peak,
    build_family_ms1_evidence_summary,
)
from tools.diagnostics.family_ms1_overlay_models import (
    FamilyMs1OverlayOutputs,
    TraceOverlayRow,
)
from tools.diagnostics.family_ms1_overlay_rendering import render_family_ms1_overlay

if TYPE_CHECKING:
    from xic_extractor.alignment.edge_scoring import DriftLookupProtocol


def write_family_ms1_overlay_outputs(
    *,
    rows: Sequence[TraceOverlayRow],
    output_dir: Path,
    output_prefix: str,
    family_id: str,
    mz: float,
    ppm: float,
    rt_min: float,
    rt_max: float,
    family_center_rt: float | None,
    drift_lookup: DriftLookupProtocol | None = None,
) -> FamilyMs1OverlayOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_tsv = output_dir / f"{output_prefix}_trace_summary.tsv"
    trace_data_json = output_dir / f"{output_prefix}_trace_data.json"
    png_path = output_dir / f"{output_prefix}.png"
    pdf_path = output_dir / f"{output_prefix}.pdf"

    _write_summary(summary_tsv, rows)
    _write_trace_data(
        trace_data_json,
        rows=rows,
        family_id=family_id,
        mz=mz,
        ppm=ppm,
        rt_min=rt_min,
        rt_max=rt_max,
        family_center_rt=family_center_rt,
    )
    render_family_ms1_overlay(
        rows=rows,
        png_path=png_path,
        pdf_path=pdf_path,
        family_id=family_id,
        mz=mz,
        ppm=ppm,
        rt_min=rt_min,
        rt_max=rt_max,
        family_center_rt=family_center_rt,
        drift_lookup=drift_lookup,
    )
    return FamilyMs1OverlayOutputs(
        png_path=png_path,
        pdf_path=pdf_path,
        summary_tsv=summary_tsv,
        trace_data_json=trace_data_json,
    )


def _write_summary(path: Path, rows: Sequence[TraceOverlayRow]) -> None:
    shape_similarity = _apex_aligned_shape_similarity(rows)
    absolute_shape_similarity = _absolute_own_max_shape_similarity(rows)
    fields = (
        "sample_stem",
        "status",
        "cell_area",
        "cell_height",
        "cell_apex_rt",
        "cell_start_rt",
        "cell_end_rt",
        "trace_max_intensity",
        "trace_apex_rt",
        "global_trace_apex_delta_min",
        "local_window_max_intensity",
        "local_window_apex_delta_min",
        "local_window_to_global_max_ratio",
        "region_shadow_verdict",
        "source_candidate_id",
        "highlight_group",
        "apex_aligned_shape_similarity",
        "absolute_own_max_shape_similarity",
    )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "sample_stem": row.sample_stem,
                    "status": row.status,
                    "cell_area": _format_float(row.cell_area),
                    "cell_height": _format_float(row.cell_height),
                    "cell_apex_rt": _format_float(row.cell_apex_rt, digits=6),
                    "cell_start_rt": _format_float(row.cell_start_rt, digits=6),
                    "cell_end_rt": _format_float(row.cell_end_rt, digits=6),
                    "trace_max_intensity": _format_float(row.trace_max_intensity),
                    "trace_apex_rt": _format_float(row.trace_apex_rt, digits=6),
                    "global_trace_apex_delta_min": _format_float(
                        _global_trace_apex_delta(row),
                    ),
                    "local_window_max_intensity": _format_float(
                        _local_window_peak(row)[1],
                    ),
                    "local_window_apex_delta_min": _format_float(
                        _local_window_peak(row)[0],
                    ),
                    "local_window_to_global_max_ratio": _format_float(
                        _local_to_global_max_ratio(row),
                    ),
                    "region_shadow_verdict": row.region_shadow_verdict,
                    "source_candidate_id": row.source_candidate_id,
                    "highlight_group": row.group,
                    "apex_aligned_shape_similarity": _format_float(
                        shape_similarity.get(row.sample_stem),
                    ),
                    "absolute_own_max_shape_similarity": _format_float(
                        absolute_shape_similarity.get(row.sample_stem),
                    ),
                }
            )


def _write_trace_data(
    path: Path,
    *,
    rows: Sequence[TraceOverlayRow],
    family_id: str,
    mz: float,
    ppm: float,
    rt_min: float,
    rt_max: float,
    family_center_rt: float | None,
) -> None:
    shape_similarity = _apex_aligned_shape_similarity(rows)
    absolute_shape_similarity = _absolute_own_max_shape_similarity(rows)
    data = {
        "family_id": family_id,
        "mz": mz,
        "ppm": ppm,
        "rt_min": rt_min,
        "rt_max": rt_max,
        "family_center_rt": family_center_rt,
        "trace_count": len(rows),
        "evidence_summary": build_family_ms1_evidence_summary(rows),
        "traces": [
            {
                "sample_stem": row.sample_stem,
                "status": row.status,
                "group": row.group,
                "cell_area": row.cell_area,
                "cell_height": row.cell_height,
                "cell_apex_rt": row.cell_apex_rt,
                "cell_start_rt": row.cell_start_rt,
                "cell_end_rt": row.cell_end_rt,
                "trace_max_intensity": row.trace_max_intensity,
                "trace_apex_rt": row.trace_apex_rt,
                "global_trace_apex_delta_min": _json_float(
                    _global_trace_apex_delta(row),
                ),
                "local_window_max_intensity": _json_float(
                    _local_window_peak(row)[1],
                ),
                "local_window_apex_delta_min": _json_float(
                    _local_window_peak(row)[0],
                ),
                "local_window_to_global_max_ratio": _json_float(
                    _local_to_global_max_ratio(row),
                ),
                "region_shadow_verdict": row.region_shadow_verdict,
                "source_candidate_id": row.source_candidate_id,
                "apex_aligned_shape_similarity": _json_float(
                    shape_similarity.get(row.sample_stem),
                ),
                "absolute_own_max_shape_similarity": _json_float(
                    absolute_shape_similarity.get(row.sample_stem),
                ),
                "rt": row.rt,
                "intensity": row.intensity,
            }
            for row in rows
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _format_float(value: float | None, *, digits: int = 6) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}g}"


def _json_float(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(value)
