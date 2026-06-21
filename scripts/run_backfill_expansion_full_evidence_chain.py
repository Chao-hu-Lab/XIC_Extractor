"""Run the Backfill expansion productization evidence chain.

This runner reconnects the existing Backfill expansion evidence providers into
one executable chain and then applies the bounded clean-target selective
activation packet. The final activation is limited to the current 84-cell
ProductWriter/default-matrix scope; it does not write workbook/GUI outputs or
change selected peak, area, or counted-detection state.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.build_backfill_expansion_default_product_activation as activation
import scripts.build_cid_nl_default_product_activation as cid_nl_activation
import scripts.check_backfill_expansion_census as census
import scripts.check_backfill_expansion_clean_target_full_chain_replay as clean_replay
import scripts.check_backfill_expansion_evidence_availability as availability
import scripts.check_backfill_expansion_expected_diff_provenance as expected_diff
import scripts.check_backfill_expansion_full_evidence_chain as full_chain
import scripts.check_backfill_expansion_peak_mode_decomposition as peak_mode
import scripts.check_backfill_expansion_raw_overlay_trace_identity as raw_trace
import scripts.check_backfill_expansion_sample_local_ms1_evidence as sample_local
import scripts.check_backfill_expansion_selective_shift_aware_gate as selective_shift
from scripts import (
    build_backfill_expansion_clean_target_selective_product_activation,
)
from tools.diagnostics import (
    family_ms1_alignment_experiment_batch,
    family_ms1_overlay_batch,
    shift_aware_backfill_calibration_pack,
    shift_aware_standard_peak_gate_calibration,
    standard_peak_ms1_authority_bundle,
)
from xic_extractor.tabular_io import read_tsv_required, text_value, write_tsv

clean_activation = build_backfill_expansion_clean_target_selective_product_activation
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_full_evidence_chain_runner_v1"
DEFAULT_RUNNER_SUMMARY_JSON = (
    full_chain.DEFAULT_OUTPUT_DIR
    / "backfill_expansion_full_evidence_chain_runner_summary.json"
)
DEFAULT_MIN_SHAPE_R = (
    shift_aware_backfill_calibration_pack.DEFAULT_STANDARD_PEAK_MIN_SHAPE_R
)

SHIFT_AWARE_CELL_EVIDENCE_ADAPTER_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "reason",
)
SAMPLE_LOCAL_ADAPTER_SOURCE_COLUMNS = (
    "peak_hypothesis_id",
    "sample_stem",
    "cell_evidence_reason",
)
RECONCILIATION_GROUP_COLUMNS = (
    "feature_family_id",
    "product_behavior_state",
    "evidence_authority_state",
    "reconciliation_class",
    "detected_cell_count",
    "rescued_cell_count",
    "top_support_component",
    "top_blocker",
    "missing_evidence",
)
OVERLAY_RECONCILIATION_SOURCE_COLUMNS = (
    "feature_family_id",
    "detected_count",
    "rescued_count",
)


@dataclass(frozen=True)
class BackfillExpansionPresetOutputs:
    summary_json: Path
    clean_target_activation_summary_json: Path
    product_authority_scope: str
    active_backfill_cell_count: object


def _scoped_dir(root: Path | None, default_dir: Path) -> Path:
    return default_dir if root is None else root / default_dir.name


def _named_path(directory: Path, default_path: Path) -> Path:
    return directory / default_path.name


def run_backfill_expansion_full_evidence_chain(
    *,
    raw_dir: Path | None = None,
    dll_dir: Path | None = None,
    reuse_existing_raw_overlay: bool = False,
    reuse_existing_shift_aware: bool = False,
    render_shift_aware_images: bool = False,
    min_shape_r: float = DEFAULT_MIN_SHAPE_R,
    require_full_chain: bool = False,
    summary_json: Path = DEFAULT_RUNNER_SUMMARY_JSON,
    docs_root: Path | None = None,
    output_root: Path | None = None,
    cid_nl_activation_summary_json: Path = (
        census.DEFAULT_CID_NL_ACTIVATION_SUMMARY_JSON
    ),
    cid_nl_universe_summary_json: Path = census.DEFAULT_CID_NL_UNIVERSE_SUMMARY_JSON,
    backfill_activation_summary_json: Path = (
        census.DEFAULT_BACKFILL_ACTIVATION_SUMMARY_JSON
    ),
    cid_nl_activation_manifest_tsv: Path = (
        census.DEFAULT_CID_NL_ACTIVATION_MANIFEST_TSV
    ),
    cid_nl_default_quant_matrix_tsv: Path = (
        census.DEFAULT_CID_NL_DEFAULT_QUANT_MATRIX_TSV
    ),
    cid_nl_default_row_summary_tsv: Path = (
        census.DEFAULT_CID_NL_DEFAULT_ROW_SUMMARY_TSV
    ),
    cid_nl_default_cell_provenance_tsv: Path = (
        census.DEFAULT_CID_NL_DEFAULT_CELL_PROVENANCE_TSV
    ),
    old_backfill_values_tsv: Path = census.DEFAULT_OLD_BACKFILL_VALUES_TSV,
    successor_decisions_tsv: Path = census.DEFAULT_SUCCESSOR_AUTHORITY_DECISIONS_TSV,
    alignment_backfill_cell_evidence_tsv: Path = (
        sample_local.DEFAULT_ALIGNMENT_BACKFILL_CELL_EVIDENCE_TSV
    ),
    alignment_review_tsv: Path = sample_local.DEFAULT_ALIGNMENT_REVIEW_TSV,
    input_matrix_identity_tsv: Path = (
        expected_diff.DEFAULT_ALIGNMENT_MATRIX_IDENTITY_TSV
    ),
    timing_recorder: Any | None = None,
) -> dict[str, Any]:
    """Run the existing 666-cell evidence chain end-to-end."""

    steps: list[dict[str, str]] = []

    census_docs = _scoped_dir(docs_root, census.DEFAULT_DOCS_DIR)
    census_output = _scoped_dir(output_root, census.DEFAULT_OUTPUT_DIR)
    availability_docs = _scoped_dir(docs_root, availability.DEFAULT_DOCS_DIR)
    availability_output = _scoped_dir(output_root, availability.DEFAULT_OUTPUT_DIR)
    sample_local_docs = _scoped_dir(docs_root, sample_local.DEFAULT_DOCS_DIR)
    sample_local_output = _scoped_dir(output_root, sample_local.DEFAULT_OUTPUT_DIR)
    raw_trace_docs = _scoped_dir(docs_root, raw_trace.DEFAULT_DOCS_DIR)
    raw_trace_output = _scoped_dir(output_root, raw_trace.DEFAULT_OUTPUT_DIR)
    expected_docs = _scoped_dir(docs_root, expected_diff.DEFAULT_DOCS_DIR)
    expected_output = _scoped_dir(output_root, expected_diff.DEFAULT_OUTPUT_DIR)
    activation_docs = _scoped_dir(docs_root, activation.DEFAULT_DOCS_DIR)
    activation_output = _scoped_dir(output_root, activation.DEFAULT_OUTPUT_DIR)
    full_docs = _scoped_dir(docs_root, full_chain.DEFAULT_DOCS_DIR)
    full_output = _scoped_dir(output_root, full_chain.DEFAULT_OUTPUT_DIR)
    peak_docs = _scoped_dir(docs_root, peak_mode.DEFAULT_DOCS_DIR)
    peak_output = _scoped_dir(output_root, peak_mode.DEFAULT_OUTPUT_DIR)
    selective_docs = _scoped_dir(docs_root, selective_shift.DEFAULT_DOCS_DIR)
    selective_output = _scoped_dir(output_root, selective_shift.DEFAULT_OUTPUT_DIR)
    clean_replay_docs = _scoped_dir(docs_root, clean_replay.DEFAULT_DOCS_DIR)
    clean_replay_output = _scoped_dir(output_root, clean_replay.DEFAULT_OUTPUT_DIR)
    clean_activation_docs = _scoped_dir(docs_root, clean_activation.DEFAULT_DOCS_DIR)
    clean_activation_output = _scoped_dir(
        output_root,
        clean_activation.DEFAULT_OUTPUT_DIR,
    )

    census_summary_json = census_docs / "backfill_expansion_census_summary.json"
    census_checks_tsv = census_docs / "backfill_expansion_census_checks.tsv"
    census_row_manifest_tsv = (
        census_docs / "backfill_expansion_census_row_manifest.tsv"
    )
    census_opportunity_cells_tsv = (
        census_output / "backfill_expansion_opportunity_cells.tsv"
    )
    availability_summary_json = (
        availability_docs / "backfill_expansion_evidence_availability_summary.json"
    )
    availability_checks_tsv = (
        availability_docs / "backfill_expansion_evidence_availability_checks.tsv"
    )
    availability_row_manifest_tsv = (
        availability_docs
        / "backfill_expansion_evidence_availability_row_manifest.tsv"
    )
    availability_cells_tsv = (
        availability_output / "backfill_expansion_evidence_availability_cells.tsv"
    )
    sample_local_summary_json = (
        sample_local_docs
        / "backfill_expansion_sample_local_ms1_evidence_summary.json"
    )
    sample_local_checks_tsv = (
        sample_local_docs / "backfill_expansion_sample_local_ms1_evidence_checks.tsv"
    )
    sample_local_row_manifest_tsv = (
        sample_local_docs
        / "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv"
    )
    sample_local_cells_tsv = (
        sample_local_output / "backfill_expansion_sample_local_ms1_evidence_cells.tsv"
    )
    overlay_queue_tsv = (
        sample_local_output / "backfill_expansion_sample_local_ms1_overlay_queue.tsv"
    )
    raw_overlay_dir = raw_trace_output / "family_ms1_overlay_batch"
    raw_overlay_summary_tsv = (
        raw_overlay_dir / "family_ms1_overlay_batch_summary.tsv"
    )
    raw_overlay_summary_json = (
        raw_overlay_dir / "family_ms1_overlay_batch_summary.json"
    )
    raw_trace_summary_json = (
        raw_trace_docs / "backfill_expansion_raw_overlay_trace_identity_summary.json"
    )
    raw_trace_checks_tsv = (
        raw_trace_docs / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
    )
    raw_trace_row_manifest_tsv = (
        raw_trace_docs
        / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
    )
    raw_trace_cells_tsv = (
        raw_trace_output / "backfill_expansion_raw_overlay_trace_identity_cells.tsv"
    )
    expected_summary_json = (
        expected_docs / "backfill_expansion_expected_diff_provenance_summary.json"
    )
    expected_checks_tsv = (
        expected_docs / "backfill_expansion_expected_diff_provenance_checks.tsv"
    )
    expected_row_manifest_tsv = (
        expected_docs / "backfill_expansion_expected_diff_provenance_row_manifest.tsv"
    )
    source_evidence_tsv = (
        expected_output
        / "backfill_expansion_expected_diff_provenance_source_evidence.tsv"
    )
    production_acceptance_manifest_tsv = (
        expected_output / "inputs/production_acceptance_manifest.tsv"
    )
    expected_diff_tsv = expected_output / "inputs/expected_diff.tsv"
    activation_summary_json = (
        activation_docs / "backfill_expansion_default_product_activation_summary.json"
    )
    activation_checks_tsv = (
        activation_docs / "backfill_expansion_default_product_activation_checks.tsv"
    )
    activation_manifest_tsv = (
        activation_docs / "backfill_expansion_default_product_activation_manifest.tsv"
    )
    adapter_tsv = full_output / "shift_aware_cell_evidence_adapter.tsv"
    reconciliation_groups_tsv = full_output / "reconciliation_groups_minimal.tsv"
    shift_summary_tsv = (
        full_output
        / "shift_aware_alignment_experiment/"
        "family_ms1_alignment_experiment_batch_summary.tsv"
    )
    shift_summary_json = (
        full_output
        / "shift_aware_alignment_experiment/"
        "family_ms1_alignment_experiment_batch_summary.json"
    )
    shift_calibration_pack_tsv = (
        full_output
        / "shift_aware_calibration_pack/"
        "shift_aware_backfill_calibration_pack.tsv"
    )
    shift_standard_peak_gate_tsv = (
        full_output
        / "shift_aware_standard_peak_gate/"
        "shift_aware_standard_peak_gate_calibration.tsv"
    )
    ms1_authority_tsv = (
        full_output
        / "standard_peak_ms1_authority_bundle/"
        "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
    )
    ms1_authority_audit_tsv = (
        full_output
        / "standard_peak_ms1_authority_bundle/"
        "backfill_ms1_pattern_product_authority_audit.tsv"
    )
    ms1_authority_summary_json = (
        full_output
        / "standard_peak_ms1_authority_bundle/"
        "standard_peak_ms1_authority_bundle_summary.json"
    )
    full_cells_tsv = _named_path(full_output, full_chain.DEFAULT_CELLS_TSV)
    full_summary_json = _named_path(full_docs, full_chain.DEFAULT_SUMMARY_JSON)
    full_checks_tsv = _named_path(full_docs, full_chain.DEFAULT_CHECKS_TSV)
    full_row_manifest_tsv = _named_path(
        full_docs,
        full_chain.DEFAULT_ROW_MANIFEST_TSV,
    )
    peak_cells_tsv = _named_path(peak_output, peak_mode.DEFAULT_CELLS_TSV)
    split_decision_tsv = _named_path(peak_docs, peak_mode.DEFAULT_SPLIT_DECISION_TSV)
    selective_cells_tsv = _named_path(
        selective_output,
        selective_shift.DEFAULT_CELLS_TSV,
    )
    clean_replay_cells_tsv = _named_path(
        clean_replay_output,
        clean_replay.DEFAULT_CELLS_TSV,
    )
    clean_replay_summary_json = _named_path(
        clean_replay_docs,
        clean_replay.DEFAULT_SUMMARY_JSON,
    )
    clean_replay_checks_tsv = _named_path(
        clean_replay_docs,
        clean_replay.DEFAULT_CHECKS_TSV,
    )
    clean_replay_row_manifest_tsv = _named_path(
        clean_replay_docs,
        clean_replay.DEFAULT_ROW_MANIFEST_TSV,
    )
    clean_activation_summary_json = _named_path(
        clean_activation_docs,
        clean_activation.DEFAULT_SUMMARY_JSON,
    )
    clean_activation_checks_tsv = _named_path(
        clean_activation_docs,
        clean_activation.DEFAULT_CHECKS_TSV,
    )
    clean_activation_manifest_tsv = _named_path(
        clean_activation_docs,
        clean_activation.DEFAULT_MANIFEST_TSV,
    )
    filtered_acceptance_manifest_tsv = _named_path(
        clean_activation_output / "inputs",
        clean_activation.DEFAULT_FILTERED_ACCEPTANCE_MANIFEST_TSV,
    )
    filtered_expected_diff_tsv = _named_path(
        clean_activation_output / "inputs",
        clean_activation.DEFAULT_FILTERED_EXPECTED_DIFF_TSV,
    )

    if (
        output_root is not None
        and summary_json == DEFAULT_RUNNER_SUMMARY_JSON
    ):
        summary_json = full_output / DEFAULT_RUNNER_SUMMARY_JSON.name

    def run_step(label: str, func: Callable[[], Any]) -> Any:
        return _run_step(label, steps, func, timing_recorder=timing_recorder)

    run_step(
        "backfill_expansion_census",
        lambda: census.build_backfill_expansion_census(
            docs_dir=census_docs,
            output_dir=census_output,
            cid_nl_activation_summary_json=cid_nl_activation_summary_json,
            cid_nl_universe_summary_json=cid_nl_universe_summary_json,
            backfill_activation_summary_json=backfill_activation_summary_json,
            cid_nl_activation_manifest_tsv=cid_nl_activation_manifest_tsv,
            cid_nl_default_quant_matrix_tsv=cid_nl_default_quant_matrix_tsv,
            cid_nl_default_row_summary_tsv=cid_nl_default_row_summary_tsv,
            cid_nl_default_cell_provenance_tsv=cid_nl_default_cell_provenance_tsv,
            old_backfill_values_tsv=old_backfill_values_tsv,
            successor_decisions_tsv=successor_decisions_tsv,
        ),
    )
    run_step(
        "backfill_expansion_evidence_availability",
        lambda: availability.build_backfill_expansion_evidence_availability(
            docs_dir=availability_docs,
            output_dir=availability_output,
            census_summary_json=census_summary_json,
            census_checks_tsv=census_checks_tsv,
            census_row_manifest_tsv=census_row_manifest_tsv,
            census_opportunity_cells_tsv=census_opportunity_cells_tsv,
        ),
    )
    run_step(
        "backfill_expansion_sample_local_ms1_evidence",
        lambda: sample_local.build_backfill_expansion_sample_local_ms1_evidence(
            docs_dir=sample_local_docs,
            output_dir=sample_local_output,
            availability_summary_json=availability_summary_json,
            availability_checks_tsv=availability_checks_tsv,
            availability_row_manifest_tsv=availability_row_manifest_tsv,
            availability_cells_tsv=availability_cells_tsv,
            alignment_backfill_cell_evidence_tsv=alignment_backfill_cell_evidence_tsv,
            alignment_review_tsv=alignment_review_tsv,
        ),
    )
    with _timed_stage(timing_recorder, "backfill_expansion:family_ms1_overlay_batch"):
        overlay_summary_tsv, raw_overlay_mode = _resolve_raw_overlay(
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            reuse_existing_raw_overlay=reuse_existing_raw_overlay,
            steps=steps,
            overlay_summary_tsv=raw_overlay_summary_tsv,
            overlay_summary_json=raw_overlay_summary_json,
            overlay_queue_tsv=overlay_queue_tsv,
            alignment_cells_tsv=alignment_backfill_cell_evidence_tsv,
            overlay_dir=raw_overlay_dir,
        )
    run_step(
        "backfill_expansion_raw_overlay_trace_identity",
        lambda: raw_trace.build_backfill_expansion_raw_overlay_trace_identity(
            docs_dir=raw_trace_docs,
            output_dir=raw_trace_output,
            sample_local_summary_json=sample_local_summary_json,
            sample_local_checks_tsv=sample_local_checks_tsv,
            sample_local_row_manifest_tsv=sample_local_row_manifest_tsv,
            sample_local_cells_tsv=sample_local_cells_tsv,
            overlay_batch_summary_tsv=overlay_summary_tsv,
            overlay_batch_summary_json=raw_overlay_summary_json,
        ),
    )
    run_step(
        "backfill_expansion_expected_diff_provenance",
        lambda: expected_diff.build_backfill_expansion_expected_diff_provenance(
            docs_dir=expected_docs,
            output_dir=expected_output,
            raw_trace_summary_json=raw_trace_summary_json,
            raw_trace_checks_tsv=raw_trace_checks_tsv,
            raw_trace_row_manifest_tsv=raw_trace_row_manifest_tsv,
            raw_trace_cells_tsv=raw_trace_cells_tsv,
            alignment_cell_evidence_tsv=alignment_backfill_cell_evidence_tsv,
            baseline_quant_matrix_tsv=cid_nl_default_quant_matrix_tsv,
            input_matrix_identity_tsv=input_matrix_identity_tsv,
        ),
    )
    run_step(
        "backfill_expansion_default_product_activation_candidate",
        lambda: activation.build_backfill_expansion_default_product_activation(
            docs_dir=activation_docs,
            output_dir=activation_output,
            packet_summary_json=expected_summary_json,
            packet_checks_tsv=expected_checks_tsv,
            packet_row_manifest_tsv=expected_row_manifest_tsv,
            packet_production_manifest_tsv=production_acceptance_manifest_tsv,
            packet_expected_diff_tsv=expected_diff_tsv,
        ),
    )

    run_step(
        "shift_aware_cell_evidence_adapter",
        lambda: write_shift_aware_cell_evidence_adapter(
            sample_local_cells_tsv=sample_local_cells_tsv,
            output_tsv=adapter_tsv,
        ),
    )
    run_step(
        "reconciliation_groups_minimal",
        lambda: write_reconciliation_groups_minimal(
            overlay_batch_summary_tsv=overlay_summary_tsv,
            output_tsv=reconciliation_groups_tsv,
        ),
    )
    run_step(
        "shift_aware_support_chain",
        lambda: run_shift_aware_support_chain(
            overlay_batch_summary_tsv=overlay_summary_tsv,
            cell_evidence_adapter_tsv=adapter_tsv,
            reconciliation_groups_tsv=reconciliation_groups_tsv,
            output_dir=full_output,
            reuse_existing=reuse_existing_shift_aware,
            render_images=render_shift_aware_images,
            min_shape_r=min_shape_r,
        ),
    )
    run_step(
        "backfill_expansion_full_evidence_chain_gate",
        lambda: full_chain.build_backfill_expansion_full_evidence_chain(
            docs_dir=full_docs,
            output_dir=full_output,
            expected_diff_tsv=expected_diff_tsv,
            source_evidence_tsv=source_evidence_tsv,
            raw_trace_cells_tsv=raw_trace_cells_tsv,
            shift_aware_batch_summary_json=shift_summary_json,
            shift_aware_cell_evidence_adapter_tsv=adapter_tsv,
            shift_aware_calibration_pack_tsv=shift_calibration_pack_tsv,
            shift_aware_standard_peak_gate_tsv=shift_standard_peak_gate_tsv,
            ms1_product_authority_tsv=ms1_authority_tsv,
            ms1_product_authority_audit_tsv=ms1_authority_audit_tsv,
            ms1_product_authority_summary_json=ms1_authority_summary_json,
            candidate_summary_json=activation_summary_json,
            candidate_checks_tsv=activation_checks_tsv,
            candidate_compact_manifest_tsv=activation_manifest_tsv,
            raw_trace_summary_json=raw_trace_summary_json,
            raw_trace_checks_tsv=raw_trace_checks_tsv,
            raw_trace_row_manifest_tsv=raw_trace_row_manifest_tsv,
            cells_tsv=full_cells_tsv,
        ),
    )
    problems = full_chain.validate_backfill_expansion_full_evidence_chain(
        summary_json=full_summary_json,
        checks_tsv=full_checks_tsv,
        row_manifest_tsv=full_row_manifest_tsv,
        cells_tsv=full_cells_tsv,
        require_full_chain=require_full_chain,
    )
    if problems:
        raise ValueError("; ".join(problems))

    run_step(
        "backfill_expansion_peak_mode_decomposition",
        lambda: peak_mode.build_backfill_expansion_peak_mode_decomposition(
            docs_dir=peak_docs,
            output_dir=peak_output,
            expected_diff_tsv=expected_diff_tsv,
            sample_local_cells_tsv=sample_local_cells_tsv,
            overlay_batch_summary_tsv=overlay_summary_tsv,
            cells_tsv=peak_cells_tsv,
        ),
    )
    run_step(
        "backfill_expansion_selective_shift_aware_gate",
        lambda: selective_shift.build_backfill_expansion_selective_shift_aware_gate(
            docs_dir=selective_docs,
            output_dir=selective_output,
            expected_diff_tsv=expected_diff_tsv,
            sample_local_cells_tsv=sample_local_cells_tsv,
            raw_trace_cells_tsv=raw_trace_cells_tsv,
            shift_aware_batch_summary_json=shift_summary_json,
            shift_aware_batch_summary_tsv=shift_summary_tsv,
            standard_peak_gate_tsv=shift_standard_peak_gate_tsv,
            cells_tsv=selective_cells_tsv,
        ),
    )
    run_step(
        "backfill_expansion_clean_target_full_chain_replay",
        lambda: clean_replay.build_backfill_expansion_clean_target_full_chain_replay(
            docs_dir=clean_replay_docs,
            output_dir=clean_replay_output,
            peak_mode_cells_tsv=peak_cells_tsv,
            split_decision_tsv=split_decision_tsv,
            full_chain_cells_tsv=full_cells_tsv,
            full_chain_summary_json=full_summary_json,
            selective_shift_cells_tsv=selective_cells_tsv,
            shift_aware_standard_peak_gate_tsv=shift_standard_peak_gate_tsv,
            overlay_batch_summary_tsv=overlay_summary_tsv,
            selective_ms1_authority_dir=(
                clean_replay_output / "selective_source_family_ms1_authority_bundle"
            ),
            cells_tsv=clean_replay_cells_tsv,
        ),
    )

    def build_clean_target_selective_activation() -> dict[str, Any]:
        return (
            clean_activation
            .build_backfill_expansion_clean_target_selective_product_activation(
                docs_dir=clean_activation_docs,
                output_dir=clean_activation_output,
                clean_replay_summary_json=clean_replay_summary_json,
                clean_replay_checks_tsv=clean_replay_checks_tsv,
                clean_replay_manifest_tsv=clean_replay_row_manifest_tsv,
                clean_replay_cells_tsv=clean_replay_cells_tsv,
                base_activation_summary_json=activation_summary_json,
                source_acceptance_manifest_tsv=production_acceptance_manifest_tsv,
                source_expected_diff_tsv=expected_diff_tsv,
                filtered_acceptance_manifest_tsv=filtered_acceptance_manifest_tsv,
                filtered_expected_diff_tsv=filtered_expected_diff_tsv,
            )
        )

    run_step(
        "backfill_expansion_clean_target_selective_product_activation",
        build_clean_target_selective_activation,
    )
    clean_activation_problems = (
        clean_activation.validate_backfill_expansion_clean_target_selective_product_activation(
            summary_json=clean_activation_summary_json,
            checks_tsv=clean_activation_checks_tsv,
            compact_manifest_tsv=clean_activation_manifest_tsv,
        )
    )
    if clean_activation_problems:
        raise ValueError("; ".join(clean_activation_problems))

    full_summary = _read_json_object(full_summary_json)
    activation_summary = _read_json_object(clean_activation_summary_json)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "validation_status": activation_summary.get("validation_status", ""),
        "raw_overlay_mode": raw_overlay_mode,
        "shift_aware_reuse_existing": reuse_existing_shift_aware,
        "shift_aware_render_images": render_shift_aware_images,
        "min_shape_r": min_shape_r,
        "candidate_cell_count": full_summary.get("candidate_cell_count"),
        "full_chain_complete": full_summary.get("full_chain_complete"),
        "full_chain_pass_cell_count": full_summary.get(
            "full_chain_pass_cell_count",
        ),
        "held_cell_count": full_summary.get("held_cell_count"),
        "primary_blocker_counts": full_summary.get("primary_blocker_counts", {}),
        "active_backfill_cell_count": activation_summary.get("written_backfill_count"),
        "active_peak_hypothesis_count": activation_summary.get("candidate_peak_count"),
        "product_authority_scope": activation_summary.get(
            "product_authority_scope",
        ),
        "default_activation_effect": activation_summary.get(
            "default_activation_effect",
        ),
        "write_authority": activation_summary.get("write_authority", False),
        "product_writer_changed": activation_summary.get(
            "product_writer_changed",
            False,
        ),
        "default_quant_matrix_changed": activation_summary.get(
            "default_quant_matrix_changed",
            False,
        ),
        "default_matrix_files_written": activation_summary.get(
            "default_matrix_files_written",
            False,
        ),
        "workbook_or_gui_changed": activation_summary.get(
            "workbook_or_gui_changed",
            False,
        ),
        "selected_peak_area_or_counting_changed": activation_summary.get(
            "selected_peak_area_or_counting_changed",
            False,
        ),
        "steps": steps,
        "full_chain_summary_json": str(full_summary_json),
        "clean_target_selective_activation_summary_json": str(
            clean_activation_summary_json,
        ),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def run_backfill_expansion_clean_target_selective_preset_from_alignment(
    *,
    alignment_dir: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path | None = None,
    reuse_existing_raw_overlay: bool = False,
    reuse_existing_shift_aware: bool = False,
    render_shift_aware_images: bool = False,
    min_shape_r: float = DEFAULT_MIN_SHAPE_R,
    timing_recorder: Any | None = None,
) -> BackfillExpansionPresetOutputs:
    """Run the bounded productization chain from a completed alignment output."""

    alignment_dir = alignment_dir.resolve()
    raw_dir = raw_dir.resolve()
    dll_dir = dll_dir.resolve()
    preset_dir = (
        output_dir.resolve()
        if output_dir is not None
        else alignment_dir / "backfill_expansion_productization_preset"
    )
    docs_root = preset_dir / "docs"
    output_root = preset_dir / "output"

    input_quant_matrix_tsv = alignment_dir / "alignment_matrix.tsv"
    input_matrix_identity_tsv = alignment_dir / "alignment_matrix_identity.tsv"
    alignment_backfill_cell_evidence_tsv = (
        alignment_dir / "alignment_backfill_cell_evidence.tsv"
    )
    alignment_review_tsv = alignment_dir / "alignment_review.tsv"
    for label, path in (
        ("alignment matrix", input_quant_matrix_tsv),
        ("alignment matrix identity", input_matrix_identity_tsv),
        ("alignment backfill cell evidence", alignment_backfill_cell_evidence_tsv),
        ("alignment review", alignment_review_tsv),
    ):
        _require_file(path, label)

    cid_docs = _scoped_dir(docs_root, cid_nl_activation.DEFAULT_DOCS_DIR)
    cid_output = _scoped_dir(output_root, cid_nl_activation.DEFAULT_OUTPUT_DIR)
    cid_summary_json = (
        cid_docs / "cid_nl_default_product_activation_summary.json"
    )
    cid_nl_activation.build_cid_nl_default_product_activation(
        docs_dir=cid_docs,
        output_dir=cid_output,
        source_root=ROOT,
        input_quant_matrix_tsv=input_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
    )

    runner_summary_json = (
        preset_dir / "backfill_expansion_productization_preset_summary.json"
    )
    payload = run_backfill_expansion_full_evidence_chain(
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        reuse_existing_raw_overlay=reuse_existing_raw_overlay,
        reuse_existing_shift_aware=reuse_existing_shift_aware,
        render_shift_aware_images=render_shift_aware_images,
        min_shape_r=min_shape_r,
        summary_json=runner_summary_json,
        docs_root=docs_root,
        output_root=output_root,
        cid_nl_activation_summary_json=cid_summary_json,
        cid_nl_activation_manifest_tsv=(
            cid_output / "inputs/cid_nl_default_product_activation_manifest.tsv"
        ),
        cid_nl_default_quant_matrix_tsv=(
            cid_output / "default_output/quant_matrix.tsv"
        ),
        cid_nl_default_row_summary_tsv=(
            cid_output / "default_output/row_summary.tsv"
        ),
        cid_nl_default_cell_provenance_tsv=(
            cid_output / "default_output/cell_provenance.tsv"
        ),
        alignment_backfill_cell_evidence_tsv=alignment_backfill_cell_evidence_tsv,
        alignment_review_tsv=alignment_review_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        timing_recorder=timing_recorder,
    )
    return BackfillExpansionPresetOutputs(
        summary_json=runner_summary_json,
        clean_target_activation_summary_json=Path(
            str(payload["clean_target_selective_activation_summary_json"])
        ),
        product_authority_scope=str(payload.get("product_authority_scope", "")),
        active_backfill_cell_count=payload.get("active_backfill_cell_count"),
    )


def write_shift_aware_cell_evidence_adapter(
    *,
    sample_local_cells_tsv: Path,
    output_tsv: Path,
) -> Path:
    rows = read_tsv_required(
        sample_local_cells_tsv,
        SAMPLE_LOCAL_ADAPTER_SOURCE_COLUMNS,
    )
    adapter_rows = [
        {
            "feature_family_id": text_value(row.get("peak_hypothesis_id")),
            "sample_stem": text_value(row.get("sample_stem")),
            "reason": text_value(row.get("cell_evidence_reason")),
        }
        for row in rows
    ]
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        output_tsv,
        adapter_rows,
        SHIFT_AWARE_CELL_EVIDENCE_ADAPTER_COLUMNS,
        extrasaction="raise",
    )
    return output_tsv


def write_reconciliation_groups_minimal(
    *,
    overlay_batch_summary_tsv: Path,
    output_tsv: Path,
) -> Path:
    rows = read_tsv_required(
        overlay_batch_summary_tsv,
        OVERLAY_RECONCILIATION_SOURCE_COLUMNS,
    )
    group_rows = [
        {
            "feature_family_id": text_value(row.get("feature_family_id")),
            "product_behavior_state": "backfill_expansion_candidate_replay_held",
            "evidence_authority_state": "candidate_only_no_product_authority",
            "reconciliation_class": "expected_diff_candidate_needs_full_chain",
            "detected_cell_count": text_value(row.get("detected_count")),
            "rescued_cell_count": text_value(row.get("rescued_count")),
            "top_support_component": "raw_overlay_trace_identity",
            "top_blocker": "shift_aware_own_max_product_authority_chain_incomplete",
            "missing_evidence": (
                "shift_aware_standard_peak_gate_or_ms1_product_authority_sidecar"
            ),
        }
        for row in rows
    ]
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        output_tsv,
        group_rows,
        RECONCILIATION_GROUP_COLUMNS,
        extrasaction="raise",
    )
    return output_tsv


def run_shift_aware_support_chain(
    *,
    overlay_batch_summary_tsv: Path,
    cell_evidence_adapter_tsv: Path,
    reconciliation_groups_tsv: Path,
    output_dir: Path,
    reuse_existing: bool,
    render_images: bool,
    min_shape_r: float,
) -> dict[str, Any]:
    shift_dir = output_dir / "shift_aware_alignment_experiment"
    pack_dir = output_dir / "shift_aware_calibration_pack"
    gate_dir = output_dir / "shift_aware_standard_peak_gate"
    authority_dir = output_dir / "standard_peak_ms1_authority_bundle"

    shift_rows, shift_summary = (
        family_ms1_alignment_experiment_batch.run_alignment_experiment_batch(
            overlay_batch_summary_tsv=overlay_batch_summary_tsv,
            cell_evidence_tsv=cell_evidence_adapter_tsv,
            output_dir=shift_dir,
            reuse_existing=reuse_existing,
            render_images=render_images,
        )
    )
    write_tsv(
        shift_dir / "family_ms1_alignment_experiment_batch_summary.tsv",
        shift_rows,
        family_ms1_alignment_experiment_batch.SUMMARY_COLUMNS,
        extrasaction="raise",
    )
    (shift_dir / "family_ms1_alignment_experiment_batch_summary.json").write_text(
        json.dumps(shift_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _run_cli_step(
        "shift-aware calibration pack",
        shift_aware_backfill_calibration_pack.main(
            [
                "--shift-aware-summary-dir",
                str(shift_dir),
                "--reconciliation-groups-tsv",
                str(reconciliation_groups_tsv),
                "--overlay-batch-summary-tsv",
                str(overlay_batch_summary_tsv),
                "--shift-aware-output-dir",
                str(shift_dir),
                "--min-shape-r",
                str(min_shape_r),
                "--include-all",
                "--output-dir",
                str(pack_dir),
            ],
        ),
    )
    _run_cli_step(
        "shift-aware standard peak gate",
        shift_aware_standard_peak_gate_calibration.main(
            [
                "--manual-pack-tsv",
                str(pack_dir / "shift_aware_backfill_calibration_pack.tsv"),
                "--output-dir",
                str(gate_dir),
            ],
        ),
    )
    _run_cli_step(
        "standard-peak MS1 authority bundle",
        standard_peak_ms1_authority_bundle.main(
            [
                "--standard-peak-gate-tsv",
                str(gate_dir / "shift_aware_standard_peak_gate_calibration.tsv"),
                "--overlay-batch-summary-tsv",
                str(overlay_batch_summary_tsv),
                "--authority-mode",
                "machine-gate",
                "--output-dir",
                str(authority_dir),
            ],
        ),
    )
    return {
        "shift_aware_summary": shift_summary,
        "shift_aware_summary_tsv": str(
            shift_dir / "family_ms1_alignment_experiment_batch_summary.tsv",
        ),
        "shift_aware_calibration_pack_tsv": str(
            pack_dir / "shift_aware_backfill_calibration_pack.tsv",
        ),
        "shift_aware_standard_peak_gate_tsv": str(
            gate_dir / "shift_aware_standard_peak_gate_calibration.tsv",
        ),
        "ms1_product_authority_tsv": str(
            authority_dir
            / "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv",
        ),
    }


def _resolve_raw_overlay(
    *,
    raw_dir: Path | None,
    dll_dir: Path | None,
    reuse_existing_raw_overlay: bool,
    steps: list[dict[str, str]],
    overlay_summary_tsv: Path | None = None,
    overlay_summary_json: Path | None = None,
    overlay_queue_tsv: Path | None = None,
    alignment_cells_tsv: Path | None = None,
    overlay_dir: Path | None = None,
) -> tuple[Path, str]:
    overlay_summary_tsv = (
        overlay_summary_tsv or raw_trace.DEFAULT_OVERLAY_BATCH_SUMMARY_TSV
    )
    overlay_summary_json = (
        overlay_summary_json or raw_trace.DEFAULT_OVERLAY_BATCH_SUMMARY_JSON
    )
    overlay_queue_tsv = overlay_queue_tsv or (
        sample_local.DEFAULT_OUTPUT_DIR
        / "backfill_expansion_sample_local_ms1_overlay_queue.tsv"
    )
    alignment_cells_tsv = (
        alignment_cells_tsv
        or sample_local.DEFAULT_ALIGNMENT_BACKFILL_CELL_EVIDENCE_TSV
    )
    overlay_dir = overlay_dir or raw_trace.DEFAULT_OVERLAY_BATCH_DIR
    if reuse_existing_raw_overlay:
        _require_file(overlay_summary_tsv, "--reuse-existing-raw-overlay")
        steps.append(
            {
                "step": "family_ms1_overlay_batch",
                "status": "pass",
                "mode": "reused_existing_raw_overlay",
                "artifact": str(overlay_summary_tsv),
            },
        )
        return overlay_summary_tsv, "reused_existing_raw_overlay"
    if raw_dir is None or dll_dir is None:
        raise ValueError(
            "Provide --raw-dir and --dll-dir, or pass "
            "--reuse-existing-raw-overlay to use the current RAW trace artifact.",
        )
    metrics: dict[str, Any] = {}
    overlay_rows = family_ms1_overlay_batch.run_overlay_batch(
        review_queue_tsv=overlay_queue_tsv,
        alignment_cells=alignment_cells_tsv,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=overlay_dir,
        start_rank=1,
        limit=None,
        ppm=10.0,
        max_highlight_rescued=8,
        reuse_existing=True,
        write_pdf=False,
        evidence_only=True,
        metrics=metrics,
    )
    family_ms1_overlay_batch._write_outputs(overlay_dir, overlay_rows, metrics=metrics)
    failed = [row for row in overlay_rows if text_value(row.get("status")) == "failed"]
    if failed:
        raise ValueError(f"family MS1 overlay batch failed rows: {len(failed)}")
    steps.append(
        {
            "step": "family_ms1_overlay_batch",
            "status": "pass",
            "mode": "rendered_raw_trace_evidence_only",
            "artifact": str(overlay_summary_tsv),
            "summary_json": str(overlay_summary_json),
            "row_count": str(len(overlay_rows)),
        },
    )
    return overlay_summary_tsv, "rendered_raw_trace_evidence_only"


def _run_step(
    label: str,
    steps: list[dict[str, str]],
    func: Callable[[], Any],
    *,
    timing_recorder: Any | None = None,
) -> Any:
    with _timed_stage(timing_recorder, f"backfill_expansion:{label}"):
        result = func()
    steps.append({"step": label, "status": "pass"})
    return result


def _timed_stage(timing_recorder: Any | None, stage: str):
    if timing_recorder is None:
        return nullcontext()
    return timing_recorder.stage(stage)


def _run_cli_step(label: str, code: int) -> None:
    if code != 0:
        raise ValueError(f"{label} failed with exit code {code}")


def _require_file(path: Path, context: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{context}: required artifact missing: {path}")


def _read_json_object(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _validate_productization_preset(*, require_full_chain: bool) -> list[str]:
    problems = [
        f"full-chain: {problem}"
        for problem in full_chain.validate_backfill_expansion_full_evidence_chain(
            require_full_chain=require_full_chain,
        )
    ]
    clean_activation_problems = (
        clean_activation.validate_backfill_expansion_clean_target_selective_product_activation()
    )
    problems.extend(
        f"clean-target activation: {problem}"
        for problem in clean_activation_problems
    )
    return problems


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--dll-dir", type=Path)
    parser.add_argument(
        "--reuse-existing-raw-overlay",
        action="store_true",
        help=(
            "Reuse the current RAW overlay trace artifact instead of reading "
            "RAW files."
        ),
    )
    parser.add_argument(
        "--reuse-existing-shift-aware",
        action="store_true",
        help="Reuse existing shift-aware per-family summaries when available.",
    )
    parser.add_argument(
        "--render-shift-aware-images",
        action="store_true",
        help="Render shift-aware PNGs. Default is TSV/JSON evidence only.",
    )
    parser.add_argument("--min-shape-r", type=float, default=DEFAULT_MIN_SHAPE_R)
    parser.add_argument("--require-full-chain", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_RUNNER_SUMMARY_JSON,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.check_only:
            problems = _validate_productization_preset(
                require_full_chain=args.require_full_chain,
            )
            if problems:
                for problem in problems:
                    print(problem, file=sys.stderr)
                return 1 if args.require_full_chain else 2
            print(
                "Backfill expansion productization preset summaries: "
                f"{full_chain.DEFAULT_SUMMARY_JSON}; "
                f"{clean_activation.DEFAULT_SUMMARY_JSON}",
            )
            return 0
        payload = run_backfill_expansion_full_evidence_chain(
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            reuse_existing_raw_overlay=args.reuse_existing_raw_overlay,
            reuse_existing_shift_aware=args.reuse_existing_shift_aware,
            render_shift_aware_images=args.render_shift_aware_images,
            min_shape_r=args.min_shape_r,
            require_full_chain=args.require_full_chain,
            summary_json=args.summary_json,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Backfill expansion full evidence-chain runner summary: {args.summary_json}")
    print(
        "Full-chain status: "
        f"{payload['full_chain_pass_cell_count']}/"
        f"{payload['candidate_cell_count']} pass; "
        f"held={payload['held_cell_count']}; "
        f"complete={payload['full_chain_complete']}",
    )
    print(
        "Active clean-target activation: "
        f"{payload['active_backfill_cell_count']} cells; "
        f"scope={payload['product_authority_scope']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
