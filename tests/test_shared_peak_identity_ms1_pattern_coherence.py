from __future__ import annotations

import csv
import json
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    machine_evidence_support,
    ms1_pattern_coherence,
)


def test_ms1_pattern_coherence_marks_boundary_constellation_supportive(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", rt_delta_sec="3.0"),
            _cell("FAM001", "S2", rt_delta_sec="2.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "supportive"
    assert rows[0]["ms1_pattern_evidence_level"] == "sample_boundary_constellation"
    assert rows[0]["drift_compatible_status"] == "compatible"
    assert rows[0]["reference_peak_count"] == "3"
    assert rows[0]["shape_correlation_score"] == ""


def test_ms1_pattern_coherence_conflicts_when_apex_far_without_drift_policy(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", apex_rt="13.0", rt_delta_sec="240.0"),
            _cell("FAM001", "S2", rt_delta_sec="2.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "conflict"
    assert rows[0]["drift_compatible_status"] == "conflict"
    assert rows[0]["reason"] == "rt_or_matrix_drift_conflict"


def test_ms1_pattern_coherence_keeps_boundary_only_mismatch_inconclusive(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", peak_start_rt="9.99", peak_end_rt="10.01"),
            _cell("FAM001", "S2", peak_start_rt="9.7", peak_end_rt="10.3"),
            _cell("FAM001", "S3", peak_start_rt="9.7", peak_end_rt="10.3"),
        ],
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "inconclusive"
    assert rows[0]["ms1_pattern_evidence_level"] == "not_available"
    assert rows[0]["reason"] == "boundary_width_similarity_too_low"


def test_ms1_pattern_coherence_accepts_independent_drift_policy(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    matrix_drift = tmp_path / "matrix_rt_drift_policy.tsv"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", apex_rt="13.0", rt_delta_sec="240.0"),
            _cell("FAM001", "S2", rt_delta_sec="2.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )
    _write_matrix_drift(
        matrix_drift,
        matrix_rt_drift_status="drift_supported",
        drift_corrected_delta_sec="5.0",
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        matrix_rt_drift_policy_tsv=matrix_drift,
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "supportive"
    assert rows[0]["apex_coherence_sec"] == "5"
    assert rows[0]["drift_compatible_status"] == "compatible"


def test_ms1_pattern_coherence_enriches_raw_overlay_shape_metric(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", rt_delta_sec="72.0"),
            _cell("FAM001", "S2", rt_delta_sec="70.0"),
            _cell("FAM001", "S3", rt_delta_sec="75.0"),
        ],
    )
    overlay.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "rt_min": 9.5,
                "rt_max": 10.5,
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill"
                },
                "traces": [
                    {
                        "sample_stem": "S1",
                        "cell_apex_rt": 10.0,
                        "cell_height": 980.0,
                        "local_window_max_intensity": 1000.0,
                        "trace_max_intensity": 1000.0,
                        "apex_aligned_shape_similarity": 0.94,
                        "local_window_to_global_max_ratio": 0.98,
                        "local_window_apex_delta_min": 0.01,
                        "global_trace_apex_delta_min": 0.02,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "partial_support"
    assert rows[0]["ms1_pattern_evidence_level"] == "trace_constellation"
    assert rows[0]["shape_correlation_score"] == "0.94"
    assert rows[0]["shape_metric_source"] == "family_ms1_overlay_raw_trace"
    assert rows[0]["cell_height"] == "980"
    assert rows[0]["local_window_max_intensity"] == "1000"
    assert rows[0]["trace_max_intensity"] == "1000"
    assert rows[0]["cell_to_local_window_max_ratio"] == "0.98"
    assert rows[0]["local_window_apex_delta_sec"] == "0.6"
    assert rows[0]["global_trace_apex_delta_sec"] == "1.2"
    assert rows[0]["family_ms1_overlay_trace_data_json"] == str(overlay)


def test_ms1_pattern_coherence_keeps_low_shape_with_local_peak_partial(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", rt_delta_sec="0.0"),
            _cell("FAM001", "S2", rt_delta_sec="1.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )
    _write_overlay(
        overlay,
        shape_similarity=0.16,
        local_window_to_global_max_ratio=1.0,
        local_window_apex_delta_min=0.083333,
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "partial_support"
    assert rows[0]["ms1_pattern_evidence_level"] == "trace_constellation"
    assert rows[0]["shape_correlation_score"] == "0.16"
    assert rows[0]["cell_to_local_window_max_ratio"] == "0.3"
    assert rows[0]["local_window_to_global_max_ratio"] == "1"
    assert rows[0]["reason"] == (
        "family_ms1_overlay_shape_metric_inconclusive_apex_or_height"
    )


def test_ms1_pattern_coherence_conflicts_on_low_local_peak_dominance(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", rt_delta_sec="0.0"),
            _cell("FAM001", "S2", rt_delta_sec="1.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )
    _write_overlay(
        overlay,
        shape_similarity=0.94,
        local_window_to_global_max_ratio=0.2,
        local_window_apex_delta_min=0.01,
    )

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "conflict"
    assert rows[0]["ms1_pattern_evidence_level"] == "trace_constellation"
    assert rows[0]["reason"] == (
        "family_ms1_overlay_expected_window_lacks_complete_peak"
    )


def test_ms1_pattern_coherence_does_not_fabricate_absent_cells(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    _write_cells(cells, [_cell("FAM001", "S1", status="absent", apex_rt="")])

    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        oracle_keys=(("FAM001", "S1"),),
    )

    assert rows[0]["ms1_pattern_status"] == "not_available"
    assert rows[0]["ms1_pattern_evidence_level"] == "not_available"
    assert rows[0]["reason"] == "alignment_cell_not_present"


def test_ms1_pattern_coherence_writer_matches_consumer_contract(
    tmp_path: Path,
) -> None:
    cells = tmp_path / "alignment_cells.tsv"
    output = tmp_path / "ms1_pattern.tsv"
    _write_cells(
        cells,
        [
            _cell("FAM001", "S1", rt_delta_sec="3.0"),
            _cell("FAM001", "S2", rt_delta_sec="2.0"),
            _cell("FAM001", "S3", rt_delta_sec="-1.0"),
        ],
    )
    rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows(
        alignment_cells_tsv=cells,
        oracle_keys=(("FAM001", "S1"),),
    )

    ms1_pattern_coherence.write_ms1_pattern_coherence_rows(output, rows)
    loaded = machine_evidence_support.load_ms1_pattern_coherence_evidence(output)

    assert loaded[("FAM001", "S1")]["ms1_pattern_status"] == "supportive"


def _cell(
    feature_family_id: str,
    sample_stem: str,
    *,
    status: str = "selected",
    apex_rt: str = "10.0",
    peak_start_rt: str = "9.9",
    peak_end_rt: str = "10.1",
    rt_delta_sec: str = "0.0",
) -> dict[str, str]:
    return {
        "feature_family_id": feature_family_id,
        "sample_stem": sample_stem,
        "status": status,
        "apex_rt": apex_rt,
        "peak_start_rt": peak_start_rt,
        "peak_end_rt": peak_end_rt,
        "rt_delta_sec": rt_delta_sec,
        "trace_quality": "clean",
        "scan_support_score": "1.0",
    }


def _write_cells(path: Path, rows: list[dict[str, str]]) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "status",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "rt_delta_sec",
            "trace_quality",
            "scan_support_score",
        ),
        rows,
    )


def _write_matrix_drift(
    path: Path,
    *,
    matrix_rt_drift_status: str,
    drift_corrected_delta_sec: str,
) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "matrix_rt_drift_status",
            "drift_evidence_level",
            "raw_rt_delta_sec",
            "drift_corrected_delta_sec",
            "matrix_shift_sec",
            "drift_reference_count",
            "drift_reference_source",
            "drift_compatible_status",
            "reason",
            "diagnostic_only",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "matrix_rt_drift_status": matrix_rt_drift_status,
                "drift_evidence_level": "sample_istd_aligned",
                "raw_rt_delta_sec": "240.0",
                "drift_corrected_delta_sec": drift_corrected_delta_sec,
                "matrix_shift_sec": "235.0",
                "drift_reference_count": "85",
                "drift_reference_source": "unit_test",
                "drift_compatible_status": "compatible",
                "reason": "unit_test_drift",
                "diagnostic_only": "TRUE",
            }
        ],
    )


def _write_overlay(
    path: Path,
    *,
    shape_similarity: float,
    local_window_to_global_max_ratio: float,
    local_window_apex_delta_min: float,
    cell_height: float = 300.0,
    local_window_max_intensity: float = 1000.0,
) -> None:
    path.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "rt_min": 9.5,
                "rt_max": 10.5,
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill"
                },
                "traces": [
                    {
                        "sample_stem": "S1",
                        "cell_apex_rt": 10.0,
                        "cell_height": cell_height,
                        "local_window_max_intensity": local_window_max_intensity,
                        "trace_max_intensity": local_window_max_intensity,
                        "apex_aligned_shape_similarity": shape_similarity,
                        "local_window_to_global_max_ratio": (
                            local_window_to_global_max_ratio
                        ),
                        "local_window_apex_delta_min": local_window_apex_delta_min,
                        "global_trace_apex_delta_min": 0.02,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
