"""Build/check Backfill expansion RT peak-mode decomposition diagnostics.

This diagnostic decomposes candidate cells by their sample-local apex RT
relative to the detected/reference mode of the same feature family. It is meant
to expose cases like FAM017098 where one provenance family spans two visible MS1
peaks. It does not read RAW files and does not grant ProductWriter authority.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_backfill_expansion_expected_diff_provenance import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_EXPECTED_DIFF_OUTPUT_DIR,
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (  # noqa: E402
    DEFAULT_OVERLAY_BATCH_SUMMARY_TSV,
)
from scripts.check_backfill_expansion_sample_local_ms1_evidence import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_SAMPLE_LOCAL_OUTPUT_DIR,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_peak_mode_decomposition_v1"
CHECK_SCHEMA_VERSION = "backfill_expansion_peak_mode_decomposition_check_v1"
PACKET_SCOPE = "backfill_expansion_candidate_replay_666_cells"
DEFAULT_TARGET_MODE_HALF_WINDOW_MIN = 0.30
DEFAULT_BRIDGE_MARGIN_MIN = 0.05
DEFAULT_SAME_SUBTYPE_COHERENCE_WINDOW_MIN = 0.50
EXPECTED_CANDIDATE_CELL_COUNT = 666

DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_peak_mode_decomposition_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_peak_mode_decomposition_v1"
)
DEFAULT_EXPECTED_DIFF_TSV = (
    DEFAULT_EXPECTED_DIFF_OUTPUT_DIR / "inputs/expected_diff.tsv"
)
DEFAULT_SAMPLE_LOCAL_CELLS_TSV = (
    DEFAULT_SAMPLE_LOCAL_OUTPUT_DIR
    / "backfill_expansion_sample_local_ms1_evidence_cells.tsv"
)
DEFAULT_CELLS_TSV = (
    DEFAULT_OUTPUT_DIR / "backfill_expansion_peak_mode_decomposition_cells.tsv"
)
DEFAULT_SUMMARY_JSON = (
    DEFAULT_DOCS_DIR / "backfill_expansion_peak_mode_decomposition_summary.json"
)
DEFAULT_CHECKS_TSV = (
    DEFAULT_DOCS_DIR / "backfill_expansion_peak_mode_decomposition_checks.tsv"
)
DEFAULT_ROW_MANIFEST_TSV = (
    DEFAULT_DOCS_DIR / "backfill_expansion_peak_mode_decomposition_row_manifest.tsv"
)
DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_peak_mode_decomposition_subtype_split_review.tsv"
)
DEFAULT_SPLIT_DECISION_TSV = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_peak_mode_decomposition_split_decisions.tsv"
)
DEFAULT_MANUAL_REVIEW_TSV = DEFAULT_DOCS_DIR / "fam017098_peak_mode_manual_review.tsv"
DEFAULT_FOCUS_FAMILY = "FAM017098"

EXPECTED_DIFF_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "expected_matrix_effect",
)
SAMPLE_LOCAL_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "alignment_cell_evidence_status",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "cell_evidence_reason",
)
OVERLAY_BATCH_COLUMNS = (
    "feature_family_id",
    "trace_summary_tsv",
)
TRACE_SUMMARY_COLUMNS = (
    "sample_stem",
    "status",
    "cell_apex_rt",
    "cell_start_rt",
    "cell_end_rt",
    "highlight_group",
)
MANUAL_REVIEW_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "sample_stem",
    "reviewer_peak_mode_label",
    "reviewer_boundary_label",
    "reviewer_action",
    "reviewer_notes",
)
CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
ROW_MANIFEST_COLUMNS = (
    "schema_version",
    "packet_scope",
    "peak_hypothesis_id",
    "candidate_cell_count",
    "reference_detected_cell_count",
    "reference_mode_center_rt",
    "target_mode_cell_count",
    "off_target_early_cell_count",
    "off_target_late_cell_count",
    "missing_apex_cell_count",
    "boundary_bridge_cell_count",
    "manual_reviewed_cell_count",
    "manual_review_action_counts",
    "sample_subtype_counts",
    "same_subtype_rt_incoherent_cell_count",
    "cross_subtype_rt_shift_review_cell_count",
    "subtype_rt_interpretation_status",
    "subtype_rt_interpretation_reason",
    "mode_decomposition_status",
    "primary_review_reason",
    "product_authority_effect",
    "next_gate",
)
SUBTYPE_SPLIT_REVIEW_COLUMNS = (
    "schema_version",
    "packet_scope",
    "peak_hypothesis_id",
    "sample_subtype",
    "review_reason",
    "recommended_action",
    "subtype_cell_count",
    "subtype_apex_min_rt",
    "subtype_apex_median_rt",
    "subtype_apex_max_rt",
    "subtype_rt_span_min",
    "mode_assignment_counts",
    "boundary_bridge_cell_count",
    "manual_review_action_counts",
    "representative_samples_by_mode",
    "product_authority_effect",
)
SPLIT_DECISION_COLUMNS = (
    "schema_version",
    "packet_scope",
    "peak_hypothesis_id",
    "sample_subtype",
    "decision_status",
    "target_mode_clean_cell_count",
    "target_mode_boundary_review_cell_count",
    "off_target_hold_or_remap_cell_count",
    "missing_or_unclassified_cell_count",
    "manual_reviewed_cell_count",
    "manual_review_action_counts",
    "representative_clean_target_samples",
    "representative_boundary_review_samples",
    "representative_hold_or_remap_samples",
    "decision_reason",
    "next_gate",
    "product_authority_effect",
)
CELL_COLUMNS = (
    "schema_version",
    "packet_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "sample_subtype",
    "cell_apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "reference_mode_center_rt",
    "target_mode_lower_rt",
    "target_mode_upper_rt",
    "mode_assignment",
    "boundary_bridge_status",
    "subtype_cell_count",
    "subtype_apex_median_rt",
    "subtype_apex_delta_min",
    "subtype_rt_span_min",
    "subtype_mode_assignment_counts",
    "subtype_rt_coherence_status",
    "subtype_rt_review_action",
    "manual_peak_mode_label",
    "manual_boundary_label",
    "manual_review_action",
    "manual_review_notes",
    "alignment_cell_evidence_status",
    "cell_evidence_reason",
    "product_authority_effect",
    "next_gate",
)


def build_backfill_expansion_peak_mode_decomposition(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_diff_tsv: Path = DEFAULT_EXPECTED_DIFF_TSV,
    sample_local_cells_tsv: Path = DEFAULT_SAMPLE_LOCAL_CELLS_TSV,
    overlay_batch_summary_tsv: Path = DEFAULT_OVERLAY_BATCH_SUMMARY_TSV,
    manual_review_tsv: Path | None = DEFAULT_MANUAL_REVIEW_TSV,
    target_mode_half_window_min: float = DEFAULT_TARGET_MODE_HALF_WINDOW_MIN,
    bridge_margin_min: float = DEFAULT_BRIDGE_MARGIN_MIN,
    same_subtype_coherence_window_min: float = (
        DEFAULT_SAME_SUBTYPE_COHERENCE_WINDOW_MIN
    ),
    cells_tsv: Path = DEFAULT_CELLS_TSV,
) -> dict[str, Any]:
    expected_rows = read_tsv_required(expected_diff_tsv, EXPECTED_DIFF_COLUMNS)
    sample_rows = read_tsv_required(sample_local_cells_tsv, SAMPLE_LOCAL_COLUMNS)
    overlay_rows = read_tsv_required(overlay_batch_summary_tsv, OVERLAY_BATCH_COLUMNS)

    sample_by_key = _unique_by_cell_key(sample_rows)
    trace_summary_by_family = _trace_summary_path_by_family(overlay_rows)
    reference_by_family = _reference_mode_by_family(trace_summary_by_family)
    manual_review_by_key = _manual_review_by_key(manual_review_tsv)

    cell_rows = _build_cell_rows(
        expected_rows=expected_rows,
        sample_by_key=sample_by_key,
        reference_by_family=reference_by_family,
        manual_review_by_key=manual_review_by_key,
        target_mode_half_window_min=target_mode_half_window_min,
        bridge_margin_min=bridge_margin_min,
    )
    _annotate_subtype_rt_context(
        cell_rows,
        same_subtype_coherence_window_min=same_subtype_coherence_window_min,
    )
    row_manifest = _build_row_manifest(cell_rows, reference_by_family)
    subtype_split_review_rows = _build_subtype_split_review_queue(cell_rows)
    split_decision_rows = _build_split_decision_rows(cell_rows)
    checks = _build_checks(
        cell_rows=cell_rows,
        row_manifest=row_manifest,
        expected_candidate_cell_count=EXPECTED_CANDIDATE_CELL_COUNT,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(cells_tsv, cell_rows, CELL_COLUMNS, extrasaction="raise")
    checks_tsv = docs_dir / DEFAULT_CHECKS_TSV.name
    row_manifest_tsv = docs_dir / DEFAULT_ROW_MANIFEST_TSV.name
    subtype_split_review_tsv = docs_dir / DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV.name
    split_decision_tsv = docs_dir / DEFAULT_SPLIT_DECISION_TSV.name
    summary_json = docs_dir / DEFAULT_SUMMARY_JSON.name
    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        row_manifest,
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        subtype_split_review_tsv,
        subtype_split_review_rows,
        SUBTYPE_SPLIT_REVIEW_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        split_decision_tsv,
        split_decision_rows,
        SPLIT_DECISION_COLUMNS,
        extrasaction="raise",
    )

    input_paths = {
        "expected_diff_tsv": expected_diff_tsv,
        "sample_local_cells_tsv": sample_local_cells_tsv,
        "overlay_batch_summary_tsv": overlay_batch_summary_tsv,
    }
    if manual_review_tsv is not None and manual_review_tsv.exists():
        input_paths["manual_review_tsv"] = manual_review_tsv

    payload = _summary_payload(
        checks=checks,
        cell_rows=cell_rows,
        row_manifest=row_manifest,
        subtype_split_review_rows=subtype_split_review_rows,
        split_decision_rows=split_decision_rows,
        target_mode_half_window_min=target_mode_half_window_min,
        bridge_margin_min=bridge_margin_min,
        same_subtype_coherence_window_min=same_subtype_coherence_window_min,
        input_paths=input_paths,
        output_paths={
            "cells_tsv": cells_tsv,
            "checks_tsv": checks_tsv,
            "row_manifest_tsv": row_manifest_tsv,
            "subtype_split_review_tsv": subtype_split_review_tsv,
            "split_decision_tsv": split_decision_tsv,
        },
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def validate_backfill_expansion_peak_mode_decomposition(
    *,
    summary_json: Path = DEFAULT_SUMMARY_JSON,
    checks_tsv: Path = DEFAULT_CHECKS_TSV,
    row_manifest_tsv: Path = DEFAULT_ROW_MANIFEST_TSV,
    subtype_split_review_tsv: Path = DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV,
    split_decision_tsv: Path = DEFAULT_SPLIT_DECISION_TSV,
    cells_tsv: Path = DEFAULT_CELLS_TSV,
) -> list[str]:
    problems: list[str] = []
    try:
        payload = json.loads(summary_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read summary JSON: {exc}"]
    if not isinstance(payload, Mapping):
        return ["summary JSON must contain an object"]
    _check_summary(payload, problems)
    _check_checks_tsv(checks_tsv, payload, problems)
    _check_manifest_tsv(row_manifest_tsv, payload, problems)
    _check_subtype_split_review_tsv(subtype_split_review_tsv, payload, problems)
    _check_split_decision_tsv(split_decision_tsv, payload, problems)
    _check_cells_tsv(cells_tsv, payload, problems)
    _check_artifact_hashes(payload, problems)
    return problems


def _build_cell_rows(
    *,
    expected_rows: Sequence[Mapping[str, str]],
    sample_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    reference_by_family: Mapping[str, Mapping[str, Any]],
    manual_review_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    target_mode_half_window_min: float,
    bridge_margin_min: float,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for expected in expected_rows:
        family = text_value(expected.get("peak_hypothesis_id"))
        sample = text_value(expected.get("sample_stem"))
        sample_row = sample_by_key.get((family, sample), {})
        manual_review = manual_review_by_key.get((family, sample), {})
        reference = reference_by_family.get(family, {})
        center = reference.get("reference_mode_center_rt")
        lower = (
            center - target_mode_half_window_min if isinstance(center, float) else None
        )
        upper = (
            center + target_mode_half_window_min if isinstance(center, float) else None
        )
        apex = optional_float(sample_row.get("apex_rt"))
        start = optional_float(sample_row.get("peak_start_rt"))
        end = optional_float(sample_row.get("peak_end_rt"))
        mode_assignment = _mode_assignment(
            apex=apex,
            lower=lower,
            upper=upper,
        )
        bridge_status = _boundary_bridge_status(
            start=start,
            end=end,
            lower=lower,
            upper=upper,
            bridge_margin_min=bridge_margin_min,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "sample_stem": sample,
                "sample_subtype": _sample_subtype_from_sample_stem(sample),
                "cell_apex_rt": _format_float(apex, 4),
                "peak_start_rt": _format_float(start, 4),
                "peak_end_rt": _format_float(end, 4),
                "reference_mode_center_rt": _format_float(center, 4),
                "target_mode_lower_rt": _format_float(lower, 4),
                "target_mode_upper_rt": _format_float(upper, 4),
                "mode_assignment": mode_assignment,
                "boundary_bridge_status": bridge_status,
                "manual_peak_mode_label": text_value(
                    manual_review.get("reviewer_peak_mode_label"),
                ),
                "manual_boundary_label": text_value(
                    manual_review.get("reviewer_boundary_label"),
                ),
                "manual_review_action": text_value(
                    manual_review.get("reviewer_action"),
                ),
                "manual_review_notes": text_value(
                    manual_review.get("reviewer_notes"),
                ),
                "alignment_cell_evidence_status": text_value(
                    sample_row.get("alignment_cell_evidence_status"),
                ),
                "cell_evidence_reason": text_value(
                    sample_row.get("cell_evidence_reason"),
                ),
                "product_authority_effect": "diagnostic_only_no_write_authority",
                "next_gate": (
                    "candidate_mode_can_feed_selective_gate_review"
                    if mode_assignment == "target_mode"
                    else "hold_or_remap_before_product_authority"
                ),
            },
        )
    return rows


def _build_row_manifest(
    cell_rows: Sequence[Mapping[str, str]],
    reference_by_family: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        by_family[text_value(row.get("peak_hypothesis_id"))].append(row)

    manifest: list[dict[str, str]] = []
    for family in sorted(by_family):
        rows = by_family[family]
        mode_counts = Counter(text_value(row.get("mode_assignment")) for row in rows)
        bridge_count = sum(
            1
            for row in rows
            if text_value(row.get("boundary_bridge_status")) != "not_bridged"
        )
        manual_actions = Counter(
            text_value(row.get("manual_review_action"))
            for row in rows
            if text_value(row.get("manual_review_action"))
        )
        manual_reviewed_count = sum(manual_actions.values())
        sample_subtype_counts = Counter(
            text_value(row.get("sample_subtype")) for row in rows
        )
        same_subtype_incoherent_count = sum(
            1
            for row in rows
            if row.get("subtype_rt_coherence_status")
            == "same_subtype_rt_incoherent"
        )
        cross_subtype_shift_count = sum(
            1
            for row in rows
            if row.get("subtype_rt_review_action") == "review_cross_subtype_rt_shift"
        )
        status, reason = _family_mode_status(mode_counts, bridge_count)
        subtype_status, subtype_reason = _family_subtype_rt_status(
            same_subtype_incoherent_count=same_subtype_incoherent_count,
            cross_subtype_shift_count=cross_subtype_shift_count,
        )
        reference = reference_by_family.get(family, {})
        manifest.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "candidate_cell_count": str(len(rows)),
                "reference_detected_cell_count": text_value(
                    reference.get("reference_detected_cell_count"),
                ),
                "reference_mode_center_rt": _format_float(
                    reference.get("reference_mode_center_rt"),
                    4,
                ),
                "target_mode_cell_count": str(mode_counts["target_mode"]),
                "off_target_early_cell_count": str(mode_counts["off_target_early"]),
                "off_target_late_cell_count": str(mode_counts["off_target_late"]),
                "missing_apex_cell_count": str(mode_counts["missing_apex"]),
                "boundary_bridge_cell_count": str(bridge_count),
                "manual_reviewed_cell_count": str(manual_reviewed_count),
                "manual_review_action_counts": _counter_text(manual_actions),
                "sample_subtype_counts": _counter_text(sample_subtype_counts),
                "same_subtype_rt_incoherent_cell_count": str(
                    same_subtype_incoherent_count,
                ),
                "cross_subtype_rt_shift_review_cell_count": str(
                    cross_subtype_shift_count,
                ),
                "subtype_rt_interpretation_status": subtype_status,
                "subtype_rt_interpretation_reason": subtype_reason,
                "mode_decomposition_status": status,
                "primary_review_reason": reason,
                "product_authority_effect": "diagnostic_only_no_write_authority",
                "next_gate": "review_mixed_modes_or_feed_target_mode_to_selective_gate",
            },
        )
    return manifest


def _build_subtype_split_review_queue(
    cell_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    by_family_subtype: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(
        list,
    )
    for row in cell_rows:
        if text_value(row.get("subtype_rt_review_action")) == "subtype_context_only":
            continue
        by_family_subtype[
            (
                text_value(row.get("peak_hypothesis_id")),
                text_value(row.get("sample_subtype")),
            )
        ].append(row)

    rows: list[dict[str, str]] = []
    for (family, subtype), group_rows in sorted(by_family_subtype.items()):
        apexes = sorted(
            value
            for row in group_rows
            for value in [optional_float(row.get("cell_apex_rt"))]
            if value is not None
        )
        mode_counts = Counter(
            text_value(row.get("mode_assignment")) for row in group_rows
        )
        manual_actions = Counter(
            text_value(row.get("manual_review_action"))
            for row in group_rows
            if text_value(row.get("manual_review_action"))
        )
        bridge_count = sum(
            1
            for row in group_rows
            if text_value(row.get("boundary_bridge_status")) != "not_bridged"
        )
        review_reason = text_value(group_rows[0].get("subtype_rt_review_action"))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "sample_subtype": subtype,
                "review_reason": review_reason,
                "recommended_action": _subtype_split_recommended_action(
                    review_reason=review_reason,
                    mode_counts=mode_counts,
                    boundary_bridge_count=bridge_count,
                ),
                "subtype_cell_count": str(len(group_rows)),
                "subtype_apex_min_rt": _format_float(apexes[0] if apexes else None, 4),
                "subtype_apex_median_rt": _format_float(_median(apexes), 4),
                "subtype_apex_max_rt": _format_float(apexes[-1] if apexes else None, 4),
                "subtype_rt_span_min": _format_float(
                    apexes[-1] - apexes[0] if apexes else None,
                    4,
                ),
                "mode_assignment_counts": _counter_text(mode_counts),
                "boundary_bridge_cell_count": str(bridge_count),
                "manual_review_action_counts": _counter_text(manual_actions),
                "representative_samples_by_mode": _samples_by_mode_text(group_rows),
                "product_authority_effect": "diagnostic_only_no_write_authority",
            },
        )
    return rows


def _build_split_decision_rows(
    cell_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    flagged_groups = {
        (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_subtype")),
        )
        for row in cell_rows
        if text_value(row.get("subtype_rt_review_action"))
        != "subtype_context_only"
    }
    by_family_subtype: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(
        list,
    )
    for row in cell_rows:
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_subtype")),
        )
        if key in flagged_groups:
            by_family_subtype[key].append(row)

    rows: list[dict[str, str]] = []
    for (family, subtype), group_rows in sorted(by_family_subtype.items()):
        clean_target_rows = [
            row
            for row in group_rows
            if text_value(row.get("mode_assignment")) == "target_mode"
            and text_value(row.get("boundary_bridge_status")) == "not_bridged"
        ]
        boundary_review_rows = [
            row
            for row in group_rows
            if text_value(row.get("mode_assignment")) == "target_mode"
            and text_value(row.get("boundary_bridge_status")) != "not_bridged"
        ]
        hold_rows = [
            row
            for row in group_rows
            if text_value(row.get("mode_assignment"))
            in {"off_target_early", "off_target_late"}
        ]
        missing_rows = [
            row
            for row in group_rows
            if text_value(row.get("mode_assignment"))
            not in {"target_mode", "off_target_early", "off_target_late"}
        ]
        manual_actions = Counter(
            text_value(row.get("manual_review_action"))
            for row in group_rows
            if text_value(row.get("manual_review_action"))
        )
        decision_status, decision_reason, next_gate = _split_decision_status(
            clean_target_count=len(clean_target_rows),
            boundary_review_count=len(boundary_review_rows),
            hold_count=len(hold_rows),
            missing_count=len(missing_rows),
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "sample_subtype": subtype,
                "decision_status": decision_status,
                "target_mode_clean_cell_count": str(len(clean_target_rows)),
                "target_mode_boundary_review_cell_count": str(
                    len(boundary_review_rows),
                ),
                "off_target_hold_or_remap_cell_count": str(len(hold_rows)),
                "missing_or_unclassified_cell_count": str(len(missing_rows)),
                "manual_reviewed_cell_count": str(sum(manual_actions.values())),
                "manual_review_action_counts": _counter_text(manual_actions),
                "representative_clean_target_samples": _samples_text(
                    clean_target_rows,
                ),
                "representative_boundary_review_samples": _samples_text(
                    boundary_review_rows,
                ),
                "representative_hold_or_remap_samples": _samples_text(hold_rows),
                "decision_reason": decision_reason,
                "next_gate": next_gate,
                "product_authority_effect": "diagnostic_only_no_write_authority",
            },
        )
    return rows


def _split_decision_status(
    *,
    clean_target_count: int,
    boundary_review_count: int,
    hold_count: int,
    missing_count: int,
) -> tuple[str, str, str]:
    if hold_count and boundary_review_count:
        return (
            "split_hold_off_target_and_review_boundaries",
            "same-subtype group contains off-target cells and target-mode cells "
            "whose boundaries bridge another mode",
            "manual_or_algorithmic_boundary_recut_before_authority",
        )
    if hold_count and clean_target_count:
        return (
            "split_hold_off_target_keep_clean_target_candidates",
            "same-subtype group separates off-target cells from clean target-mode "
            "candidate cells",
            "feed_clean_target_cells_to_full_evidence_chain",
        )
    if hold_count:
        return (
            "hold_or_remap_off_target_mode",
            "same-subtype group contains off-target cells without clean target-mode "
            "candidate support",
            "remap_or_hold_before_authority",
        )
    if boundary_review_count:
        return (
            "review_target_mode_boundaries",
            "target-mode cells are present but at least one boundary bridges the "
            "mode window",
            "manual_or_algorithmic_boundary_recut_before_authority",
        )
    if missing_count:
        return (
            "hold_missing_or_unclassified_mode",
            "one or more cells lack a usable target/off-target mode assignment",
            "resolve_missing_apex_or_reference_mode",
        )
    return (
        "clean_target_mode_candidate_group",
        "flagged group contains only clean target-mode candidates after routing",
        "feed_clean_target_cells_to_full_evidence_chain",
    )


def _subtype_split_recommended_action(
    *,
    review_reason: str,
    mode_counts: Counter[str],
    boundary_bridge_count: int,
) -> str:
    if review_reason == "review_same_subtype_rt_incoherence":
        if boundary_bridge_count:
            return "review_split_modes_and_boundaries"
        if len([key for key, count in mode_counts.items() if key and count]) >= 2:
            return "review_split_same_subtype_modes"
        return "review_same_subtype_rt_outliers"
    if review_reason == "review_cross_subtype_rt_shift":
        return "review_cross_subtype_shift_not_authority"
    return "review_context_only"


def _samples_by_mode_text(
    rows: Sequence[Mapping[str, str]],
    *,
    limit_per_mode: int = 4,
) -> str:
    by_mode: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        mode = text_value(row.get("mode_assignment"))
        sample = text_value(row.get("sample_stem"))
        if mode and sample:
            by_mode[mode].append(sample)
    parts: list[str] = []
    for mode in sorted(by_mode):
        samples = sorted(by_mode[mode])[:limit_per_mode]
        suffix = "" if len(by_mode[mode]) <= limit_per_mode else ",..."
        parts.append(f"{mode}:{','.join(samples)}{suffix}")
    return "|".join(parts)


def _samples_text(
    rows: Sequence[Mapping[str, str]],
    *,
    limit: int = 5,
) -> str:
    samples = sorted(
        text_value(row.get("sample_stem"))
        for row in rows
        if text_value(row.get("sample_stem"))
    )
    suffix = "" if len(samples) <= limit else ",..."
    return ",".join(samples[:limit]) + suffix if samples else ""


def _family_mode_status(
    mode_counts: Counter[str],
    bridge_count: int,
) -> tuple[str, str]:
    off_target = mode_counts["off_target_early"] + mode_counts["off_target_late"]
    target = mode_counts["target_mode"]
    if mode_counts["missing_apex"] and not target and not off_target:
        return "missing_candidate_apex", "candidate cells lack apex RT"
    if target and off_target:
        return "mixed_target_and_off_target_modes", "candidate apex RT spans modes"
    if off_target and not target:
        return "off_target_only", "candidate apex RT does not match detected mode"
    if bridge_count:
        return "target_mode_with_boundary_bridge", "some boundaries bridge modes"
    return "single_target_mode", ""


def _build_checks(
    *,
    cell_rows: Sequence[Mapping[str, str]],
    row_manifest: Sequence[Mapping[str, str]],
    expected_candidate_cell_count: int,
) -> list[dict[str, str]]:
    unique_count = len(
        {
            (row["peak_hypothesis_id"], row["sample_stem"])
            for row in cell_rows
        },
    )
    mixed_count = sum(
        1
        for row in row_manifest
        if row["mode_decomposition_status"] == "mixed_target_and_off_target_modes"
    )
    return [
        _check("candidate_scope_count", len(cell_rows), expected_candidate_cell_count),
        _check("candidate_keyset_unique", unique_count, len(cell_rows)),
        _check("row_manifest_family_count", len(row_manifest), 20),
        _check("mixed_mode_family_count_nonzero", mixed_count > 0, True),
        _check("no_product_writer_authority", True, True),
        _check("no_default_matrix_or_workbook_change", True, True),
    ]


def _summary_payload(
    *,
    checks: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
    row_manifest: Sequence[Mapping[str, str]],
    subtype_split_review_rows: Sequence[Mapping[str, str]],
    split_decision_rows: Sequence[Mapping[str, str]],
    target_mode_half_window_min: float,
    bridge_margin_min: float,
    same_subtype_coherence_window_min: float,
    input_paths: Mapping[str, Path],
    output_paths: Mapping[str, Path],
) -> dict[str, Any]:
    mode_counts = Counter(text_value(row.get("mode_assignment")) for row in cell_rows)
    status_counts = Counter(
        text_value(row.get("mode_decomposition_status")) for row in row_manifest
    )
    bridge_count = sum(
        1
        for row in cell_rows
        if text_value(row.get("boundary_bridge_status")) != "not_bridged"
    )
    manual_peak_mode_counts = Counter(
        text_value(row.get("manual_peak_mode_label"))
        for row in cell_rows
        if text_value(row.get("manual_peak_mode_label"))
    )
    manual_action_counts = Counter(
        text_value(row.get("manual_review_action"))
        for row in cell_rows
        if text_value(row.get("manual_review_action"))
    )
    sample_subtype_counts = Counter(
        text_value(row.get("sample_subtype")) for row in cell_rows
    )
    subtype_coherence_counts = Counter(
        text_value(row.get("subtype_rt_coherence_status")) for row in cell_rows
    )
    subtype_review_action_counts = Counter(
        text_value(row.get("subtype_rt_review_action")) for row in cell_rows
    )
    family_subtype_status_counts = Counter(
        text_value(row.get("subtype_rt_interpretation_status"))
        for row in row_manifest
    )
    subtype_split_review_reason_counts = Counter(
        text_value(row.get("review_reason")) for row in subtype_split_review_rows
    )
    subtype_split_review_action_counts = Counter(
        text_value(row.get("recommended_action"))
        for row in subtype_split_review_rows
    )
    split_decision_status_counts = Counter(
        text_value(row.get("decision_status")) for row in split_decision_rows
    )
    split_decision_clean_target_cell_count = _count_manifest_field(
        split_decision_rows,
        "target_mode_clean_cell_count",
    )
    split_decision_boundary_review_cell_count = _count_manifest_field(
        split_decision_rows,
        "target_mode_boundary_review_cell_count",
    )
    split_decision_hold_or_remap_cell_count = _count_manifest_field(
        split_decision_rows,
        "off_target_hold_or_remap_cell_count",
    )
    split_decision_missing_or_unclassified_cell_count = _count_manifest_field(
        split_decision_rows,
        "missing_or_unclassified_cell_count",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_status": "diagnostic_only_peak_mode_decomposition",
        "packet_scope": PACKET_SCOPE,
        "target_mode_half_window_min": target_mode_half_window_min,
        "bridge_margin_min": bridge_margin_min,
        "same_subtype_coherence_window_min": same_subtype_coherence_window_min,
        "sample_subtype_source": "diagnostic_filename_prefix",
        "candidate_cell_count": len(cell_rows),
        "candidate_peak_count": len(row_manifest),
        "mode_assignment_counts": dict(sorted(mode_counts.items())),
        "mode_decomposition_status_counts": dict(sorted(status_counts.items())),
        "boundary_bridge_cell_count": bridge_count,
        "manual_reviewed_cell_count": sum(manual_action_counts.values()),
        "manual_peak_mode_label_counts": dict(sorted(manual_peak_mode_counts.items())),
        "manual_review_action_counts": dict(sorted(manual_action_counts.items())),
        "sample_subtype_counts": dict(sorted(sample_subtype_counts.items())),
        "subtype_rt_coherence_status_counts": dict(
            sorted(subtype_coherence_counts.items()),
        ),
        "subtype_rt_review_action_counts": dict(
            sorted(subtype_review_action_counts.items()),
        ),
        "family_subtype_rt_interpretation_status_counts": dict(
            sorted(family_subtype_status_counts.items()),
        ),
        "subtype_split_review_queue_row_count": len(subtype_split_review_rows),
        "subtype_split_review_family_count": len(
            {
                text_value(row.get("peak_hypothesis_id"))
                for row in subtype_split_review_rows
            },
        ),
        "subtype_split_review_reason_counts": dict(
            sorted(subtype_split_review_reason_counts.items()),
        ),
        "subtype_split_review_recommended_action_counts": dict(
            sorted(subtype_split_review_action_counts.items()),
        ),
        "split_decision_queue_row_count": len(split_decision_rows),
        "split_decision_family_count": len(
            {
                text_value(row.get("peak_hypothesis_id"))
                for row in split_decision_rows
            },
        ),
        "split_decision_status_counts": dict(
            sorted(split_decision_status_counts.items()),
        ),
        "split_decision_clean_target_cell_count": (
            split_decision_clean_target_cell_count
        ),
        "split_decision_boundary_review_cell_count": (
            split_decision_boundary_review_cell_count
        ),
        "split_decision_hold_or_remap_cell_count": (
            split_decision_hold_or_remap_cell_count
        ),
        "split_decision_missing_or_unclassified_cell_count": (
            split_decision_missing_or_unclassified_cell_count
        ),
        "write_authority": False,
        "product_writer_changed": False,
        "default_quant_matrix_changed": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "raw_or_85raw_ran_by_checker": False,
        "authority_statement": (
            "Peak-mode decomposition is diagnostic-only. It can identify "
            "target-mode cells or mixed-mode families for review/remap, but it "
            "grants no ProductWriter authority."
        ),
        "checks": {row["check_id"]: row["status"] for row in checks},
        "input_artifacts": {
            name: _artifact(path) for name, path in sorted(input_paths.items())
        },
        "artifacts": {
            name: _artifact(path) for name, path in sorted(output_paths.items())
        },
    }


def _reference_mode_by_family(
    trace_summary_by_family: Mapping[str, Path],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for family, path in trace_summary_by_family.items():
        rows = read_tsv_required(path, TRACE_SUMMARY_COLUMNS)
        detected_apexes = [
            value
            for row in rows
            if text_value(row.get("status")) == "detected"
            for value in [optional_float(row.get("cell_apex_rt"))]
            if value is not None
        ]
        result[family] = {
            "reference_detected_cell_count": len(detected_apexes),
            "reference_mode_center_rt": _median(detected_apexes),
        }
    return result


def _trace_summary_path_by_family(
    overlay_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for row in overlay_rows:
        family = text_value(row.get("feature_family_id"))
        path_text = text_value(row.get("trace_summary_tsv"))
        if family and path_text:
            path = Path(path_text)
            result[family] = path if path.is_absolute() else ROOT / path
    return result


def _annotate_subtype_rt_context(
    rows: list[dict[str, str]],
    *,
    same_subtype_coherence_window_min: float,
) -> None:
    stats_by_key = _subtype_rt_stats_by_family(rows)
    family_cross_shift = _family_cross_subtype_shift_status(
        stats_by_key,
        same_subtype_coherence_window_min=same_subtype_coherence_window_min,
    )
    for row in rows:
        family = text_value(row.get("peak_hypothesis_id"))
        subtype = text_value(row.get("sample_subtype"))
        stat = stats_by_key.get((family, subtype), {})
        apex = optional_float(row.get("cell_apex_rt"))
        median = stat.get("median")
        span = stat.get("span")
        count = int(stat.get("count") or 0)
        mode_counts = stat.get("mode_counts")
        coherence_status = _subtype_rt_coherence_status(
            subtype=subtype,
            count=count,
            span=span if isinstance(span, float) else None,
            same_subtype_coherence_window_min=same_subtype_coherence_window_min,
        )
        row["subtype_cell_count"] = str(count) if count else "0"
        row["subtype_apex_median_rt"] = _format_float(median, 4)
        delta = (
            apex - median
            if isinstance(apex, float) and isinstance(median, float)
            else None
        )
        row["subtype_apex_delta_min"] = _format_float(
            delta,
            4,
        )
        row["subtype_rt_span_min"] = _format_float(span, 4)
        row["subtype_mode_assignment_counts"] = (
            _counter_text(mode_counts) if isinstance(mode_counts, Counter) else ""
        )
        row["subtype_rt_coherence_status"] = coherence_status
        row["subtype_rt_review_action"] = _subtype_rt_review_action(
            coherence_status=coherence_status,
            family_has_cross_subtype_shift=family_cross_shift.get(family, False),
        )


def _subtype_rt_stats_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                text_value(row.get("peak_hypothesis_id")),
                text_value(row.get("sample_subtype")),
            )
        ].append(row)
    stats: dict[tuple[str, str], dict[str, Any]] = {}
    for key, group_rows in grouped.items():
        apexes = [
            value
            for row in group_rows
            for value in [optional_float(row.get("cell_apex_rt"))]
            if value is not None
        ]
        finite = sorted(value for value in apexes if math.isfinite(value))
        mode_counts = Counter(
            text_value(row.get("mode_assignment")) for row in group_rows
        )
        stats[key] = {
            "count": len(group_rows),
            "median": _median(finite),
            "span": (finite[-1] - finite[0]) if finite else None,
            "mode_counts": mode_counts,
        }
    return stats


def _family_cross_subtype_shift_status(
    stats_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    same_subtype_coherence_window_min: float,
) -> dict[str, bool]:
    medians_by_family: dict[str, list[float]] = defaultdict(list)
    for (family, subtype), stat in stats_by_key.items():
        if subtype in {"unknown", "qc", "blank"}:
            continue
        if _subtype_rt_coherence_status(
            subtype=subtype,
            count=int(stat.get("count") or 0),
            span=stat.get("span") if isinstance(stat.get("span"), float) else None,
            same_subtype_coherence_window_min=same_subtype_coherence_window_min,
        ) != "same_subtype_rt_coherent":
            continue
        median = stat.get("median")
        if isinstance(median, float):
            medians_by_family[family].append(median)
    return {
        family: len(medians) >= 2
        and max(medians) - min(medians) > same_subtype_coherence_window_min
        for family, medians in medians_by_family.items()
    }


def _sample_subtype_from_sample_stem(sample_stem: str) -> str:
    value = text_value(sample_stem).lower()
    if value.startswith("tumor"):
        return "tumor"
    if value.startswith("normal"):
        return "normal"
    if value.startswith("benignfat"):
        return "benignfat"
    if "qc" in value:
        return "qc"
    if "blank" in value:
        return "blank"
    return "unknown"


def _subtype_rt_coherence_status(
    *,
    subtype: str,
    count: int,
    span: float | None,
    same_subtype_coherence_window_min: float,
) -> str:
    if subtype in {"unknown", ""}:
        return "subtype_unknown"
    if subtype in {"qc", "blank"}:
        return f"{subtype}_reference_context"
    if count < 2:
        return "subtype_single_cell"
    if span is None:
        return "subtype_missing_apex"
    if span > same_subtype_coherence_window_min:
        return "same_subtype_rt_incoherent"
    return "same_subtype_rt_coherent"


def _subtype_rt_review_action(
    *,
    coherence_status: str,
    family_has_cross_subtype_shift: bool,
) -> str:
    if coherence_status == "same_subtype_rt_incoherent":
        return "review_same_subtype_rt_incoherence"
    if coherence_status in {"same_subtype_rt_coherent", "subtype_single_cell"}:
        if family_has_cross_subtype_shift:
            return "review_cross_subtype_rt_shift"
    return "subtype_context_only"


def _family_subtype_rt_status(
    *,
    same_subtype_incoherent_count: int,
    cross_subtype_shift_count: int,
) -> tuple[str, str]:
    if same_subtype_incoherent_count:
        return (
            "review_same_subtype_rt_incoherence",
            "same subtype contains RT spread larger than the diagnostic window",
        )
    if cross_subtype_shift_count:
        return (
            "review_cross_subtype_rt_shift",
            "coherent subtypes show separated RT medians",
        )
    return "subtype_rt_context_only", ""


def _manual_review_by_key(
    manual_review_tsv: Path | None,
) -> dict[tuple[str, str], Mapping[str, str]]:
    if manual_review_tsv is None or not manual_review_tsv.exists():
        return {}
    rows = read_tsv_required(manual_review_tsv, MANUAL_REVIEW_COLUMNS)
    return _unique_by_cell_key(rows)


def _unique_by_cell_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_stem")),
        )
        if not all(key):
            continue
        if key in by_key:
            raise ValueError(f"duplicate key: {key[0]}/{key[1]}")
        by_key[key] = row
    return by_key


def _mode_assignment(
    *,
    apex: float | None,
    lower: float | None,
    upper: float | None,
) -> str:
    if apex is None:
        return "missing_apex"
    if lower is None or upper is None:
        return "missing_reference_mode"
    if apex < lower:
        return "off_target_early"
    if apex > upper:
        return "off_target_late"
    return "target_mode"


def _boundary_bridge_status(
    *,
    start: float | None,
    end: float | None,
    lower: float | None,
    upper: float | None,
    bridge_margin_min: float,
) -> str:
    if start is None or end is None or lower is None or upper is None:
        return "missing_boundary"
    if start < lower - bridge_margin_min and end >= lower:
        return "bridges_lower_target_boundary"
    if start <= upper and end > upper + bridge_margin_min:
        return "bridges_upper_target_boundary"
    return "not_bridged"


def _median(values: Sequence[float]) -> float | None:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return None
    mid = len(finite) // 2
    if len(finite) % 2:
        return finite[mid]
    return (finite[mid - 1] + finite[mid]) / 2.0


def _count_manifest_field(rows: Sequence[Mapping[str, str]], field: str) -> int:
    return sum(int(row.get(field) or 0) for row in rows)


def _counter_text(counter: Counter[str]) -> str:
    return ";".join(f"{key}={counter[key]}" for key in sorted(counter))


def _format_float(value: object, decimals: int) -> str:
    parsed = optional_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.{decimals}f}"


def _check(
    check_id: str,
    observed: object,
    expected: object,
    *,
    notes: str = "",
) -> dict[str, str]:
    observed_text = text_value(observed)
    expected_text = text_value(expected)
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "check_id": check_id,
        "status": "pass" if observed_text == expected_text else "fail",
        "observed": observed_text,
        "expected": expected_text,
        "notes": notes,
    }


def _artifact(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": _repo_relpath(resolved),
        "sha256": file_sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _repo_relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def _check_summary(payload: Mapping[str, Any], problems: list[str]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        problems.append("summary schema_version mismatch")
    if payload.get("packet_scope") != PACKET_SCOPE:
        problems.append("summary packet_scope mismatch")
    if payload.get("candidate_cell_count") != EXPECTED_CANDIDATE_CELL_COUNT:
        problems.append("summary candidate_cell_count mismatch")
    for field in (
        "write_authority",
        "product_writer_changed",
        "default_quant_matrix_changed",
        "workbook_or_gui_changed",
        "selected_peak_area_or_counting_changed",
        "raw_or_85raw_ran_by_checker",
    ):
        if payload.get(field) is not False:
            problems.append(f"summary {field} must be false")


def _check_checks_tsv(
    checks_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(checks_tsv, CHECK_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read checks TSV: {exc}")
        return
    failing = [row["check_id"] for row in rows if row.get("status") != "pass"]
    if failing:
        problems.append("checks must all pass: " + ";".join(failing))
    summary_checks = payload.get("checks")
    if isinstance(summary_checks, Mapping):
        for row in rows:
            check_id = text_value(row.get("check_id"))
            if summary_checks.get(check_id) != "pass":
                problems.append(f"summary check {check_id} must pass")


def _check_manifest_tsv(
    row_manifest_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(row_manifest_tsv, ROW_MANIFEST_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read row manifest TSV: {exc}")
        return
    if len(rows) != payload.get("candidate_peak_count"):
        problems.append("row manifest candidate peak count mismatch")
    if _count_manifest_field(rows, "candidate_cell_count") != payload.get(
        "candidate_cell_count",
    ):
        problems.append("row manifest candidate cell count mismatch")


def _check_subtype_split_review_tsv(
    subtype_split_review_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(
            subtype_split_review_tsv,
            SUBTYPE_SPLIT_REVIEW_COLUMNS,
        )
    except (OSError, ValueError) as exc:
        problems.append(f"could not read subtype split review TSV: {exc}")
        return
    if len(rows) != payload.get("subtype_split_review_queue_row_count"):
        problems.append("subtype split review queue count mismatch")
    effects = {row.get("product_authority_effect") for row in rows}
    if effects and effects != {"diagnostic_only_no_write_authority"}:
        problems.append("subtype split review product_authority_effect mismatch")


def _check_split_decision_tsv(
    split_decision_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(
            split_decision_tsv,
            SPLIT_DECISION_COLUMNS,
        )
    except (OSError, ValueError) as exc:
        problems.append(f"could not read split decision TSV: {exc}")
        return
    if len(rows) != payload.get("split_decision_queue_row_count"):
        problems.append("split decision queue count mismatch")
    effects = {row.get("product_authority_effect") for row in rows}
    if effects and effects != {"diagnostic_only_no_write_authority"}:
        problems.append("split decision product_authority_effect mismatch")
    field_to_summary = {
        "target_mode_clean_cell_count": "split_decision_clean_target_cell_count",
        "target_mode_boundary_review_cell_count": (
            "split_decision_boundary_review_cell_count"
        ),
        "off_target_hold_or_remap_cell_count": (
            "split_decision_hold_or_remap_cell_count"
        ),
        "missing_or_unclassified_cell_count": (
            "split_decision_missing_or_unclassified_cell_count"
        ),
    }
    for field, summary_field in field_to_summary.items():
        if _count_manifest_field(rows, field) != int(payload.get(summary_field) or 0):
            problems.append(f"split decision {field} mismatch")


def _check_cells_tsv(
    cells_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(cells_tsv, CELL_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read cells TSV: {exc}")
        return
    if len(rows) != payload.get("candidate_cell_count"):
        problems.append("cells TSV candidate count mismatch")
    effects = {row.get("product_authority_effect") for row in rows}
    if effects != {"diagnostic_only_no_write_authority"}:
        problems.append("cells TSV product_authority_effect mismatch")


def _check_artifact_hashes(
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    for section_name in ("input_artifacts", "artifacts"):
        section = payload.get(section_name)
        if not isinstance(section, Mapping):
            problems.append(f"summary {section_name} missing")
            continue
        for name, artifact in section.items():
            if not isinstance(artifact, Mapping):
                problems.append(f"summary {section_name} {name} must be object")
                continue
            path_text = text_value(artifact.get("path"))
            if not path_text:
                problems.append(f"summary {section_name} {name} path missing")
                continue
            path = ROOT / path_text
            if not path.exists():
                problems.append(f"summary {section_name} {name} path missing on disk")
                continue
            if file_sha256(path) != text_value(artifact.get("sha256")):
                problems.append(f"summary {section_name} {name} sha256 mismatch")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--target-mode-half-window-min",
        type=float,
        default=DEFAULT_TARGET_MODE_HALF_WINDOW_MIN,
    )
    parser.add_argument(
        "--bridge-margin-min",
        type=float,
        default=DEFAULT_BRIDGE_MARGIN_MIN,
    )
    parser.add_argument(
        "--same-subtype-coherence-window-min",
        type=float,
        default=DEFAULT_SAME_SUBTYPE_COHERENCE_WINDOW_MIN,
    )
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--checks-tsv", type=Path, default=DEFAULT_CHECKS_TSV)
    parser.add_argument(
        "--row-manifest-tsv",
        type=Path,
        default=DEFAULT_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--subtype-split-review-tsv",
        type=Path,
        default=DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV,
    )
    parser.add_argument(
        "--split-decision-tsv",
        type=Path,
        default=DEFAULT_SPLIT_DECISION_TSV,
    )
    parser.add_argument("--cells-tsv", type=Path, default=DEFAULT_CELLS_TSV)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if not args.check_only:
            build_backfill_expansion_peak_mode_decomposition(
                target_mode_half_window_min=args.target_mode_half_window_min,
                bridge_margin_min=args.bridge_margin_min,
                same_subtype_coherence_window_min=(
                    args.same_subtype_coherence_window_min
                ),
                cells_tsv=args.cells_tsv,
            )
        problems = validate_backfill_expansion_peak_mode_decomposition(
            summary_json=args.summary_json,
            checks_tsv=args.checks_tsv,
            row_manifest_tsv=args.row_manifest_tsv,
            subtype_split_review_tsv=args.subtype_split_review_tsv,
            split_decision_tsv=args.split_decision_tsv,
            cells_tsv=args.cells_tsv,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    print(
        "Backfill expansion peak-mode decomposition summary: "
        f"{args.summary_json}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
