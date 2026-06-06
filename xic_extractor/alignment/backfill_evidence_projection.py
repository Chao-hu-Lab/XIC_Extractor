from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    machine_evidence_support as evidence_support,
)
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required, text_value

BACKFILL_PROJECTION_COLUMNS = (
    "backfill_ms1_pattern_status",
    "backfill_ms1_pattern_evidence_level",
    "backfill_qc_reference_status",
    "backfill_qc_reference_evidence_level",
    "backfill_matrix_rt_drift_status",
    "backfill_drift_evidence_level",
    "backfill_drift_compatible_status",
    "backfill_drift_corrected_delta_sec",
    "backfill_candidate_ms2_pattern_status",
    "backfill_candidate_ms2_evidence_level",
    "backfill_ms2_trigger_scan_count",
    "backfill_strict_nl_scan_count",
    "backfill_ms2_trace_strength",
    "backfill_dda_missing_nl_policy_status",
    "backfill_family_ms2_required_tag_status",
    "backfill_evidence_reason",
)

_CANDIDATE_MS2_SUPPORT_STATUSES = frozenset({"supportive", "partial_support"})
_CANDIDATE_MS2_OBSERVED_LEVELS = frozenset(
    {"sample_candidate_aligned", "sample_boundary_aligned"}
)
_DDA_NON_DISPOSITIVE_TRIGGER_SCAN_MIN = 3
_DDA_NON_DISPOSITIVE_TRACE_STRENGTHS = frozenset({"moderate", "strong"})


def load_candidate_ms2_pattern_rows(
    path: Path | None,
) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(
        path,
        evidence_support.CANDIDATE_MS2_PATTERN_REQUIRED_COLUMNS,
    )


def load_ms1_pattern_coherence_rows(
    path: Path | None,
) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(
        path,
        evidence_support.MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS,
    )


def load_qc_ms1_pattern_reference_rows(
    path: Path | None,
) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(
        path,
        evidence_support.QC_MS1_PATTERN_REFERENCE_REQUIRED_COLUMNS,
    )


def load_matrix_rt_drift_policy_rows(
    path: Path | None,
) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(
        path,
        evidence_support.MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS,
    )


def project_backfill_evidence_to_cells(
    *,
    cell_rows: Sequence[Mapping[str, str]],
    candidate_ms2_pattern_rows: Sequence[Mapping[str, str]] = (),
    ms1_pattern_coherence_rows: Sequence[Mapping[str, str]] = (),
    qc_ms1_pattern_reference_rows: Sequence[Mapping[str, str]] = (),
    matrix_rt_drift_policy_rows: Sequence[Mapping[str, str]] = (),
) -> tuple[dict[str, str], ...]:
    candidate_ms2 = _rows_by_key(candidate_ms2_pattern_rows)
    ms1_pattern = _rows_by_key(ms1_pattern_coherence_rows)
    qc_reference = _rows_by_key(qc_ms1_pattern_reference_rows)
    rt_drift = _rows_by_key(matrix_rt_drift_policy_rows)
    family_required_tag = _family_ms2_required_tag_by_family(candidate_ms2)

    projected_rows: list[dict[str, str]] = []
    for cell in cell_rows:
        row = dict(cell)
        _ensure_projection_columns(row)
        if text_value(row.get("status")) != "rescued":
            projected_rows.append(row)
            continue

        family_id = text_value(row.get("feature_family_id"))
        sample_stem = text_value(row.get("sample_stem") or row.get("sample_id"))
        if not family_id or not sample_stem:
            projected_rows.append(row)
            continue

        key = (family_id, sample_stem)
        source_tokens: list[str] = []
        if _copy_projection(
            row,
            ms1_pattern.get(key),
            {
                "ms1_pattern_status": "backfill_ms1_pattern_status",
                "ms1_pattern_evidence_level": (
                    "backfill_ms1_pattern_evidence_level"
                ),
            },
        ):
            source_tokens.append("ms1_pattern_coherence")
        if _copy_projection(
            row,
            qc_reference.get(key),
            {
                "qc_reference_status": "backfill_qc_reference_status",
                "qc_reference_evidence_level": (
                    "backfill_qc_reference_evidence_level"
                ),
            },
        ):
            source_tokens.append("qc_ms1_pattern_reference")
        if _copy_projection(
            row,
            rt_drift.get(key),
            {
                "matrix_rt_drift_status": "backfill_matrix_rt_drift_status",
                "drift_evidence_level": "backfill_drift_evidence_level",
                "drift_compatible_status": "backfill_drift_compatible_status",
                "drift_corrected_delta_sec": (
                    "backfill_drift_corrected_delta_sec"
                ),
            },
        ):
            source_tokens.append("matrix_rt_drift_policy")

        candidate = candidate_ms2.get(key)
        if _copy_projection(
            row,
            candidate,
            {
                "candidate_ms2_pattern_status": (
                    "backfill_candidate_ms2_pattern_status"
                ),
                "candidate_ms2_evidence_level": (
                    "backfill_candidate_ms2_evidence_level"
                ),
                "raw_ms2_trigger_scan_count": "backfill_ms2_trigger_scan_count",
                "raw_ms2_strict_nl_scan_count": "backfill_strict_nl_scan_count",
                "raw_ms2_trace_strength": "backfill_ms2_trace_strength",
            },
        ):
            source_tokens.append("candidate_ms2_pattern")
        if _dda_missing_nl_not_dispositive(candidate):
            row["backfill_dda_missing_nl_policy_status"] = "not_dispositive"
            _append_unique(source_tokens, "dda_missing_nl_policy")
        if family_id in family_required_tag:
            row["backfill_family_ms2_required_tag_status"] = "observed_in_family"
            _append_unique(source_tokens, "family_ms2_required_tag")

        row["backfill_evidence_reason"] = _merged_reason(
            row.get("backfill_evidence_reason", ""),
            source_tokens,
        )
        projected_rows.append(row)
    return tuple(projected_rows)


def _rows_by_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        family_id = text_value(row.get("feature_family_id"))
        sample_stem = text_value(row.get("sample_stem") or row.get("sample_id"))
        if family_id and sample_stem:
            by_key[(family_id, sample_stem)] = row
    return by_key


def _family_ms2_required_tag_by_family(
    rows_by_key: Mapping[tuple[str, str], Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    observed: dict[str, Mapping[str, str]] = {}
    for family_id, _sample_stem in rows_by_key:
        row = rows_by_key[(family_id, _sample_stem)]
        if family_id and family_id not in observed and _has_required_tag(row):
            observed[family_id] = row
    return observed


def _has_required_tag(row: Mapping[str, str] | None) -> bool:
    if not row:
        return False
    if (
        row.get("candidate_ms2_pattern_status")
        not in _CANDIDATE_MS2_SUPPORT_STATUSES
    ):
        return False
    if row.get("candidate_ms2_evidence_level") not in (
        _CANDIDATE_MS2_OBSERVED_LEVELS
    ):
        return False
    return any(
        (count := _int_or_none(row.get(field))) is not None and count >= 1
        for field in (
            "raw_ms2_strict_nl_scan_count",
            "matched_neutral_loss_count",
            "source_matched_tag_count",
        )
    )


def _dda_missing_nl_not_dispositive(row: Mapping[str, str] | None) -> bool:
    if not row:
        return False
    if row.get("candidate_ms2_pattern_status") != "not_observed":
        return False
    if (
        row.get("candidate_ms2_evidence_level")
        != "sample_boundary_no_observed_pattern"
    ):
        return False
    trigger_count = _int_or_none(row.get("raw_ms2_trigger_scan_count"))
    if trigger_count is None or trigger_count < _DDA_NON_DISPOSITIVE_TRIGGER_SCAN_MIN:
        return False
    strict_nl_count = _int_or_none(row.get("raw_ms2_strict_nl_scan_count"))
    if strict_nl_count not in {0, None}:
        return False
    return (
        row.get("raw_ms2_trace_strength") in _DDA_NON_DISPOSITIVE_TRACE_STRENGTHS
        or row.get("raw_ms2_diagnostic_product_absence_reason")
        == "product_outside_diagnostic_window"
    )


def _copy_projection(
    row: dict[str, str],
    source: Mapping[str, str] | None,
    mapping: Mapping[str, str],
) -> bool:
    if source is None:
        return False
    copied = False
    for source_field, destination_field in mapping.items():
        value = text_value(source.get(source_field))
        if value:
            row[destination_field] = value
            copied = True
    return copied


def _ensure_projection_columns(row: dict[str, str]) -> None:
    for column in BACKFILL_PROJECTION_COLUMNS:
        row.setdefault(column, "")


def _merged_reason(existing: object, tokens: Sequence[str]) -> str:
    parts = [part for part in text_value(existing).split(";") if part]
    for token in tokens:
        _append_unique(parts, token)
    return ";".join(parts)


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _int_or_none(value: object) -> int | None:
    try:
        text = text_value(value)
        return int(float(text)) if text else None
    except (TypeError, ValueError):
        return None
