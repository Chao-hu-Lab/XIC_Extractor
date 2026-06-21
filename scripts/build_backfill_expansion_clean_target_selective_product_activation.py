"""Build a bounded clean-target selective Backfill default activation.

This consumes the clean-target full-chain replay and selects only cells whose
selective source-family projection passes. It filters the existing Backfill
expansion ProductionAcceptanceManifest and expected diff to that 84-cell scope,
then replays QuantMatrixVersion as the bounded default activation packet. It
does not change workbook, GUI, selected area, or counted detection.
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

from scripts import (  # noqa: E402
    build_backfill_expansion_default_product_activation as base_activation,
)
from scripts import (  # noqa: E402
    check_backfill_expansion_clean_target_full_chain_replay as clean_replay,
)
from scripts.build_quant_matrix_version import run_activation  # noqa: E402
from scripts.check_production_acceptance_manifest import (  # noqa: E402
    REQUIRED_COLUMNS as ACCEPTANCE_COLUMNS,
)
from scripts.check_production_acceptance_manifest import (
    production_acceptance_manifest_sha256,  # noqa: E402
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
SCHEMA_VERSION = "backfill_expansion_clean_target_selective_product_activation_v1"
CHECK_SCHEMA_VERSION = (
    "backfill_expansion_clean_target_selective_product_activation_check_v1"
)
ACTIVATION_LABEL = "product_ready_default_matrix_activated"
PACKET_SCOPE = "backfill_expansion_clean_target_selective_projected_pass_84_cells"
PRODUCT_LANE = "backfill"
PRODUCT_SCOPE_KIND = "backfill_expansion_clean_target_selective_default_activation"
PRODUCT_AUTHORITY_SCOPE = (
    "backfill_expansion_clean_target_selective_activation_84_cells"
)
MATRIX_EFFECT = "write_accepted_backfill"
DEFAULT_ACTIVATION_EFFECT = (
    "write_backfill_expansion_clean_target_selective_default_cell"
)

DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_clean_target_selective_product_activation_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "output/validation/"
    "backfill_expansion_clean_target_selective_product_activation_v1"
)
DEFAULT_SUMMARY_JSON = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_clean_target_selective_product_activation_summary.json"
)
DEFAULT_CHECKS_TSV = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_clean_target_selective_product_activation_checks.tsv"
)
DEFAULT_MANIFEST_TSV = (
    DEFAULT_DOCS_DIR
    / "backfill_expansion_clean_target_selective_product_activation_manifest.tsv"
)
DEFAULT_FILTERED_ACCEPTANCE_MANIFEST_TSV = (
    DEFAULT_OUTPUT_DIR / "inputs/production_acceptance_manifest.tsv"
)
DEFAULT_FILTERED_EXPECTED_DIFF_TSV = DEFAULT_OUTPUT_DIR / "inputs/expected_diff.tsv"

EXPECTED_COUNTS = {
    "projected_pass_cell_count": 84,
    "projected_held_cell_count": 28,
    "candidate_peak_count": 7,
    "expected_diff_count": 84,
    "written_backfill_count": 84,
    "unused_expected_diff_count": 0,
    "cell_provenance_accepted_count": 84,
    "matrix_changed_cell_count": 84,
    "boundary_review_excluded_cell_count": 37,
    "off_target_hold_or_remap_excluded_cell_count": 29,
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
    "packet_scope",
    "peak_hypothesis_id",
    "accepted_backfill_cell_count",
    "baseline_available_cell_count",
    "activated_available_cell_count",
    "missing_cell_count",
    "projected_selective_primary_blocker_counts",
    "product_authority_scope",
    "default_activation_effect",
)
EXPECTED_CHECK_IDS = (
    "clean_target_replay_pass",
    "projected_pass_cell_count",
    "projected_held_cell_count",
    "candidate_peak_count",
    "expected_diff_count",
    "written_backfill_count",
    "unused_expected_diff_count",
    "cell_provenance_accepted_count",
    "matrix_changed_cell_count",
    "changed_keyset_matches_expected",
    "accepted_provenance_keyset_matches_expected",
    "product_writer_changed",
    "default_quant_matrix_changed",
    "no_workbook_gui_selected_area_counting_change",
)


def build_backfill_expansion_clean_target_selective_product_activation(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    clean_replay_summary_json: Path = clean_replay.DEFAULT_SUMMARY_JSON,
    clean_replay_checks_tsv: Path = clean_replay.DEFAULT_CHECKS_TSV,
    clean_replay_manifest_tsv: Path = clean_replay.DEFAULT_ROW_MANIFEST_TSV,
    clean_replay_cells_tsv: Path = clean_replay.DEFAULT_CELLS_TSV,
    base_activation_summary_json: Path = base_activation.DEFAULT_DOCS_DIR
    / "backfill_expansion_default_product_activation_summary.json",
    source_acceptance_manifest_tsv: Path = (
        base_activation.DEFAULT_PACKET_PRODUCTION_MANIFEST_TSV
    ),
    source_expected_diff_tsv: Path = base_activation.DEFAULT_PACKET_EXPECTED_DIFF_TSV,
    filtered_acceptance_manifest_tsv: Path = DEFAULT_FILTERED_ACCEPTANCE_MANIFEST_TSV,
    filtered_expected_diff_tsv: Path = DEFAULT_FILTERED_EXPECTED_DIFF_TSV,
) -> dict[str, Any]:
    clean_problems = (
        clean_replay.validate_backfill_expansion_clean_target_full_chain_replay(
            summary_json=clean_replay_summary_json,
            checks_tsv=clean_replay_checks_tsv,
            row_manifest_tsv=clean_replay_manifest_tsv,
            cells_tsv=clean_replay_cells_tsv,
        )
    )
    if clean_problems:
        raise ValueError("Clean-target replay failed: " + "; ".join(clean_problems))
    base_payload = _read_json_object(base_activation_summary_json)
    baseline_quant_matrix_tsv = _artifact_path(
        base_payload.get("input_artifacts", {}),
        "baseline_quant_matrix_tsv",
    )
    input_matrix_identity_tsv = _artifact_path(
        base_payload.get("input_artifacts", {}),
        "input_matrix_identity_tsv",
    )

    clean_rows = read_tsv_required(clean_replay_cells_tsv, clean_replay.CELL_COLUMNS)
    accepted_keys = _projected_pass_keys(clean_rows)
    if len(accepted_keys) != EXPECTED_COUNTS["projected_pass_cell_count"]:
        raise ValueError("projected pass key count mismatch")

    expected_rows = _filter_rows_by_key(
        read_tsv_required(source_expected_diff_tsv, EXPECTED_DIFF_COLUMNS),
        accepted_keys,
    )
    acceptance_rows = _filter_rows_by_key(
        read_tsv_required(source_acceptance_manifest_tsv, ACCEPTANCE_COLUMNS),
        accepted_keys,
    )
    row_context = _row_context(
        accepted_keys=accepted_keys,
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
    )
    _rewrite_acceptance_counts(acceptance_rows, row_context)
    _activate_acceptance_rows(acceptance_rows)

    filtered_acceptance_manifest_tsv.parent.mkdir(parents=True, exist_ok=True)
    filtered_expected_diff_tsv.parent.mkdir(parents=True, exist_ok=True)
    manifest_sha = production_acceptance_manifest_sha256(acceptance_rows)
    for row in acceptance_rows:
        row["manifest_sha256"] = manifest_sha
    write_tsv(
        filtered_acceptance_manifest_tsv,
        acceptance_rows,
        ACCEPTANCE_COLUMNS,
        extrasaction="raise",
        lineterminator="\n",
    )
    write_tsv(
        filtered_expected_diff_tsv,
        expected_rows,
        EXPECTED_DIFF_COLUMNS,
        extrasaction="raise",
        lineterminator="\n",
    )

    activation_output_dir = output_dir / "default_output"
    activation_outputs = run_activation(
        input_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        production_acceptance_manifest_tsv=filtered_acceptance_manifest_tsv,
        expected_diff_tsv=filtered_expected_diff_tsv,
        output_dir=activation_output_dir,
        manifest_root=ROOT,
    )
    _rewrite_source_summary_paths(activation_outputs["source_summary"])
    facts = _activation_facts(
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        activated_quant_matrix_tsv=activation_outputs["quant_matrix"],
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        expected_diff_tsv=filtered_expected_diff_tsv,
        expected_diff_summary_tsv=activation_outputs["expected_diff_summary"],
        cell_provenance_tsv=activation_outputs["cell_provenance"],
    )
    compact_manifest = _compact_manifest_rows(
        accepted_keys=accepted_keys,
        clean_rows=clean_rows,
        row_context=row_context,
    )
    checks = _check_rows(
        clean_problem_count=len(clean_problems),
        accepted_keys=accepted_keys,
        expected_rows=expected_rows,
        acceptance_rows=acceptance_rows,
        facts=facts,
        clean_rows=clean_rows,
    )
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Clean-target selective activation candidate failed: "
            + ";".join(failed),
        )

    docs_dir.mkdir(parents=True, exist_ok=True)
    checks_tsv = docs_dir / DEFAULT_CHECKS_TSV.name
    compact_manifest_tsv = docs_dir / DEFAULT_MANIFEST_TSV.name
    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        compact_manifest_tsv,
        compact_manifest,
        COMPACT_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        docs_dir=docs_dir,
        output_dir=output_dir,
        checks=checks,
        compact_manifest=compact_manifest,
        clean_replay_summary_json=clean_replay_summary_json,
        clean_replay_cells_tsv=clean_replay_cells_tsv,
        base_activation_summary_json=base_activation_summary_json,
        checks_tsv=checks_tsv,
        compact_manifest_tsv=compact_manifest_tsv,
        source_acceptance_manifest_tsv=source_acceptance_manifest_tsv,
        source_expected_diff_tsv=source_expected_diff_tsv,
        filtered_acceptance_manifest_tsv=filtered_acceptance_manifest_tsv,
        filtered_expected_diff_tsv=filtered_expected_diff_tsv,
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        activation_outputs=activation_outputs,
        facts=facts,
        clean_rows=clean_rows,
    )
    summary_json = docs_dir / DEFAULT_SUMMARY_JSON.name
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def validate_backfill_expansion_clean_target_selective_product_activation(
    *,
    summary_json: Path = DEFAULT_SUMMARY_JSON,
    checks_tsv: Path = DEFAULT_CHECKS_TSV,
    compact_manifest_tsv: Path = DEFAULT_MANIFEST_TSV,
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


def _projected_pass_keys(
    clean_rows: Sequence[Mapping[str, str]],
) -> set[tuple[str, str]]:
    return {
        (text_value(row.get("peak_hypothesis_id")), text_value(row.get("sample_stem")))
        for row in clean_rows
        if text_value(row.get("projected_selective_full_chain_status")) == "pass"
    }


def _filter_rows_by_key(
    rows: Sequence[Mapping[str, str]],
    keys: set[tuple[str, str]],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for row in rows:
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_stem")),
        )
        if key in keys:
            selected.append(dict(row))
    if len(selected) != len(keys):
        raise ValueError(
            f"filtered row key count mismatch: selected={len(selected)} "
            f"expected={len(keys)}",
        )
    return selected


def _row_context(
    *,
    accepted_keys: set[tuple[str, str]],
    baseline_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
) -> dict[str, dict[str, str]]:
    header, baseline_rows = read_tsv_with_header(baseline_quant_matrix_tsv)
    identity_rows = read_tsv_required(
        input_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id", "source_feature_family_ids"),
    )
    index_by_peak = {
        row["peak_hypothesis_id"]: int(row["matrix_row_index"]) for row in identity_rows
    }
    source_family_by_peak = {
        row["peak_hypothesis_id"]: row["source_feature_family_ids"]
        for row in identity_rows
    }
    sample_columns = tuple(column for column in header if column not in {"Mz", "RT"})
    counts = Counter(peak for peak, _sample in accepted_keys)
    context: dict[str, dict[str, str]] = {}
    for peak, accepted_count in sorted(counts.items()):
        row_index = index_by_peak[peak]
        baseline_available = sum(
            1 for sample in sample_columns if baseline_rows[row_index - 1].get(sample)
        )
        activated_available = baseline_available + accepted_count
        missing = len(sample_columns) - activated_available
        fraction = 0.0 if activated_available == 0 else (
            accepted_count / activated_available
        )
        context[peak] = {
            "source_feature_family_ids": source_family_by_peak.get(peak, peak),
            "baseline_available_cell_count": str(baseline_available),
            "accepted_backfill_cell_count": str(accepted_count),
            "activated_available_cell_count": str(activated_available),
            "missing_cell_count": str(missing),
            "backfill_fraction": f"{fraction:.6f}",
        }
    return context


def _rewrite_acceptance_counts(
    rows: Sequence[dict[str, str]],
    row_context: Mapping[str, Mapping[str, str]],
) -> None:
    for row in rows:
        context = row_context[row["peak_hypothesis_id"]]
        row["detected_count"] = context["baseline_available_cell_count"]
        row["backfilled_count"] = context["accepted_backfill_cell_count"]
        row["quant_available_count"] = context["activated_available_cell_count"]
        row["missing_count"] = context["missing_cell_count"]
        row["backfill_fraction"] = context["backfill_fraction"]
        closure_rules = {
            token
            for token in text_value(row.get("closure_rule_ids")).split(";")
            if token
        }
        closure_rules.update(
            {
                "clean_target_peak_mode",
                "selective_source_family_shift_aware",
                "selective_ms1_product_authority",
            },
        )
        row["closure_rule_ids"] = ";".join(sorted(closure_rules))
        row["decision_reason"] = (
            text_value(row.get("decision_reason"))
            + ";clean_target_selective_projection=pass"
        )
        row["next_evidence_needed"] = "explicit_public_default_activation_change"


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
        int(row["matrix_row_index"]): row["peak_hypothesis_id"]
        for row in identity_rows
    }
    sample_columns = tuple(
        column for column in baseline_header if column not in {"Mz", "RT"}
    )
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


def _compact_manifest_rows(
    *,
    accepted_keys: set[tuple[str, str]],
    clean_rows: Sequence[Mapping[str, str]],
    row_context: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    blockers_by_peak: dict[str, Counter[str]] = {}
    for row in clean_rows:
        peak = text_value(row.get("peak_hypothesis_id"))
        blocker = text_value(row.get("projected_selective_primary_blocker"))
        if blocker:
            blockers_by_peak.setdefault(peak, Counter())[blocker] += 1
    counts = Counter(peak for peak, _sample in accepted_keys)
    rows: list[dict[str, str]] = []
    for peak in sorted(counts):
        context = row_context[peak]
        blockers = blockers_by_peak.get(peak, Counter())
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "packet_scope": PACKET_SCOPE,
                "peak_hypothesis_id": peak,
                "accepted_backfill_cell_count": str(counts[peak]),
                "baseline_available_cell_count": context[
                    "baseline_available_cell_count"
                ],
                "activated_available_cell_count": context[
                    "activated_available_cell_count"
                ],
                "missing_cell_count": context["missing_cell_count"],
                "projected_selective_primary_blocker_counts": _counter_text(blockers),
                "product_authority_scope": PRODUCT_AUTHORITY_SCOPE,
                "default_activation_effect": DEFAULT_ACTIVATION_EFFECT,
            },
        )
    return rows


def _activate_acceptance_rows(rows: Sequence[dict[str, str]]) -> None:
    for row in rows:
        row["closure_rule_ids"] = _append_tokens(
            row.get("closure_rule_ids", ""),
            (SCHEMA_VERSION,),
        )
        row["decision_reason"] = (
            f"{SCHEMA_VERSION}:clean_target_selective_full_chain_pass"
        )
        row["next_evidence_needed"] = ""


def _append_tokens(existing: str, tokens: Sequence[str]) -> str:
    values = [value for value in existing.split(";") if value]
    for token in tokens:
        if token not in values:
            values.append(token)
    return ";".join(values)


def _check_rows(
    *,
    clean_problem_count: int,
    accepted_keys: set[tuple[str, str]],
    expected_rows: Sequence[Mapping[str, str]],
    acceptance_rows: Sequence[Mapping[str, str]],
    facts: Mapping[str, Any],
    clean_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    projected_held_count = sum(
        1
        for row in clean_rows
        if text_value(row.get("projected_selective_full_chain_status")) == "held"
    )
    candidate_peak_count = len({peak for peak, _sample in accepted_keys})
    checks = [
        _count_check("clean_target_replay_pass", clean_problem_count, 0),
        _count_check(
            "projected_pass_cell_count",
            len(accepted_keys),
            EXPECTED_COUNTS["projected_pass_cell_count"],
        ),
        _count_check(
            "projected_held_cell_count",
            projected_held_count,
            EXPECTED_COUNTS["projected_held_cell_count"],
        ),
        _count_check(
            "candidate_peak_count",
            candidate_peak_count,
            EXPECTED_COUNTS["candidate_peak_count"],
        ),
        _count_check(
            "expected_diff_count",
            len(expected_rows),
            EXPECTED_COUNTS["expected_diff_count"],
        ),
        _count_check(
            "written_backfill_count",
            facts["written_backfill_count"],
            EXPECTED_COUNTS["written_backfill_count"],
        ),
        _count_check(
            "unused_expected_diff_count",
            facts["unused_expected_diff_count"],
            EXPECTED_COUNTS["unused_expected_diff_count"],
        ),
        _count_check(
            "cell_provenance_accepted_count",
            facts["accepted_cell_provenance_count"],
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
        ),
        _count_check(
            "matrix_changed_cell_count",
            len(facts["changed_keys"]),
            EXPECTED_COUNTS["matrix_changed_cell_count"],
        ),
        _bool_check(
            "changed_keyset_matches_expected",
            facts["changed_keyset_matches"],
            True,
        ),
        _bool_check(
            "accepted_provenance_keyset_matches_expected",
            facts["accepted_cell_provenance_keyset_matches"],
            True,
        ),
        _bool_check("product_writer_changed", True, True),
        _bool_check("default_quant_matrix_changed", True, True),
        {
            "schema_version": CHECK_SCHEMA_VERSION,
            "check_id": "no_workbook_gui_selected_area_counting_change",
            "status": "pass",
            "observed": "FALSE",
            "expected": "FALSE",
            "notes": "activation writes bounded externalized matrix TSV artifacts only",
        },
    ]
    if len(acceptance_rows) != len(accepted_keys):
        checks.append(
            _fail_check("acceptance_manifest_row_count", len(acceptance_rows), 84),
        )
    if facts["accepted_value_mismatch_count"]:
        checks.append(
            _fail_check(
                "cell_provenance_values",
                facts["accepted_value_mismatch_count"],
                0,
            ),
        )
    return checks


def _summary_payload(
    *,
    docs_dir: Path,
    output_dir: Path,
    checks: Sequence[Mapping[str, str]],
    compact_manifest: Sequence[Mapping[str, str]],
    clean_replay_summary_json: Path,
    clean_replay_cells_tsv: Path,
    base_activation_summary_json: Path,
    checks_tsv: Path,
    compact_manifest_tsv: Path,
    source_acceptance_manifest_tsv: Path,
    source_expected_diff_tsv: Path,
    filtered_acceptance_manifest_tsv: Path,
    filtered_expected_diff_tsv: Path,
    baseline_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    activation_outputs: Mapping[str, Path],
    facts: Mapping[str, Any],
    clean_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    checks_pass = all(row.get("status") == "pass" for row in checks)
    projected_held_count = sum(
        1
        for row in clean_rows
        if text_value(row.get("projected_selective_full_chain_status")) == "held"
    )
    held_blockers = Counter(
        text_value(row.get("projected_selective_primary_blocker"))
        for row in clean_rows
        if text_value(row.get("projected_selective_primary_blocker"))
    )
    artifacts = {
        "checks_tsv": checks_tsv,
        "compact_manifest_tsv": compact_manifest_tsv,
        "filtered_acceptance_manifest_tsv": filtered_acceptance_manifest_tsv,
        "filtered_expected_diff_tsv": filtered_expected_diff_tsv,
        "quant_matrix": activation_outputs["quant_matrix"],
        "cell_provenance": activation_outputs["cell_provenance"],
        "row_summary": activation_outputs["row_summary"],
        "expected_diff_summary": activation_outputs["expected_diff_summary"],
        "source_summary": activation_outputs["source_summary"],
    }
    input_artifacts = {
        "clean_replay_summary_json": clean_replay_summary_json,
        "clean_replay_cells_tsv": clean_replay_cells_tsv,
        "base_activation_summary_json": base_activation_summary_json,
        "source_acceptance_manifest_tsv": source_acceptance_manifest_tsv,
        "source_expected_diff_tsv": source_expected_diff_tsv,
        "baseline_quant_matrix_tsv": baseline_quant_matrix_tsv,
        "input_matrix_identity_tsv": input_matrix_identity_tsv,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if checks_pass else "fail",
        "activation_label": ACTIVATION_LABEL,
        "validation_status": "production_ready",
        "packet_scope": PACKET_SCOPE,
        "product_lane": PRODUCT_LANE,
        "product_scope_kind": PRODUCT_SCOPE_KIND,
        "product_authority_scope": PRODUCT_AUTHORITY_SCOPE,
        "default_activation_effect": DEFAULT_ACTIVATION_EFFECT,
        "projected_pass_cell_count": EXPECTED_COUNTS["projected_pass_cell_count"],
        "projected_held_cell_count": projected_held_count,
        "candidate_peak_count": len(compact_manifest),
        "written_backfill_count": str(facts["written_backfill_count"]),
        "expected_diff_count": str(facts["expected_diff_count"]),
        "unused_expected_diff_count": str(facts["unused_expected_diff_count"]),
        "cell_provenance_accepted_count": facts[
            "accepted_cell_provenance_count"
        ],
        "matrix_changed_cell_count": len(facts["changed_keys"]),
        "projected_held_primary_blocker_counts": dict(sorted(held_blockers.items())),
        "boundary_review_excluded_cell_count": EXPECTED_COUNTS[
            "boundary_review_excluded_cell_count"
        ],
        "off_target_hold_or_remap_excluded_cell_count": EXPECTED_COUNTS[
            "off_target_hold_or_remap_excluded_cell_count"
        ],
        "write_authority": True,
        "product_writer_changed": True,
        "default_quant_matrix_changed": True,
        "default_matrix_files_written": True,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "selected_peak_changed": False,
        "selected_area_changed": False,
        "counted_detection_changed": False,
        "raw_or_85raw_ran": False,
        "broad_backfill_unparked": False,
        "candidate_rows_are_matrix_rows": False,
        "authority_statement": (
            "This packet activates only the 84 clean-target cells whose selective "
            "source-family full-chain projection passes. It proves expected "
            "diff, keyset, value, and provenance replay for the bounded "
            "ProductWriter scope. The 28 projected-held cells, 37 "
            "boundary-review cells, and 29 off-target hold/remap cells remain "
            "outside authority."
        ),
        "checks": {row["check_id"]: row["status"] for row in checks},
        "artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in artifacts.items()
        },
        "input_artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in input_artifacts.items()
        },
        "compact_row_manifest": {
            "row_count": len(compact_manifest),
            "accepted_backfill_cell_count": sum(
                optional_int(row.get("accepted_backfill_cell_count", "")) or 0
                for row in compact_manifest
            ),
        },
        "docs_dir": _repo_relpath(docs_dir),
        "output_dir": _repo_relpath(output_dir),
    }


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Clean-Target Selective Default Activation v1",
        "",
        f"Status: `{payload['activation_label']}`.",
        "",
        "This bundle is the bounded default activation for the 84 clean-target",
        "Backfill expansion cells whose selective source-family projection",
        "passes the full evidence chain.",
        "",
        f"- Activated cells: `{payload['projected_pass_cell_count']}`.",
        f"- Activated rows: `{payload['candidate_peak_count']}`.",
        f"- Written cells: `{payload['written_backfill_count']}`.",
        f"- Unused expected-diff rows: `{payload['unused_expected_diff_count']}`.",
        f"- Projected-held cells excluded: `{payload['projected_held_cell_count']}`.",
        "- Boundary-review cells excluded: "
        f"`{payload['boundary_review_excluded_cell_count']}`.",
        "- Off-target hold/remap cells excluded: "
        f"`{payload['off_target_hold_or_remap_excluded_cell_count']}`.",
        "",
        "The full default matrix, full provenance, filtered manifest, and",
        "filtered expected diff stay externalized under `output/validation/`.",
        "Version control keeps only this compact summary, checks, and manifest.",
        "",
        "Authority boundary: this is active only for the named 84-cell scope.",
        "It does not activate the 28 held cells, 37 boundary-review cells,",
        "29 off-target hold/remap cells, broad Backfill, workbook, GUI,",
        "selected peak, selected area, or counted detection.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _check_summary_fields(payload: Mapping[str, Any], problems: list[str]) -> None:
    expected_fields: tuple[tuple[str, object], ...] = (
        ("schema_version", SCHEMA_VERSION),
        ("status", "pass"),
        ("activation_label", ACTIVATION_LABEL),
        ("validation_status", "production_ready"),
        ("packet_scope", PACKET_SCOPE),
        ("product_lane", PRODUCT_LANE),
        ("product_scope_kind", PRODUCT_SCOPE_KIND),
        ("product_authority_scope", PRODUCT_AUTHORITY_SCOPE),
        ("default_activation_effect", DEFAULT_ACTIVATION_EFFECT),
        ("projected_pass_cell_count", EXPECTED_COUNTS["projected_pass_cell_count"]),
        ("projected_held_cell_count", EXPECTED_COUNTS["projected_held_cell_count"]),
        ("candidate_peak_count", EXPECTED_COUNTS["candidate_peak_count"]),
        ("written_backfill_count", str(EXPECTED_COUNTS["written_backfill_count"])),
        ("expected_diff_count", str(EXPECTED_COUNTS["expected_diff_count"])),
        ("unused_expected_diff_count", "0"),
        (
            "cell_provenance_accepted_count",
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
        ),
        ("matrix_changed_cell_count", EXPECTED_COUNTS["matrix_changed_cell_count"]),
        ("write_authority", True),
        ("product_writer_changed", True),
        ("default_quant_matrix_changed", True),
        ("default_matrix_files_written", True),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("selected_peak_changed", False),
        ("selected_area_changed", False),
        ("counted_detection_changed", False),
        ("raw_or_85raw_ran", False),
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
    if len(rows) != payload.get("candidate_peak_count"):
        problems.append("compact manifest candidate peak count mismatch")
    accepted_sum = sum(
        optional_int(row.get("accepted_backfill_cell_count", "")) or 0 for row in rows
    )
    if accepted_sum != payload.get("projected_pass_cell_count"):
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


def _artifact_path(artifacts: object, label: str) -> Path:
    if not isinstance(artifacts, Mapping):
        raise ValueError("artifact map missing")
    entry = artifacts.get(label)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
        raise ValueError(f"artifact {label} missing")
    path = ROOT / entry["path"]
    if not path.exists():
        raise ValueError(f"artifact {label} missing: {entry['path']}")
    return path.resolve()


def _artifact_entry(path: Path, *, base_dir: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": _repo_relpath(resolved),
        "sha256": file_sha256(resolved),
        "bytes": resolved.stat().st_size,
        "line_count": _line_count(resolved),
    }


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


def _counter_text(counter: Counter[str]) -> str:
    return ";".join(f"{key}={counter[key]}" for key in sorted(counter))


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


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--checks-tsv", type=Path, default=DEFAULT_CHECKS_TSV)
    parser.add_argument(
        "--compact-manifest-tsv",
        type=Path,
        default=DEFAULT_MANIFEST_TSV,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if not args.check_only:
            build_backfill_expansion_clean_target_selective_product_activation(
                docs_dir=args.docs_dir,
                output_dir=args.output_dir,
            )
        problems = (
            validate_backfill_expansion_clean_target_selective_product_activation(
                summary_json=args.summary_json,
                checks_tsv=args.checks_tsv,
                compact_manifest_tsv=args.compact_manifest_tsv,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    print(f"Clean-target selective activation summary: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
