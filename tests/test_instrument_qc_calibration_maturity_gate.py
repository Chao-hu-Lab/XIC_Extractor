from xic_extractor.instrument_qc.calibration_maturity_gate import (
    build_calibration_maturity_decisions,
)


def test_current_like_evidence_allows_level2_but_blocks_production() -> None:
    decisions = build_calibration_maturity_decisions(
        rt_model_summary=_rt_summary(fail=60, p95=0.633),
        matrix_rt_preview_summary=_matrix_summary(shadow_only=6279),
        matrix_rt_preview_row_summary=_matrix_row_summary(
            shadow_only=6279,
            extrapolated=1080,
            blocked=1434,
        ),
        biological_istd_transfer_summary=_transfer_summary(
            transfer_supported=3,
            direction_supported=2,
            transfer_not_supported=1,
            insufficient_biological=1,
        ),
    )

    by_level = {row.maturity_level: row for row in decisions}

    assert by_level["level_2"].go_no_go == "go"
    assert by_level["level_2"].target_state == "rt_aware_audit_alignment_support"
    assert by_level["level_3"].go_no_go == "no_go"
    assert "loao_fail_count=60" in by_level["level_3"].blockers
    assert "matrix_rt_extrapolated_rows=1080" in by_level["level_3"].blockers
    assert "matrix_rt_blocked_rows=1434" in by_level["level_3"].blockers
    assert by_level["level_4"].go_no_go == "no_go"
    assert by_level["level_5"].go_no_go == "no_go"


def test_level2_blocks_without_informative_transfer_rows() -> None:
    decisions = build_calibration_maturity_decisions(
        rt_model_summary=_rt_summary(fail=0, p95=0.1),
        matrix_rt_preview_summary=_matrix_summary(shadow_only=10),
        matrix_rt_preview_row_summary=_matrix_row_summary(shadow_only=10),
        biological_istd_transfer_summary=_transfer_summary(
            transfer_supported=1,
            direction_supported=1,
        ),
    )

    level2 = decisions[0]

    assert level2.maturity_level == "level_2"
    assert level2.go_no_go == "no_go"
    assert "insufficient_informative_istd_transfer_rows" in level2.blockers


def test_level3_candidate_requires_clean_residuals_and_transfer() -> None:
    decisions = build_calibration_maturity_decisions(
        rt_model_summary=_rt_summary(fail=0, p95=0.2),
        matrix_rt_preview_summary=_matrix_summary(shadow_only=10),
        matrix_rt_preview_row_summary=_matrix_row_summary(shadow_only=10),
        biological_istd_transfer_summary=_transfer_summary(transfer_supported=4),
    )

    level3 = {row.maturity_level: row for row in decisions}["level_3"]

    assert level3.decision == "candidate"
    assert level3.go_no_go == "go"
    assert level3.blockers == ()


def test_level4_and_level5_can_pass_only_when_response_dependencies_exist() -> None:
    decisions = build_calibration_maturity_decisions(
        rt_model_summary=_rt_summary(fail=0, p95=0.2),
        matrix_rt_preview_summary=_matrix_summary(shadow_only=10),
        matrix_rt_preview_row_summary=_matrix_row_summary(shadow_only=10),
        biological_istd_transfer_summary=_transfer_summary(transfer_supported=4),
        response_model_summary={"status": "present"},
        biological_response_transfer_summary={"status": "present"},
        downstream_compatibility_summary={"status": "present"},
    )

    by_level = {row.maturity_level: row for row in decisions}

    assert by_level["level_4"].go_no_go == "go"
    assert by_level["level_5"].go_no_go == "go"


def _rt_summary(*, fail: int, p95: float) -> dict[str, object]:
    return {
        "leave_one_anchor_out_status_counts": {
            "PASS": 10,
            "WARN": 2,
            "FAIL": fail,
        },
        "leave_one_anchor_out_p95_abs_error_min": p95,
    }


def _matrix_summary(*, shadow_only: int) -> dict[str, object]:
    return {
        "counts_by_correction_status": {
            "shadow_only": shadow_only,
            "blocked_missing_value": 1,
        }
    }


def _matrix_row_summary(
    *,
    shadow_only: int,
    extrapolated: int = 0,
    blocked: int = 0,
) -> dict[str, object]:
    return {
        "counts_by_coverage_status": {
            "covered": shadow_only,
            "extrapolated": extrapolated,
        },
        "counts_by_correction_status": {
            "shadow_only": shadow_only,
            "blocked_missing_value": blocked,
        },
    }


def _transfer_summary(
    *,
    transfer_supported: int = 0,
    direction_supported: int = 0,
    transfer_not_supported: int = 0,
    insufficient_biological: int = 0,
) -> dict[str, object]:
    return {
        "counts_by_transfer_status": {
            "transfer_supported": transfer_supported,
            "direction_supported_magnitude_shifted": direction_supported,
            "transfer_not_supported": transfer_not_supported,
            "insufficient_biological_istd": insufficient_biological,
        },
        "istd_scope": "provided_biological_qc_istd_summary_rows",
    }
