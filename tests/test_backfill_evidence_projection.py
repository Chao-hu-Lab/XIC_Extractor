from xic_extractor.alignment.backfill_evidence_projection import (
    BACKFILL_PROJECTION_COLUMNS,
    project_backfill_evidence_to_cells,
)
from xic_extractor.alignment.promotion_policy import evidence_from_tsv_rows


def test_backfill_projection_maps_sidecar_evidence_into_supported_rescue_cell() -> None:
    rows = project_backfill_evidence_to_cells(
        cell_rows=[
            _cell_row("FAM_DROPOUT", "S1", status="detected"),
            _cell_row(
                "FAM_DROPOUT",
                "S2",
                status="rescued",
                rt_delta_sec="120",
            ),
        ],
        candidate_ms2_pattern_rows=[
            {
                "feature_family_id": "FAM_DROPOUT",
                "sample_stem": "S1",
                "candidate_ms2_pattern_status": "supportive",
                "candidate_ms2_evidence_level": "sample_candidate_aligned",
                "raw_ms2_trigger_scan_count": "5",
                "raw_ms2_strict_nl_scan_count": "2",
                "raw_ms2_trace_strength": "strong",
            },
            {
                "feature_family_id": "FAM_DROPOUT",
                "sample_stem": "S2",
                "candidate_ms2_pattern_status": "not_observed",
                "candidate_ms2_evidence_level": "sample_boundary_no_observed_pattern",
                "raw_ms2_trigger_scan_count": "3",
                "raw_ms2_strict_nl_scan_count": "0",
                "raw_ms2_trace_strength": "moderate",
            },
        ],
        ms1_pattern_coherence_rows=[
            {
                "feature_family_id": "FAM_DROPOUT",
                "sample_stem": "S2",
                "ms1_pattern_status": "supportive",
                "ms1_pattern_evidence_level": "sample_constellation",
                "reason": "gaussian15_ms1_pattern_coherent",
            }
        ],
        matrix_rt_drift_policy_rows=[
            {
                "feature_family_id": "FAM_DROPOUT",
                "sample_stem": "S2",
                "matrix_rt_drift_status": "drift_supported",
                "drift_evidence_level": "matrix_reference_aligned",
                "drift_corrected_delta_sec": "20",
                "drift_compatible_status": "compatible",
                "reason": "istd_drift_explains_rt_delta",
            }
        ],
    )

    rescued = _row(rows, "FAM_DROPOUT", "S2")
    assert rescued["backfill_ms1_pattern_status"] == "supportive"
    assert rescued["backfill_ms1_pattern_evidence_level"] == "sample_constellation"
    assert rescued["backfill_matrix_rt_drift_status"] == "drift_supported"
    assert rescued["backfill_drift_evidence_level"] == "matrix_reference_aligned"
    assert rescued["backfill_drift_corrected_delta_sec"] == "20"
    assert rescued["backfill_candidate_ms2_pattern_status"] == "not_observed"
    assert (
        rescued["backfill_candidate_ms2_evidence_level"]
        == "sample_boundary_no_observed_pattern"
    )
    assert rescued["backfill_ms2_trigger_scan_count"] == "3"
    assert rescued["backfill_strict_nl_scan_count"] == "0"
    assert rescued["backfill_ms2_trace_strength"] == "moderate"
    assert rescued["backfill_dda_missing_nl_policy_status"] == "not_dispositive"
    assert (
        rescued["backfill_family_ms2_required_tag_status"]
        == "observed_in_family"
    )
    assert "ms1_pattern_coherence" in rescued["backfill_evidence_reason"]
    assert "candidate_ms2_pattern" in rescued["backfill_evidence_reason"]

    evidence = evidence_from_tsv_rows(
        {
            "neutral_loss_tag": "DNA_dR",
            "primary_evidence": "owner_complete_link",
            "detected_count": "2",
            "accepted_rescue_count": "1",
        },
        [rescued],
        seed_quality=None,
        sample_count=3,
    )
    assert evidence.cells[0].supported_for_backfill

    detected = _row(rows, "FAM_DROPOUT", "S1")
    assert all(detected[column] == "" for column in BACKFILL_PROJECTION_COLUMNS)


def test_backfill_projection_is_fail_closed_when_sidecars_are_missing() -> None:
    rows = project_backfill_evidence_to_cells(
        cell_rows=[_cell_row("FAM_MISSING", "S2", status="rescued")]
    )

    row = rows[0]
    assert all(column in row for column in BACKFILL_PROJECTION_COLUMNS)
    assert all(row[column] == "" for column in BACKFILL_PROJECTION_COLUMNS)

    evidence = evidence_from_tsv_rows(
        {
            "neutral_loss_tag": "DNA_dR",
            "primary_evidence": "owner_complete_link",
            "detected_count": "2",
            "accepted_rescue_count": "1",
        },
        rows,
        seed_quality=None,
        sample_count=3,
    )
    assert not evidence.cells[0].supported_for_backfill
    assert evidence.cells[0].backfill_identity_block_reason != ""


def _cell_row(
    family_id: str,
    sample_stem: str,
    *,
    status: str,
    rt_delta_sec: str = "30",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_stem,
        "status": status,
        "primary_matrix_area": "123",
        "apex_rt": "10.0",
        "height": "40000",
        "peak_start_rt": "9.8",
        "peak_end_rt": "10.2",
        "rt_delta_sec": rt_delta_sec,
        "scan_support_score": "0.8",
    }


def _row(
    rows: tuple[dict[str, str], ...],
    family_id: str,
    sample_stem: str,
) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["feature_family_id"] == family_id and row["sample_stem"] == sample_stem
    )
