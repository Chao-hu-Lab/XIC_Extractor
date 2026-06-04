from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from xic_extractor.config import Target
from xic_extractor.target_pair_rt_calibration import (
    TargetPairRTCalibrationRow,
    load_target_pair_rt_calibration,
)

TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS = (
    "sample_name",
    "target_label",
    "role",
    "trace_group_id",
    "previous_candidate_id",
    "selected_candidate_id",
    "selection_action",
    "selection_basis",
    "selection_status",
    "product_switch_allowed",
    "expected_diff_stable_row_id",
    "evidence_comparison_policy",
    "previous_candidate_rt",
    "selected_candidate_rt",
    "paired_istd_rt",
    "pair_rt_delta_expected",
    "pair_rt_delta_observed",
    "pair_rt_delta_error",
    "calibration_source",
    "calibration_status",
    "missing_ms2_explanation",
    "role_policy",
    "gate_decision",
    "block_reason",
)

TARGET_PAIR_RT_AUTO_RESELECTION_SUMMARY_HEADERS = (
    "limited_evidence_shadow_count",
    "inconclusive_count",
    "blocked_diff_count",
    "shadow_auto_reselect_proposed_count",
    "auto_reselect_blocked_count",
    "changed_row_denominator",
    "false_positive_strata",
    "product_switch_allowed_true_count",
    "auto_reselected_count",
)

_ALLOWED_SELECTION_ACTIONS = frozenset(
    {"none", "shadow_auto_reselect_proposed", "auto_reselect_blocked"}
)


class FileResultForTargetPairRT(Protocol):
    @property
    def sample_name(self) -> str: ...

    @property
    def results(self) -> Mapping[str, Any]: ...

    @property
    def peak_candidate_rows(self) -> Sequence[Mapping[str, str]]: ...


def write_target_pair_rt_auto_reselection_for_file_results(
    path: Path,
    file_results: Sequence[FileResultForTargetPairRT],
    *,
    targets: Sequence[Target],
    calibration_path: Path,
    target_config_hash: str | None = None,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    calibration_rows = load_target_pair_rt_calibration(
        calibration_path,
        expected_target_config_hash=target_config_hash,
    )
    rows = build_target_pair_rt_auto_reselection_rows(
        file_results,
        targets=targets,
        calibration_rows=calibration_rows,
    )
    write_target_pair_rt_auto_reselection_tsv(path, rows)
    write_target_pair_rt_auto_reselection_summary_tsv(
        path.with_name("target_pair_rt_auto_reselection_summary.tsv"),
        summarize_target_pair_rt_auto_reselection_rows(rows),
    )


def build_target_pair_rt_auto_reselection_rows(
    file_results: Sequence[FileResultForTargetPairRT],
    *,
    targets: Sequence[Target],
    calibration_rows: Sequence[TargetPairRTCalibrationRow],
) -> list[dict[str, str]]:
    calibration_by_key = {
        (row.target_label, row.paired_istd_label): row for row in calibration_rows
    }
    targets_by_label = {target.label: target for target in targets}
    out: list[dict[str, str]] = []
    for file_result in file_results:
        candidate_lookup = _candidate_lookup(file_result)
        for target in targets:
            paired_label = target.label if target.is_istd else target.istd_pair
            calibration = calibration_by_key.get((target.label, paired_label))
            if calibration is None:
                continue
            result = file_result.results.get(target.label)
            out.append(
                _row_from_result(
                    file_result.sample_name,
                    target,
                    result,
                    calibration,
                    candidate_lookup=candidate_lookup,
                    paired_istd_result=file_result.results.get(paired_label),
                    paired_istd_target=targets_by_label.get(paired_label),
                )
            )
    return out


def write_target_pair_rt_auto_reselection_tsv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            sanitized = _sanitize_row(row, TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS)
            action = sanitized["selection_action"]
            if action not in _ALLOWED_SELECTION_ACTIONS:
                raise ValueError(f"invalid selection_action={action!r}")
            sanitized["product_switch_allowed"] = "FALSE"
            writer.writerow(sanitized)


def write_target_pair_rt_auto_reselection_summary_tsv(
    path: Path,
    summary: Mapping[str, str],
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TARGET_PAIR_RT_AUTO_RESELECTION_SUMMARY_HEADERS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerow(
            _sanitize_row(summary, TARGET_PAIR_RT_AUTO_RESELECTION_SUMMARY_HEADERS)
        )


def summarize_target_pair_rt_auto_reselection_rows(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    limited = sum(
        1
        for row in rows
        if row.get("evidence_comparison_policy") == "limited_evidence_shadow"
    )
    inconclusive = sum(
        1 for row in rows if row.get("selection_status") == "inconclusive"
    )
    blocked_diff = sum(
        1 for row in rows if row.get("selection_status") == "blocked_diff"
    )
    proposed = sum(
        1
        for row in rows
        if row.get("selection_action") == "shadow_auto_reselect_proposed"
    )
    blocked = sum(
        1 for row in rows if row.get("selection_action") == "auto_reselect_blocked"
    )
    changed = sum(
        1
        for row in rows
        if row.get("previous_candidate_id")
        and row.get("selected_candidate_id")
        and row.get("previous_candidate_id") != row.get("selected_candidate_id")
    )
    strata = sorted(
        {
            row.get("missing_ms2_explanation", "") or "ms2_not_classified"
            for row in rows
            if row.get("selection_action") != "none"
        }
    )
    return {
        "limited_evidence_shadow_count": str(limited),
        "inconclusive_count": str(inconclusive),
        "blocked_diff_count": str(blocked_diff),
        "shadow_auto_reselect_proposed_count": str(proposed),
        "auto_reselect_blocked_count": str(blocked),
        "changed_row_denominator": str(changed),
        "false_positive_strata": ";".join(strata),
        "product_switch_allowed_true_count": "0",
        "auto_reselected_count": "0",
    }


def _row_from_result(
    sample_name: str,
    target: Target,
    result: object | None,
    calibration: TargetPairRTCalibrationRow,
    *,
    candidate_lookup: Mapping[tuple[str, str], Mapping[str, str]],
    paired_istd_result: object | None,
    paired_istd_target: Target | None,
) -> dict[str, str]:
    model = getattr(result, "model_selection_result", None)
    previous_candidate_id = getattr(model, "legacy_selected_candidate_id", "")
    selected_candidate_id = getattr(model, "selected_candidate_id", "")
    if not previous_candidate_id:
        selected_hypothesis = getattr(result, "selected_hypothesis", None)
        previous_candidate_id = getattr(selected_hypothesis, "hypothesis_id", "")
    if not selected_candidate_id:
        selected_candidate_id = previous_candidate_id
    previous_rt = _candidate_rt(
        candidate_lookup,
        target.label,
        previous_candidate_id,
        fallback=getattr(result, "reported_rt", None),
    )
    selected_rt = _candidate_rt(
        candidate_lookup,
        target.label,
        selected_candidate_id,
        fallback=getattr(result, "reported_rt", None),
    )
    paired_istd_rt = getattr(paired_istd_result, "reported_rt", None)
    observed_delta = _observed_delta(selected_rt, paired_istd_rt)
    delta_error = (
        observed_delta - calibration.rt_delta_median_min
        if observed_delta is not None
        else None
    )
    selection_status = getattr(model, "selection_status", "inconclusive")
    evidence_policy = getattr(
        model,
        "evidence_comparison_policy",
        "limited_evidence_shadow",
    )
    action, gate_decision, block_reason = _shadow_action(
        previous_candidate_id,
        selected_candidate_id,
        selection_status,
        calibration.activation_block_reason,
        diff_reasons=getattr(model, "diff_reasons", ()),
    )
    trace_group_id = getattr(model, "trace_group_id", "")
    return {
        "sample_name": sample_name,
        "target_label": target.label,
        "role": "ISTD" if target.is_istd else "Analyte",
        "trace_group_id": trace_group_id,
        "previous_candidate_id": previous_candidate_id,
        "selected_candidate_id": selected_candidate_id,
        "selection_action": action,
        "selection_basis": _selection_basis(calibration, target),
        "selection_status": str(selection_status),
        "product_switch_allowed": "FALSE",
        "expected_diff_stable_row_id": getattr(model, "stable_row_id", ""),
        "evidence_comparison_policy": str(evidence_policy),
        "previous_candidate_rt": _format_optional_float(previous_rt),
        "selected_candidate_rt": _format_optional_float(selected_rt),
        "paired_istd_rt": _format_optional_float(paired_istd_rt),
        "pair_rt_delta_expected": _format_optional_float(
            calibration.rt_delta_median_min
        ),
        "pair_rt_delta_observed": _format_optional_float(observed_delta),
        "pair_rt_delta_error": _format_optional_float(delta_error),
        "calibration_source": calibration.delta_source,
        "calibration_status": calibration.calibration_status,
        "missing_ms2_explanation": _missing_ms2_explanation(result),
        "role_policy": _role_policy(target, paired_istd_target),
        "gate_decision": gate_decision,
        "block_reason": block_reason,
    }


def _candidate_lookup(
    file_result: FileResultForTargetPairRT,
) -> dict[tuple[str, str], Mapping[str, str]]:
    lookup: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in file_result.peak_candidate_rows:
        target_label = str(row.get("target_label", ""))
        candidate_id = str(row.get("candidate_id", ""))
        if target_label and candidate_id:
            lookup[(target_label, candidate_id)] = row
    return lookup


def _shadow_action(
    previous_candidate_id: str,
    selected_candidate_id: str,
    selection_status: str,
    calibration_block_reason: str,
    *,
    diff_reasons: Sequence[str],
) -> tuple[str, str, str]:
    reasons = [reason for reason in calibration_block_reason.split(";") if reason]
    hard_shadow_blocks = _hard_shadow_block_reasons(reasons)
    if hard_shadow_blocks:
        hard_shadow_blocks.extend(diff_reasons)
        return (
            "auto_reselect_blocked",
            "no_go",
            ";".join(dict.fromkeys(hard_shadow_blocks)),
        )
    if (
        previous_candidate_id != selected_candidate_id
        and selection_status == "expected_diff"
    ):
        reasons.append("phase_2_product_switch_blocked")
        return (
            "shadow_auto_reselect_proposed",
            "externalize",
            ";".join(dict.fromkeys(reasons)),
        )
    if selection_status in {"blocked_diff", "inconclusive"} or calibration_block_reason:
        reasons.extend(diff_reasons)
        return (
            "auto_reselect_blocked",
            "no_go" if calibration_block_reason else "defer",
            ";".join(dict.fromkeys(reasons)) or str(selection_status),
        )
    return "none", "defer", ""


def _hard_shadow_block_reasons(reasons: Sequence[str]) -> list[str]:
    return [
        reason
        for reason in reasons
        if reason
        in {
            "target_config_hash_mismatch",
            "source_hash_mismatch",
        }
        or reason.startswith("calibration_status:")
    ]


def _selection_basis(
    calibration: TargetPairRTCalibrationRow,
    target: Target,
) -> str:
    if target.is_istd:
        return "role_aware_istd_shadow"
    if target.istd_pair:
        return f"paired_rt_{calibration.delta_source}"
    return "unpaired_target_no_auto_reselection"


def _role_policy(target: Target, paired_istd_target: Target | None) -> str:
    if target.is_istd:
        return "istd"
    if target.istd_pair and paired_istd_target is not None:
        return "paired_analyte"
    return "unpaired_analyte"


def _candidate_rt(
    lookup: Mapping[tuple[str, str], Mapping[str, str]],
    target_label: str,
    candidate_id: str,
    *,
    fallback: object | None,
) -> float | None:
    row = lookup.get((target_label, candidate_id))
    if row is not None:
        parsed = _optional_float(row.get("rt_apex_min", ""))
        if parsed is not None:
            return parsed
    return _optional_float(fallback)


def _observed_delta(
    selected_rt: float | None,
    paired_istd_rt: float | None,
) -> float | None:
    if not _finite(selected_rt) or not _finite(paired_istd_rt):
        return None
    assert selected_rt is not None
    assert paired_istd_rt is not None
    return selected_rt - paired_istd_rt


def _missing_ms2_explanation(result: object | None) -> str:
    evidence = getattr(result, "candidate_ms2_evidence", None)
    if evidence is None:
        token = getattr(result, "nl_token", "") or ""
        return "not_observed" if token == "NO_MS2" else ""
    if not getattr(evidence, "ms2_present", False):
        return "not_observed"
    if getattr(evidence, "strict_nl_scan_count", 0) == 0:
        return (
            "contradicted"
            if getattr(evidence, "trigger_scan_count", 0)
            else "not_observed"
        )
    return ""


def _sanitize_row(
    row: Mapping[str, str],
    headers: Sequence[str],
) -> dict[str, str]:
    return {header: _sanitize_field(str(row.get(header, ""))) for header in headers}


def _sanitize_field(value: str) -> str:
    return " ".join(value.replace("\t", " ").splitlines())


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def _format_optional_float(value: object | None) -> str:
    parsed = _optional_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.5f}"
