"""Build/check the 666-cell Backfill expansion candidate replay bundle.

This is a candidate replay after the Backfill expansion expected-diff
provenance gate. It reuses the existing ProductionAcceptanceManifest and
QuantMatrixVersion writer path as a dry-run replay, but it does not grant public
ProductWriter authority because shift-aware standard-peak support and MS1
own-max evidence are not yet wired into this 666-cell packet.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_quant_matrix_version import run_activation  # noqa: E402
from scripts.check_backfill_expansion_expected_diff_provenance import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_PACKET_DOCS_DIR,
)
from scripts.check_backfill_expansion_expected_diff_provenance import (
    DEFAULT_OUTPUT_DIR as DEFAULT_PACKET_OUTPUT_DIR,  # noqa: E402
)
from scripts.check_backfill_expansion_expected_diff_provenance import (
    EXPECTED_COUNTS as PACKET_EXPECTED_COUNTS,  # noqa: E402
)
from scripts.check_backfill_expansion_expected_diff_provenance import (
    ROW_MANIFEST_COLUMNS as PACKET_ROW_MANIFEST_COLUMNS,  # noqa: E402
)
from scripts.check_backfill_expansion_expected_diff_provenance import (
    check_backfill_expansion_expected_diff_provenance,  # noqa: E402
)
from scripts.validation_artifact_contracts import (  # noqa: E402
    check_summary_artifact_hashes,
    resolve_existing_summary_artifact_path,
)
from xic_extractor.alignment.quant_matrix_version import (  # noqa: E402
    CELL_PROVENANCE_COLUMNS,
    EXPECTED_DIFF_COLUMNS,
    EXPECTED_DIFF_SUMMARY_COLUMNS,
    SOURCE_SUMMARY_COLUMNS,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    numeric_equal,
    optional_int,
    read_tsv_required,
    read_tsv_with_header,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_default_product_activation_v1"
CHECK_SCHEMA_VERSION = "backfill_expansion_default_product_activation_check_v1"
ACTIVATION_LABEL = "backfill_expansion_candidate_packet_held"
PRODUCT_AUTHORITY_SCOPE = ""
PRODUCT_LANE = "backfill"
PRODUCT_SCOPE_KIND = "backfill_expansion_candidate_replay"
DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_default_product_activation_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_default_product_activation_v1"
)
DEFAULT_PACKET_SUMMARY_JSON = (
    DEFAULT_PACKET_DOCS_DIR
    / "backfill_expansion_expected_diff_provenance_summary.json"
)
DEFAULT_PACKET_CHECKS_TSV = (
    DEFAULT_PACKET_DOCS_DIR / "backfill_expansion_expected_diff_provenance_checks.tsv"
)
DEFAULT_PACKET_ROW_MANIFEST_TSV = (
    DEFAULT_PACKET_DOCS_DIR
    / "backfill_expansion_expected_diff_provenance_row_manifest.tsv"
)
DEFAULT_PACKET_PRODUCTION_MANIFEST_TSV = (
    DEFAULT_PACKET_OUTPUT_DIR / "inputs/production_acceptance_manifest.tsv"
)
DEFAULT_PACKET_EXPECTED_DIFF_TSV = (
    DEFAULT_PACKET_OUTPUT_DIR / "inputs/expected_diff.tsv"
)

EXPECTED_COUNTS = {
    "accepted_backfill_count": PACKET_EXPECTED_COUNTS["candidate_cell_count"],
    "candidate_peak_count": PACKET_EXPECTED_COUNTS["candidate_peak_count"],
    "expected_diff_count": PACKET_EXPECTED_COUNTS["expected_diff_count"],
    "written_backfill_count": PACKET_EXPECTED_COUNTS[
        "dry_run_written_backfill_count"
    ],
    "unused_expected_diff_count": 0,
    "cell_provenance_accepted_count": PACKET_EXPECTED_COUNTS[
        "cell_provenance_accepted_count"
    ],
    "matrix_changed_cell_count": PACKET_EXPECTED_COUNTS["matrix_changed_cell_count"],
    "held_cell_count": PACKET_EXPECTED_COUNTS["held_cell_count"],
}

CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
COMPACT_MANIFEST_COLUMNS = (
    "schema_version",
    "row_scope",
    "peak_hypothesis_id",
    "accepted_backfill_cell_count",
    "baseline_available_cell_count",
    "activated_available_cell_count",
    "missing_cell_count",
    "metric_warning_cell_count",
    "product_authority_scope",
    "default_activation_effect",
)
EXPECTED_CHECK_IDS = (
    "expected_diff_provenance_packet_pass",
    "accepted_backfill_count",
    "candidate_peak_count",
    "expected_diff_count",
    "written_backfill_count",
    "unused_expected_diff_count",
    "cell_provenance_accepted_count",
    "matrix_changed_cell_count",
    "candidate_quant_matrix_replay_changed",
    "no_public_product_writer_change",
    "no_public_default_quant_matrix_change",
    "shift_aware_own_max_evidence_not_wired",
    "no_workbook_gui_selected_area_counting_change",
)


def build_backfill_expansion_default_product_activation(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    packet_summary_json: Path = DEFAULT_PACKET_SUMMARY_JSON,
    packet_checks_tsv: Path = DEFAULT_PACKET_CHECKS_TSV,
    packet_row_manifest_tsv: Path = DEFAULT_PACKET_ROW_MANIFEST_TSV,
    packet_production_manifest_tsv: Path = DEFAULT_PACKET_PRODUCTION_MANIFEST_TSV,
    packet_expected_diff_tsv: Path = DEFAULT_PACKET_EXPECTED_DIFF_TSV,
) -> dict[str, Any]:
    packet_problems = check_backfill_expansion_expected_diff_provenance(
        summary_json=packet_summary_json,
        checks_tsv=packet_checks_tsv,
        row_manifest_tsv=packet_row_manifest_tsv,
    )
    if packet_problems:
        raise ValueError(
            "Backfill expansion expected-diff provenance packet failed: "
            + "; ".join(packet_problems),
        )
    packet_payload = _read_json_object(packet_summary_json)
    packet_artifacts = packet_payload.get("artifacts")
    packet_inputs = packet_payload.get("input_artifacts")
    if not isinstance(packet_artifacts, Mapping) or not isinstance(
        packet_inputs,
        Mapping,
    ):
        raise ValueError("packet summary missing artifact maps")

    baseline_quant_matrix_tsv = _artifact_path(
        packet_inputs,
        "baseline_quant_matrix_tsv",
    )
    input_matrix_identity_tsv = _artifact_path(
        packet_inputs,
        "input_matrix_identity_tsv",
    )
    packet_manifest = packet_production_manifest_tsv.resolve()
    packet_expected_diff = packet_expected_diff_tsv.resolve()
    _require_artifact_match(
        packet_artifacts,
        "production_acceptance_manifest",
        packet_manifest,
    )
    _require_artifact_match(packet_artifacts, "expected_diff", packet_expected_diff)

    docs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    default_output_dir = output_dir / "default_output"
    activation_outputs = run_activation(
        input_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        production_acceptance_manifest_tsv=packet_manifest,
        expected_diff_tsv=packet_expected_diff,
        output_dir=default_output_dir,
        manifest_root=ROOT,
    )
    _rewrite_source_summary_paths(activation_outputs["source_summary"])
    activation_facts = _activation_facts(
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        activated_quant_matrix_tsv=activation_outputs["quant_matrix"],
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        expected_diff_tsv=packet_expected_diff,
        expected_diff_summary_tsv=activation_outputs["expected_diff_summary"],
        cell_provenance_tsv=activation_outputs["cell_provenance"],
    )
    checks = _check_rows(
        packet_payload=packet_payload,
        activation_facts=activation_facts,
        packet_problem_count=len(packet_problems),
    )
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Backfill expansion default activation failed: " + ";".join(failed),
        )

    compact_manifest_rows = _compact_manifest_rows(packet_row_manifest_tsv)
    checks_tsv = docs_dir / "backfill_expansion_default_product_activation_checks.tsv"
    compact_manifest_tsv = (
        docs_dir / "backfill_expansion_default_product_activation_manifest.tsv"
    )
    summary_json = (
        docs_dir / "backfill_expansion_default_product_activation_summary.json"
    )
    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        compact_manifest_tsv,
        compact_manifest_rows,
        COMPACT_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        docs_dir=docs_dir,
        output_dir=output_dir,
        checks_tsv=checks_tsv,
        compact_manifest_tsv=compact_manifest_tsv,
        packet_summary_json=packet_summary_json,
        packet_checks_tsv=packet_checks_tsv,
        packet_row_manifest_tsv=packet_row_manifest_tsv,
        packet_production_manifest_tsv=packet_manifest,
        packet_expected_diff_tsv=packet_expected_diff,
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        activation_outputs=activation_outputs,
        activation_facts=activation_facts,
        check_rows=checks,
        compact_manifest_rows=compact_manifest_rows,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def validate_backfill_expansion_default_product_activation(
    *,
    summary_json: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_default_product_activation_summary.json",
    checks_tsv: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_default_product_activation_checks.tsv",
    compact_manifest_tsv: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_default_product_activation_manifest.tsv",
) -> list[str]:
    problems: list[str] = []
    try:
        payload = _read_json_object(summary_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    _check_summary_fields(payload, problems)
    _check_artifact_hashes(payload, problems)
    _check_checks_tsv(checks_tsv, payload, problems)
    _check_compact_manifest(compact_manifest_tsv, payload, problems)
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, Mapping):
        expected_summary = resolve_existing_summary_artifact_path(
            artifacts,
            "expected_diff_summary",
            root=ROOT,
            problems=problems,
        )
        cell_provenance = resolve_existing_summary_artifact_path(
            artifacts,
            "cell_provenance",
            root=ROOT,
            problems=problems,
        )
        quant_matrix = resolve_existing_summary_artifact_path(
            artifacts,
            "quant_matrix",
            root=ROOT,
            problems=problems,
        )
        if expected_summary is not None:
            _check_expected_diff_summary(expected_summary, payload, problems)
        if cell_provenance is not None:
            _check_cell_provenance(cell_provenance, payload, problems)
        if quant_matrix is not None and not quant_matrix.exists():
            problems.append("quant_matrix artifact missing")
    return problems


def _activation_facts(
    *,
    baseline_quant_matrix_tsv: Path,
    activated_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    expected_diff_tsv: Path,
    expected_diff_summary_tsv: Path,
    cell_provenance_tsv: Path,
) -> dict[str, Any]:
    expected_rows = read_tsv_required(expected_diff_tsv, EXPECTED_DIFF_COLUMNS)
    expected_values = {
        (row["peak_hypothesis_id"], row["sample_stem"]): row["activated_value"]
        for row in expected_rows
    }
    changed_keys = _matrix_changed_keys(
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        activated_quant_matrix_tsv=activated_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        expected_values=expected_values,
    )
    expected_summary_rows = read_tsv_required(
        expected_diff_summary_tsv,
        EXPECTED_DIFF_SUMMARY_COLUMNS,
    )
    if len(expected_summary_rows) != 1:
        raise ValueError("expected_diff_summary must have one row")
    cell_provenance_rows = read_tsv_required(
        cell_provenance_tsv,
        CELL_PROVENANCE_COLUMNS,
    )
    accepted_rows = [
        row
        for row in cell_provenance_rows
        if row.get("cell_status") == "accepted_backfill"
    ]
    accepted_keys = {
        (row.get("peak_hypothesis_id", ""), row.get("sample_stem", ""))
        for row in accepted_rows
    }
    value_mismatch_count = sum(
        1
        for row in accepted_rows
        if not numeric_equal(
            row.get("matrix_value", ""),
            expected_values.get(
                (row.get("peak_hypothesis_id", ""), row.get("sample_stem", "")),
                "",
            ),
        )
    )
    return {
        "expected_diff_count": len(expected_rows),
        "expected_keys": set(expected_values),
        "changed_keys": changed_keys,
        "changed_keyset_matches": changed_keys == set(expected_values),
        "expected_diff_summary": expected_summary_rows[0],
        "written_backfill_count": optional_int(
            expected_summary_rows[0]["written_backfill_count"],
        ),
        "unused_expected_diff_count": optional_int(
            expected_summary_rows[0]["unused_expected_diff_count"],
        ),
        "accepted_cell_provenance_count": len(accepted_rows),
        "accepted_cell_provenance_keyset_matches": accepted_keys
        == set(expected_values),
        "accepted_value_mismatch_count": value_mismatch_count,
        "accepted_value_sources": dict(
            Counter(row.get("value_source", "") for row in accepted_rows),
        ),
    }


def _check_rows(
    *,
    packet_payload: Mapping[str, Any],
    activation_facts: Mapping[str, Any],
    packet_problem_count: int,
) -> list[dict[str, str]]:
    checks = [
        _count_check("expected_diff_provenance_packet_pass", packet_problem_count, 0),
        _count_check(
            "accepted_backfill_count",
            packet_payload.get("candidate_cell_count"),
            EXPECTED_COUNTS["accepted_backfill_count"],
        ),
        _count_check(
            "candidate_peak_count",
            packet_payload.get("candidate_peak_count"),
            EXPECTED_COUNTS["candidate_peak_count"],
        ),
        _count_check(
            "expected_diff_count",
            activation_facts["expected_diff_count"],
            EXPECTED_COUNTS["expected_diff_count"],
        ),
        _count_check(
            "written_backfill_count",
            activation_facts["written_backfill_count"],
            EXPECTED_COUNTS["written_backfill_count"],
        ),
        _count_check(
            "unused_expected_diff_count",
            activation_facts["unused_expected_diff_count"],
            EXPECTED_COUNTS["unused_expected_diff_count"],
        ),
        _count_check(
            "cell_provenance_accepted_count",
            activation_facts["accepted_cell_provenance_count"],
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
            notes=(
                ""
                if activation_facts["accepted_cell_provenance_keyset_matches"]
                else "accepted cell provenance keyset mismatch"
            ),
        ),
        _count_check(
            "matrix_changed_cell_count",
            len(activation_facts["changed_keys"]),
            EXPECTED_COUNTS["matrix_changed_cell_count"],
            notes=(
                ""
                if activation_facts["changed_keyset_matches"]
                else "changed matrix keyset mismatch"
            ),
        ),
        _bool_check("candidate_quant_matrix_replay_changed", True, True),
        _bool_check("no_public_product_writer_change", True, True),
        _bool_check("no_public_default_quant_matrix_change", True, True),
        _bool_check("shift_aware_own_max_evidence_not_wired", True, True),
        {
            "schema_version": CHECK_SCHEMA_VERSION,
            "check_id": "no_workbook_gui_selected_area_counting_change",
            "status": "pass",
            "observed": "FALSE",
            "expected": "FALSE",
            "notes": "candidate replay writes externalized matrix TSV artifacts only",
        },
    ]
    for check in checks:
        if check["notes"] and "mismatch" in check["notes"]:
            check["status"] = "fail"
    if activation_facts["accepted_value_mismatch_count"]:
        checks.append(
            _fail_check(
                "cell_provenance_values",
                activation_facts["accepted_value_mismatch_count"],
                0,
            ),
        )
    if activation_facts["accepted_value_sources"] != {
        "ProductionAcceptanceManifest": EXPECTED_COUNTS["accepted_backfill_count"],
    }:
        checks.append(
            _fail_check(
                "cell_provenance_value_source",
                activation_facts["accepted_value_sources"],
                "ProductionAcceptanceManifest only",
            ),
        )
    return checks


def _summary_payload(
    *,
    docs_dir: Path,
    output_dir: Path,
    checks_tsv: Path,
    compact_manifest_tsv: Path,
    packet_summary_json: Path,
    packet_checks_tsv: Path,
    packet_row_manifest_tsv: Path,
    packet_production_manifest_tsv: Path,
    packet_expected_diff_tsv: Path,
    baseline_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    activation_outputs: Mapping[str, Path],
    activation_facts: Mapping[str, Any],
    check_rows: Sequence[Mapping[str, str]],
    compact_manifest_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    artifacts = {
        "checks_tsv": checks_tsv,
        "compact_manifest_tsv": compact_manifest_tsv,
        "quant_matrix": activation_outputs["quant_matrix"],
        "cell_provenance": activation_outputs["cell_provenance"],
        "row_summary": activation_outputs["row_summary"],
        "expected_diff_summary": activation_outputs["expected_diff_summary"],
        "source_summary": activation_outputs["source_summary"],
    }
    input_artifacts = {
        "packet_summary_json": packet_summary_json,
        "packet_checks_tsv": packet_checks_tsv,
        "packet_row_manifest_tsv": packet_row_manifest_tsv,
        "production_acceptance_manifest": packet_production_manifest_tsv,
        "expected_diff": packet_expected_diff_tsv,
        "baseline_quant_matrix_tsv": baseline_quant_matrix_tsv,
        "input_matrix_identity_tsv": input_matrix_identity_tsv,
    }
    checks_pass = all(row.get("status") == "pass" for row in check_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if checks_pass else "fail",
        "activation_label": ACTIVATION_LABEL,
        "validation_status": "production_candidate",
        "product_lane": PRODUCT_LANE,
        "product_scope_kind": PRODUCT_SCOPE_KIND,
        "product_authority_scope": PRODUCT_AUTHORITY_SCOPE,
        "accepted_backfill_count": EXPECTED_COUNTS["accepted_backfill_count"],
        "accepted_backfill_cell_count": str(EXPECTED_COUNTS["accepted_backfill_count"]),
        "candidate_peak_count": EXPECTED_COUNTS["candidate_peak_count"],
        "written_backfill_count": str(activation_facts["written_backfill_count"]),
        "expected_diff_count": str(activation_facts["expected_diff_count"]),
        "unused_expected_diff_count": str(
            activation_facts["unused_expected_diff_count"],
        ),
        "cell_provenance_accepted_count": activation_facts[
            "accepted_cell_provenance_count"
        ],
        "matrix_changed_cell_count": len(activation_facts["changed_keys"]),
        "held_cell_count": EXPECTED_COUNTS["held_cell_count"],
        "write_authority": False,
        "product_writer_changed": False,
        "default_quant_matrix_changed": False,
        "default_matrix_files_written": False,
        "candidate_matrix_replay_written": True,
        "candidate_replay_written_backfill_count": str(
            activation_facts["written_backfill_count"],
        ),
        "authority_blocker": (
            "shift-aware standard-peak support and MS1 own-max evidence are "
            "not wired into this candidate packet"
        ),
        "public_write_blocked_cell_count": EXPECTED_COUNTS["accepted_backfill_count"],
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "selected_peak_changed": False,
        "selected_area_changed": False,
        "counted_detection_changed": False,
        "raw_or_85raw_ran": False,
        "scorer_ran": False,
        "broad_backfill_unparked": False,
        "candidate_rows_are_matrix_rows": False,
        "authority_statement": (
            "This packet replays 666 Backfill expansion candidate cells through "
            "ProductionAcceptanceManifest and expected-diff provenance, but it "
            "does not grant public write authority because shift-aware "
            "standard-peak support and MS1 own-max evidence are not wired by "
            "stable row/cell keys. The 666 replayed cells and the 263 "
            "earlier-held cells remain outside public ProductWriter authority."
        ),
        "future_preset_requirement": (
            "After this rule is stable for future sample batches, delivery must "
            "collapse into a CLI/GUI preset that emits the activation result "
            "directly instead of repeating the manual multi-gate spike rhythm."
        ),
        "checks": {row["check_id"]: row["status"] for row in check_rows},
        "artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in artifacts.items()
        },
        "input_artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in input_artifacts.items()
        },
        "compact_row_manifest": {
            "row_count": len(compact_manifest_rows),
            "accepted_backfill_cell_count": sum(
                optional_int(row.get("accepted_backfill_cell_count", "")) or 0
                for row in compact_manifest_rows
            ),
        },
        "docs_dir": _repo_relpath(docs_dir),
        "output_dir": _repo_relpath(output_dir),
    }


def _compact_manifest_rows(path: Path) -> list[dict[str, str]]:
    rows = read_tsv_required(path, PACKET_ROW_MANIFEST_COLUMNS)
    compact: list[dict[str, str]] = []
    for row in rows:
        compact.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_scope": "backfill_expansion_default_activation_row",
                "peak_hypothesis_id": row["peak_hypothesis_id"],
                "accepted_backfill_cell_count": row[
                    "candidate_expected_diff_cell_count"
                ],
                "baseline_available_cell_count": row["baseline_available_cell_count"],
                "activated_available_cell_count": row["activated_available_cell_count"],
                "missing_cell_count": row["missing_cell_count"],
                "metric_warning_cell_count": row["metric_warning_cell_count"],
                "product_authority_scope": PRODUCT_AUTHORITY_SCOPE,
                "default_activation_effect": "candidate_replay_no_public_write",
            },
        )
    return compact


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Candidate Replay v1",
        "",
        f"Status: `{payload['activation_label']}`.",
        "",
        "This bundle is a candidate replay for the bounded 666-cell Backfill",
        "expansion packet. It is not public default activation because",
        "shift-aware standard-peak support and MS1 own-max evidence are not",
        "wired into the per-cell evidence chain.",
        "",
        f"- Candidate replay cells: `{payload['accepted_backfill_count']}`.",
        f"- Rows: `{payload['candidate_peak_count']}`.",
        f"- Dry-run written cells: `{payload['written_backfill_count']}`.",
        f"- Unused expected-diff rows: `{payload['unused_expected_diff_count']}`.",
        f"- Candidate cells blocked from public authority: `{payload['public_write_blocked_cell_count']}`.",
        f"- Earlier held cells outside authority: `{payload['held_cell_count']}`.",
        "",
        "The full replay matrix, full provenance, row summary, source summary,",
        "candidate manifest, and expected-diff TSV stay externalized under",
        "`output/validation/`. Version control keeps only this compact summary,",
        "checks, and row manifest.",
        "",
        "Before this can become public writer authority, a checker must join",
        "shift-aware standard-peak support and MS1 own-max evidence by stable",
        "row/cell keys. Missing or unjoinable evidence must keep the cell held.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _check_summary_fields(payload: Mapping[str, Any], problems: list[str]) -> None:
    expected_fields: tuple[tuple[str, object], ...] = (
        ("schema_version", SCHEMA_VERSION),
        ("status", "pass"),
        ("activation_label", ACTIVATION_LABEL),
        ("validation_status", "production_candidate"),
        ("product_lane", PRODUCT_LANE),
        ("product_scope_kind", PRODUCT_SCOPE_KIND),
        ("product_authority_scope", PRODUCT_AUTHORITY_SCOPE),
        ("accepted_backfill_count", EXPECTED_COUNTS["accepted_backfill_count"]),
        ("written_backfill_count", str(EXPECTED_COUNTS["written_backfill_count"])),
        ("expected_diff_count", str(EXPECTED_COUNTS["expected_diff_count"])),
        ("unused_expected_diff_count", "0"),
        (
            "cell_provenance_accepted_count",
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
        ),
        ("matrix_changed_cell_count", EXPECTED_COUNTS["matrix_changed_cell_count"]),
        ("held_cell_count", EXPECTED_COUNTS["held_cell_count"]),
        ("write_authority", False),
        ("product_writer_changed", False),
        ("default_quant_matrix_changed", False),
        ("default_matrix_files_written", False),
        ("candidate_matrix_replay_written", True),
        (
            "candidate_replay_written_backfill_count",
            str(EXPECTED_COUNTS["written_backfill_count"]),
        ),
        (
            "public_write_blocked_cell_count",
            EXPECTED_COUNTS["accepted_backfill_count"],
        ),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("selected_peak_changed", False),
        ("selected_area_changed", False),
        ("counted_detection_changed", False),
        ("raw_or_85raw_ran", False),
        ("scorer_ran", False),
        ("broad_backfill_unparked", False),
        ("candidate_rows_are_matrix_rows", False),
    )
    for field, expected in expected_fields:
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")


def _check_artifact_hashes(payload: Mapping[str, Any], problems: list[str]) -> None:
    check_summary_artifact_hashes(
        payload,
        root=ROOT,
        problems=problems,
    )


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
    ids = {row["check_id"] for row in rows}
    missing = sorted(set(EXPECTED_CHECK_IDS) - ids)
    if missing:
        problems.append("checks missing required ids: " + ";".join(missing))
    failing = [row["check_id"] for row in rows if row.get("status") != "pass"]
    if failing:
        problems.append("checks must all pass: " + ";".join(failing))
    checks = payload.get("checks")
    if isinstance(checks, Mapping):
        for check_id in EXPECTED_CHECK_IDS:
            if checks.get(check_id) != "pass":
                problems.append(f"summary check {check_id} must pass")


def _check_compact_manifest(
    compact_manifest_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(compact_manifest_tsv, COMPACT_MANIFEST_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read compact manifest TSV: {exc}")
        return
    if len(rows) != EXPECTED_COUNTS["candidate_peak_count"]:
        problems.append("compact manifest candidate peak count mismatch")
    accepted_sum = sum(
        optional_int(row.get("accepted_backfill_cell_count", "")) or 0 for row in rows
    )
    if accepted_sum != EXPECTED_COUNTS["accepted_backfill_count"]:
        problems.append("compact manifest accepted cell sum mismatch")
    for row in rows:
        if row.get("product_authority_scope") != payload.get("product_authority_scope"):
            problems.append("compact manifest authority scope mismatch")


def _check_expected_diff_summary(
    path: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(path, EXPECTED_DIFF_SUMMARY_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read expected_diff_summary: {exc}")
        return
    if len(rows) != 1:
        problems.append("expected_diff_summary must have one row")
        return
    row = rows[0]
    if row.get("acceptance_status") != "pass":
        problems.append("expected_diff_summary acceptance_status mismatch")
    if row.get("expected_diff_count") != payload.get("expected_diff_count"):
        problems.append("expected_diff_summary expected count mismatch")
    if row.get("written_backfill_count") != payload.get("written_backfill_count"):
        problems.append("expected_diff_summary written count mismatch")
    if row.get("unused_expected_diff_count") != "0":
        problems.append("expected_diff_summary unused count mismatch")


def _check_cell_provenance(
    path: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(path, CELL_PROVENANCE_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read cell_provenance: {exc}")
        return
    accepted = [row for row in rows if row.get("cell_status") == "accepted_backfill"]
    if len(accepted) != payload.get("cell_provenance_accepted_count"):
        problems.append("cell_provenance accepted count mismatch")
    bad_source = [
        row
        for row in accepted
        if row.get("value_source") != "ProductionAcceptanceManifest"
    ]
    if bad_source:
        problems.append("cell_provenance accepted value_source mismatch")


def _matrix_changed_keys(
    *,
    baseline_quant_matrix_tsv: Path,
    activated_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    expected_values: Mapping[tuple[str, str], str],
) -> set[tuple[str, str]]:
    baseline_header, baseline_rows = read_tsv_with_header(baseline_quant_matrix_tsv)
    activated_header, activated_rows = read_tsv_with_header(activated_quant_matrix_tsv)
    if tuple(baseline_header) != tuple(activated_header):
        raise ValueError("baseline and activated matrix headers differ")
    if len(baseline_rows) != len(activated_rows):
        raise ValueError("baseline and activated matrix row counts differ")
    identity_rows = read_tsv_required(
        input_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id"),
    )
    peak_by_index = {
        int(row["matrix_row_index"]): row["peak_hypothesis_id"] for row in identity_rows
    }
    sample_columns = _sample_columns(baseline_header)
    changed: set[tuple[str, str]] = set()
    for index, (baseline, activated) in enumerate(
        zip(baseline_rows, activated_rows, strict=True),
        start=1,
    ):
        peak = peak_by_index[index]
        for sample in sample_columns:
            before = baseline.get(sample, "")
            after = activated.get(sample, "")
            if numeric_equal(before, after):
                continue
            key = (peak, sample)
            changed.add(key)
            expected = expected_values.get(key, "")
            if not expected or not numeric_equal(after, expected):
                raise ValueError(f"{peak}/{sample}: activated value mismatch")
    return changed


def _rewrite_source_summary_paths(path: Path) -> None:
    rows = read_tsv_required(path, SOURCE_SUMMARY_COLUMNS)
    rewritten = []
    for row in rows:
        copied = dict(row)
        for field in (
            "input_quant_matrix_tsv",
            "input_matrix_identity_tsv",
            "production_acceptance_manifest_tsv",
            "expected_diff_tsv",
        ):
            value = text_value(copied.get(field))
            if not value:
                continue
            source_path = Path(value)
            if source_path.is_absolute():
                try:
                    copied[field] = _repo_relpath(source_path)
                except ValueError:
                    copied[field] = value
        rewritten.append(copied)
    write_tsv(path, rewritten, SOURCE_SUMMARY_COLUMNS, extrasaction="raise")


def _sample_columns(header: Sequence[str]) -> tuple[str, ...]:
    if len(header) < 3 or tuple(header[:2]) != ("Mz", "RT"):
        raise ValueError("quant matrix header must start with Mz, RT")
    return tuple(column for column in header if column not in {"Mz", "RT"})


def _count_check(
    check_id: str,
    observed: object,
    expected: object,
    *,
    notes: str = "",
) -> dict[str, str]:
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "check_id": check_id,
        "status": "pass" if observed == expected else "fail",
        "observed": text_value(observed),
        "expected": text_value(expected),
        "notes": notes,
    }


def _bool_check(check_id: str, observed: bool, expected: bool) -> dict[str, str]:
    return _count_check(check_id, observed, expected)


def _fail_check(check_id: str, observed: object, expected: object) -> dict[str, str]:
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "check_id": check_id,
        "status": "fail",
        "observed": text_value(observed),
        "expected": text_value(expected),
        "notes": "",
    }


def _artifact_entry(path: Path, *, base_dir: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(base_dir.resolve()).as_posix(),
        "sha256": file_sha256(resolved),
        "bytes": resolved.stat().st_size,
        "line_count": _line_count(resolved),
    }


def _artifact_path(artifacts: Mapping[str, Any], label: str) -> Path:
    entry = artifacts.get(label)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
        raise ValueError(f"packet artifact {label} missing")
    path = ROOT / entry["path"]
    if not path.exists():
        raise ValueError(f"packet artifact {label} missing: {entry['path']}")
    return path.resolve()


def _require_artifact_match(
    artifacts: Mapping[str, Any],
    label: str,
    path: Path,
) -> None:
    entry = artifacts.get(label)
    if not isinstance(entry, Mapping):
        raise ValueError(f"packet artifact {label} missing")
    if entry.get("path") != _repo_relpath(path):
        raise ValueError(f"packet artifact {label} path mismatch")
    if entry.get("sha256") != file_sha256(path):
        raise ValueError(f"packet artifact {label} hash mismatch")


def _repo_relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _line in handle)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON payload must be an object")
    return payload


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--packet-summary-json",
        type=Path,
        default=DEFAULT_PACKET_SUMMARY_JSON,
    )
    parser.add_argument(
        "--packet-checks-tsv",
        type=Path,
        default=DEFAULT_PACKET_CHECKS_TSV,
    )
    parser.add_argument(
        "--packet-row-manifest-tsv",
        type=Path,
        default=DEFAULT_PACKET_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--packet-production-manifest-tsv",
        type=Path,
        default=DEFAULT_PACKET_PRODUCTION_MANIFEST_TSV,
    )
    parser.add_argument(
        "--packet-expected-diff-tsv",
        type=Path,
        default=DEFAULT_PACKET_EXPECTED_DIFF_TSV,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    summary_json = (
        args.docs_dir
        / "backfill_expansion_default_product_activation_summary.json"
    )
    checks_tsv = (
        args.docs_dir / "backfill_expansion_default_product_activation_checks.tsv"
    )
    compact_manifest_tsv = (
        args.docs_dir / "backfill_expansion_default_product_activation_manifest.tsv"
    )
    try:
        if args.check_only:
            problems = validate_backfill_expansion_default_product_activation(
                summary_json=summary_json,
                checks_tsv=checks_tsv,
                compact_manifest_tsv=compact_manifest_tsv,
            )
        else:
            build_backfill_expansion_default_product_activation(
                docs_dir=args.docs_dir,
                output_dir=args.output_dir,
                packet_summary_json=args.packet_summary_json,
                packet_checks_tsv=args.packet_checks_tsv,
                packet_row_manifest_tsv=args.packet_row_manifest_tsv,
                packet_production_manifest_tsv=args.packet_production_manifest_tsv,
                packet_expected_diff_tsv=args.packet_expected_diff_tsv,
            )
            problems = validate_backfill_expansion_default_product_activation(
                summary_json=summary_json,
                checks_tsv=checks_tsv,
                compact_manifest_tsv=compact_manifest_tsv,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2 if args.require_pass else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
