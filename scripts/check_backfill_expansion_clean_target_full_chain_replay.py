"""Build/check clean-target-only Backfill expansion full-chain replay.

This diagnostic projects the peak-mode split decision packet back onto the
existing 666-cell full evidence-chain map. It keeps only cells that were routed
as clean target-mode candidates by peak-mode decomposition. It does not read RAW
files, mutate the default matrix, or grant ProductWriter authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    check_backfill_expansion_full_evidence_chain as full_chain,
)
from scripts import (  # noqa: E402
    check_backfill_expansion_peak_mode_decomposition as peak_mode,
)
from scripts import (
    check_backfill_expansion_raw_overlay_trace_identity as raw_trace,  # noqa: E402
)
from scripts import (  # noqa: E402
    check_backfill_expansion_selective_shift_aware_gate as selective_shift,
)
from xic_extractor.diagnostics import (  # noqa: E402
    standard_peak_ms1_authority_bundle as ms1_authority_bundle,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_clean_target_full_chain_replay_v1"
CHECK_SCHEMA_VERSION = (
    "backfill_expansion_clean_target_full_chain_replay_check_v1"
)
PACKET_SCOPE = "backfill_expansion_clean_target_split_decision_112_cells"

DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_clean_target_full_chain_replay_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "output/validation/backfill_expansion_clean_target_full_chain_replay_v1"
)
DEFAULT_SUMMARY_JSON = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_clean_target_full_chain_replay_summary.json"
)
DEFAULT_CHECKS_TSV = (
    DEFAULT_DOCS_DIR / "backfill_expansion_clean_target_full_chain_replay_checks.tsv"
)
DEFAULT_ROW_MANIFEST_TSV = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_clean_target_full_chain_replay_row_manifest.tsv"
)
DEFAULT_CELLS_TSV = (
    DEFAULT_OUTPUT_DIR
    / "backfill_expansion_clean_target_full_chain_replay_cells.tsv"
)
DEFAULT_SELECTIVE_MS1_AUTHORITY_DIR = (
    DEFAULT_OUTPUT_DIR / "selective_source_family_ms1_authority_bundle"
)
DEFAULT_SELECTIVE_MS1_PRODUCT_AUTHORITY_TSV = (
    DEFAULT_SELECTIVE_MS1_AUTHORITY_DIR
    / "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
)
DEFAULT_SELECTIVE_MS1_PRODUCT_AUTHORITY_AUDIT_TSV = (
    DEFAULT_SELECTIVE_MS1_AUTHORITY_DIR
    / "backfill_ms1_pattern_product_authority_audit.tsv"
)
DEFAULT_SELECTIVE_MS1_PRODUCT_AUTHORITY_SUMMARY_JSON = (
    DEFAULT_SELECTIVE_MS1_AUTHORITY_DIR
    / "standard_peak_ms1_authority_bundle_summary.json"
)

EXPECTED_COUNTS = {
    "split_decision_group_count": 18,
    "split_decision_family_count": 11,
    "clean_target_candidate_cell_count": 112,
    "boundary_review_excluded_cell_count": 37,
    "off_target_hold_or_remap_excluded_cell_count": 29,
    "missing_or_unclassified_excluded_cell_count": 0,
}

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
    "sample_subtype",
    "split_decision_status",
    "clean_target_candidate_cell_count",
    "full_chain_pass_cell_count",
    "held_cell_count",
    "primary_blocker_counts",
    "projected_selective_full_chain_pass_cell_count",
    "projected_selective_held_cell_count",
    "projected_selective_primary_blocker_counts",
    "product_authority_effect",
    "next_gate",
)
CELL_COLUMNS = (
    "schema_version",
    "packet_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "sample_subtype",
    "split_decision_status",
    "peak_mode_route",
    "expected_diff_status",
    "source_evidence_status",
    "raw_trace_status",
    "own_max_metric_status",
    "own_max_metric_value",
    "shift_aware_gate_status",
    "shift_aware_gate_call",
    "selective_source_family",
    "selective_source_family_shift_status",
    "selective_source_family_shape_r",
    "selective_source_family_shift_sec",
    "selective_evidence_status",
    "selective_primary_blocker",
    "selective_secondary_blockers",
    "ms1_product_authority_status",
    "ms1_product_authority_source",
    "selective_ms1_product_authority_status",
    "selective_ms1_product_authority_source",
    "full_chain_status",
    "primary_blocker",
    "secondary_blockers",
    "projected_selective_full_chain_status",
    "projected_selective_primary_blocker",
    "projected_selective_secondary_blockers",
    "product_authority_effect",
    "next_gate",
)


def build_backfill_expansion_clean_target_full_chain_replay(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    peak_mode_cells_tsv: Path = peak_mode.DEFAULT_CELLS_TSV,
    split_decision_tsv: Path = peak_mode.DEFAULT_SPLIT_DECISION_TSV,
    full_chain_cells_tsv: Path = full_chain.DEFAULT_CELLS_TSV,
    full_chain_summary_json: Path = full_chain.DEFAULT_SUMMARY_JSON,
    selective_shift_cells_tsv: Path = selective_shift.DEFAULT_CELLS_TSV,
    shift_aware_standard_peak_gate_tsv: Path = (
        full_chain.DEFAULT_SHIFT_AWARE_STANDARD_PEAK_GATE_TSV
    ),
    overlay_batch_summary_tsv: Path = raw_trace.DEFAULT_OVERLAY_BATCH_SUMMARY_TSV,
    selective_ms1_authority_dir: Path = DEFAULT_SELECTIVE_MS1_AUTHORITY_DIR,
    cells_tsv: Path = DEFAULT_CELLS_TSV,
) -> dict[str, Any]:
    peak_mode_cells = read_tsv_required(peak_mode_cells_tsv, peak_mode.CELL_COLUMNS)
    split_decisions = read_tsv_required(
        split_decision_tsv,
        peak_mode.SPLIT_DECISION_COLUMNS,
    )
    full_chain_cells = read_tsv_required(
        full_chain_cells_tsv,
        full_chain.CELL_CHAIN_COLUMNS,
    )
    selective_shift_cells = read_tsv_required(
        selective_shift_cells_tsv,
        selective_shift.CELL_COLUMNS,
    )
    selective_authority_outputs = (
        ms1_authority_bundle.run_standard_peak_ms1_authority_bundle(
            standard_peak_gate_tsv=shift_aware_standard_peak_gate_tsv,
            overlay_batch_summary_tsv=overlay_batch_summary_tsv,
            output_dir=selective_ms1_authority_dir,
            authority_mode=(
                ms1_authority_bundle.AUTHORITY_MODE_MACHINE_SELECTIVE_SOURCE_GATE
            ),
            selective_shift_cells_tsv=selective_shift_cells_tsv,
        )
    )
    selective_authority_rows = read_tsv_required(
        selective_authority_outputs.authorized_ms1_pattern_tsv,
        full_chain.MS1_AUTHORITY_COLUMNS,
    )

    split_by_group = {
        (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_subtype")),
        ): row
        for row in split_decisions
    }
    full_chain_by_key = _unique_by_cell_key(full_chain_cells)
    selective_shift_by_key = _unique_by_cell_key(selective_shift_cells)
    selective_authority_by_key = _unique_by_cell_key(
        selective_authority_rows,
        family_field="feature_family_id",
    )
    clean_target_rows = _clean_target_peak_mode_rows(
        peak_mode_cells,
        split_by_group,
    )
    cell_rows = _build_projection_cell_rows(
        clean_target_rows=clean_target_rows,
        split_by_group=split_by_group,
        full_chain_by_key=full_chain_by_key,
        selective_shift_by_key=selective_shift_by_key,
        selective_authority_by_key=selective_authority_by_key,
    )
    row_manifest = _build_row_manifest(cell_rows, split_decisions)
    excluded_counts = _split_decision_excluded_counts(split_decisions)
    checks = _build_checks(
        split_decisions=split_decisions,
        cell_rows=cell_rows,
        excluded_counts=excluded_counts,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(cells_tsv, cell_rows, CELL_COLUMNS, extrasaction="raise")
    checks_tsv = docs_dir / DEFAULT_CHECKS_TSV.name
    row_manifest_tsv = docs_dir / DEFAULT_ROW_MANIFEST_TSV.name
    summary_json = docs_dir / DEFAULT_SUMMARY_JSON.name
    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        row_manifest,
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )

    payload = _summary_payload(
        checks=checks,
        cell_rows=cell_rows,
        row_manifest=row_manifest,
        split_decisions=split_decisions,
        excluded_counts=excluded_counts,
        input_paths={
            "peak_mode_cells_tsv": peak_mode_cells_tsv,
            "split_decision_tsv": split_decision_tsv,
            "full_chain_cells_tsv": full_chain_cells_tsv,
            "full_chain_summary_json": full_chain_summary_json,
            "selective_shift_cells_tsv": selective_shift_cells_tsv,
            "shift_aware_standard_peak_gate_tsv": shift_aware_standard_peak_gate_tsv,
            "overlay_batch_summary_tsv": overlay_batch_summary_tsv,
        },
        output_paths={
            "cells_tsv": cells_tsv,
            "checks_tsv": checks_tsv,
            "row_manifest_tsv": row_manifest_tsv,
            "selective_ms1_product_authority_tsv": (
                selective_authority_outputs.authorized_ms1_pattern_tsv
            ),
            "selective_ms1_product_authority_audit_tsv": (
                selective_authority_outputs.authority_audit_tsv
            ),
            "selective_ms1_product_authority_summary_json": (
                selective_authority_outputs.summary_json
            ),
        },
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def validate_backfill_expansion_clean_target_full_chain_replay(
    *,
    summary_json: Path = DEFAULT_SUMMARY_JSON,
    checks_tsv: Path = DEFAULT_CHECKS_TSV,
    row_manifest_tsv: Path = DEFAULT_ROW_MANIFEST_TSV,
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
    _check_cells_tsv(cells_tsv, payload, problems)
    _check_artifact_hashes(payload, problems)
    return problems


def _clean_target_peak_mode_rows(
    peak_mode_cells: Sequence[Mapping[str, str]],
    split_by_group: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[Mapping[str, str]]:
    rows: list[Mapping[str, str]] = []
    for row in peak_mode_cells:
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_subtype")),
        )
        if key not in split_by_group:
            continue
        if text_value(row.get("mode_assignment")) != "target_mode":
            continue
        if text_value(row.get("boundary_bridge_status")) != "not_bridged":
            continue
        rows.append(row)
    return rows


def _build_projection_cell_rows(
    *,
    clean_target_rows: Sequence[Mapping[str, str]],
    split_by_group: Mapping[tuple[str, str], Mapping[str, str]],
    full_chain_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    selective_shift_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    selective_authority_by_key: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for peak_row in clean_target_rows:
        family = text_value(peak_row.get("peak_hypothesis_id"))
        sample = text_value(peak_row.get("sample_stem"))
        subtype = text_value(peak_row.get("sample_subtype"))
        split_row = split_by_group.get((family, subtype), {})
        chain_row = full_chain_by_key.get((family, sample), {})
        selective_row = selective_shift_by_key.get((family, sample), {})
        selective_authority_row = selective_authority_by_key.get((family, sample), {})
        selective_authority_status = "pass" if selective_authority_row else "missing"
        projected_blockers = _projected_selective_full_chain_blockers(
            chain_row=chain_row,
            selective_row=selective_row,
            selective_authority_status=selective_authority_status,
        )
        projected_status = "pass" if not projected_blockers else "held"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "sample_stem": sample,
                "sample_subtype": subtype,
                "split_decision_status": text_value(
                    split_row.get("decision_status"),
                ),
                "peak_mode_route": "clean_target_mode_not_boundary_bridged",
                "expected_diff_status": text_value(
                    chain_row.get("expected_diff_status"),
                )
                or "missing_full_chain_row",
                "source_evidence_status": text_value(
                    chain_row.get("source_evidence_status"),
                )
                or "missing_full_chain_row",
                "raw_trace_status": text_value(chain_row.get("raw_trace_status"))
                or "missing_full_chain_row",
                "own_max_metric_status": text_value(
                    chain_row.get("own_max_metric_status"),
                )
                or "missing_full_chain_row",
                "own_max_metric_value": text_value(
                    chain_row.get("own_max_metric_value"),
                ),
                "shift_aware_gate_status": text_value(
                    chain_row.get("shift_aware_gate_status"),
                )
                or "missing_full_chain_row",
                "shift_aware_gate_call": text_value(
                    chain_row.get("shift_aware_gate_call"),
                ),
                "selective_source_family": text_value(
                    selective_row.get("source_family"),
                ),
                "selective_source_family_shift_status": text_value(
                    selective_row.get("source_family_shift_status"),
                )
                or "missing_selective_shift_row",
                "selective_source_family_shape_r": text_value(
                    selective_row.get("source_family_shape_r"),
                ),
                "selective_source_family_shift_sec": text_value(
                    selective_row.get("source_family_shift_sec"),
                ),
                "selective_evidence_status": text_value(
                    selective_row.get("selective_evidence_status"),
                )
                or "missing_selective_shift_row",
                "selective_primary_blocker": text_value(
                    selective_row.get("primary_blocker"),
                ),
                "selective_secondary_blockers": text_value(
                    selective_row.get("secondary_blockers"),
                ),
                "ms1_product_authority_status": text_value(
                    chain_row.get("ms1_product_authority_status"),
                )
                or "missing_full_chain_row",
                "ms1_product_authority_source": text_value(
                    chain_row.get("ms1_product_authority_source"),
                ),
                "selective_ms1_product_authority_status": (
                    selective_authority_status
                ),
                "selective_ms1_product_authority_source": text_value(
                    selective_authority_row.get("product_authority_source"),
                ),
                "full_chain_status": text_value(chain_row.get("full_chain_status"))
                or "held",
                "primary_blocker": text_value(chain_row.get("primary_blocker"))
                or (
                    "missing_full_chain_row"
                    if not chain_row
                    else ""
                ),
                "secondary_blockers": text_value(
                    chain_row.get("secondary_blockers"),
                ),
                "projected_selective_full_chain_status": projected_status,
                "projected_selective_primary_blocker": (
                    projected_blockers[0] if projected_blockers else ""
                ),
                "projected_selective_secondary_blockers": ";".join(
                    projected_blockers[1:],
                ),
                "product_authority_effect": "diagnostic_only_no_write_authority",
                "next_gate": (
                    "eligible_for_expected_diff_authority_design"
                    if projected_status == "pass"
                    else "resolve_full_evidence_chain_before_product_writer_authority"
                ),
            },
        )
    return rows


def _build_row_manifest(
    cell_rows: Sequence[Mapping[str, str]],
    split_decisions: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    by_group: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        by_group[
            (
                text_value(row.get("peak_hypothesis_id")),
                text_value(row.get("sample_subtype")),
            )
        ].append(row)

    rows: list[dict[str, str]] = []
    for split_row in sorted(
        split_decisions,
        key=lambda row: (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_subtype")),
        ),
    ):
        family = text_value(split_row.get("peak_hypothesis_id"))
        subtype = text_value(split_row.get("sample_subtype"))
        group_rows = by_group.get((family, subtype), [])
        blockers = Counter(
            text_value(row.get("primary_blocker"))
            for row in group_rows
            if text_value(row.get("primary_blocker"))
        )
        projected_blockers = Counter(
            text_value(row.get("projected_selective_primary_blocker"))
            for row in group_rows
            if text_value(row.get("projected_selective_primary_blocker"))
        )
        held_count = _count_status(group_rows, "full_chain_status", "held")
        pass_count = _count_status(group_rows, "full_chain_status", "pass")
        projected_held_count = _count_status(
            group_rows,
            "projected_selective_full_chain_status",
            "held",
        )
        projected_pass_count = _count_status(
            group_rows,
            "projected_selective_full_chain_status",
            "pass",
        )
        next_gate = "resolve_full_evidence_chain_before_product_writer_authority"
        if not group_rows:
            next_gate = "no_clean_target_cells_after_split_decision"
        elif projected_held_count == "0":
            next_gate = "eligible_for_expected_diff_authority_design"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "sample_subtype": subtype,
                "split_decision_status": text_value(split_row.get("decision_status")),
                "clean_target_candidate_cell_count": str(len(group_rows)),
                "full_chain_pass_cell_count": pass_count,
                "held_cell_count": held_count,
                "primary_blocker_counts": _counter_text(blockers),
                "projected_selective_full_chain_pass_cell_count": (
                    projected_pass_count
                ),
                "projected_selective_held_cell_count": projected_held_count,
                "projected_selective_primary_blocker_counts": _counter_text(
                    projected_blockers,
                ),
                "product_authority_effect": "diagnostic_only_no_write_authority",
                "next_gate": next_gate,
            },
        )
    return rows


def _split_decision_excluded_counts(
    split_decisions: Sequence[Mapping[str, str]],
) -> dict[str, int]:
    return {
        "boundary_review_excluded_cell_count": _sum_int(
            split_decisions,
            "target_mode_boundary_review_cell_count",
        ),
        "off_target_hold_or_remap_excluded_cell_count": _sum_int(
            split_decisions,
            "off_target_hold_or_remap_cell_count",
        ),
        "missing_or_unclassified_excluded_cell_count": _sum_int(
            split_decisions,
            "missing_or_unclassified_cell_count",
        ),
    }


def _build_checks(
    *,
    split_decisions: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
    excluded_counts: Mapping[str, int],
) -> list[dict[str, str]]:
    unique_count = len(
        {
            (row["peak_hypothesis_id"], row["sample_stem"])
            for row in cell_rows
        },
    )
    family_count = len(
        {
            text_value(row.get("peak_hypothesis_id"))
            for row in split_decisions
        },
    )
    return [
        _check(
            "split_decision_group_count",
            len(split_decisions),
            EXPECTED_COUNTS["split_decision_group_count"],
        ),
        _check(
            "split_decision_family_count",
            family_count,
            EXPECTED_COUNTS["split_decision_family_count"],
        ),
        _check(
            "clean_target_candidate_cell_count",
            len(cell_rows),
            EXPECTED_COUNTS["clean_target_candidate_cell_count"],
        ),
        _check("clean_target_keyset_unique", unique_count, len(cell_rows)),
        _check(
            "boundary_review_excluded_cell_count",
            excluded_counts["boundary_review_excluded_cell_count"],
            EXPECTED_COUNTS["boundary_review_excluded_cell_count"],
        ),
        _check(
            "off_target_hold_or_remap_excluded_cell_count",
            excluded_counts["off_target_hold_or_remap_excluded_cell_count"],
            EXPECTED_COUNTS["off_target_hold_or_remap_excluded_cell_count"],
        ),
        _check(
            "missing_or_unclassified_excluded_cell_count",
            excluded_counts["missing_or_unclassified_excluded_cell_count"],
            EXPECTED_COUNTS["missing_or_unclassified_excluded_cell_count"],
        ),
        _check("no_product_writer_authority", True, True),
        _check("no_default_matrix_or_workbook_change", True, True),
    ]


def _summary_payload(
    *,
    checks: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
    row_manifest: Sequence[Mapping[str, str]],
    split_decisions: Sequence[Mapping[str, str]],
    excluded_counts: Mapping[str, int],
    input_paths: Mapping[str, Path],
    output_paths: Mapping[str, Path],
) -> dict[str, Any]:
    blocker_counts = Counter(
        text_value(row.get("primary_blocker"))
        for row in cell_rows
        if text_value(row.get("primary_blocker"))
    )
    projected_blocker_counts = Counter(
        text_value(row.get("projected_selective_primary_blocker"))
        for row in cell_rows
        if text_value(row.get("projected_selective_primary_blocker"))
    )
    split_status_counts = Counter(
        text_value(row.get("decision_status")) for row in split_decisions
    )
    full_chain_pass_cell_count = int(
        _count_status(cell_rows, "full_chain_status", "pass"),
    )
    held_cell_count = int(_count_status(cell_rows, "full_chain_status", "held"))
    full_chain_complete = full_chain_pass_cell_count == len(cell_rows)
    selective_pass_cell_count = int(
        _count_status(cell_rows, "selective_evidence_status", "pass"),
    )
    selective_held_cell_count = int(
        _count_status(cell_rows, "selective_evidence_status", "held"),
    )
    old_shift_aware_blocker_rows = [
        row
        for row in cell_rows
        if text_value(row.get("primary_blocker"))
        == "shift_aware_gate_blocked_shift_aware_same_pattern_not_supported"
    ]
    old_shift_aware_blocker_selective_pass_count = sum(
        1
        for row in old_shift_aware_blocker_rows
        if text_value(row.get("selective_evidence_status")) == "pass"
    )
    projected_selective_pass_cell_count = int(
        _count_status(
            cell_rows,
            "projected_selective_full_chain_status",
            "pass",
        ),
    )
    projected_selective_held_cell_count = int(
        _count_status(
            cell_rows,
            "projected_selective_full_chain_status",
            "held",
        ),
    )
    projected_selective_full_chain_complete = (
        projected_selective_pass_cell_count == len(cell_rows)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_status": (
            "diagnostic_clean_target_selective_projection_pass"
            if projected_selective_full_chain_complete
            else "diagnostic_clean_target_selective_projection_held"
        ),
        "packet_scope": PACKET_SCOPE,
        "split_decision_group_count": len(split_decisions),
        "split_decision_family_count": len(
            {
                text_value(row.get("peak_hypothesis_id"))
                for row in split_decisions
            },
        ),
        "split_decision_status_counts": dict(sorted(split_status_counts.items())),
        "clean_target_candidate_cell_count": len(cell_rows),
        **excluded_counts,
        "row_manifest_group_count": len(row_manifest),
        "full_chain_pass_cell_count": full_chain_pass_cell_count,
        "held_cell_count": held_cell_count,
        "full_chain_complete": full_chain_complete,
        "primary_blocker_counts": dict(sorted(blocker_counts.items())),
        "selective_evidence_pass_cell_count": selective_pass_cell_count,
        "selective_evidence_held_cell_count": selective_held_cell_count,
        "old_shift_aware_blocker_cell_count": len(old_shift_aware_blocker_rows),
        "old_shift_aware_blocker_selective_pass_cell_count": (
            old_shift_aware_blocker_selective_pass_count
        ),
        "old_shift_aware_blocker_selective_held_cell_count": (
            len(old_shift_aware_blocker_rows)
            - old_shift_aware_blocker_selective_pass_count
        ),
        "projected_selective_full_chain_pass_cell_count": (
            projected_selective_pass_cell_count
        ),
        "projected_selective_held_cell_count": projected_selective_held_cell_count,
        "projected_selective_full_chain_complete": (
            projected_selective_full_chain_complete
        ),
        "projected_selective_primary_blocker_counts": dict(
            sorted(projected_blocker_counts.items()),
        ),
        "product_authority_effect": "diagnostic_only_no_write_authority",
        "write_authority": False,
        "product_writer_changed": False,
        "default_quant_matrix_changed": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "raw_or_85raw_ran_by_checker": False,
        "authority_statement": (
            "This replay only projects clean target-mode split decisions onto "
            "the existing full evidence-chain map and the selective "
            "source-family shift-aware evidence map. Passing projected cells "
            "can inform a later expected-diff authority design, but this "
            "artifact grants no ProductWriter authority."
        ),
        "checks": {row["check_id"]: row["status"] for row in checks},
        "input_artifacts": {
            name: _artifact(path) for name, path in sorted(input_paths.items())
        },
        "artifacts": {
            name: _artifact(path) for name, path in sorted(output_paths.items())
        },
    }


def _check_summary(payload: Mapping[str, Any], problems: list[str]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        problems.append("summary schema_version mismatch")
    if payload.get("packet_scope") != PACKET_SCOPE:
        problems.append("summary packet_scope mismatch")
    for field, expected in EXPECTED_COUNTS.items():
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")
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
    if len(rows) != payload.get("row_manifest_group_count"):
        problems.append("row manifest group count mismatch")
    pass_sum = _sum_int(rows, "full_chain_pass_cell_count")
    if pass_sum != payload.get("full_chain_pass_cell_count"):
        problems.append("row manifest pass count mismatch")
    held_sum = _sum_int(rows, "held_cell_count")
    if held_sum != payload.get("held_cell_count"):
        problems.append("row manifest held count mismatch")
    projected_pass_sum = _sum_int(
        rows,
        "projected_selective_full_chain_pass_cell_count",
    )
    if projected_pass_sum != payload.get(
        "projected_selective_full_chain_pass_cell_count",
    ):
        problems.append("row manifest projected pass count mismatch")
    projected_held_sum = _sum_int(rows, "projected_selective_held_cell_count")
    if projected_held_sum != payload.get("projected_selective_held_cell_count"):
        problems.append("row manifest projected held count mismatch")
    effects = {row.get("product_authority_effect") for row in rows}
    if effects != {"diagnostic_only_no_write_authority"}:
        problems.append("row manifest product_authority_effect mismatch")


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
    if len(rows) != payload.get("clean_target_candidate_cell_count"):
        problems.append("cells TSV clean target count mismatch")
    pass_count = sum(1 for row in rows if row.get("full_chain_status") == "pass")
    if pass_count != payload.get("full_chain_pass_cell_count"):
        problems.append("cells TSV pass count mismatch")
    projected_pass_count = sum(
        1
        for row in rows
        if row.get("projected_selective_full_chain_status") == "pass"
    )
    if projected_pass_count != payload.get(
        "projected_selective_full_chain_pass_cell_count",
    ):
        problems.append("cells TSV projected pass count mismatch")
    effects = {row.get("product_authority_effect") for row in rows}
    if effects != {"diagnostic_only_no_write_authority"}:
        problems.append("cells TSV product_authority_effect mismatch")


def _projected_selective_full_chain_blockers(
    *,
    chain_row: Mapping[str, str],
    selective_row: Mapping[str, str],
    selective_authority_status: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    for field, prefix in (
        ("expected_diff_status", "expected_diff_"),
        ("source_evidence_status", "source_evidence_"),
        ("raw_trace_status", "raw_trace_"),
    ):
        status = text_value(chain_row.get(field)) or "missing_full_chain_row"
        if status != "pass":
            blockers.append(prefix + status)

    selective_status = (
        text_value(selective_row.get("selective_evidence_status"))
        or "missing_selective_shift_row"
    )
    if selective_status != "pass":
        selective_blocker = (
            text_value(selective_row.get("primary_blocker"))
            or selective_status
        )
        blockers.append("selective_" + selective_blocker)

    if selective_authority_status != "pass":
        blockers.append("selective_ms1_product_authority_" + selective_authority_status)
    return tuple(blockers)


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


def _unique_by_cell_key(
    rows: Sequence[Mapping[str, str]],
    *,
    family_field: str = "peak_hypothesis_id",
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (
            text_value(row.get(family_field)),
            text_value(row.get("sample_stem")),
        )
        if not all(key):
            continue
        if key in by_key:
            raise ValueError(f"duplicate cell key: {key[0]}/{key[1]}")
        by_key[key] = row
    return by_key


def _count_status(
    rows: Sequence[Mapping[str, str]],
    field: str,
    value: str,
) -> str:
    return str(sum(1 for row in rows if text_value(row.get(field)) == value))


def _sum_int(rows: Sequence[Mapping[str, str]], field: str) -> int:
    return sum(int(row.get(field) or 0) for row in rows)


def _counter_text(counter: Counter[str]) -> str:
    return ";".join(f"{key}={counter[key]}" for key in sorted(counter))


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


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--checks-tsv", type=Path, default=DEFAULT_CHECKS_TSV)
    parser.add_argument(
        "--row-manifest-tsv",
        type=Path,
        default=DEFAULT_ROW_MANIFEST_TSV,
    )
    parser.add_argument("--cells-tsv", type=Path, default=DEFAULT_CELLS_TSV)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if not args.check_only:
            build_backfill_expansion_clean_target_full_chain_replay(
                cells_tsv=args.cells_tsv,
            )
        problems = validate_backfill_expansion_clean_target_full_chain_replay(
            summary_json=args.summary_json,
            checks_tsv=args.checks_tsv,
            row_manifest_tsv=args.row_manifest_tsv,
            cells_tsv=args.cells_tsv,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    print(f"Clean-target full-chain replay summary: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
