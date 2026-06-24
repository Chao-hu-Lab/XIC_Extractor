"""Build/check the 666-cell Backfill expansion full evidence-chain gate.

This checker consumes the existing Backfill expansion expected-diff packet,
RAW overlay trace identity artifact, shift-aware standard-peak gate, and MS1
product-authority sidecar. It does not read RAW files, mutate the default
matrix, or grant ProductWriter authority.
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

from scripts.build_backfill_expansion_default_product_activation import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_CANDIDATE_DOCS_DIR,
)
from scripts.build_backfill_expansion_default_product_activation import (
    validate_backfill_expansion_default_product_activation,  # noqa: E402
)
from scripts.check_backfill_expansion_expected_diff_provenance import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_EXPECTED_DIFF_OUTPUT_DIR,
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_RAW_TRACE_DOCS_DIR,
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (
    DEFAULT_OUTPUT_DIR as DEFAULT_RAW_TRACE_OUTPUT_DIR,  # noqa: E402
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (
    check_backfill_expansion_raw_overlay_trace_identity,  # noqa: E402
)
from scripts.validation_artifact_contracts import (  # noqa: E402
    check_summary_artifact_hashes,
    is_declared_externalized_artifact_path,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_full_evidence_chain_v1"
CHECK_SCHEMA_VERSION = "backfill_expansion_full_evidence_chain_check_v1"
PRODUCT_LANE = "backfill"
PACKET_SCOPE = "backfill_expansion_candidate_replay_666_cells"
PRODUCT_AUTHORIZED_STATUS = "product_authorized"
PRODUCT_AUTHORIZED_SCOPE = "feature_family_sample"
STANDARD_PEAK_GATE_SUPPORTED = "standard_peak_gate_supported"
OWN_MAX_THRESHOLD = 0.5

DEFAULT_DOCS_DIR = (
    ROOT / "docs/superpowers/validation/backfill_expansion_full_evidence_chain_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_full_evidence_chain_v1"
)
DEFAULT_EXPECTED_DIFF_TSV = (
    DEFAULT_EXPECTED_DIFF_OUTPUT_DIR / "inputs/expected_diff.tsv"
)
DEFAULT_SOURCE_EVIDENCE_TSV = (
    DEFAULT_EXPECTED_DIFF_OUTPUT_DIR
    / "backfill_expansion_expected_diff_provenance_source_evidence.tsv"
)
DEFAULT_RAW_TRACE_CELLS_TSV = (
    DEFAULT_RAW_TRACE_OUTPUT_DIR
    / "backfill_expansion_raw_overlay_trace_identity_cells.tsv"
)
DEFAULT_SHIFT_AWARE_BATCH_SUMMARY_JSON = (
    DEFAULT_OUTPUT_DIR
    / "shift_aware_alignment_experiment/"
    "family_ms1_alignment_experiment_batch_summary.json"
)
DEFAULT_SHIFT_AWARE_CELL_EVIDENCE_ADAPTER_TSV = (
    DEFAULT_OUTPUT_DIR / "shift_aware_cell_evidence_adapter.tsv"
)
DEFAULT_SHIFT_AWARE_CALIBRATION_PACK_TSV = (
    DEFAULT_OUTPUT_DIR
    / "shift_aware_calibration_pack/shift_aware_backfill_calibration_pack.tsv"
)
DEFAULT_SHIFT_AWARE_STANDARD_PEAK_GATE_TSV = (
    DEFAULT_OUTPUT_DIR
    / "shift_aware_standard_peak_gate/shift_aware_standard_peak_gate_calibration.tsv"
)
DEFAULT_MS1_PRODUCT_AUTHORITY_TSV = (
    DEFAULT_OUTPUT_DIR
    / "standard_peak_ms1_authority_bundle/"
    "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
)
DEFAULT_MS1_PRODUCT_AUTHORITY_AUDIT_TSV = (
    DEFAULT_OUTPUT_DIR
    / "standard_peak_ms1_authority_bundle/"
    "backfill_ms1_pattern_product_authority_audit.tsv"
)
DEFAULT_MS1_PRODUCT_AUTHORITY_SUMMARY_JSON = (
    DEFAULT_OUTPUT_DIR
    / "standard_peak_ms1_authority_bundle/"
    "standard_peak_ms1_authority_bundle_summary.json"
)
DEFAULT_CELLS_TSV = (
    DEFAULT_OUTPUT_DIR / "backfill_expansion_full_evidence_chain_cells.tsv"
)
DEFAULT_SUMMARY_JSON = (
    DEFAULT_DOCS_DIR / "backfill_expansion_full_evidence_chain_summary.json"
)
DEFAULT_CHECKS_TSV = (
    DEFAULT_DOCS_DIR / "backfill_expansion_full_evidence_chain_checks.tsv"
)
DEFAULT_ROW_MANIFEST_TSV = (
    DEFAULT_DOCS_DIR / "backfill_expansion_full_evidence_chain_row_manifest.tsv"
)
DEFAULT_CANDIDATE_SUMMARY_JSON = (
    DEFAULT_CANDIDATE_DOCS_DIR
    / "backfill_expansion_default_product_activation_summary.json"
)
DEFAULT_CANDIDATE_CHECKS_TSV = (
    DEFAULT_CANDIDATE_DOCS_DIR
    / "backfill_expansion_default_product_activation_checks.tsv"
)
DEFAULT_CANDIDATE_MANIFEST_TSV = (
    DEFAULT_CANDIDATE_DOCS_DIR
    / "backfill_expansion_default_product_activation_manifest.tsv"
)
DEFAULT_RAW_TRACE_SUMMARY_JSON = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_summary.json"
)
DEFAULT_RAW_TRACE_CHECKS_TSV = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
)
DEFAULT_RAW_TRACE_ROW_MANIFEST_TSV = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
)

EXPECTED_COUNTS = {
    "candidate_cell_count": 666,
    "candidate_peak_count": 20,
    "expected_diff_present_cell_count": 666,
    "source_evidence_present_cell_count": 666,
    "raw_trace_observed_cell_count": 666,
    "shift_aware_gate_family_count": 20,
    "shift_aware_gate_supported_family_count": 14,
    "shift_aware_gate_supported_cell_count": 492,
    "own_max_metric_supported_cell_count": 496,
    "ms1_product_authorized_cell_count": 374,
    "full_chain_pass_cell_count": 374,
    "held_cell_count": 292,
}

EXPECTED_CHECK_IDS = (
    "upstream_candidate_packet_pass",
    "upstream_raw_trace_identity_pass",
    "candidate_scope_count",
    "candidate_keyset_unique",
    "expected_diff_all_present",
    "source_evidence_all_present",
    "raw_trace_observed_all_present",
    "shift_aware_batch_success",
    "shift_aware_gate_family_count",
    "shift_aware_gate_supported_family_count",
    "shift_aware_gate_supported_cell_count",
    "own_max_metric_supported_cell_count",
    "ms1_product_authorized_cell_count",
    "full_chain_pass_cell_count",
    "held_cell_count",
    "full_chain_complete_is_false",
    "no_product_writer_authority",
    "no_default_matrix_or_workbook_change",
)

EXPECTED_DIFF_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "expected_matrix_effect",
)
SOURCE_EVIDENCE_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "alignment_status",
    "production_cell_status",
    "identity_decision",
    "raw_trace_gate_status",
    "source_row_sha256",
)
RAW_TRACE_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "trace_status",
    "absolute_own_max_shape_similarity",
    "raw_trace_gate_status",
    "metric_warning_flags",
)
STANDARD_GATE_COLUMNS = (
    "feature_family_id",
    "standard_peak_gate_call",
    "standard_peak_gate_reasons",
    "standard_peak_gate_blockers",
)
MS1_AUTHORITY_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "product_authority_status",
    "product_authority_scope",
    "product_authority_source",
    "product_authority_reason",
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
    "row_scope",
    "peak_hypothesis_id",
    "candidate_cell_count",
    "expected_diff_present_cell_count",
    "source_evidence_present_cell_count",
    "raw_trace_observed_cell_count",
    "shift_aware_gate_supported_cell_count",
    "own_max_metric_supported_cell_count",
    "ms1_product_authorized_cell_count",
    "full_chain_pass_cell_count",
    "held_cell_count",
    "primary_blocker",
    "product_authority_effect",
    "next_gate",
)
CELL_CHAIN_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "sample_stem",
    "expected_diff_status",
    "source_evidence_status",
    "raw_trace_status",
    "own_max_metric_status",
    "own_max_metric_value",
    "shift_aware_gate_status",
    "shift_aware_gate_call",
    "ms1_product_authority_status",
    "ms1_product_authority_source",
    "full_chain_status",
    "primary_blocker",
    "secondary_blockers",
    "product_authority_effect",
    "next_gate",
)


def build_backfill_expansion_full_evidence_chain(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_diff_tsv: Path = DEFAULT_EXPECTED_DIFF_TSV,
    source_evidence_tsv: Path = DEFAULT_SOURCE_EVIDENCE_TSV,
    raw_trace_cells_tsv: Path = DEFAULT_RAW_TRACE_CELLS_TSV,
    shift_aware_batch_summary_json: Path = DEFAULT_SHIFT_AWARE_BATCH_SUMMARY_JSON,
    shift_aware_cell_evidence_adapter_tsv: Path = (
        DEFAULT_SHIFT_AWARE_CELL_EVIDENCE_ADAPTER_TSV
    ),
    shift_aware_calibration_pack_tsv: Path = DEFAULT_SHIFT_AWARE_CALIBRATION_PACK_TSV,
    shift_aware_standard_peak_gate_tsv: Path = (
        DEFAULT_SHIFT_AWARE_STANDARD_PEAK_GATE_TSV
    ),
    ms1_product_authority_tsv: Path = DEFAULT_MS1_PRODUCT_AUTHORITY_TSV,
    ms1_product_authority_audit_tsv: Path = DEFAULT_MS1_PRODUCT_AUTHORITY_AUDIT_TSV,
    ms1_product_authority_summary_json: Path = (
        DEFAULT_MS1_PRODUCT_AUTHORITY_SUMMARY_JSON
    ),
    candidate_summary_json: Path = DEFAULT_CANDIDATE_SUMMARY_JSON,
    candidate_checks_tsv: Path = DEFAULT_CANDIDATE_CHECKS_TSV,
    candidate_compact_manifest_tsv: Path = DEFAULT_CANDIDATE_MANIFEST_TSV,
    raw_trace_summary_json: Path = DEFAULT_RAW_TRACE_SUMMARY_JSON,
    raw_trace_checks_tsv: Path = DEFAULT_RAW_TRACE_CHECKS_TSV,
    raw_trace_row_manifest_tsv: Path = DEFAULT_RAW_TRACE_ROW_MANIFEST_TSV,
    cells_tsv: Path = DEFAULT_CELLS_TSV,
) -> dict[str, Any]:
    candidate_problems = validate_backfill_expansion_default_product_activation(
        summary_json=candidate_summary_json,
        checks_tsv=candidate_checks_tsv,
        compact_manifest_tsv=candidate_compact_manifest_tsv,
    )
    if candidate_problems:
        raise ValueError(
            "Backfill expansion candidate packet failed: "
            + "; ".join(candidate_problems),
        )
    raw_trace_problems = check_backfill_expansion_raw_overlay_trace_identity(
        summary_json=raw_trace_summary_json,
        checks_tsv=raw_trace_checks_tsv,
        row_manifest_tsv=raw_trace_row_manifest_tsv,
    )
    if raw_trace_problems:
        raise ValueError(
            "Backfill expansion raw trace identity packet failed: "
            + "; ".join(raw_trace_problems),
        )

    expected_rows = read_tsv_required(expected_diff_tsv, EXPECTED_DIFF_COLUMNS)
    source_rows = read_tsv_required(source_evidence_tsv, SOURCE_EVIDENCE_COLUMNS)
    raw_rows = read_tsv_required(raw_trace_cells_tsv, RAW_TRACE_COLUMNS)
    gate_rows = read_tsv_required(
        shift_aware_standard_peak_gate_tsv,
        STANDARD_GATE_COLUMNS,
    )
    authority_rows = read_tsv_required(ms1_product_authority_tsv, MS1_AUTHORITY_COLUMNS)

    expected_by_key = _unique_by_key(expected_rows, "peak_hypothesis_id")
    source_by_key = _unique_by_key(source_rows, "peak_hypothesis_id")
    raw_by_key = _unique_by_key(raw_rows, "peak_hypothesis_id")
    gate_by_family = {
        text_value(row.get("feature_family_id")): row
        for row in gate_rows
        if text_value(row.get("feature_family_id"))
    }
    authority_by_key = _unique_by_key(authority_rows, "feature_family_id")

    cell_rows = _build_cell_rows(
        expected_rows=expected_rows,
        expected_by_key=expected_by_key,
        source_by_key=source_by_key,
        raw_by_key=raw_by_key,
        gate_by_family=gate_by_family,
        authority_by_key=authority_by_key,
    )
    row_manifest = _build_row_manifest(cell_rows)
    checks = _build_checks(
        cell_rows=cell_rows,
        row_manifest=row_manifest,
        gate_rows=gate_rows,
        shift_aware_batch_summary_json=shift_aware_batch_summary_json,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(cells_tsv, cell_rows, CELL_CHAIN_COLUMNS, extrasaction="raise")
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
        input_paths={
            "expected_diff_tsv": expected_diff_tsv,
            "source_evidence_tsv": source_evidence_tsv,
            "raw_trace_cells_tsv": raw_trace_cells_tsv,
            "shift_aware_batch_summary_json": shift_aware_batch_summary_json,
            "shift_aware_cell_evidence_adapter_tsv": (
                shift_aware_cell_evidence_adapter_tsv
            ),
            "shift_aware_calibration_pack_tsv": shift_aware_calibration_pack_tsv,
            "shift_aware_standard_peak_gate_tsv": shift_aware_standard_peak_gate_tsv,
            "ms1_product_authority_tsv": ms1_product_authority_tsv,
            "ms1_product_authority_audit_tsv": ms1_product_authority_audit_tsv,
            "ms1_product_authority_summary_json": (
                ms1_product_authority_summary_json
            ),
            "candidate_summary_json": candidate_summary_json,
            "candidate_checks_tsv": candidate_checks_tsv,
            "candidate_compact_manifest_tsv": candidate_compact_manifest_tsv,
            "raw_trace_summary_json": raw_trace_summary_json,
            "raw_trace_checks_tsv": raw_trace_checks_tsv,
            "raw_trace_row_manifest_tsv": raw_trace_row_manifest_tsv,
        },
        output_paths={
            "cells_tsv": cells_tsv,
            "checks_tsv": checks_tsv,
            "row_manifest_tsv": row_manifest_tsv,
        },
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def validate_backfill_expansion_full_evidence_chain(
    *,
    summary_json: Path = DEFAULT_SUMMARY_JSON,
    checks_tsv: Path = DEFAULT_CHECKS_TSV,
    row_manifest_tsv: Path = DEFAULT_ROW_MANIFEST_TSV,
    cells_tsv: Path = DEFAULT_CELLS_TSV,
    require_full_chain: bool = False,
) -> list[str]:
    problems: list[str] = []
    try:
        payload = json.loads(summary_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read summary JSON: {exc}"]
    if not isinstance(payload, Mapping):
        return ["summary JSON must contain an object"]

    _check_summary_counts(payload, problems)
    _check_checks_tsv(checks_tsv, payload, problems)
    _check_manifest_tsv(row_manifest_tsv, payload, problems)
    if cells_tsv.exists():
        _check_cells_tsv(cells_tsv, payload, problems)
    elif not is_declared_externalized_artifact_path(
        payload,
        "cells_tsv",
        cells_tsv,
        root=ROOT,
    ):
        problems.append(f"cells TSV missing: {cells_tsv}")
    _check_artifact_hashes(payload, problems)
    if require_full_chain and payload.get("full_chain_complete") is not True:
        problems.append(
            "full evidence chain incomplete: "
            f"{payload.get('full_chain_pass_cell_count')}/"
            f"{payload.get('candidate_cell_count')} cells pass; "
            f"held={payload.get('held_cell_count')}",
        )
    return problems


def _build_cell_rows(
    *,
    expected_rows: Sequence[Mapping[str, str]],
    expected_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    source_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    raw_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    gate_by_family: Mapping[str, Mapping[str, str]],
    authority_by_key: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for expected in expected_rows:
        family = text_value(expected.get("peak_hypothesis_id"))
        sample = text_value(expected.get("sample_stem"))
        key = (family, sample)
        source = source_by_key.get(key)
        raw = raw_by_key.get(key)
        gate = gate_by_family.get(family)
        authority = authority_by_key.get(key)

        expected_status = _expected_status(expected_by_key.get(key))
        source_status = _source_status(source)
        raw_status = _raw_trace_status(raw)
        own_status, own_value = _own_max_status(raw)
        gate_status = _gate_status(gate)
        authority_status = _authority_status(authority)
        blockers = _blockers(
            expected_status=expected_status,
            source_status=source_status,
            raw_status=raw_status,
            own_status=own_status,
            gate_status=gate_status,
            authority_status=authority_status,
        )
        full_chain_status = "pass" if not blockers else "held"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "peak_hypothesis_id": family,
                "sample_stem": sample,
                "expected_diff_status": expected_status,
                "source_evidence_status": source_status,
                "raw_trace_status": raw_status,
                "own_max_metric_status": own_status,
                "own_max_metric_value": own_value,
                "shift_aware_gate_status": gate_status,
                "shift_aware_gate_call": text_value(
                    (gate or {}).get("standard_peak_gate_call"),
                ),
                "ms1_product_authority_status": authority_status,
                "ms1_product_authority_source": text_value(
                    (authority or {}).get("product_authority_source"),
                ),
                "full_chain_status": full_chain_status,
                "primary_blocker": blockers[0] if blockers else "",
                "secondary_blockers": ";".join(blockers[1:]),
                "product_authority_effect": "candidate_only_no_write_authority",
                "next_gate": (
                    "ready_for_product_authority_activation_contract"
                    if full_chain_status == "pass"
                    else "resolve_full_evidence_chain_before_product_writer_authority"
                ),
            },
        )
    return rows


def _build_row_manifest(
    cell_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        by_family[text_value(row.get("peak_hypothesis_id"))].append(row)

    manifest: list[dict[str, str]] = []
    for family in sorted(by_family):
        rows = by_family[family]
        blockers = Counter(
            text_value(row.get("primary_blocker")) for row in rows if row.get(
                "primary_blocker",
            )
        )
        primary_blocker = blockers.most_common(1)[0][0] if blockers else ""
        manifest.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_scope": PACKET_SCOPE,
                "peak_hypothesis_id": family,
                "candidate_cell_count": str(len(rows)),
                "expected_diff_present_cell_count": _count_status(
                    rows,
                    "expected_diff_status",
                    "pass",
                ),
                "source_evidence_present_cell_count": _count_status(
                    rows,
                    "source_evidence_status",
                    "pass",
                ),
                "raw_trace_observed_cell_count": _count_status(
                    rows,
                    "raw_trace_status",
                    "pass",
                ),
                "shift_aware_gate_supported_cell_count": _count_status(
                    rows,
                    "shift_aware_gate_status",
                    "pass",
                ),
                "own_max_metric_supported_cell_count": _count_status(
                    rows,
                    "own_max_metric_status",
                    "pass",
                ),
                "ms1_product_authorized_cell_count": _count_status(
                    rows,
                    "ms1_product_authority_status",
                    "pass",
                ),
                "full_chain_pass_cell_count": _count_status(
                    rows,
                    "full_chain_status",
                    "pass",
                ),
                "held_cell_count": _count_status(rows, "full_chain_status", "held"),
                "primary_blocker": primary_blocker,
                "product_authority_effect": "candidate_only_no_write_authority",
                "next_gate": (
                    "resolve_full_evidence_chain_before_product_writer_authority"
                ),
            },
        )
    return manifest


def _build_checks(
    *,
    cell_rows: Sequence[Mapping[str, str]],
    row_manifest: Sequence[Mapping[str, str]],
    gate_rows: Sequence[Mapping[str, str]],
    shift_aware_batch_summary_json: Path,
) -> list[dict[str, str]]:
    candidate_count = len(cell_rows)
    unique_count = len(
        {
            (row["peak_hypothesis_id"], row["sample_stem"])
            for row in cell_rows
        },
    )
    gate_supported_family_count = sum(
        1
        for row in gate_rows
        if text_value(row.get("standard_peak_gate_call"))
        == STANDARD_PEAK_GATE_SUPPORTED
    )
    batch_summary = _read_json_object(shift_aware_batch_summary_json)
    return [
        _check("upstream_candidate_packet_pass", "TRUE", "TRUE"),
        _check("upstream_raw_trace_identity_pass", "TRUE", "TRUE"),
        _check(
            "candidate_scope_count",
            candidate_count,
            EXPECTED_COUNTS["candidate_cell_count"],
        ),
        _check("candidate_keyset_unique", unique_count, candidate_count),
        _counted_status_check(
            "expected_diff_all_present",
            cell_rows,
            "expected_diff_status",
            "pass",
            EXPECTED_COUNTS["expected_diff_present_cell_count"],
        ),
        _counted_status_check(
            "source_evidence_all_present",
            cell_rows,
            "source_evidence_status",
            "pass",
            EXPECTED_COUNTS["source_evidence_present_cell_count"],
        ),
        _counted_status_check(
            "raw_trace_observed_all_present",
            cell_rows,
            "raw_trace_status",
            "pass",
            EXPECTED_COUNTS["raw_trace_observed_cell_count"],
        ),
        _check(
            "shift_aware_batch_success",
            batch_summary.get("successful_shift_aware_row_count"),
            EXPECTED_COUNTS["candidate_peak_count"],
        ),
        _check(
            "shift_aware_gate_family_count",
            len(gate_rows),
            EXPECTED_COUNTS["shift_aware_gate_family_count"],
        ),
        _check(
            "shift_aware_gate_supported_family_count",
            gate_supported_family_count,
            EXPECTED_COUNTS["shift_aware_gate_supported_family_count"],
        ),
        _counted_status_check(
            "shift_aware_gate_supported_cell_count",
            cell_rows,
            "shift_aware_gate_status",
            "pass",
            EXPECTED_COUNTS["shift_aware_gate_supported_cell_count"],
        ),
        _counted_status_check(
            "own_max_metric_supported_cell_count",
            cell_rows,
            "own_max_metric_status",
            "pass",
            EXPECTED_COUNTS["own_max_metric_supported_cell_count"],
        ),
        _counted_status_check(
            "ms1_product_authorized_cell_count",
            cell_rows,
            "ms1_product_authority_status",
            "pass",
            EXPECTED_COUNTS["ms1_product_authorized_cell_count"],
        ),
        _counted_status_check(
            "full_chain_pass_cell_count",
            cell_rows,
            "full_chain_status",
            "pass",
            EXPECTED_COUNTS["full_chain_pass_cell_count"],
        ),
        _counted_status_check(
            "held_cell_count",
            cell_rows,
            "full_chain_status",
            "held",
            EXPECTED_COUNTS["held_cell_count"],
        ),
        _check("full_chain_complete_is_false", "FALSE", "FALSE"),
        _check("no_product_writer_authority", "TRUE", "TRUE"),
        _check("no_default_matrix_or_workbook_change", "TRUE", "TRUE"),
    ]


def _summary_payload(
    *,
    checks: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
    row_manifest: Sequence[Mapping[str, str]],
    input_paths: Mapping[str, Path],
    output_paths: Mapping[str, Path],
) -> dict[str, Any]:
    check_observed = {row["check_id"]: row["observed"] for row in checks}
    counts = {
        "candidate_cell_count": len(cell_rows),
        "candidate_peak_count": len(row_manifest),
        "shift_aware_gate_family_count": _int_from_check(
            check_observed,
            "shift_aware_gate_family_count",
        ),
        "shift_aware_gate_supported_family_count": _int_from_check(
            check_observed,
            "shift_aware_gate_supported_family_count",
        ),
        "expected_diff_present_cell_count": int(
            _count_status(cell_rows, "expected_diff_status", "pass"),
        ),
        "source_evidence_present_cell_count": int(
            _count_status(cell_rows, "source_evidence_status", "pass"),
        ),
        "raw_trace_observed_cell_count": int(
            _count_status(cell_rows, "raw_trace_status", "pass"),
        ),
        "shift_aware_gate_supported_cell_count": int(
            _count_status(cell_rows, "shift_aware_gate_status", "pass"),
        ),
        "own_max_metric_supported_cell_count": int(
            _count_status(cell_rows, "own_max_metric_status", "pass"),
        ),
        "ms1_product_authorized_cell_count": int(
            _count_status(cell_rows, "ms1_product_authority_status", "pass"),
        ),
        "full_chain_pass_cell_count": int(
            _count_status(cell_rows, "full_chain_status", "pass"),
        ),
        "held_cell_count": int(_count_status(cell_rows, "full_chain_status", "held")),
    }
    full_chain_complete = (
        counts["full_chain_pass_cell_count"] == counts["candidate_cell_count"]
    )
    blocker_counts = Counter(
        text_value(row.get("primary_blocker"))
        for row in cell_rows
        if text_value(row.get("primary_blocker"))
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_status": (
            "production_candidate_full_chain_pass"
            if full_chain_complete
            else "production_candidate_held_incomplete_chain"
        ),
        "product_lane": PRODUCT_LANE,
        "packet_scope": PACKET_SCOPE,
        **counts,
        "full_chain_complete": full_chain_complete,
        "primary_blocker_counts": dict(sorted(blocker_counts.items())),
        "product_authority_effect": "candidate_only_no_write_authority",
        "write_authority": False,
        "product_writer_changed": False,
        "default_quant_matrix_changed": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "raw_or_85raw_ran_by_checker": False,
        "authority_statement": (
            "Only cells with expected diff, sample-local source evidence, "
            "RAW trace identity, shift-aware standard-peak gate support, "
            "own-max metric support, and product-authorized MS1 sidecar can "
            "advance to a later activation contract. This checker grants no "
            "ProductWriter authority."
        ),
        "checks": {row["check_id"]: row["status"] for row in checks},
        "input_artifacts": {
            name: _artifact(path) for name, path in sorted(input_paths.items())
        },
        "artifacts": {
            name: _artifact(path) for name, path in sorted(output_paths.items())
        },
    }


def _expected_status(row: Mapping[str, str] | None) -> str:
    if row is None:
        return "missing"
    if text_value(row.get("expected_matrix_effect")) != "write_accepted_backfill":
        return "unexpected_effect"
    return "pass"


def _source_status(row: Mapping[str, str] | None) -> str:
    if row is None:
        return "missing"
    if text_value(row.get("alignment_status")) != "rescued":
        return "alignment_not_rescued"
    if text_value(row.get("production_cell_status")) != "review_rescue":
        return "production_cell_not_review_rescue"
    if text_value(row.get("identity_decision")) != "production_family":
        return "identity_not_production_family"
    return "pass"


def _raw_trace_status(row: Mapping[str, str] | None) -> str:
    if row is None:
        return "missing"
    if text_value(row.get("trace_status")) != "rescued":
        return "trace_not_rescued"
    if (
        text_value(row.get("raw_trace_gate_status"))
        != "raw_trace_observed_expected_diff_candidate"
    ):
        return "raw_trace_gate_not_candidate"
    return "pass"


def _own_max_status(row: Mapping[str, str] | None) -> tuple[str, str]:
    if row is None:
        return "missing", ""
    value = optional_float(row.get("absolute_own_max_shape_similarity"))
    if value is None:
        return "missing", ""
    formatted = f"{value:.6g}"
    if value <= OWN_MAX_THRESHOLD:
        return "below_threshold", formatted
    return "pass", formatted


def _gate_status(row: Mapping[str, str] | None) -> str:
    if row is None:
        return "missing"
    if text_value(row.get("standard_peak_gate_call")) != STANDARD_PEAK_GATE_SUPPORTED:
        blockers = text_value(row.get("standard_peak_gate_blockers"))
        return "blocked:" + (blockers or "standard_peak_gate_not_supported")
    return "pass"


def _authority_status(row: Mapping[str, str] | None) -> str:
    if row is None:
        return "missing"
    if text_value(row.get("product_authority_status")) != PRODUCT_AUTHORIZED_STATUS:
        return "not_product_authorized"
    if text_value(row.get("product_authority_scope")) != PRODUCT_AUTHORIZED_SCOPE:
        return "wrong_scope"
    if not text_value(row.get("product_authority_source")):
        return "missing_source"
    return "pass"


def _blockers(
    *,
    expected_status: str,
    source_status: str,
    raw_status: str,
    own_status: str,
    gate_status: str,
    authority_status: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if expected_status != "pass":
        blockers.append("expected_diff_" + expected_status)
    if source_status != "pass":
        blockers.append("source_evidence_" + source_status)
    if raw_status != "pass":
        blockers.append("raw_trace_" + raw_status)
    if gate_status != "pass":
        blockers.append("shift_aware_gate_" + gate_status.replace(":", "_"))
    if own_status != "pass":
        blockers.append("own_max_metric_" + own_status)
    if authority_status != "pass":
        blockers.append("ms1_product_authority_" + authority_status)
    return tuple(blockers)


def _unique_by_key(
    rows: Sequence[Mapping[str, str]],
    family_field: str,
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
            raise ValueError(f"duplicate key: {key[0]}/{key[1]}")
        by_key[key] = row
    return by_key


def _counted_status_check(
    check_id: str,
    rows: Sequence[Mapping[str, str]],
    field: str,
    value: str,
    expected: object,
) -> dict[str, str]:
    return _check(check_id, _count_status(rows, field, value), expected)


def _count_status(
    rows: Sequence[Mapping[str, str]],
    field: str,
    value: str,
) -> str:
    return str(sum(1 for row in rows if text_value(row.get(field)) == value))


def _int_from_check(check_observed: Mapping[str, str], check_id: str) -> int:
    return int(check_observed[check_id])


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


def _read_json_object(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _check_summary_counts(payload: Mapping[str, Any], problems: list[str]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        problems.append("summary schema_version mismatch")
    if payload.get("packet_scope") != PACKET_SCOPE:
        problems.append("summary packet_scope mismatch")
    for field, expected in EXPECTED_COUNTS.items():
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")
    if payload.get("full_chain_complete") is not False:
        problems.append("summary full_chain_complete must be false for this packet")
    if payload.get("write_authority") is not False:
        problems.append("summary write_authority must be false")
    if payload.get("product_writer_changed") is not False:
        problems.append("summary product_writer_changed must be false")
    if payload.get("default_quant_matrix_changed") is not False:
        problems.append("summary default_quant_matrix_changed must be false")


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
    observed_ids = {row.get("check_id", "") for row in rows}
    missing = [
        check_id for check_id in EXPECTED_CHECK_IDS if check_id not in observed_ids
    ]
    if missing:
        problems.append("checks missing required ids: " + ";".join(missing))
    failing = [row["check_id"] for row in rows if row.get("status") != "pass"]
    if failing:
        problems.append("checks must all pass: " + ";".join(failing))
    summary_checks = payload.get("checks")
    if isinstance(summary_checks, Mapping):
        for check_id in EXPECTED_CHECK_IDS:
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
    full_chain_sum = sum(
        int(row.get("full_chain_pass_cell_count") or 0) for row in rows
    )
    if full_chain_sum != payload.get("full_chain_pass_cell_count"):
        problems.append("row manifest full-chain pass cell count mismatch")
    held_sum = sum(int(row.get("held_cell_count") or 0) for row in rows)
    if held_sum != payload.get("held_cell_count"):
        problems.append("row manifest held cell count mismatch")
    bad_effect = [
        row
        for row in rows
        if row.get("product_authority_effect") != "candidate_only_no_write_authority"
    ]
    if bad_effect:
        problems.append("row manifest product_authority_effect mismatch")


def _check_cells_tsv(
    cells_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(cells_tsv, CELL_CHAIN_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read cells TSV: {exc}")
        return
    if len(rows) != payload.get("candidate_cell_count"):
        problems.append("cells TSV candidate count mismatch")
    full_chain_count = sum(1 for row in rows if row.get("full_chain_status") == "pass")
    if full_chain_count != payload.get("full_chain_pass_cell_count"):
        problems.append("cells TSV full-chain pass count mismatch")
    writer_effects = {row.get("product_authority_effect") for row in rows}
    if writer_effects != {"candidate_only_no_write_authority"}:
        problems.append("cells TSV product_authority_effect mismatch")


def _check_artifact_hashes(payload: Mapping[str, Any], problems: list[str]) -> None:
    check_summary_artifact_hashes(
        payload,
        root=ROOT,
        problems=problems,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-full-chain", action="store_true")
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
            build_backfill_expansion_full_evidence_chain(
                cells_tsv=args.cells_tsv,
            )
        problems = validate_backfill_expansion_full_evidence_chain(
            summary_json=args.summary_json,
            checks_tsv=args.checks_tsv,
            row_manifest_tsv=args.row_manifest_tsv,
            cells_tsv=args.cells_tsv,
            require_full_chain=args.require_full_chain,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if args.require_full_chain else 2
    print(f"Backfill expansion full evidence-chain summary: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
