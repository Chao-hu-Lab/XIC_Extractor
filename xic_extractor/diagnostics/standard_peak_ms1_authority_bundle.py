from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment import backfill_ms1_product_authority as authority
from xic_extractor.alignment.backfill_evidence_projection import (
    PRODUCT_AUTHORITY_SCOPE_FIELD,
    PRODUCT_AUTHORITY_SOURCE_FIELD,
    PRODUCT_AUTHORITY_STATUS_FIELD,
    PRODUCT_AUTHORIZED_SCOPE,
    PRODUCT_AUTHORIZED_STATUS,
)
from xic_extractor.alignment.promotion_policy import (
    STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
)
from xic_extractor.diagnostics.diagnostic_io import (
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

SCHEMA_VERSION = "standard_peak_ms1_authority_bundle_v0"
DEFAULT_AUTHORITY_SOURCE = "manual_standard_peak_gate_calibration"
STANDARD_PEAK_SUPPORTED = "standard_peak_gate_supported"
MANUAL_AUTHORIZED_CALL = "authorize_standard_peak_backfill"

STANDARD_PEAK_GATE_COLUMNS = (
    "feature_family_id",
    "standard_peak_gate_call",
    "standard_peak_gate_reasons",
    "standard_peak_gate_blockers",
    "manual_backfill_authority_call",
    "calibration_outcome",
    "min_shape_r_after_best_shift",
    "max_abs_shift_sec",
)
OVERLAY_BATCH_COLUMNS = (
    "feature_family_id",
    "family_verdict",
    "detected_count",
    "rescued_count",
    "detected_rescued_count",
    "absolute_own_max_shape_supported_count",
    "trace_summary_tsv",
    "trace_data_json",
)
TRACE_SUMMARY_COLUMNS = (
    "sample_stem",
    "status",
    "cell_area",
    "cell_height",
    "cell_apex_rt",
    "cell_start_rt",
    "cell_end_rt",
    "local_window_apex_delta_min",
    "local_window_to_global_max_ratio",
    "apex_aligned_shape_similarity",
    "absolute_own_max_shape_similarity",
)
MS1_PATTERN_EXTRA_COLUMNS = (
    "shape_metric_source",
    "anchor_peak_own_max_shape_similarity",
    "family_ms1_overlay_trace_data_json",
    "peak_quality_vector_status",
    "peak_quality_vector_basis",
    "standard_peak_gate_call",
    "standard_peak_gate_min_shape_r_after_best_shift",
    "standard_peak_gate_max_abs_shift_sec",
)
MS1_PATTERN_COLUMNS = (
    *authority.required_ms1_pattern_columns(),
    *MS1_PATTERN_EXTRA_COLUMNS,
)


@dataclass(frozen=True)
class StandardPeakAuthorityBundleOutputs:
    ms1_pattern_evidence_tsv: Path
    authority_allowlist_tsv: Path
    authorized_ms1_pattern_tsv: Path
    authority_audit_tsv: Path
    summary_json: Path


def run_standard_peak_ms1_authority_bundle(
    *,
    standard_peak_gate_tsv: Path,
    overlay_batch_summary_tsv: Path,
    output_dir: Path,
    authority_source: str = DEFAULT_AUTHORITY_SOURCE,
    min_anchor_own_max_shape_similarity: float = (
        authority.DEFAULT_MIN_ANCHOR_OWN_MAX_SHAPE_SIMILARITY
    ),
) -> StandardPeakAuthorityBundleOutputs:
    gate_rows = read_tsv_required(standard_peak_gate_tsv, STANDARD_PEAK_GATE_COLUMNS)
    overlay_rows = read_tsv_required(overlay_batch_summary_tsv, OVERLAY_BATCH_COLUMNS)
    overlay_by_family = {
        text_value(row.get("feature_family_id")): row for row in overlay_rows
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_data_dir = output_dir / "trace_data"
    trace_data_dir.mkdir(parents=True, exist_ok=True)

    source_rows: list[dict[str, str]] = []
    allowlist_rows: list[dict[str, str]] = []
    skipped: Counter[str] = Counter()

    for gate_row in gate_rows:
        family_id = text_value(gate_row.get("feature_family_id"))
        if not family_id:
            skipped["missing_family_id"] += 1
            continue
        if not _gate_row_is_authorized_standard_peak(gate_row):
            skipped["gate_not_manual_authorized_standard_peak"] += 1
            continue
        overlay_row = overlay_by_family.get(family_id)
        if overlay_row is None:
            skipped["overlay_summary_missing"] += 1
            continue
        trace_summary_path = _resolve_input_path(
            overlay_row.get("trace_summary_tsv"),
            base_dir=overlay_batch_summary_tsv.parent,
        )
        trace_data_path = _resolve_input_path(
            overlay_row.get("trace_data_json"),
            base_dir=overlay_batch_summary_tsv.parent,
        )
        if trace_summary_path is None or trace_data_path is None:
            skipped["overlay_artifact_missing"] += 1
            continue
        trace_summary_rows = read_tsv_required(
            trace_summary_path,
            TRACE_SUMMARY_COLUMNS,
        )
        copied_trace_path = _copy_trace_data(
            family_id,
            trace_data_path,
            trace_data_dir,
        )
        relative_trace_path = copied_trace_path.relative_to(output_dir).as_posix()
        trace_sha256 = _sha256_file(copied_trace_path)
        for trace_row in trace_summary_rows:
            if text_value(trace_row.get("status")) != "rescued":
                continue
            sample_stem = text_value(trace_row.get("sample_stem"))
            if not sample_stem:
                skipped["trace_sample_missing"] += 1
                continue
            source_rows.append(
                _source_row(
                    family_id=family_id,
                    sample_stem=sample_stem,
                    trace_row=trace_row,
                    overlay_row=overlay_row,
                    gate_row=gate_row,
                    relative_trace_path=relative_trace_path,
                )
            )
            allowlist_rows.append(
                _allowlist_row(
                    family_id=family_id,
                    sample_stem=sample_stem,
                    authority_source=authority_source,
                    authority_reason=_authority_reason(gate_row),
                    relative_trace_path=relative_trace_path,
                    trace_sha256=trace_sha256,
                    min_shape_similarity=min_anchor_own_max_shape_similarity,
                )
            )

    ms1_pattern_tsv = output_dir / "standard_peak_ms1_pattern_coherence_evidence.tsv"
    allowlist_tsv = output_dir / "standard_peak_ms1_product_authority_allowlist.tsv"
    authorized_tsv = (
        output_dir / "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
    )
    audit_tsv = output_dir / "backfill_ms1_pattern_product_authority_audit.tsv"
    summary_json = output_dir / "standard_peak_ms1_authority_bundle_summary.json"

    authorized_rows, audit_rows = _authorize_standard_peak_rows(
        source_rows=source_rows,
        allowlist_rows=allowlist_rows,
        artifact_base_dir=output_dir,
    )
    write_tsv(ms1_pattern_tsv, source_rows, MS1_PATTERN_COLUMNS, lineterminator="\n")
    write_tsv(
        allowlist_tsv,
        allowlist_rows,
        authority.ALLOWLIST_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        authorized_tsv,
        authorized_rows,
        authority.output_columns(MS1_PATTERN_COLUMNS),
        lineterminator="\n",
    )
    write_tsv(
        audit_tsv,
        audit_rows,
        authority.AUDIT_COLUMNS,
        lineterminator="\n",
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "validation_label": "diagnostic_only",
        "product_behavior_changed": False,
        "matrix_contract_changed": False,
        "standard_peak_gate_tsv": str(standard_peak_gate_tsv),
        "standard_peak_gate_sha256": _sha256_file(standard_peak_gate_tsv),
        "overlay_batch_summary_tsv": str(overlay_batch_summary_tsv),
        "overlay_batch_summary_sha256": _sha256_file(overlay_batch_summary_tsv),
        "source_row_count": len(source_rows),
        "allowlist_row_count": len(allowlist_rows),
        "authorized_row_count": len(authorized_rows),
        "authority_rejected_row_count": len(audit_rows) - len(authorized_rows),
        "skipped_counts": dict(sorted(skipped.items())),
        "authority_summary": {
            "schema_version": authority.SCHEMA_VERSION,
            "allowlist_row_count": len(allowlist_rows),
            "source_row_count": len(source_rows),
            "authorized_row_count": len(authorized_rows),
            "rejected_row_count": len(audit_rows) - len(authorized_rows),
            "product_ready": False,
            "readiness_label": "standard_peak_product_authority_sidecar_candidate",
        },
    }
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return StandardPeakAuthorityBundleOutputs(
        ms1_pattern_evidence_tsv=ms1_pattern_tsv,
        authority_allowlist_tsv=allowlist_tsv,
        authorized_ms1_pattern_tsv=authorized_tsv,
        authority_audit_tsv=audit_tsv,
        summary_json=summary_json,
    )


def _gate_row_is_authorized_standard_peak(row: Mapping[str, str]) -> bool:
    return (
        text_value(row.get("standard_peak_gate_call")) == STANDARD_PEAK_SUPPORTED
        and text_value(row.get("manual_backfill_authority_call"))
        == MANUAL_AUTHORIZED_CALL
    )


def _source_row(
    *,
    family_id: str,
    sample_stem: str,
    trace_row: Mapping[str, str],
    overlay_row: Mapping[str, str],
    gate_row: Mapping[str, str],
    relative_trace_path: str,
) -> dict[str, str]:
    own_max = optional_float(trace_row.get("absolute_own_max_shape_similarity"))
    apex_aligned = optional_float(trace_row.get("apex_aligned_shape_similarity"))
    apex_coherence_sec = _abs_min_to_sec(
        trace_row.get("local_window_apex_delta_min")
    )
    local_interference = _local_interference_score(
        trace_row.get("local_window_to_global_max_ratio")
    )
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_stem,
        "ms1_pattern_status": "supportive",
        "ms1_pattern_evidence_level": "trace_constellation",
        "apex_coherence_sec": _format_float(apex_coherence_sec),
        "boundary_overlap_score": "1",
        "shape_correlation_score": _format_float(apex_aligned),
        "relative_pattern_stability_score": _format_float(own_max),
        "local_interference_score": _format_float(local_interference),
        "constellation_peak_count": text_value(
            overlay_row.get("detected_rescued_count")
        ),
        "reference_peak_count": text_value(overlay_row.get("detected_count")),
        "drift_compatible_status": "compatible",
        "reason": STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
        "diagnostic_only": "TRUE",
        "shape_metric_source": "shift_aware_standard_peak_gate",
        "anchor_peak_own_max_shape_similarity": _format_float(own_max),
        "family_ms1_overlay_trace_data_json": relative_trace_path,
        "peak_quality_vector_status": "supportive",
        "peak_quality_vector_basis": "family_ms1_overlay_raw_trace_vector",
        "standard_peak_gate_call": text_value(gate_row.get("standard_peak_gate_call")),
        "standard_peak_gate_min_shape_r_after_best_shift": text_value(
            gate_row.get("min_shape_r_after_best_shift")
        ),
        "standard_peak_gate_max_abs_shift_sec": text_value(
            gate_row.get("max_abs_shift_sec")
        ),
    }


def _authorize_standard_peak_rows(
    *,
    source_rows: Sequence[Mapping[str, str]],
    allowlist_rows: Sequence[Mapping[str, str]],
    artifact_base_dir: Path,
) -> tuple[tuple[dict[str, str], ...], tuple[dict[str, str], ...]]:
    allowlist_by_key = {
        (
            text_value(row.get("feature_family_id")),
            text_value(row.get("sample_stem")),
        ): row
        for row in allowlist_rows
    }
    authorized_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    for source_row in source_rows:
        key = (
            text_value(source_row.get("feature_family_id")),
            text_value(source_row.get("sample_stem")),
        )
        allowlist_row = allowlist_by_key.get(key)
        decision, reason, trace_sha256 = _standard_peak_authority_decision(
            source_row,
            allowlist_row,
            artifact_base_dir=artifact_base_dir,
        )
        audit_rows.append(
            _standard_peak_audit_row(
                key,
                source_row=source_row,
                allowlist_row=allowlist_row,
                decision=decision,
                reason=reason,
                trace_sha256=trace_sha256,
            )
        )
        if decision == "authorized" and allowlist_row is not None:
            authorized_rows.append(
                _standard_peak_authorized_row(
                    source_row,
                    allowlist_row=allowlist_row,
                    trace_sha256=trace_sha256,
                )
            )
    return tuple(authorized_rows), tuple(audit_rows)


def _standard_peak_authority_decision(
    source_row: Mapping[str, str],
    allowlist_row: Mapping[str, str] | None,
    *,
    artifact_base_dir: Path,
) -> tuple[str, str, str]:
    if allowlist_row is None:
        return "rejected", "allowlist_row_missing", ""
    if text_value(allowlist_row.get("authority_status")) != PRODUCT_AUTHORIZED_STATUS:
        return "rejected", "allowlist_status_not_product_authorized", ""
    if text_value(source_row.get("ms1_pattern_status")) != "supportive":
        return "rejected", "source_ms1_pattern_not_supportive", ""
    if (
        text_value(source_row.get("ms1_pattern_evidence_level"))
        != "trace_constellation"
    ):
        return "rejected", "source_ms1_pattern_not_trace_constellation", ""
    if (
        text_value(source_row.get("shape_metric_source"))
        != "shift_aware_standard_peak_gate"
    ):
        return "rejected", "source_shape_metric_not_standard_peak_gate", ""
    if not _has_reason_token(
        source_row.get("reason"),
        STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
    ):
        return "rejected", "source_standard_peak_reason_missing", ""
    trace_status, trace_sha256 = _validate_trace_data(
        source_row,
        artifact_base_dir=artifact_base_dir,
    )
    if trace_status != "valid":
        return "rejected", trace_status, trace_sha256
    expected_sha256 = text_value(
        allowlist_row.get("expected_overlay_trace_data_sha256")
    ).upper()
    if trace_sha256 != expected_sha256:
        return "rejected", "allowlist_overlay_trace_sha256_mismatch", trace_sha256
    return "authorized", "standard_peak_gate_product_authorized", trace_sha256


def _standard_peak_authorized_row(
    source_row: Mapping[str, str],
    *,
    allowlist_row: Mapping[str, str],
    trace_sha256: str,
) -> dict[str, str]:
    row = {key: text_value(value) for key, value in source_row.items()}
    row["diagnostic_only"] = "FALSE"
    row[PRODUCT_AUTHORITY_STATUS_FIELD] = PRODUCT_AUTHORIZED_STATUS
    row[PRODUCT_AUTHORITY_SCOPE_FIELD] = PRODUCT_AUTHORIZED_SCOPE
    row[PRODUCT_AUTHORITY_SOURCE_FIELD] = text_value(
        allowlist_row.get("authority_source")
    )
    row["product_authority_reason"] = text_value(
        allowlist_row.get("authority_reason")
    ) or "standard_peak_gate_product_authorized"
    row["product_authority_overlay_trace_data_json"] = text_value(
        source_row.get("family_ms1_overlay_trace_data_json")
    )
    row["product_authority_min_anchor_own_max_shape_similarity"] = text_value(
        allowlist_row.get("min_anchor_own_max_shape_similarity")
    )
    row["product_authority_observed_anchor_own_max_shape_similarity"] = text_value(
        source_row.get("anchor_peak_own_max_shape_similarity")
    )
    row["product_authority_overlay_trace_data_sha256"] = trace_sha256
    row["product_authority_expected_overlay_trace_data_sha256"] = text_value(
        allowlist_row.get("expected_overlay_trace_data_sha256")
    ).upper()
    return row


def _standard_peak_audit_row(
    key: tuple[str, str],
    *,
    source_row: Mapping[str, str],
    allowlist_row: Mapping[str, str] | None,
    decision: str,
    reason: str,
    trace_sha256: str,
) -> dict[str, str]:
    allowlist = allowlist_row or {}
    return {
        "schema_version": authority.SCHEMA_VERSION,
        "feature_family_id": key[0],
        "sample_stem": key[1],
        "authority_status": text_value(allowlist.get("authority_status")),
        "decision": decision,
        "decision_reason": reason,
        "source_ms1_pattern_status": text_value(
            source_row.get("ms1_pattern_status")
        ),
        "source_ms1_pattern_evidence_level": text_value(
            source_row.get("ms1_pattern_evidence_level")
        ),
        "source_anchor_own_max_shape_similarity": text_value(
            source_row.get("anchor_peak_own_max_shape_similarity")
        ),
        "source_overlay_trace_data_status": (
            "valid" if decision == "authorized" else reason
        ),
        "source_overlay_trace_data_json": text_value(
            source_row.get("family_ms1_overlay_trace_data_json")
        ),
        "source_overlay_trace_data_sha256": trace_sha256,
        "expected_overlay_trace_data_json": text_value(
            allowlist.get("expected_overlay_trace_data_json")
        ),
        "expected_overlay_trace_data_sha256": text_value(
            allowlist.get("expected_overlay_trace_data_sha256")
        ).upper(),
    }


def _allowlist_row(
    *,
    family_id: str,
    sample_stem: str,
    authority_source: str,
    authority_reason: str,
    relative_trace_path: str,
    trace_sha256: str,
    min_shape_similarity: float,
) -> dict[str, str]:
    return {
        "schema_version": authority.SCHEMA_VERSION,
        "feature_family_id": family_id,
        "sample_stem": sample_stem,
        "authority_status": PRODUCT_AUTHORIZED_STATUS,
        "authority_source": authority_source,
        "authority_reason": authority_reason,
        "expected_overlay_trace_data_json": relative_trace_path,
        "expected_overlay_trace_data_sha256": trace_sha256,
        "min_anchor_own_max_shape_similarity": _format_float(min_shape_similarity),
    }


def _authority_reason(row: Mapping[str, str]) -> str:
    parts = [
        "manual_standard_peak_gate_authorized",
        text_value(row.get("calibration_outcome")),
        text_value(row.get("standard_peak_gate_reasons")),
    ]
    return ";".join(part for part in parts if part)


def _validate_trace_data(
    source_row: Mapping[str, str],
    *,
    artifact_base_dir: Path,
) -> tuple[str, str]:
    path = artifact_base_dir / text_value(
        source_row.get("family_ms1_overlay_trace_data_json")
    )
    try:
        payload = path.read_bytes()
    except OSError:
        return "source_overlay_trace_json_unreadable", ""
    trace_sha256 = hashlib.sha256(payload).hexdigest().upper()
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "source_overlay_trace_json_invalid", trace_sha256
    if not isinstance(data, dict):
        return "source_overlay_trace_json_not_object", trace_sha256
    family_id = text_value(source_row.get("feature_family_id"))
    if text_value(data.get("family_id")) != family_id:
        return "source_overlay_trace_family_mismatch", trace_sha256
    traces = data.get("traces")
    if not isinstance(traces, list):
        return "source_overlay_trace_json_missing_traces", trace_sha256
    sample_stem = text_value(source_row.get("sample_stem"))
    matching = [
        trace
        for trace in traces
        if isinstance(trace, dict)
        and text_value(trace.get("sample_stem")) == sample_stem
    ]
    if not matching:
        return "source_overlay_trace_sample_missing", trace_sha256
    if len(matching) > 1:
        return "source_overlay_trace_sample_duplicate", trace_sha256
    trace = matching[0]
    rt = _numeric_sequence(trace.get("rt"))
    intensity = _numeric_sequence(trace.get("intensity"))
    if len(rt) < 3 or len(intensity) < 3 or len(rt) != len(intensity):
        return "source_overlay_trace_vector_invalid", trace_sha256
    return "valid", trace_sha256


def _numeric_sequence(value: object) -> tuple[float, ...]:
    if not isinstance(value, list):
        return ()
    parsed: list[float] = []
    for item in value:
        parsed_value = optional_float(item)
        if parsed_value is None:
            return ()
        parsed.append(parsed_value)
    return tuple(parsed)


def _has_reason_token(value: object, token: str) -> bool:
    return token in {
        part.strip()
        for part in text_value(value).split(";")
        if part.strip()
    }


def _resolve_input_path(value: object, *, base_dir: Path) -> Path | None:
    text = text_value(value)
    if not text:
        return None
    path = Path(text)
    candidates = [path] if path.is_absolute() else [base_dir / path, path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _copy_trace_data(family_id: str, source: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{_safe_stem(family_id)}_trace_data.json"
    shutil.copy2(source, destination)
    return destination


def _safe_stem(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in value
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _abs_min_to_sec(value: object) -> float | None:
    parsed = optional_float(value)
    if parsed is None:
        return None
    return abs(parsed) * 60.0


def _local_interference_score(value: object) -> float | None:
    ratio = optional_float(value)
    if ratio is None:
        return None
    return max(0.0, 1.0 - ratio)


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"
