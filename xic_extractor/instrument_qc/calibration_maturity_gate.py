from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

LEVEL2_INFORMATIVE_TRANSFER_STATUSES = {
    "transfer_supported",
    "direction_supported_magnitude_shifted",
}
TRANSFER_BLOCKER_STATUSES = {
    "transfer_not_supported",
    "insufficient_biological_istd",
    "insufficient_clean_standard",
}
LOAO_P95_PRODUCTION_MAX_MIN = 0.30


@dataclass(frozen=True)
class CalibrationMaturityDecision:
    maturity_level: str
    target_state: str
    decision: str
    go_no_go: str
    blocker_count: int
    blockers: tuple[str, ...]
    evidence_summary: str
    review_reason: str


def build_calibration_maturity_decisions(
    *,
    rt_model_summary: Mapping[str, Any] | None,
    matrix_rt_preview_summary: Mapping[str, Any] | None,
    matrix_rt_preview_row_summary: Mapping[str, Any] | None,
    biological_istd_transfer_summary: Mapping[str, Any] | None,
    response_model_summary: Mapping[str, Any] | None = None,
    biological_response_transfer_summary: Mapping[str, Any] | None = None,
    downstream_compatibility_summary: Mapping[str, Any] | None = None,
) -> tuple[CalibrationMaturityDecision, ...]:
    level2 = _level2_decision(
        rt_model_summary=rt_model_summary,
        matrix_rt_preview_summary=matrix_rt_preview_summary,
        matrix_rt_preview_row_summary=matrix_rt_preview_row_summary,
        biological_istd_transfer_summary=biological_istd_transfer_summary,
    )
    level3 = _level3_decision(
        rt_model_summary=rt_model_summary,
        matrix_rt_preview_row_summary=matrix_rt_preview_row_summary,
        biological_istd_transfer_summary=biological_istd_transfer_summary,
    )
    level4 = _level4_decision(
        response_model_summary=response_model_summary,
        biological_response_transfer_summary=biological_response_transfer_summary,
    )
    level5 = _level5_decision(
        level4_decision=level4,
        downstream_compatibility_summary=downstream_compatibility_summary,
    )
    return (level2, level3, level4, level5)


def _level2_decision(
    *,
    rt_model_summary: Mapping[str, Any] | None,
    matrix_rt_preview_summary: Mapping[str, Any] | None,
    matrix_rt_preview_row_summary: Mapping[str, Any] | None,
    biological_istd_transfer_summary: Mapping[str, Any] | None,
) -> CalibrationMaturityDecision:
    blockers: list[str] = []
    if rt_model_summary is None:
        blockers.append("missing_rt_model_summary")
    if matrix_rt_preview_summary is None:
        blockers.append("missing_matrix_rt_preview_summary")
    if matrix_rt_preview_row_summary is None:
        blockers.append("missing_matrix_rt_preview_row_summary")
    if biological_istd_transfer_summary is None:
        blockers.append("missing_biological_istd_transfer_summary")
    transfer_scope = _string_value(
        biological_istd_transfer_summary,
        "istd_scope",
    )
    if biological_istd_transfer_summary is not None and not transfer_scope:
        blockers.append("missing_istd_transfer_scope")

    preview_status_counts = _counts(
        matrix_rt_preview_summary,
        "counts_by_correction_status",
    )
    if matrix_rt_preview_summary is not None and preview_status_counts.get(
        "shadow_only", 0
    ) == 0:
        blockers.append("missing_shadow_only_rt_preview_rows")

    transfer_counts = _counts(
        biological_istd_transfer_summary,
        "counts_by_transfer_status",
    )
    informative_count = sum(
        transfer_counts.get(status, 0)
        for status in LEVEL2_INFORMATIVE_TRANSFER_STATUSES
    )
    if biological_istd_transfer_summary is not None and informative_count < 3:
        blockers.append("insufficient_informative_istd_transfer_rows")

    decision = "go" if not blockers else "no_go"
    return CalibrationMaturityDecision(
        maturity_level="level_2",
        target_state="rt_aware_audit_alignment_support",
        decision=decision,
        go_no_go=decision,
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        evidence_summary=(
            f"shadow_only={preview_status_counts.get('shadow_only', 0)}; "
            f"informative_transfer_rows={informative_count}; "
            f"istd_scope={transfer_scope or 'missing'}"
        ),
        review_reason=(
            "RT-aware audit can support alignment review without matrix mutation."
            if not blockers
            else "Level 2 audit support is missing required evidence."
        ),
    )


def _level3_decision(
    *,
    rt_model_summary: Mapping[str, Any] | None,
    matrix_rt_preview_row_summary: Mapping[str, Any] | None,
    biological_istd_transfer_summary: Mapping[str, Any] | None,
) -> CalibrationMaturityDecision:
    blockers: list[str] = []
    if rt_model_summary is None:
        blockers.append("missing_rt_model_summary")
    if matrix_rt_preview_row_summary is None:
        blockers.append("missing_matrix_rt_preview_row_summary")
    loao_counts = _counts(rt_model_summary, "leave_one_anchor_out_status_counts")
    fail_count = loao_counts.get("FAIL", 0)
    if fail_count > 0:
        blockers.append(f"loao_fail_count={fail_count}")
    p95 = _float_value(
        rt_model_summary,
        "leave_one_anchor_out_p95_abs_error_min",
    )
    if p95 is None:
        blockers.append("missing_loao_p95_abs_error")
    elif p95 > LOAO_P95_PRODUCTION_MAX_MIN:
        blockers.append(f"loao_p95_abs_error_min={p95:.6g}")

    transfer_counts = _counts(
        biological_istd_transfer_summary,
        "counts_by_transfer_status",
    )
    for status in sorted(TRANSFER_BLOCKER_STATUSES):
        count = transfer_counts.get(status, 0)
        if count > 0:
            blockers.append(f"{status}={count}")
    if biological_istd_transfer_summary is None:
        blockers.append("missing_biological_istd_transfer_summary")
    transfer_scope = _string_value(
        biological_istd_transfer_summary,
        "istd_scope",
    )
    if biological_istd_transfer_summary is not None and not transfer_scope:
        blockers.append("missing_istd_transfer_scope")

    coverage_counts = _counts(
        matrix_rt_preview_row_summary,
        "counts_by_coverage_status",
    )
    extrapolated_count = coverage_counts.get("extrapolated", 0)
    if extrapolated_count > 0:
        blockers.append(f"matrix_rt_extrapolated_rows={extrapolated_count}")
    correction_counts = _counts(
        matrix_rt_preview_row_summary,
        "counts_by_correction_status",
    )
    blocked_count = sum(
        count
        for status, count in correction_counts.items()
        if status.startswith("blocked_")
    )
    if blocked_count > 0:
        blockers.append(f"matrix_rt_blocked_rows={blocked_count}")

    decision = "candidate" if not blockers else "no_go"
    return CalibrationMaturityDecision(
        maturity_level="level_3",
        target_state="rt_production_candidate",
        decision=decision,
        go_no_go="go" if decision == "candidate" else "no_go",
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        evidence_summary=(
            f"loao_fail={fail_count}; loao_p95={_format_optional_float(p95)}; "
            f"transfer_blockers={_transfer_blocker_summary(transfer_counts)}; "
            f"extrapolated_rows={extrapolated_count}; "
            f"blocked_rows={blocked_count}; "
            f"istd_scope={transfer_scope or 'missing'}"
        ),
        review_reason=(
            "RT production candidate evidence passes current conservative gates."
            if not blockers
            else "RT production correction remains blocked by residual or "
            "transfer evidence."
        ),
    )


def _level4_decision(
    *,
    response_model_summary: Mapping[str, Any] | None,
    biological_response_transfer_summary: Mapping[str, Any] | None,
) -> CalibrationMaturityDecision:
    blockers: list[str] = []
    if response_model_summary is None:
        blockers.append("missing_response_model_summary")
    if biological_response_transfer_summary is None:
        blockers.append("missing_biological_response_transfer_summary")
    decision = "candidate" if not blockers else "no_go"
    return CalibrationMaturityDecision(
        maturity_level="level_4",
        target_state="response_shadow_candidate",
        decision=decision,
        go_no_go="go" if decision == "candidate" else "no_go",
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        evidence_summary=(
            "response_model=present; biological_response_transfer=present"
            if not blockers
            else "response evidence incomplete"
        ),
        review_reason=(
            "Response shadow candidate can be reviewed without production scaling."
            if not blockers
            else "Response drift remains blocked until response model and "
            "biological transfer evidence exist."
        ),
    )


def _level5_decision(
    *,
    level4_decision: CalibrationMaturityDecision,
    downstream_compatibility_summary: Mapping[str, Any] | None,
) -> CalibrationMaturityDecision:
    blockers: list[str] = []
    if level4_decision.go_no_go != "go":
        blockers.append("level4_response_shadow_not_ready")
    if downstream_compatibility_summary is None:
        blockers.append("missing_downstream_compatibility_summary")
    decision = "candidate" if not blockers else "no_go"
    return CalibrationMaturityDecision(
        maturity_level="level_5",
        target_state="response_production_candidate",
        decision=decision,
        go_no_go="go" if decision == "candidate" else "no_go",
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        evidence_summary=(
            "level4=go; downstream_compatibility=present"
            if not blockers
            else "response production prerequisites incomplete"
        ),
        review_reason=(
            "Response production candidate can enter separate reviewed planning."
            if not blockers
            else "Response production correction is blocked by shadow or "
            "downstream evidence gaps."
        ),
    )


def _counts(
    summary: Mapping[str, Any] | None,
    key: str,
) -> dict[str, int]:
    if summary is None:
        return {}
    value = summary.get(key)
    if not isinstance(value, Mapping):
        return {}
    output: dict[str, int] = {}
    for raw_key, raw_value in value.items():
        try:
            output[str(raw_key)] = int(raw_value)
        except (TypeError, ValueError):
            continue
    return output


def _float_value(summary: Mapping[str, Any] | None, key: str) -> float | None:
    if summary is None:
        return None
    value = summary.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_value(summary: Mapping[str, Any] | None, key: str) -> str:
    if summary is None:
        return ""
    value = summary.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "missing"
    return f"{value:.6g}"


def _transfer_blocker_summary(counts: dict[str, int]) -> str:
    parts = [
        f"{status}={counts.get(status, 0)}"
        for status in sorted(TRANSFER_BLOCKER_STATUSES)
    ]
    return ",".join(parts)
