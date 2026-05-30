from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.diagnostics.diagnostic_io import read_tsv_required
from xic_extractor.alignment.config import AlignmentConfig

from .machine_artifacts import MachineMatch
from .schema import (
    MACHINE_EVIDENCE_SUPPORT_SCHEMA_VERSION,
    validate_row_tokens,
)

_POSITIVE_MACHINE_LABELS = frozenset(
    {"detected", "rescued", "selected", "present", "provisional_discovery"}
)
_ABSENT_MACHINE_LABELS = frozenset(
    {"absent", "missing", "no_match", "not_available", "not_detected", "unchecked"}
)
_RT_TAGS = frozenset({"rt_close", "rt_too_far", "rt_drift_possible"})
_SHAPE_TAGS = frozenset({"shape_complete", "shape_normal", "shape_bad"})
_PATTERN_TAGS = frozenset({"pattern_similar", "pattern_partial", "pattern_mismatch"})
_OPPORTUNITY_TAGS = frozenset({"low_intensity", "dda_stochastic_missing"})
_DEFAULT_ALIGNMENT_CONFIG = AlignmentConfig()
CWT_SHAPE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "cwt_status",
    "cwt_nearest_apex_rt",
    "cwt_apex_delta_sec",
    "cwt_boundary_width_sec",
    "cwt_prominence",
    "cwt_region_scan_count",
    "cwt_quality_flags",
    "cwt_shape_status",
)
TIER2_TRACE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "raw_trace_reread_status",
    "scan_support_score",
    "trace_scan_count",
    "scan_availability_score",
    "trace_signal_to_noise_proxy",
    "trace_apex_prominence_score",
    "challenge_blockers",
)
CANDIDATE_MS2_PATTERN_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "candidate_ms2_pattern_status",
    "candidate_ms2_evidence_level",
)
_CANDIDATE_MS2_OBSERVED_LEVELS = frozenset(
    {"sample_candidate_aligned", "sample_boundary_aligned"}
)
_CANDIDATE_MS2_SUPPORT_STATUSES = frozenset({"supportive", "partial_support"})
_CANDIDATE_MS2_CONFLICT_STATUSES = frozenset({"conflict"})


def load_cwt_shape_evidence(
    path: Path | None,
) -> dict[tuple[str, str], Mapping[str, str]]:
    if path is None:
        return {}
    rows = read_tsv_required(path, CWT_SHAPE_REQUIRED_COLUMNS)
    return {
        (row["feature_family_id"], row["sample_stem"]): row
        for row in rows
    }


def load_tier2_trace_evidence(path: Path | None) -> dict[str, Mapping[str, str]]:
    if path is None:
        return {}
    rows = read_tsv_required(path, TIER2_TRACE_REQUIRED_COLUMNS)
    return {row["feature_family_id"]: row for row in rows}


def load_candidate_ms2_pattern_evidence(
    path: Path | None,
) -> dict[tuple[str, str], Mapping[str, str]]:
    if path is None:
        return {}
    rows = read_tsv_required(path, CANDIDATE_MS2_PATTERN_REQUIRED_COLUMNS)
    return {
        (row["feature_family_id"], row["sample_stem"]): row
        for row in rows
    }


def build_machine_evidence_support_rows(
    *,
    explanations: Sequence[Mapping[str, str]],
    shadow_rows: Sequence[Mapping[str, str]],
    machine_matches: Mapping[str, Sequence[MachineMatch]],
    cwt_shape_evidence: Mapping[tuple[str, str], Mapping[str, str]] | None = None,
    tier2_trace_evidence: Mapping[str, Mapping[str, str]] | None = None,
    candidate_ms2_pattern_evidence: Mapping[
        tuple[str, str], Mapping[str, str]
    ] | None = None,
) -> tuple[dict[str, str], ...]:
    shadow_by_id = {row["oracle_row_id"]: row for row in shadow_rows}
    cwt_shape_evidence = cwt_shape_evidence or {}
    tier2_trace_evidence = tier2_trace_evidence or {}
    candidate_ms2_pattern_evidence = candidate_ms2_pattern_evidence or {}
    support_rows = [
        _support_row(
            explanation=explanation,
            shadow=shadow_by_id.get(explanation["oracle_row_id"], {}),
            matches=tuple(machine_matches.get(explanation["oracle_row_id"], ())),
            cwt_row=cwt_shape_evidence.get(
                (explanation["feature_family_id"], explanation["sample_id"]),
            ),
            tier2_row=tier2_trace_evidence.get(explanation["feature_family_id"]),
            candidate_ms2_row=candidate_ms2_pattern_evidence.get(
                (explanation["feature_family_id"], explanation["sample_id"]),
            ),
        )
        for explanation in explanations
    ]
    return tuple(
        sorted(
            support_rows,
            key=lambda row: (row["feature_family_id"], row["sample_id"]),
        )
    )


def _support_row(
    *,
    explanation: Mapping[str, str],
    shadow: Mapping[str, str],
    matches: Sequence[MachineMatch],
    cwt_row: Mapping[str, str] | None,
    tier2_row: Mapping[str, str] | None,
    candidate_ms2_row: Mapping[str, str] | None,
) -> dict[str, str]:
    tags = _tags(explanation)
    sample_matches = tuple(match for match in matches if match.sample_level)
    context_matches = tuple(match for match in matches if not match.sample_level)
    observed_metrics = _observed_machine_metrics(
        sample_matches,
        context_matches,
        cwt_row=cwt_row,
        tier2_row=tier2_row,
        candidate_ms2_row=candidate_ms2_row,
    )
    manual_facts = _manual_derived_facts(tags, explanation)
    missing_evidence = _missing_machine_evidence(
        explanation=explanation,
        tags=tags,
        sample_matches=sample_matches,
        context_matches=context_matches,
        cwt_row=cwt_row,
        tier2_row=tier2_row,
        candidate_ms2_row=candidate_ms2_row,
    )
    literature_refs = _literature_refs(
        tags=tags,
        missing_evidence=missing_evidence,
        explanation=explanation,
    )
    row = {
        "machine_evidence_support_schema_version": (
            MACHINE_EVIDENCE_SUPPORT_SCHEMA_VERSION
        ),
        "oracle_row_id": explanation["oracle_row_id"],
        "feature_family_id": explanation["feature_family_id"],
        "sample_id": explanation["sample_id"],
        "manual_label": explanation["manual_label"],
        "machine_current_label": explanation["machine_current_label"],
        "shadow_label": shadow.get("shadow_label", "unresolved_gap"),
        "shadow_alignment_status": shadow.get(
            "shadow_alignment_status",
            "unresolved",
        ),
        "status_label_alignment_status": _status_label_alignment_status(
            manual_label=explanation["manual_label"],
            machine_label=explanation["machine_current_label"],
        ),
        "rt_basis_status": _rt_basis_status(tags, sample_matches),
        "shape_basis_status": _shape_basis_status(tags, sample_matches, cwt_row),
        "pattern_basis_status": _pattern_basis_status(
            tags,
            context_matches,
            candidate_ms2_row,
        ),
        "opportunity_basis_status": _opportunity_basis_status(
            tags,
            sample_matches,
            context_matches,
            tier2_row,
        ),
        "scope_basis_status": _scope_basis_status(explanation, tags),
        "observed_machine_metrics": observed_metrics,
        "manual_derived_facts": manual_facts,
        "missing_machine_evidence": ";".join(missing_evidence),
        "literature_support_refs": ";".join(literature_refs),
        "evidence_support_status": _evidence_support_status(
            manual_label=explanation["manual_label"],
            sample_id=explanation["sample_id"],
            missing_evidence=missing_evidence,
            observed_metrics=observed_metrics,
            manual_facts=manual_facts,
            has_machine_observed_metric=_has_machine_observed_metric(
                cwt_row=cwt_row,
                tier2_row=tier2_row,
                candidate_ms2_row=candidate_ms2_row,
            ),
        ),
        "diagnostic_only": "TRUE",
    }
    validate_row_tokens(row)
    return row


def _status_label_alignment_status(*, manual_label: str, machine_label: str) -> str:
    if manual_label == "not_applicable":
        return "context_only"
    if manual_label == "human_unjudgeable":
        return "not_evaluable"
    if machine_label in _POSITIVE_MACHINE_LABELS:
        if manual_label == "pass":
            return "proxy_agrees"
        if manual_label == "suspect":
            return "proxy_partial"
        if manual_label == "fail":
            return "proxy_contradicts"
    if machine_label in _ABSENT_MACHINE_LABELS:
        if manual_label == "fail":
            return "proxy_agrees"
        if manual_label == "suspect":
            return "proxy_partial"
        if manual_label == "pass":
            return "proxy_contradicts"
    return "not_available"


def _rt_basis_status(
    tags: frozenset[str],
    sample_matches: Sequence[MachineMatch],
) -> str:
    if any(_has_value(match.row.get("apex_rt")) for match in sample_matches) and any(
        _has_value(match.row.get("rt_delta_sec")) for match in sample_matches
    ):
        return "machine_observed"
    if tags & _RT_TAGS:
        return "manual_oracle_derived"
    return "not_available"


def _shape_basis_status(
    tags: frozenset[str],
    sample_matches: Sequence[MachineMatch],
    cwt_row: Mapping[str, str] | None,
) -> str:
    if _has_cwt_metric(cwt_row):
        return "machine_observed"
    has_proxy = any(
        _has_value(match.row.get("trace_quality")) for match in sample_matches
    )
    has_manual = bool(tags & _SHAPE_TAGS)
    return _basis_status(has_machine_proxy=has_proxy, has_manual=has_manual)


def _pattern_basis_status(
    tags: frozenset[str],
    context_matches: Sequence[MachineMatch],
    candidate_ms2_row: Mapping[str, str] | None,
) -> str:
    if _has_candidate_ms2_pattern_metric(candidate_ms2_row):
        return "machine_observed"
    has_family_proxy = any(
        _has_value(match.row.get("neutral_loss_tag")) for match in context_matches
    )
    return _basis_status(
        has_machine_proxy=has_family_proxy,
        has_manual=bool(tags & _PATTERN_TAGS),
    )


def _opportunity_basis_status(
    tags: frozenset[str],
    sample_matches: Sequence[MachineMatch],
    context_matches: Sequence[MachineMatch],
    tier2_row: Mapping[str, str] | None,
) -> str:
    if _has_tier2_trace_metric(tier2_row):
        return "machine_observed"
    machine_tokens = _machine_tokens(sample_matches, context_matches)
    has_proxy = any(
        _has_value(match.row.get("scan_support_score")) for match in sample_matches
    ) or bool(
        machine_tokens
        & {
            "low_scan_support",
            "weak_scan_support",
            "no_local_ms1_owner",
            "metric_unavailable",
        }
    )
    return _basis_status(
        has_machine_proxy=has_proxy,
        has_manual=bool(tags & _OPPORTUNITY_TAGS),
    )


def _scope_basis_status(
    explanation: Mapping[str, str],
    tags: frozenset[str],
) -> str:
    if (
        explanation.get("manual_scope") == "scope_derived_unmentioned_fail"
        or "scope_derived_unmentioned_fail" in tags
    ):
        return "manual_oracle_derived"
    return "not_applicable"


def _basis_status(*, has_machine_proxy: bool, has_manual: bool) -> str:
    if has_machine_proxy and has_manual:
        return "mixed"
    if has_machine_proxy:
        return "machine_proxy"
    if has_manual:
        return "manual_oracle_derived"
    return "not_available"


def _observed_machine_metrics(
    sample_matches: Sequence[MachineMatch],
    context_matches: Sequence[MachineMatch],
    *,
    cwt_row: Mapping[str, str] | None,
    tier2_row: Mapping[str, str] | None,
    candidate_ms2_row: Mapping[str, str] | None,
) -> str:
    metrics: list[str] = []
    if sample_matches:
        first_sample = sample_matches[0].row
        _append_metric(metrics, "status", first_sample.get("status"))
        _append_metric(metrics, "apex_rt", first_sample.get("apex_rt"))
        _append_metric(metrics, "rt_delta_sec", first_sample.get("rt_delta_sec"))
        if _has_rt_preferred_window_conflict(sample_matches):
            metrics.append("rt_preferred_window_status=outside_preferred_window")
        _append_metric(metrics, "trace_quality", first_sample.get("trace_quality"))
        _append_metric(
            metrics,
            "scan_support_score",
            first_sample.get("scan_support_score"),
        )
        width_sec = _peak_width_sec(first_sample)
        if width_sec:
            metrics.append(f"peak_width_sec={width_sec}")
    for match in context_matches:
        if match.evidence_source == "alignment_review":
            if _has_cid_nl_pattern_context((match,)):
                metrics.append("cid_nl_pattern_context=family_level_present")
            _append_metric(
                metrics,
                "neutral_loss_tag",
                match.row.get("neutral_loss_tag"),
            )
            _append_metric(
                metrics,
                "family_product_mz",
                match.row.get("family_product_mz"),
            )
            _append_metric(
                metrics,
                "family_observed_neutral_loss_da",
                match.row.get("family_observed_neutral_loss_da"),
            )
            break
    if cwt_row:
        _append_metric(metrics, "cwt_status", cwt_row.get("cwt_status"))
        _append_metric(metrics, "cwt_shape_status", cwt_row.get("cwt_shape_status"))
        _append_metric(metrics, "cwt_apex_delta_sec", cwt_row.get("cwt_apex_delta_sec"))
        _append_metric(
            metrics,
            "cwt_boundary_width_sec",
            cwt_row.get("cwt_boundary_width_sec"),
        )
        _append_metric(metrics, "cwt_prominence", cwt_row.get("cwt_prominence"))
        _append_metric(
            metrics,
            "cwt_region_scan_count",
            cwt_row.get("cwt_region_scan_count"),
        )
        _append_metric(
            metrics,
            "cwt_quality_flags",
            cwt_row.get("cwt_quality_flags"),
        )
    if tier2_row:
        _append_metric(
            metrics,
            "tier2_raw_trace_status",
            tier2_row.get("raw_trace_reread_status"),
        )
        _append_metric(
            metrics,
            "tier2_scan_support_score",
            tier2_row.get("scan_support_score"),
        )
        _append_metric(
            metrics,
            "tier2_trace_scan_count",
            tier2_row.get("trace_scan_count"),
        )
        _append_metric(
            metrics,
            "tier2_sn_proxy",
            tier2_row.get("trace_signal_to_noise_proxy"),
        )
        _append_metric(
            metrics,
            "tier2_apex_prominence_score",
            tier2_row.get("trace_apex_prominence_score"),
        )
    if candidate_ms2_row:
        _append_metric(
            metrics,
            "candidate_ms2_pattern_status",
            candidate_ms2_row.get("candidate_ms2_pattern_status"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_evidence_level",
            candidate_ms2_row.get("candidate_ms2_evidence_level"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_similarity_score",
            candidate_ms2_row.get("candidate_ms2_similarity_score"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_matched_product_count",
            candidate_ms2_row.get("matched_product_count"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_matched_neutral_loss_count",
            candidate_ms2_row.get("matched_neutral_loss_count"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_apex_delta_sec",
            candidate_ms2_row.get("apex_ms2_delta_sec"),
        )
        _append_metric(
            metrics,
            "candidate_ms2_alignment_source",
            candidate_ms2_row.get("ms2_alignment_source"),
        )
    return ";".join(metrics)


def _manual_derived_facts(
    tags: frozenset[str],
    explanation: Mapping[str, str],
) -> str:
    facts = sorted(
        tag
        for tag in tags
        if tag
        in (
            _RT_TAGS
            | _SHAPE_TAGS
            | _PATTERN_TAGS
            | _OPPORTUNITY_TAGS
            | {"scope_derived_unmentioned_fail", "human_unjudgeable"}
        )
    )
    if explanation.get("manual_label") == "human_unjudgeable":
        facts.append("manual_label:human_unjudgeable")
    return ";".join(_unique(facts))


def _missing_machine_evidence(
    *,
    explanation: Mapping[str, str],
    tags: frozenset[str],
    sample_matches: Sequence[MachineMatch],
    context_matches: Sequence[MachineMatch],
    cwt_row: Mapping[str, str] | None,
    tier2_row: Mapping[str, str] | None,
    candidate_ms2_row: Mapping[str, str] | None,
) -> tuple[str, ...]:
    missing: list[str] = []
    gap_class = explanation.get("evidence_gap_class", "")
    if tags & _SHAPE_TAGS and not _has_cwt_metric(cwt_row):
        missing.append("formal_shape_metric")
    if _cwt_conflicts_with_manual(tags, cwt_row):
        missing.append("shape_metric_not_supportive")
    if (
        tags & _PATTERN_TAGS
        and not _has_candidate_ms2_pattern_metric(candidate_ms2_row)
    ):
        missing.append("formal_pattern_metric")
    if tags & _OPPORTUNITY_TAGS:
        if not _has_tier2_trace_metric(tier2_row):
            missing.append("intensity_opportunity_metric")
        missing.append("dda_opportunity_policy")
    if "rt_drift_possible" in tags:
        missing.append("matrix_rt_drift_policy")
    if "rt_too_far" in tags and not _has_rt_preferred_window_conflict(
        sample_matches
    ):
        missing.append("rt_pattern_conflict_gate")
    if _candidate_ms2_conflicts_with_manual(tags, candidate_ms2_row):
        missing.append("pattern_metric_not_supportive")
    if (
        "pattern_mismatch" in tags
        and not _candidate_ms2_supports_manual(tags, candidate_ms2_row)
        and not _has_candidate_ms2_pattern_metric(candidate_ms2_row)
    ):
        missing.append("candidate_aligned_ms2_pattern")
    if (
        explanation.get("manual_scope") == "scope_derived_unmentioned_fail"
        or "scope_derived_unmentioned_fail" in tags
        or gap_class == "machine_too_permissive_scope_rule_conflict"
    ):
        missing.extend(("manual_scope_policy", "sample_level_negative_evidence"))
    if explanation.get("manual_label") == "human_unjudgeable":
        missing.append("human_review_or_retire_from_training")
    if "delta_mass_related" in tags:
        missing.append("delta_mass_family_model")
    if not sample_matches and explanation.get("manual_label") not in {
        "not_applicable",
        "human_unjudgeable",
    }:
        missing.append("sample_level_machine_observation")
    if (
        not context_matches
        and tags & _PATTERN_TAGS
        and not _has_candidate_ms2_pattern_metric(candidate_ms2_row)
    ):
        missing.append("family_ms2_pattern_context")
    return _unique(missing)


def _literature_refs(
    *,
    tags: frozenset[str],
    missing_evidence: Sequence[str],
    explanation: Mapping[str, str],
) -> tuple[str, ...]:
    refs: list[str] = ["sumner_2007_msi"]
    if tags & _SHAPE_TAGS or "formal_shape_metric" in missing_evidence:
        refs.extend(
            (
                "scipy_signal_find_peaks_cwt_docs",
                "tautenhahn_2008_centwave",
                "zhang_2014_eic_quality",
                "kumler_2023_peak_quality",
            )
        )
    if tags & _PATTERN_TAGS or "candidate_aligned_ms2_pattern" in missing_evidence:
        refs.extend(
            (
                "neutral_loss_product_ion_annotation",
                "watrous_2012_gnps_molecular_networking",
                "huber_2021_spec2vec",
                "biesinger_2022_spectral_alignment",
            )
        )
    if tags & _OPPORTUNITY_TAGS or "dda_opportunity_policy" in missing_evidence:
        refs.extend(("koelmel_2017_iterative_exclusion", "tsugawa_2017_ts_dda"))
    if tags & _RT_TAGS or "matrix_rt_drift_policy" in missing_evidence:
        refs.extend(("prince_2006_obiwarp", "gika_2010_nonlinear_rt_alignment"))
    if (
        explanation.get("manual_scope") == "scope_derived_unmentioned_fail"
        or "sample_level_negative_evidence" in missing_evidence
    ):
        refs.append("sumner_2007_msi")
    return _unique(refs)


def _evidence_support_status(
    *,
    manual_label: str,
    sample_id: str,
    missing_evidence: Sequence[str],
    observed_metrics: str,
    manual_facts: str,
    has_machine_observed_metric: bool,
) -> str:
    if manual_label == "not_applicable" or sample_id == "__family_context__":
        return "context_only"
    if manual_label == "human_unjudgeable":
        return "not_evaluable"
    if "shape_metric_not_supportive" in missing_evidence:
        return "machine_observed_conflict"
    if "pattern_metric_not_supportive" in missing_evidence:
        return "machine_observed_conflict"
    if "manual_scope_policy" in missing_evidence:
        return "blocked_missing_metric"
    if missing_evidence:
        if has_machine_observed_metric:
            return "machine_observed_partial"
        return "machine_proxy_only" if observed_metrics else "manual_derived_only"
    if observed_metrics and has_machine_observed_metric:
        return "machine_observed_sufficient"
    if observed_metrics:
        return (
            "machine_observed_partial"
            if has_machine_observed_metric
            else "machine_proxy_only"
        )
    return "manual_derived_only"


def _machine_tokens(
    sample_matches: Sequence[MachineMatch],
    context_matches: Sequence[MachineMatch],
) -> frozenset[str]:
    tokens: set[str] = set()
    for match in (*sample_matches, *context_matches):
        tokens.update(_split_semicolon(match.machine_reason.replace(" ", "_")))
        tokens.update(match.machine_blockers)
        for field in ("reason", "challenge_blockers", "dependent_context", "row_flags"):
            tokens.update(_split_semicolon(match.row.get(field, "")))
    return frozenset(token.lower() for token in tokens)


def _tags(row: Mapping[str, str]) -> frozenset[str]:
    return frozenset(_split_semicolon(row.get("manual_reason_tags", "")))


def _split_semicolon(value: object) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(value or "").split(";") if part.strip())


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return tuple(result)


def _append_metric(metrics: list[str], name: str, value: object) -> None:
    if _has_value(value):
        metrics.append(f"{name}={value}")


def _has_value(value: object) -> bool:
    return str(value or "").strip() not in {"", "nan", "None"}


def _float_or_none(value: object) -> float | None:
    text = str(value or "").strip().strip("'")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _peak_width_sec(row: Mapping[str, str]) -> str:
    try:
        start = float(str(row.get("peak_start_rt", "")).strip("'"))
        end = float(str(row.get("peak_end_rt", "")).strip("'"))
    except ValueError:
        return ""
    width = max(0.0, (end - start) * 60.0)
    return f"{width:.3f}"


def _has_rt_preferred_window_conflict(
    sample_matches: Sequence[MachineMatch],
) -> bool:
    return any(
        (rt_delta_sec := _float_or_none(match.row.get("rt_delta_sec"))) is not None
        and abs(rt_delta_sec) > _DEFAULT_ALIGNMENT_CONFIG.preferred_rt_sec
        for match in sample_matches
    )


def _has_cwt_metric(cwt_row: Mapping[str, str] | None) -> bool:
    if not cwt_row:
        return False
    return _has_value(cwt_row.get("cwt_status")) and cwt_row.get("cwt_status") not in {
        "not_assessed",
        "unavailable",
    }


def _has_tier2_trace_metric(tier2_row: Mapping[str, str] | None) -> bool:
    if not tier2_row:
        return False
    return any(
        _has_value(tier2_row.get(field))
        for field in (
            "scan_support_score",
            "trace_scan_count",
            "scan_availability_score",
            "trace_signal_to_noise_proxy",
            "trace_apex_prominence_score",
        )
    )


def _has_cid_nl_pattern_context(context_matches: Sequence[MachineMatch]) -> bool:
    return any(
        match.evidence_source == "alignment_review"
        and _has_value(match.row.get("neutral_loss_tag"))
        and _has_value(match.row.get("family_product_mz"))
        and _has_value(match.row.get("family_observed_neutral_loss_da"))
        for match in context_matches
    )


def _has_machine_observed_metric(
    *,
    cwt_row: Mapping[str, str] | None,
    tier2_row: Mapping[str, str] | None,
    candidate_ms2_row: Mapping[str, str] | None,
) -> bool:
    return (
        _has_cwt_metric(cwt_row)
        or _has_tier2_trace_metric(tier2_row)
        or _has_candidate_ms2_pattern_metric(candidate_ms2_row)
    )


def _cwt_conflicts_with_manual(
    tags: frozenset[str],
    cwt_row: Mapping[str, str] | None,
) -> bool:
    if not _has_cwt_metric(cwt_row):
        return False
    if cwt_row is None:
        return False
    cwt_supports_shape = cwt_row.get("cwt_status") == "OK"
    if tags & {"shape_complete", "shape_normal"}:
        return not cwt_supports_shape
    if "shape_bad" in tags:
        return cwt_supports_shape
    return False


def _has_candidate_ms2_pattern_metric(row: Mapping[str, str] | None) -> bool:
    if not row:
        return False
    return (
        row.get("candidate_ms2_evidence_level") in _CANDIDATE_MS2_OBSERVED_LEVELS
        and row.get("candidate_ms2_pattern_status")
        in (_CANDIDATE_MS2_SUPPORT_STATUSES | _CANDIDATE_MS2_CONFLICT_STATUSES)
    )


def _candidate_ms2_supports_manual(
    tags: frozenset[str],
    row: Mapping[str, str] | None,
) -> bool:
    if not _has_candidate_ms2_pattern_metric(row):
        return False
    if row is None:
        return False
    status = row["candidate_ms2_pattern_status"]
    if "pattern_mismatch" in tags:
        return status in _CANDIDATE_MS2_CONFLICT_STATUSES
    if tags & {"pattern_similar", "pattern_partial"}:
        return status in _CANDIDATE_MS2_SUPPORT_STATUSES
    return False


def _candidate_ms2_conflicts_with_manual(
    tags: frozenset[str],
    row: Mapping[str, str] | None,
) -> bool:
    if not _has_candidate_ms2_pattern_metric(row):
        return False
    if row is None:
        return False
    status = row["candidate_ms2_pattern_status"]
    if "pattern_mismatch" in tags:
        return status in _CANDIDATE_MS2_SUPPORT_STATUSES
    if tags & {"pattern_similar", "pattern_partial"}:
        return status in _CANDIDATE_MS2_CONFLICT_STATUSES
    return False
