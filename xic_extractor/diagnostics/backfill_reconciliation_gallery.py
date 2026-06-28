"""Backfill evidence reconciliation indexes and gallery rendering."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_evidence as _gallery_evidence,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_inputs as _gallery_inputs,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_overlay_links as _gallery_overlay_links,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_provenance as _gallery_provenance,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_review_modes as _gallery_review_modes,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_source_context as _gallery_source_context,
)
from xic_extractor.diagnostics import (
    backfill_reconciliation_gallery_target_benchmark as _gallery_target_benchmark,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_assets import (
    gallery_css as _gallery_css,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_assets import (
    lightbox_html as _lightbox_html,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_assets import (
    lightbox_script as _lightbox_script,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    badge as _badge,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    badge_label as _badge_label,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    escape_attr as _escape_attr,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    escape_html as _escape,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    href_for_path as _href_for_path,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_html import (
    safe_href as _safe_href,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _activation_application_summary,
    _activation_delta_cell_from_row,
    _activation_value_delta_matrix_effect_counts,
    _activation_written_projection_cell_count,
    _activation_written_projection_group_keys,
    _current_matrix_written_projection_cell_count,
    _current_matrix_written_projection_group_keys,
    _group_sort_key,
    _is_projected_new_accept,
    _representative_sort_key,
    _shadow_policy_cell_from_row,
    _shadow_policy_cell_sort_key,
    _shadow_policy_cells_for_family_groups,
    _shadow_policy_cells_for_group,
    _shadow_policy_compact_summary,
    _shadow_policy_decision_counts,
    _shadow_policy_production_gap_counts,
    _shadow_projection_cell_from_row,
    _shadow_projection_cell_sort_key,
    _shadow_projection_cells_for_family_groups,
    _shadow_projection_cells_for_group,
    _shadow_projection_compact_summary,
    _shadow_projection_decision_counts,
    _shadow_projection_matrix_counts,
    _target_benchmark_context_counts,
    _target_benchmark_context_from_row,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _activation_written_cell_keys as _activation_written_cell_keys,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _is_activation_matrix_write as _is_activation_matrix_write,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _is_current_backfill_matrix_write as _is_current_backfill_matrix_write,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _representatives_by_group as _representatives_by_group,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _shadow_policy_cells_by_family as _shadow_policy_cells_by_family,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _shadow_policy_cells_by_group as _shadow_policy_cells_by_group,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _shadow_projection_accept_group_keys as _shadow_projection_accept_group_keys,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _shadow_projection_cells_by_family as _shadow_projection_cells_by_family,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _shadow_projection_cells_by_group as _shadow_projection_cells_by_group,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_indices import (
    _target_benchmark_contexts_by_family as _target_benchmark_contexts_by_family,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_inputs import (
    load_reconciliation_input_rows,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_models import (
    EVIDENCE_AUTHORITY_STATES as EVIDENCE_AUTHORITY_STATES,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_models import (
    GROUP_TSV_COLUMNS,
    REPRESENTATIVE_CELL_TSV_COLUMNS,
    ReconciliationGroup,
    ReconciliationIndex,
    ReconciliationOutputs,
    RepresentativeCell,
    ShadowPolicyCell,
    ShadowProjectionCell,
    TargetBenchmarkContext,
    _ordered_unique,
    _SeedRecord,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_models import (
    RECONCILIATION_CLASS_PRIORITY as RECONCILIATION_CLASS_PRIORITY,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_models import (
    RECONCILIATION_CLASSES as RECONCILIATION_CLASSES,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_render_context import (
    _gallery_render_context,
    _html_scope_notice,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_render_context import (
    _html_priority_group as _html_priority_group,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery_render_context import (
    _html_render_groups as _html_render_groups,
)
from xic_extractor.diagnostics.diagnostic_io import (
    bool_value,
    optional_float,
    split_semicolon_labels,
    text_value,
    write_tsv,
)

_read_required_tsv = _gallery_inputs._read_required_tsv
_input_artifact_summary = _gallery_inputs._input_artifact_summary
_input_artifact_hashes = _gallery_inputs._input_artifact_hashes
_REQUIRED_ALIGNMENT_REVIEW_COLUMNS = (
    _gallery_inputs._REQUIRED_ALIGNMENT_REVIEW_COLUMNS
)
_REQUIRED_ALIGNMENT_CELLS_COLUMNS = (
    _gallery_inputs._REQUIRED_ALIGNMENT_CELLS_COLUMNS
)
_REQUIRED_ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS = (
    _gallery_inputs._REQUIRED_ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS
)
_REQUIRED_RETAINED_BACKFILL_GATE_COLUMNS = (
    _gallery_inputs._REQUIRED_RETAINED_BACKFILL_GATE_COLUMNS
)
_REQUIRED_SHIFT_AWARE_STANDARD_PEAK_GATE_COLUMNS = (
    _gallery_inputs._REQUIRED_SHIFT_AWARE_STANDARD_PEAK_GATE_COLUMNS
)
_REQUIRED_TARGETED_ISTD_BENCHMARK_SUMMARY_COLUMNS = (
    _gallery_inputs._REQUIRED_TARGETED_ISTD_BENCHMARK_SUMMARY_COLUMNS
)
_INPUT_ARTIFACT_LABEL_BY_KEY = _gallery_inputs._INPUT_ARTIFACT_LABEL_BY_KEY
_source_hashes_from_input_artifacts = (
    _gallery_source_context._source_hashes_from_input_artifacts
)
_first_by_family = _gallery_source_context._first_by_family
_first_by_family_and_seed_group = (
    _gallery_source_context._first_by_family_and_seed_group
)
_group_by_family = _gallery_source_context._group_by_family
_cells_by_family_seed_group = _gallery_source_context._cells_by_family_seed_group
_overlay_rows_by_family_seed_group = (
    _gallery_source_context._overlay_rows_by_family_seed_group
)
_legacy_overlay_rows_by_family = (
    _gallery_source_context._legacy_overlay_rows_by_family
)
_overlay_rows_for_seed_group = _gallery_source_context._overlay_rows_for_seed_group
_legacy_overlay_rows = _gallery_source_context._legacy_overlay_rows
_candidate_family_ids = _gallery_source_context._candidate_family_ids
_detected_family_ids = _gallery_source_context._detected_family_ids
_seed_records_by_family = _gallery_source_context._seed_records_by_family
_seed_samples_by_family = _gallery_source_context._seed_samples_by_family
_seed_group_id = _gallery_source_context._seed_group_id
_fallback_seed_record = _gallery_source_context._fallback_seed_record
_cells_for_seed_record = _gallery_source_context._cells_for_seed_record
_seed_detected_anchor_count = _gallery_source_context._seed_detected_anchor_count
_count_cells = _gallery_source_context._count_cells
_count_provisional = _gallery_source_context._count_provisional
_int_text = _gallery_source_context._int_text
SHIFT_AWARE_SAME_PATTERN_SUPPORT_MIN_R = (
    _gallery_evidence.SHIFT_AWARE_SAME_PATTERN_SUPPORT_MIN_R
)
SHIFT_AWARE_SAME_PATTERN_CONFLICT_MAX_R = (
    _gallery_evidence.SHIFT_AWARE_SAME_PATTERN_CONFLICT_MAX_R
)
_HUMAN_REVIEW_PREFIXES = _gallery_evidence._HUMAN_REVIEW_PREFIXES
_HUMAN_REVIEW_TOKENS = _gallery_evidence._HUMAN_REVIEW_TOKENS
_ANCHOR_SHAPE_SUPPORTED_REASON = _gallery_evidence._ANCHOR_SHAPE_SUPPORTED_REASON
_ANCHOR_SHAPE_REVIEW_REASON = _gallery_evidence._ANCHOR_SHAPE_REVIEW_REASON
_classify_evidence = _gallery_evidence._classify_evidence
_overlay_evidence_notes = _gallery_evidence._overlay_evidence_notes
_shift_aware_standard_peak_gate_components = (
    _gallery_evidence._shift_aware_standard_peak_gate_components
)
_shift_aware_same_pattern_evidence = (
    _gallery_evidence._shift_aware_same_pattern_evidence
)
_product_authority_components = _gallery_evidence._product_authority_components
_append_product_authority_component = (
    _gallery_evidence._append_product_authority_component
)
_anchor_peak_overlay_notes = _gallery_evidence._anchor_peak_overlay_notes
_existing_path_from_text = _gallery_evidence._existing_path_from_text
_compact_note_items = _gallery_evidence._compact_note_items
_is_stale_or_join_token = _gallery_evidence._is_stale_or_join_token
_is_human_review_token = _gallery_evidence._is_human_review_token
_candidate_gate_source_warnings = _gallery_evidence._candidate_gate_source_warnings
_product_behavior = _gallery_evidence._product_behavior
_cell_writes_primary_matrix = _gallery_evidence._cell_writes_primary_matrix
_cell_has_primary_area_context = _gallery_evidence._cell_has_primary_area_context
_reconciliation_class = _gallery_evidence._reconciliation_class
_first_path = _gallery_evidence._first_path
OVERLAY_INTERPRETATION_GUIDE_PATH = (
    _gallery_provenance.OVERLAY_INTERPRETATION_GUIDE_PATH
)
_interpretation_guide_callout_html = (
    _gallery_provenance._interpretation_guide_callout_html
)
_write_local_overlay_interpretation_guide = (
    _gallery_provenance._write_local_overlay_interpretation_guide
)
_artifact_links = _gallery_provenance._artifact_links
_input_artifact_links = _gallery_provenance._input_artifact_links
_source_artifacts_html = _gallery_provenance._source_artifacts_html
_input_artifact_paths_by_label = _gallery_provenance._input_artifact_paths_by_label
_input_artifact_path_rows = _gallery_provenance._input_artifact_path_rows
_compact_counts_text = _gallery_target_benchmark._compact_counts_text
_target_benchmark_summary_text = (
    _gallery_target_benchmark._target_benchmark_summary_text
)
_target_benchmark_panel_html = (
    _gallery_target_benchmark._target_benchmark_panel_html
)
_family_target_summary_html = _gallery_target_benchmark._family_target_summary_html
_target_benchmark_compact_summary = (
    _gallery_target_benchmark._target_benchmark_compact_summary
)
_target_benchmark_contexts_html = (
    _gallery_target_benchmark._target_benchmark_contexts_html
)
_target_coverage_text = _gallery_target_benchmark._target_coverage_text
_target_benchmark_supplied = _gallery_target_benchmark._target_benchmark_supplied
_is_cid_nl_successor_review_group = (
    _gallery_review_modes._is_cid_nl_successor_review_group
)
_is_cid_nl_differential_review_group = (
    _gallery_review_modes._is_cid_nl_differential_review_group
)
_cid_nl_transition_label = _gallery_review_modes._cid_nl_transition_label
_is_cid_nl_successor_review_index = (
    _gallery_review_modes._is_cid_nl_successor_review_index
)
_missing_overlay_status_html = _gallery_overlay_links._missing_overlay_status_html
_overlay_not_required_status_html = (
    _gallery_overlay_links._overlay_not_required_status_html
)
_overlay_not_required_by_gate = _gallery_overlay_links._overlay_not_required_by_gate
_missing_overlay_reason_text = _gallery_overlay_links._missing_overlay_reason_text
_overlay_batch_supplied = _gallery_overlay_links._overlay_batch_supplied
_family_pattern_link_html = _gallery_overlay_links._family_pattern_link_html
_family_overlay_links = _gallery_overlay_links._family_overlay_links
_overlay_link_html = _gallery_overlay_links._overlay_link_html
_path_overlay_link_html = _gallery_overlay_links._path_overlay_link_html
_hypothesis_overlay_path = _gallery_overlay_links._hypothesis_overlay_path
_hypothesis_overlay_link_html = _gallery_overlay_links._hypothesis_overlay_link_html
_overlay_href_context = _gallery_overlay_links._overlay_href_context
_seed_overlay_cell_html = _gallery_overlay_links._seed_overlay_cell_html
_shadow_projection_overlay_link_html = (
    _gallery_overlay_links._shadow_projection_overlay_link_html
)
_shadow_policy_overlay_link_html = (
    _gallery_overlay_links._shadow_policy_overlay_link_html
)

SCHEMA_VERSION = "backfill_evidence_reconciliation_v0"

_REVIEW_CATEGORY_LABELS = {
    "needs_review": "Needs review",
    "accepted_supported": "Evidence-supported rows",
    "conflict_or_blocked": "Conflict / blocked",
    "missing_evidence": "Missing evidence",
}
_DEFAULT_FILTER_CATEGORY = "product_rows"
_REVIEW_FILTER_LABELS = {
    "product_rows": "Review queue",
    "projection_accepts": "Projected matrix writes",
    **_REVIEW_CATEGORY_LABELS,
    "debug_rows": "Duplicate / audit debug",
}
_REVIEW_CATEGORY_SUMMARY_LABELS = {
    "needs_review": "Review",
    "accepted_supported": "Evidence-supported",
    "conflict_or_blocked": "Conflict",
    "missing_evidence": "Missing",
}
_REVIEW_CATEGORY_BY_CLASS = {
    "product_rejects_but_product_grade_supports": "needs_review",
    "product_rejects_but_visual_supports": "needs_review",
    "evidence_inconclusive": "needs_review",
    "machine_support_no_overlay": "accepted_supported",
    "product_accepts_and_product_grade_supports": "accepted_supported",
    "product_accepts_and_visual_supports": "accepted_supported",
    "product_accepts_but_evidence_conflicts": "conflict_or_blocked",
    "product_rejects_and_evidence_blocks": "conflict_or_blocked",
    "not_assessable_missing_overlay": "missing_evidence",
    "not_assessable_missing_seed_provenance": "missing_evidence",
    "not_assessable_join_gap": "missing_evidence",
}
_HIGH_SEED_ALIAS_COUNT = 5


def run_reconciliation_gallery(
    *,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    output_dir: Path,
    alignment_matrix_tsv: Path | None = None,
    backfill_seed_audit_tsv: Path | None = None,
    overlay_batch_summary_tsvs: Sequence[Path] = (),
    shift_aware_same_pattern_tsvs: Sequence[Path] = (),
    shift_aware_standard_peak_gate_tsvs: Sequence[Path] = (),
    seed_aware_family_tsv: Path | None = None,
    seed_aware_summary_tsv: Path | None = None,
    candidate_gate_tsv: Path | None = None,
    retained_backfill_gate_tsv: Path | None = None,
    tier2_trace_evidence_tsv: Path | None = None,
    shadow_policy_cells_tsv: Path | None = None,
    shadow_projection_cells_tsv: Path | None = None,
    activation_application_summary_tsv: Path | None = None,
    activation_value_delta_tsv: Path | None = None,
    targeted_istd_benchmark_summary_tsv: Path | None = None,
    source_run_id: str = "",
) -> ReconciliationOutputs:
    """Load existing artifacts, write reconciliation indexes, and render HTML."""

    input_rows = load_reconciliation_input_rows(
        alignment_review_tsv=alignment_review_tsv,
        alignment_cells_tsv=alignment_cells_tsv,
        alignment_matrix_tsv=alignment_matrix_tsv,
        backfill_seed_audit_tsv=backfill_seed_audit_tsv,
        overlay_batch_summary_tsvs=overlay_batch_summary_tsvs,
        shift_aware_same_pattern_tsvs=shift_aware_same_pattern_tsvs,
        shift_aware_standard_peak_gate_tsvs=shift_aware_standard_peak_gate_tsvs,
        seed_aware_family_tsv=seed_aware_family_tsv,
        seed_aware_summary_tsv=seed_aware_summary_tsv,
        candidate_gate_tsv=candidate_gate_tsv,
        retained_backfill_gate_tsv=retained_backfill_gate_tsv,
        tier2_trace_evidence_tsv=tier2_trace_evidence_tsv,
        shadow_policy_cells_tsv=shadow_policy_cells_tsv,
        shadow_projection_cells_tsv=shadow_projection_cells_tsv,
        activation_application_summary_tsv=activation_application_summary_tsv,
        activation_value_delta_tsv=activation_value_delta_tsv,
        targeted_istd_benchmark_summary_tsv=targeted_istd_benchmark_summary_tsv,
        source_run_id=source_run_id,
    )
    index = build_reconciliation_index(
        review_rows=input_rows.review_rows,
        cell_rows=input_rows.cell_rows,
        alignment_matrix_rows=input_rows.matrix_rows,
        seed_audit_rows=input_rows.seed_audit_rows,
        overlay_rows=input_rows.overlay_rows,
        shift_aware_same_pattern_rows=input_rows.shift_aware_rows,
        shift_aware_standard_peak_gate_rows=input_rows.standard_peak_gate_rows,
        seed_aware_family_rows=input_rows.seed_aware_family_rows,
        seed_aware_summary_rows=input_rows.seed_aware_summary_rows,
        candidate_gate_rows=input_rows.candidate_gate_rows,
        retained_gate_rows=input_rows.retained_gate_rows,
        tier2_trace_evidence_rows=input_rows.tier2_trace_evidence_rows,
        shadow_policy_rows=input_rows.shadow_policy_rows,
        shadow_projection_rows=input_rows.shadow_projection_rows,
        activation_application_summary_rows=(
            input_rows.activation_application_summary_rows
        ),
        activation_value_delta_rows=input_rows.activation_value_delta_rows,
        target_benchmark_rows=input_rows.target_benchmark_rows,
        input_artifacts=input_rows.input_artifacts,
    )
    paths = write_reconciliation_outputs(output_dir, index)
    gallery_html = output_dir / "backfill_evidence_reconciliation_gallery.html"
    write_reconciliation_gallery_html(gallery_html, index, output_paths=paths)
    return ReconciliationOutputs(
        groups_tsv=paths["groups_tsv"],
        representative_cells_tsv=paths["representative_cells_tsv"],
        summary_json=paths["summary_json"],
        gallery_html=gallery_html,
    )


def build_reconciliation_index(
    *,
    review_rows: Iterable[Mapping[str, str]],
    cell_rows: Iterable[Mapping[str, str]],
    alignment_matrix_rows: Iterable[Mapping[str, str]] = (),
    seed_audit_rows: Iterable[Mapping[str, str]] = (),
    overlay_rows: Iterable[Mapping[str, str]] = (),
    shift_aware_same_pattern_rows: Iterable[Mapping[str, str]] = (),
    shift_aware_standard_peak_gate_rows: Iterable[Mapping[str, str]] = (),
    seed_aware_family_rows: Iterable[Mapping[str, str]] = (),
    seed_aware_summary_rows: Iterable[Mapping[str, str]] = (),
    candidate_gate_rows: Iterable[Mapping[str, str]] = (),
    retained_gate_rows: Iterable[Mapping[str, str]] = (),
    tier2_trace_evidence_rows: Iterable[Mapping[str, str]] = (),
    shadow_policy_rows: Iterable[Mapping[str, str]] = (),
    shadow_projection_rows: Iterable[Mapping[str, str]] = (),
    activation_application_summary_rows: Iterable[Mapping[str, str]] = (),
    activation_value_delta_rows: Iterable[Mapping[str, str]] = (),
    target_benchmark_rows: Iterable[Mapping[str, str]] = (),
    input_artifacts: Mapping[str, object] | None = None,
) -> ReconciliationIndex:
    """Return deterministic reconciliation groups, representative cells, and summary."""

    reviews = [dict(row) for row in review_rows]
    cells = [dict(row) for row in cell_rows]
    matrices = [dict(row) for row in alignment_matrix_rows]
    seeds = [dict(row) for row in seed_audit_rows]
    overlays = [dict(row) for row in overlay_rows]
    shift_aware = [dict(row) for row in shift_aware_same_pattern_rows]
    standard_peak_gate = [dict(row) for row in shift_aware_standard_peak_gate_rows]
    seed_aware = [dict(row) for row in seed_aware_family_rows]
    seed_aware_summary = [dict(row) for row in seed_aware_summary_rows]
    candidates = [dict(row) for row in candidate_gate_rows]
    retained_gate = [dict(row) for row in retained_gate_rows]
    tier2 = [dict(row) for row in tier2_trace_evidence_rows]
    shadow_policy_cells = tuple(
        _shadow_policy_cell_from_row(row) for row in shadow_policy_rows
    )
    shadow_projection_cells = tuple(
        _shadow_projection_cell_from_row(row) for row in shadow_projection_rows
    )
    activation_application_summary = [
        dict(row) for row in activation_application_summary_rows
    ]
    activation_delta_cells = tuple(
        _activation_delta_cell_from_row(row) for row in activation_value_delta_rows
    )
    activated_projection_group_keys = _activation_written_projection_group_keys(
        shadow_projection_cells,
        activation_delta_cells,
    )
    current_written_projection_group_keys = (
        _current_matrix_written_projection_group_keys(shadow_projection_cells)
    )
    target_contexts = tuple(
        context
        for row in target_benchmark_rows
        if (context := _target_benchmark_context_from_row(row)) is not None
    )

    reviews_by_family = _first_by_family(reviews)
    cells_by_family = _group_by_family(cells)
    matrix_families = {text_value(row.get("feature_family_id")) for row in matrices}
    seed_records_by_family = _seed_records_by_family(seeds)
    seed_samples_by_family = _seed_samples_by_family(seeds)
    family_ids, excluded_family_counts = _candidate_family_ids(
        reviews=reviews,
        cells=cells,
        seeds=seeds,
        seed_aware=seed_aware,
        seed_aware_summary=seed_aware_summary,
        candidates=candidates,
    )
    cells_by_seed_group = _cells_by_family_seed_group(
        cells_by_family=cells_by_family,
        seed_records_by_family=seed_records_by_family,
        family_ids=family_ids,
    )
    overlay_rows_by_seed_group = _overlay_rows_by_family_seed_group(overlays)
    legacy_overlay_rows_by_family = _legacy_overlay_rows_by_family(overlays)
    shift_aware_by_family = _group_by_family(shift_aware)
    standard_peak_gate_by_family = _group_by_family(standard_peak_gate)
    seed_aware_by_family = _first_by_family(seed_aware)
    candidate_by_family = _first_by_family(candidates)
    retained_gate_by_group = _first_by_family_and_seed_group(retained_gate)
    source_hashes = _source_hashes_from_input_artifacts(input_artifacts or {})
    tier2_families = {
        text_value(row.get("feature_family_id"))
        for row in tier2
        if row.get("feature_family_id")
    }

    groups: list[ReconciliationGroup] = []
    representatives: list[RepresentativeCell] = []
    for family in sorted(family_ids):
        seed_records = seed_records_by_family.get(
            family,
            (_fallback_seed_record(family),),
        )
        sorted_seed_records = sorted(
            seed_records,
            key=lambda record: record.seed_group_id,
        )
        for seed_record in sorted_seed_records:
            review = reviews_by_family.get(family, {})
            family_cells = tuple(cells_by_family.get(family, ()))
            group_cells = cells_by_seed_group.get(
                (family, seed_record.seed_group_id),
                _cells_for_seed_record(family_cells, seed_record),
            )
            evidence = _classify_evidence(
                family=family,
                seed_record=seed_record,
                family_cells=family_cells,
                group_cells=group_cells,
                has_matrix_context=family in matrix_families,
                seed_samples=seed_samples_by_family.get(family, frozenset()),
                overlay_rows=overlay_rows_by_seed_group.get(
                    (family, seed_record.seed_group_id),
                    (),
                ),
                shift_aware_same_pattern_rows=shift_aware_by_family.get(
                    family,
                    (),
                ),
                shift_aware_standard_peak_gate_rows=(
                    standard_peak_gate_by_family.get(family, ())
                ),
                legacy_overlay_rows=legacy_overlay_rows_by_family.get(
                    family,
                    (),
                ),
                seed_aware_row=seed_aware_by_family.get(family, {}),
                candidate_gate_row=candidate_by_family.get(family, {}),
                retained_gate_row=retained_gate_by_group.get(
                    (family, seed_record.seed_group_id),
                    {},
                ),
                source_hashes=source_hashes,
                has_tier2_trace_evidence=family in tier2_families,
            )
            product_behavior = _product_behavior(review, family_cells)
            current_written_by_projection = (
                family,
                seed_record.seed_group_id,
            ) in current_written_projection_group_keys
            activated_by_delta = (
                family,
                seed_record.seed_group_id,
            ) in activated_projection_group_keys
            if current_written_by_projection or activated_by_delta:
                product_behavior = "product_primary_backfilled"
            product_reason = _top_product_reason(review)
            if activated_by_delta:
                product_reason = "activation_value_delta_written"
            elif current_written_by_projection:
                product_reason = "shadow_projection_current_matrix_written"
            source_artifacts = tuple(evidence["source_artifacts"])
            if current_written_by_projection or activated_by_delta:
                product_sources = ["shadow_production_projection_cells.tsv"]
                if activated_by_delta:
                    product_sources.extend(
                        (
                            "activation_application_summary.tsv",
                            "activation_value_delta.tsv",
                        ),
                    )
                source_artifacts = tuple(
                    _ordered_unique(
                        (
                            *source_artifacts,
                            *product_sources,
                        ),
                    ),
                )
            seed_count_cells = group_cells or family_cells
            representative_cells = _representative_cells_for_group(
                family=family,
                seed_group_id=seed_record.seed_group_id,
                product_behavior_state=product_behavior,
                evidence=evidence,
                group_cells=group_cells or family_cells,
                seed_record=seed_record,
            )
            group = ReconciliationGroup(
                feature_family_id=family,
                seed_group_id=seed_record.seed_group_id,
                seed_group_basis=seed_record.seed_group_basis,
                seed_mz=seed_record.seed_mz,
                seed_rt=seed_record.seed_rt,
                seed_rt_window=seed_record.seed_rt_window,
                seed_ppm=seed_record.ppm,
                tag_or_class=_tag_or_class(
                    review,
                    seed_aware_by_family.get(family, {}),
                ),
                product_behavior_state=product_behavior,
                evidence_authority_state=evidence["authority_state"],
                reconciliation_class=_reconciliation_class(
                    product_behavior,
                    evidence["authority_state"],
                    tuple(evidence["missing_evidence"]),
                    tuple(evidence["source_warnings"]),
                ),
                include_in_primary_matrix=bool_value(
                    review.get("include_in_primary_matrix"),
                )
                is True,
                identity_decision=text_value(review.get("identity_decision")),
                row_flags=text_value(review.get("row_flags")),
                family_evidence=text_value(review.get("family_evidence")),
                accepted_cell_count=_int_text(review.get("accepted_cell_count")),
                detected_cell_count=_count_cells(family_cells, "detected"),
                rescued_cell_count=_count_cells(seed_count_cells, "rescued"),
                provisional_cell_count=_count_provisional(seed_count_cells),
                seed_detected_anchor_count=_seed_detected_anchor_count(
                    family_cells,
                    seed_record=seed_record,
                    seed_records=sorted_seed_records,
                ),
                duplicate_assigned_cell_count=_count_cells(
                    family_cells,
                    "duplicate_assigned",
                ),
                cell_total_count=len(family_cells),
                top_product_reason=product_reason,
                top_support_component=_first_label(
                    evidence["product_grade_support_components"]
                    or evidence["review_only_visual_components"]
                    or evidence["dependent_context_components"],
                ),
                top_blocker=_first_label(evidence["blocker_components"]),
                missing_evidence=tuple(evidence["missing_evidence"]),
                overlay_png_path=text_value(evidence["overlay_png_path"]),
                overlay_trace_json_path=text_value(evidence["overlay_trace_json_path"]),
                family_pattern_png_path=text_value(evidence["family_pattern_png_path"]),
                family_pattern_trace_json_path=text_value(
                    evidence["family_pattern_trace_json_path"],
                ),
                family_pattern_verdict=text_value(evidence["family_pattern_verdict"]),
                overlay_evidence_notes=tuple(evidence["overlay_evidence_notes"]),
                source_artifacts=source_artifacts,
                source_warnings=tuple(evidence["source_warnings"]),
                product_grade_support_components=tuple(
                    evidence["product_grade_support_components"],
                ),
                review_only_visual_components=tuple(
                    evidence["review_only_visual_components"],
                ),
                dependent_context_components=tuple(evidence["dependent_context_components"]),
                blocker_components=tuple(evidence["blocker_components"]),
                representative_cells=representative_cells,
            )
            groups.append(group)
            representatives.extend(representative_cells)

    groups = sorted(groups, key=_group_sort_key)
    representatives = sorted(representatives, key=_representative_sort_key)
    summary = _summary(groups, representatives, input_artifacts or {})
    summary["excluded_family_counts"] = dict(excluded_family_counts)
    summary["shadow_policy_decision_counts"] = _shadow_policy_decision_counts(
        shadow_policy_cells,
    )
    summary["shadow_policy_production_gap_counts"] = (
        _shadow_policy_production_gap_counts(shadow_policy_cells)
    )
    summary["shadow_projection_decision_counts"] = (
        _shadow_projection_decision_counts(shadow_projection_cells)
    )
    summary["shadow_projection_matrix_counts"] = _shadow_projection_matrix_counts(
        shadow_projection_cells,
    )
    summary["activation_application_summary"] = _activation_application_summary(
        activation_application_summary,
    )
    summary["activation_value_delta_matrix_effect_counts"] = (
        _activation_value_delta_matrix_effect_counts(activation_delta_cells)
    )
    summary["activation_written_projection_group_count"] = len(
        activated_projection_group_keys,
    )
    summary["activation_written_projection_cell_count"] = (
        _activation_written_projection_cell_count(
            shadow_projection_cells,
            activation_delta_cells,
        )
    )
    summary["current_written_projection_group_count"] = len(
        current_written_projection_group_keys,
    )
    summary["current_written_projection_cell_count"] = (
        _current_matrix_written_projection_cell_count(shadow_projection_cells)
    )
    summary["activation_delta_view"] = (
        "activated_matrix"
        if activation_delta_cells
        else "not_supplied"
    )
    summary["product_behavior_changed"] = bool(
        activated_projection_group_keys or current_written_projection_group_keys,
    )
    product_behavior_sources: list[str] = []
    if current_written_projection_group_keys:
        product_behavior_sources.append("shadow_production_projection_cells.tsv")
    if activated_projection_group_keys:
        product_behavior_sources.append("activation_value_delta.tsv")
    summary["product_behavior_source"] = ";".join(product_behavior_sources)
    summary["target_benchmark_context_counts"] = _target_benchmark_context_counts(
        target_contexts,
    )
    return ReconciliationIndex(
        groups=tuple(groups),
        representative_cells=tuple(representatives),
        shadow_policy_cells=shadow_policy_cells,
        shadow_projection_cells=shadow_projection_cells,
        activation_delta_cells=activation_delta_cells,
        target_benchmark_contexts=target_contexts,
        summary=summary,
    )


def write_reconciliation_outputs(
    output_dir: Path,
    index: ReconciliationIndex,
) -> dict[str, Path]:
    """Write groups TSV, representative-cells TSV, and summary JSON."""

    output_dir.mkdir(parents=True, exist_ok=True)
    groups = sorted(index.groups, key=_group_sort_key)
    representatives = sorted(index.representative_cells, key=_representative_sort_key)
    group_rows = [
        _group_as_row(group, priority_rank=priority)
        for priority, group in enumerate(groups, start=1)
    ]
    representative_rows = [_representative_as_row(row) for row in representatives]
    summary = _summary(
        groups,
        representatives,
        _string_object_mapping(index.summary.get("input_artifacts")),
    )
    summary.update(
        {
            key: value
            for key, value in index.summary.items()
            if key not in {"group_count", "representative_cell_count"}
        },
    )
    if index.shadow_policy_cells:
        summary["shadow_policy_decision_counts"] = _shadow_policy_decision_counts(
            index.shadow_policy_cells,
        )
        summary["shadow_policy_production_gap_counts"] = (
            _shadow_policy_production_gap_counts(index.shadow_policy_cells)
        )
    if index.shadow_projection_cells:
        summary["shadow_projection_decision_counts"] = (
            _shadow_projection_decision_counts(index.shadow_projection_cells)
        )
        summary["shadow_projection_matrix_counts"] = (
            _shadow_projection_matrix_counts(index.shadow_projection_cells)
        )
    if index.activation_delta_cells:
        summary["activation_value_delta_matrix_effect_counts"] = (
            _activation_value_delta_matrix_effect_counts(index.activation_delta_cells)
        )
    if index.target_benchmark_contexts:
        summary["target_benchmark_context_counts"] = _target_benchmark_context_counts(
            index.target_benchmark_contexts,
        )
    summary["group_count"] = len(groups)
    summary["representative_cell_count"] = len(representatives)

    groups_tsv = output_dir / "backfill_evidence_reconciliation_groups.tsv"
    representative_cells_tsv = (
        output_dir / "backfill_evidence_reconciliation_representative_cells.tsv"
    )
    summary_json = output_dir / "backfill_evidence_reconciliation_summary.json"
    write_tsv(groups_tsv, group_rows, GROUP_TSV_COLUMNS, lineterminator="\n")
    write_tsv(
        representative_cells_tsv,
        representative_rows,
        REPRESENTATIVE_CELL_TSV_COLUMNS,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "groups_tsv": groups_tsv,
        "representative_cells_tsv": representative_cells_tsv,
        "summary_json": summary_json,
    }


def write_reconciliation_gallery_html(
    path: Path,
    index: ReconciliationIndex,
    *,
    output_paths: Mapping[str, Path],
) -> None:
    """Render a table-first human review gallery from a reconciliation index."""

    path.parent.mkdir(parents=True, exist_ok=True)
    local_interpretation_guide = _write_local_overlay_interpretation_guide(
        path.parent,
    )
    render_context = _gallery_render_context(index)
    gallery_title = _gallery_document_title(render_context.html_groups)
    hero = _gallery_hero_copy(render_context.html_groups)
    lines = [
        "<!doctype html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_escape(gallery_title)}</title>",
        "<style>",
        _gallery_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        '<header class="gallery-hero" aria-label="gallery introduction">',
        f'<div class="hero-kicker">{_escape(str(hero["kicker"]))}</div>',
        f"<h1>{_escape(str(hero['heading']))}</h1>",
        f'<p class="hero-copy">{_escape(str(hero["copy"]))}</p>',
        '<div class="hero-status-strip" aria-label="gallery role">',
        *[
            f"<span>{_escape(label)}</span>"
            for label in tuple(hero["status_labels"])
        ],
        "</div>",
        "</header>",
        *_summary_html(
            index,
            output_paths,
            html_path=path,
            local_interpretation_guide=local_interpretation_guide,
        ),
        *_html_scope_notice(render_context.all_groups, render_context.html_groups),
        *_filter_html(
            total_families=len(_family_groups(render_context.html_groups)),
            default_visible_families=_default_visible_family_count(
                render_context.html_groups,
            ),
            has_shadow_projection=bool(
                render_context.html_shadow_projection_cells,
            ),
        ),
    ]
    if not render_context.html_groups:
        lines.append(
            '<p class="empty-state">沒有 backfill family/seed group 可審閱。</p>',
        )
    else:
        lines.extend(
            _table_html(
                render_context.html_groups,
                representatives_by_group=render_context.representatives_by_group,
                shadow_policy_cells_by_group=(
                    render_context.shadow_policy_cells_by_group
                ),
                shadow_policy_cells_by_family=(
                    render_context.shadow_policy_cells_by_family
                ),
                shadow_projection_cells_by_group=(
                    render_context.shadow_projection_cells_by_group
                ),
                shadow_projection_cells_by_family=(
                    render_context.shadow_projection_cells_by_family
                ),
                target_benchmark_contexts_by_family=(
                    render_context.target_benchmark_contexts_by_family
                ),
                html_path=path,
                input_artifacts=index.summary.get("input_artifacts", {}),
            ),
        )
        lines.extend(_lightbox_html())
    lines.extend(["</main>", _lightbox_script(), "</body>", "</html>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _gallery_document_title(groups: Sequence[ReconciliationGroup]) -> str:
    if _is_cid_nl_successor_review_index(groups):
        return "Evidence Review Gallery - CID-NL Feature Inclusion Review"
    return "Backfill evidence reconciliation gallery"


def _gallery_hero_copy(
    groups: Sequence[ReconciliationGroup],
) -> dict[str, str | tuple[str, ...]]:
    if _is_cid_nl_successor_review_index(groups):
        return {
            "kicker": "Evidence review surface",
            "heading": "CID-NL Feature Inclusion / Identity Review",
            "copy": (
                "CID-NL/MS2 evidence, MS1 feature context, source/successor "
                "identity relationships, representative cells, and adoption "
                "candidate decisions are shown here without granting "
                "ProductWriter authority."
            ),
            "status_labels": (
                "feature inclusion first",
                "identity authority separate",
                "MS1 trace context only",
                "does not write matrix",
            ),
        }
    return {
        "kicker": "Matrix-decision audit surface",
        "heading": "Backfill Evidence Reconciliation",
        "copy": (
            "Production decisions, same-peak evidence, missing artifacts, "
            "and review-only context are reconciled here without recalculating "
            "domain evidence."
        ),
        "status_labels": (
            "artifact consumer only",
            "does not write matrix",
            "hypothesis first",
            "human review ready",
        ),
    }


























def _representative_cells_for_group(
    *,
    family: str,
    seed_group_id: str,
    product_behavior_state: str,
    evidence: Mapping[str, Any],
    group_cells: Sequence[Mapping[str, str]],
    seed_record: _SeedRecord,
) -> tuple[RepresentativeCell, ...]:
    rescued = [
        row for row in group_cells if text_value(row.get("status")).lower() == "rescued"
    ]
    if not rescued:
        return ()
    by_key: dict[str, RepresentativeCell] = {}

    def add(role: str, row: Mapping[str, str], reason: str) -> None:
        key = _source_row_key(family, row)
        existing = by_key.get(key)
        roles = (
            (role,)
            if existing is None
            else _ordered_unique((*existing.representative_roles, role))
        )
        by_key[key] = RepresentativeCell(
            feature_family_id=family,
            seed_group_id=seed_group_id,
            representative_roles=tuple(roles),
            sample_stem=text_value(row.get("sample_stem")),
            cell_status=text_value(row.get("status")),
            product_cell_state=_product_cell_state(row, product_behavior_state),
            shape_similarity=text_value(row.get("shape_similarity")),
            scan_support_score=text_value(row.get("scan_support_score")),
            apex_delta_sec=_apex_delta_sec(row, seed_record),
            boundary_overlap=text_value(row.get("boundary_overlap")),
            interference_signal=text_value(
                row.get("interference_signal")
                or row.get("neighbor_interference")
                or row.get("trace_quality"),
            ),
            representative_reason=reason,
            source_row_key=key,
        )

    support_row = max(
        rescued,
        key=lambda row: (
            optional_float(row.get("shape_similarity")) or -1.0,
            optional_float(row.get("scan_support_score")) or -1.0,
            text_value(row.get("sample_stem")),
        ),
    )
    add("strongest_support", support_row, "highest existing support metric")
    seed_row = min(
        rescued,
        key=lambda row: (
            abs(optional_float(_apex_delta_sec(row, seed_record)) or 999999.0),
            text_value(row.get("sample_stem")),
        ),
    )
    add("seed_representative", seed_row, "seed/request representative")
    if evidence.get("blocker_components"):
        add("strongest_blocker", rescued[0], "existing blocker component")
    if evidence.get("authority_state") in {
        "product_grade_support",
        "review_only_visual_support",
        "evidence_blocks_backfill",
    }:
        add("product_disagreement_example", rescued[0], "product/evidence example")
    return tuple(sorted(by_key.values(), key=_representative_sort_key))


def _group_as_row(group: ReconciliationGroup, *, priority_rank: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "priority_rank": priority_rank,
        "feature_family_id": group.feature_family_id,
        "seed_group_id": group.seed_group_id,
        "seed_group_basis": group.seed_group_basis,
        "seed_mz": group.seed_mz,
        "seed_rt": group.seed_rt,
        "seed_rt_window": group.seed_rt_window,
        "seed_ppm": group.seed_ppm,
        "tag_or_class": group.tag_or_class,
        "product_behavior_state": group.product_behavior_state,
        "evidence_authority_state": group.evidence_authority_state,
        "reconciliation_class": group.reconciliation_class,
        "detected_cell_count": group.detected_cell_count,
        "rescued_cell_count": group.rescued_cell_count,
        "provisional_cell_count": group.provisional_cell_count,
        "top_product_reason": group.top_product_reason,
        "top_support_component": group.top_support_component,
        "top_blocker": group.top_blocker,
        "missing_evidence": ";".join(group.missing_evidence),
        "overlay_png_path": group.overlay_png_path,
        "overlay_trace_json_path": group.overlay_trace_json_path,
        "source_artifacts": ";".join(group.source_artifacts),
        "source_warnings": ";".join(group.source_warnings),
    }


def _representative_as_row(cell: RepresentativeCell) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "feature_family_id": cell.feature_family_id,
        "seed_group_id": cell.seed_group_id,
        "representative_roles": ";".join(cell.representative_roles),
        "sample_stem": cell.sample_stem,
        "cell_status": cell.cell_status,
        "product_cell_state": cell.product_cell_state,
        "shape_similarity": cell.shape_similarity,
        "scan_support_score": cell.scan_support_score,
        "apex_delta_sec": cell.apex_delta_sec,
        "boundary_overlap": cell.boundary_overlap,
        "interference_signal": cell.interference_signal,
        "representative_reason": cell.representative_reason,
        "source_row_key": cell.source_row_key,
    }


def _summary(
    groups: Sequence[ReconciliationGroup],
    representatives: Sequence[RepresentativeCell],
    input_artifacts: Mapping[str, object],
) -> dict[str, object]:
    reconciliation_counts = Counter(group.reconciliation_class for group in groups)
    missing_counts: Counter[str] = Counter()
    for group in groups:
        missing_counts.update(
            set(group.missing_evidence)
            | {
                token
                for token in group.source_warnings
                if token.startswith(("join_gap_", "stale_"))
            },
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_label": "diagnostic_only",
        "group_count": len(groups),
        "representative_cell_count": len(representatives),
        "reconciliation_class_counts": dict(sorted(reconciliation_counts.items())),
        "missing_evidence_counts": dict(sorted(missing_counts.items())),
        "excluded_family_counts": {},
        "input_artifacts": dict(input_artifacts),
        "matrix_contract_changed": False,
        "product_behavior_changed": False,
    }


def _string_object_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {text_value(key): item for key, item in value.items() if text_value(key)}


def _string_int_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        text_key = text_value(key)
        if not text_key:
            continue
        result[text_key] = _int_text(item)
    return result


def _activation_summary_text(summary: Mapping[str, object]) -> str:
    if text_value(summary.get("activation_delta_view")) == "not_supplied":
        return "not supplied"
    effect_counts = _string_int_mapping(
        summary.get("activation_value_delta_matrix_effect_counts"),
    )
    written = effect_counts.get("written", 0)
    groups = _int_text(summary.get("activation_written_projection_group_count"))
    cells = _int_text(summary.get("activation_written_projection_cell_count"))
    return f"written {written} · groups {groups} · cells {cells}"


def _current_rescue_summary_text(summary: Mapping[str, object]) -> str:
    if not summary.get("shadow_projection_matrix_counts"):
        return "not supplied"
    groups = _int_text(summary.get("current_written_projection_group_count"))
    cells = _int_text(summary.get("current_written_projection_cell_count"))
    return f"written {cells} · groups {groups}"


def _summary_html(
    index: ReconciliationIndex,
    output_paths: Mapping[str, Path],
    *,
    html_path: Path,
    local_interpretation_guide: Path | None,
) -> list[str]:
    summary = _summary(
        index.groups,
        index.representative_cells,
        _string_object_mapping(index.summary.get("input_artifacts")),
    )
    summary.update(index.summary)
    missing_counts = summary["missing_evidence_counts"]
    category_counts = _review_category_counts(index.groups)
    excluded_counts = summary.get("excluded_family_counts", {})
    target_context_counts = _string_int_mapping(
        summary.get("target_benchmark_context_counts"),
    )
    validation_label = text_value(summary.get("validation_label")) or "diagnostic_only"
    return [
        '<section class="summary" aria-label="reconciliation summary">',
        _decision_legend_html(),
        _interpretation_guide_callout_html(
            summary,
            html_path=html_path,
            local_interpretation_guide=local_interpretation_guide,
        ),
        _summary_item("validation", "Validation", validation_label),
        _summary_item("groups", "Groups", str(summary["group_count"])),
        _summary_item(
            "families",
            "Families",
            str(len({group.feature_family_id for group in index.groups})),
        ),
        _summary_item(
            "representatives",
            "Representative cells",
            str(summary["representative_cell_count"]),
        ),
        _summary_item(
            "missing-overlay",
            "Missing overlay",
            str(_count_token_prefix(missing_counts, "missing_overlay")),
        ),
        _summary_item(
            "missing-seed",
            "Missing seed provenance",
            str(_count_token_prefix(missing_counts, "missing_seed_provenance")),
        ),
        _summary_item(
            "excluded-detected-zero",
            "Excluded detected=0",
            str(_count_token_prefix(excluded_counts, "detected_zero_family")),
        ),
        _summary_item(
            "classes",
            "Review focus",
            (
                " · ".join(
                    f"{_REVIEW_CATEGORY_SUMMARY_LABELS.get(key, key)} {value}"
                    for key, value in category_counts.items()
                )
                or "none"
            ),
        ),
        _summary_item(
            "target-benchmark",
            "Target benchmark",
            _target_benchmark_summary_text(
                index.target_benchmark_contexts,
                target_context_counts,
                summary.get("input_artifacts"),
            ),
        ),
        _summary_item(
            "current-rescue",
            "Current rescue writes",
            _current_rescue_summary_text(summary),
        ),
        _summary_item(
            "activation-delta",
            "Activated writes",
            _activation_summary_text(summary),
        ),
        *_artifact_links(output_paths, html_path=html_path),
        *_target_benchmark_panel_html(
            index.target_benchmark_contexts,
            summary.get("input_artifacts"),
            target_context_counts,
        ),
        (
            '<p class="authority-note">這個 gallery 只消費既有 artifact；'
            "不會修改 alignment matrix、cells、review TSV、workbooks "
            "或 product decisions。"
            "</p>"
        ),
        *_input_artifact_links(
            _string_object_mapping(summary.get("input_artifacts")),
            html_path=html_path,
        ),
        "</section>",
    ]


def _decision_legend_html() -> str:
    items = (
        (
            "matrix written",
            "Final matrix value",
            "Only this wording means the cell is written to the delivered matrix.",
        ),
        (
            "candidate only",
            "Evidence candidate",
            "Candidate counts are review/provenance cells, not matrix writes.",
        ),
        (
            "not written + blocks",
            "Blocked or rejected",
            "The evidence chain says to leave the value out unless policy changes.",
        ),
    )
    rows = "".join(
        '<div class="decision-legend-item">'
        f'<span class="decision-token">{_escape(token)}</span>'
        f"<strong>{_escape(title)}</strong>"
        f"<p>{_escape(copy)}</p>"
        "</div>"
        for token, title, copy in items
    )
    return (
        '<div class="decision-legend" aria-label="decision wording guide">'
        '<div class="decision-legend-heading">'
        "<span>Read first</span>"
        "<strong>Candidate is not a matrix write.</strong>"
        "</div>"
        f"{rows}"
        "</div>"
    )


def _summary_item(css_class: str, label: str, value: str) -> str:
    return (
        f'<div class="summary-item {css_class}">'
        f"<span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"
    )


def _filter_html(
    *,
    total_families: int,
    default_visible_families: int,
    has_shadow_projection: bool,
) -> list[str]:
    labels = dict(_REVIEW_FILTER_LABELS)
    if not has_shadow_projection:
        labels.pop("projection_accepts", None)
    return [
        '<section class="filters" aria-label="table filters">',
        '<label for="categoryFilter">Focus</label>',
        '<select id="categoryFilter" data-filter-control>',
        *[
            (
                f'<option value="{_escape_attr(value)}"'
                f'{" selected" if value == _DEFAULT_FILTER_CATEGORY else ""}>'
                f"{_escape(label)}</option>"
            )
            for value, label in labels.items()
        ],
        '<option value="">All rows</option>',
        "</select>",
        '<label for="searchBox">Search</label>',
        '<input id="searchBox" type="search" data-search-control '
        'aria-label="Search family, seed group, support, blocker">',
        (
            '<span class="result-count" data-result-count '
            f'data-total-families="{total_families}">'
            f"顯示 {default_visible_families} / {total_families} families</span>"
        ),
        "</section>",
    ]


def _table_html(
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[
        str,
        tuple[ShadowProjectionCell, ...],
    ],
    target_benchmark_contexts_by_family: Mapping[
        str,
        tuple[TargetBenchmarkContext, ...],
    ],
    html_path: Path,
    input_artifacts: object,
) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="review-table" aria-describedby="galleryTableDescription">',
        '<caption id="galleryTableDescription">'
        "Hypothesis-first backfill evidence review queue. "
        "Family rows are compact MS1 pattern context headers."
        "</caption>",
        "<colgroup>",
        '<col class="col-priority">',
        '<col class="col-family">',
        '<col class="col-state">',
        '<col class="col-issue">',
        '<col class="col-counts">',
        '<col class="col-overlay">',
        '<col class="col-details">',
        "</colgroup>",
        "<thead>",
        "<tr>",
        '<th scope="col">rank</th>',
        '<th scope="col">family / hypothesis</th>',
        '<th scope="col">state</th>',
        '<th scope="col">issue</th>',
        (
            '<th scope="col"><span title="Cell-level impact. With shadow '
            "projection input: Current=current production decision writes, "
            "Review=projection candidate pool, Write=new projected matrix "
            "writes, Block=projected hard blockers. Without projection "
            "input: NL/Candidate/Dup/Review remain alignment provenance counts, "
            'not matrix-written counts or target benchmark coverage.">'
            "impact</span></th>"
        ),
        '<th scope="col">overlay</th>',
        '<th scope="col">chain</th>',
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for priority, family_groups in enumerate(_family_groups(groups), start=1):
        lines.extend(
            _family_table_row(
                priority,
                family_groups,
                representatives_by_group=representatives_by_group,
                shadow_policy_cells_by_group=shadow_policy_cells_by_group,
                shadow_policy_cells_by_family=shadow_policy_cells_by_family,
                shadow_projection_cells_by_group=shadow_projection_cells_by_group,
                shadow_projection_cells_by_family=shadow_projection_cells_by_family,
                target_benchmark_contexts=target_benchmark_contexts_by_family.get(
                    family_groups[0].feature_family_id,
                    (),
                ),
                html_path=html_path,
                input_artifacts=input_artifacts,
            ),
        )
    lines.extend(["</tbody>", "</table>", "</div>"])
    return lines


def _family_groups(
    groups: Sequence[ReconciliationGroup],
) -> tuple[tuple[ReconciliationGroup, ...], ...]:
    grouped: dict[str, list[ReconciliationGroup]] = {}
    for group in sorted(groups, key=_group_sort_key):
        grouped.setdefault(group.feature_family_id, []).append(group)
    return tuple(
        tuple(items)
        for _, items in sorted(
            grouped.items(),
            key=lambda item: _family_sort_key(tuple(item[1])),
        )
    )


def _family_sort_key(groups: tuple[ReconciliationGroup, ...]) -> tuple[int, str, str]:
    primary = sorted(groups, key=_group_sort_key)[0]
    return _group_sort_key(primary)


def _default_visible_family_count(groups: Sequence[ReconciliationGroup]) -> int:
    return sum(
        1
        for family_groups in _family_groups(groups)
        if _DEFAULT_FILTER_CATEGORY in _family_filter_categories(family_groups)
    )


def _review_category(reconciliation_class: str) -> str:
    return _REVIEW_CATEGORY_BY_CLASS.get(reconciliation_class, "needs_review")


def _family_filter_categories(
    groups: Sequence[ReconciliationGroup],
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> tuple[str, ...]:
    categories: list[str] = []
    for group in groups:
        categories.extend(_group_filter_categories(group))
    categories.extend(_shadow_projection_filter_categories(shadow_projection_cells))
    return tuple(_ordered_unique(categories))


def _group_filter_categories(group: ReconciliationGroup) -> tuple[str, ...]:
    category = _review_category(group.reconciliation_class)
    if _debug_only_group(group):
        return (category, "debug_rows")
    return (category, "product_rows")


def _debug_only_group(group: ReconciliationGroup) -> bool:
    flags = group.row_flags.lower()
    identity = group.identity_decision.lower()
    if group.include_in_primary_matrix:
        return False
    return (
        "family_consolidation_loser" in flags
        or "duplicate_only" in flags
        or (
            "audit_family" in identity
            and group.duplicate_assigned_cell_count > 0
            and group.accepted_cell_count == 0
        )
    )


def _shadow_projection_filter_categories(
    cells: Sequence[ShadowProjectionCell],
) -> tuple[str, ...]:
    if any(_is_projected_new_accept(cell) for cell in cells):
        return ("projection_accepts",)
    return ()




def _review_category_counts(
    groups: Sequence[ReconciliationGroup],
) -> dict[str, int]:
    counts: Counter[str] = Counter(
        _review_category(group.reconciliation_class) for group in groups
    )
    return {
        key: counts[key]
        for key in _REVIEW_CATEGORY_LABELS
        if counts[key]
    }


def _family_seed_summary(groups: Sequence[ReconciliationGroup]) -> str:
    seed_count = len(groups)
    seed_label = "1 seed" if seed_count == 1 else f"{seed_count} seeds"
    mz = _compact_value_range(group.seed_mz for group in groups)
    rt = _compact_value_range(group.seed_rt for group in groups)
    return f"{seed_label} · m/z {mz} · RT {rt}"


def _family_window_summary(groups: Sequence[ReconciliationGroup]) -> str:
    windows = _compact_text_values(group.seed_rt_window for group in groups)
    if not windows:
        return "window unknown"
    window = windows[0] if len(windows) == 1 else f"{len(windows)} windows"
    return f"window {window}"


def _compact_value_range(values: Iterable[str]) -> str:
    unique = _compact_text_values(values)
    if not unique:
        return "unknown"
    if len(unique) == 1:
        return unique[0]
    numeric = [optional_float(value) for value in unique]
    if all(value is not None for value in numeric):
        finite = [value for value in numeric if value is not None]
        return f"{min(finite):.6g}-{max(finite):.6g}"
    return f"{unique[0]}-{unique[-1]}"


def _compact_text_values(values: Iterable[str]) -> tuple[str, ...]:
    return _ordered_unique(text_value(value) for value in values if text_value(value))


def _family_tag_html(groups: Sequence[ReconciliationGroup]) -> str:
    tags = _compact_text_values(group.tag_or_class for group in groups)
    pieces = [
        "1 seed group" if len(groups) == 1 else f"{len(groups)} seed groups",
    ]
    if tags:
        pieces.append("class=" + "/".join(tags))
    return f'<span class="family-meta">{_escape(" · ".join(pieces))}</span>'


def _family_detail_summary(
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells: Sequence[ShadowPolicyCell] = (),
) -> str:
    representative_count = sum(
        len(
            representatives_by_group.get(
                (group.feature_family_id, group.seed_group_id),
                (),
            ),
        )
        for group in groups
    )
    seed_label = "1 seed" if len(groups) == 1 else f"{len(groups)} seeds"
    rep_label = "1 rep" if representative_count == 1 else f"{representative_count} reps"
    shadow = _shadow_policy_compact_summary(shadow_policy_cells)
    if shadow:
        return f"{seed_label} · {rep_label} · {shadow}"
    return f"{seed_label} · {rep_label}"


def _top_issue_html(group: ReconciliationGroup) -> str:
    support = text_value(group.top_support_component)
    blocker = text_value(group.top_blocker)
    missing = "; ".join((*group.missing_evidence, *group.source_warnings))
    detail = blocker or missing or support or group.top_product_reason or "no top issue"
    detail_class = (
        "blocker" if blocker or missing else "support" if support else "context"
    )
    return (
        '<div class="top-issue">'
        f"{_badge(group.reconciliation_class)}"
        f'<span class="issue-text {detail_class}" '
        f'title="{_escape_attr(_compact_issue_label(detail))}">'
        f"{_escape(_compact_issue_label(detail))}</span>"
        "</div>"
    )


def _state_html(group: ReconciliationGroup) -> str:
    return _state_html_for_shadow(group, ())


def _state_aria_label(
    group: ReconciliationGroup,
    shadow_summary: str,
    projection_summary: str,
) -> str:
    product = _badge_label(group.product_behavior_state)
    if group.product_behavior_state == "product_rescued_context_only":
        product = "candidate only, not matrix written"
    elif group.product_behavior_state == "product_not_backfilled":
        product = "not matrix written"
    evidence = _badge_label(group.evidence_authority_state)
    parts = [f"Product: {product}", f"Evidence: {evidence}"]
    if shadow_summary:
        parts.append(f"Shadow: {shadow_summary}")
    if projection_summary:
        parts.append(f"Projection: {projection_summary}")
    return "; ".join(parts)


def _state_html_for_shadow(
    group: ReconciliationGroup,
    shadow_policy_cells: Sequence[ShadowPolicyCell],
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    shadow_summary = _shadow_policy_compact_summary(shadow_policy_cells)
    projection_summary = _shadow_projection_compact_summary(shadow_projection_cells)
    shadow_state_key = "Legacy" if projection_summary else "Shadow"
    shadow_state_label = _shadow_policy_state_label(
        shadow_summary,
        projection_summary,
    )
    shadow_html = (
        '<div class="state-line shadow-line">'
        f'<span class="state-key">{shadow_state_key}</span>'
        f'<span class="shadow-pill">{_escape(shadow_state_label)}</span>'
        "</div>"
        if shadow_summary
        else ""
    )
    projection_html = (
        '<div class="state-line projection-line">'
        '<span class="state-key">Projection</span>'
        f'<span class="shadow-pill">{_escape(projection_summary)}</span>'
        "</div>"
        if projection_summary
        else ""
    )
    aria_label = _state_aria_label(group, shadow_summary, projection_summary)
    return (
        f'<div class="state-stack" aria-label="{_escape_attr(aria_label)}">'
        '<div class="state-line">'
        '<span class="state-key">Product</span>'
        f"{_badge(group.product_behavior_state)}"
        "</div>"
        '<div class="state-line">'
        '<span class="state-key">Evidence</span>'
        f"{_badge(group.evidence_authority_state)}"
        "</div>"
        f"{shadow_html}"
        f"{projection_html}"
        "</div>"
    )


def _counts_html(
    group: ReconciliationGroup,
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    if shadow_projection_cells:
        return _projection_counts_html(group, shadow_projection_cells)
    if _is_cid_nl_successor_review_group(group):
        return _cid_nl_successor_counts_html(group)
    return _impact_counts_html(
        detected=group.detected_cell_count,
        rescued=group.rescued_cell_count,
        duplicate=group.duplicate_assigned_cell_count,
        provisional=group.provisional_cell_count,
        aria_label=(
            "NL anchors are family detected required-tag anchors; "
            "Candidate-only is hypothesis candidate cells, not matrix-written; "
            "Dup is family duplicate-assigned cell context; "
            "Review is hypothesis provisional cell context. "
            "These are alignment cell provenance counts, not target benchmark coverage."
        ),
    )


def _cid_nl_successor_counts_html(group: ReconciliationGroup) -> str:
    items = [
        _count_pill(
            "Candidate",
            "successor MS1-backed feature-inclusion candidate cells; "
            "not active matrix writes",
            group.rescued_cell_count,
        ),
        _count_pill(
            "Existing",
            "cells where the successor feature already has a detected baseline value",
            group.detected_cell_count,
        ),
    ]
    if group.provisional_cell_count:
        items.append(
            _count_pill(
                "Omit",
                "legacy cells omitted because no safe successor write target exists",
                group.provisional_cell_count,
            ),
        )
    return (
        '<dl class="count-stack cid-nl-successor-counts" '
        'aria-label="CID-NL feature-inclusion review counts. '
        'Candidate is successor MS1 feature-inclusion candidate cells; Existing '
        'is detected-baseline successor feature context; Omit is no safe '
        'successor target. These are not NL-tag coverage counts and are not '
        'active matrix writes.">'
        f"{''.join(items)}"
        "</dl>"
    )


def _projection_counts_html(
    group: ReconciliationGroup,
    cells: Sequence[ShadowProjectionCell],
) -> str:
    del group
    return _projection_impact_counts_html(
        current=sum(cell.current_matrix_written for cell in cells),
        review=sum(cell.review_rescued_cell for cell in cells),
        accept=sum(
            cell.shadow_decision == "accept" and cell.projected_matrix_written
            for cell in cells
        ),
        block=sum(cell.shadow_decision == "block" for cell in cells),
        aria_label=(
            "Shadow production projection impact. Current is cells already "
            "written by the production-decision snapshot; Review is the "
            "projection candidate pool; Write is new projected matrix writes; "
            "Block is hard projection blockers."
        ),
    )


def _projection_impact_counts_html(
    *,
    current: int,
    review: int,
    accept: int,
    block: int,
    aria_label: str,
) -> str:
    items = [
        _count_pill("Current", "already written in the production snapshot", current),
        _count_pill(
            "Review",
            "projection candidate pool; final status is Current, Write, or Block",
            review,
        ),
        _count_pill("Write", "new matrix cells authorized by this projection", accept),
        _count_pill("Block", "shadow hard-blocked cells", block),
    ]
    return (
        '<dl class="count-stack projection-counts" '
        f'aria-label="{_escape_attr(aria_label)}">'
        f"{''.join(items)}"
        "</dl>"
    )


def _impact_counts_html(
    *,
    detected: int,
    rescued: int,
    duplicate: int,
    provisional: int,
    aria_label: str,
) -> str:
    items = [
        _count_pill("NL", "family detected required-tag anchors", detected),
        _count_pill(
            "Candidate-only",
            "hypothesis candidate-only cells; not matrix-written",
            rescued,
        ),
    ]
    if duplicate:
        items.append(_count_pill("Dup", "family duplicate-assigned cells", duplicate))
    if provisional:
        items.append(_count_pill("Review", "hypothesis provisional cells", provisional))
    return (
        '<dl class="count-stack" '
        f'aria-label="{_escape_attr(aria_label)}">'
        f"{''.join(items)}"
        "</dl>"
    )


def _count_pill(label: str, title: str, value: int) -> str:
    return (
        f'<div title="{_escape_attr(title)}">'
        f"<dt>{_escape(label)}</dt><dd>{value}</dd></div>"
    )


def _compact_issue_label(value: str) -> str:
    text = text_value(value)
    replacements = {
        "seed_request_provenance": "seed provenance",
        "review_required_neighboring_ms1_interference": "neighboring MS1 review",
        "review_required_interference": "interference review",
        "evidence_inconclusive": "inconclusive",
        "machine_support_no_overlay": "machine support, no overlay",
        "track_machine_supported_backfill": "track machine-supported candidate",
        "ms1_shape_supports_family_backfill": (
            "MS1 shape supports same-peak candidate"
        ),
        "primary_identity_retained_backfill_review_only": (
            "primary identity retained; candidate only"
        ),
        "product_authorized_same_peak_backfill": "same-peak policy would write",
        "backfill_ms1_pattern_blocked": "MS1 pattern blocks matrix write",
        "review_only": "review only",
        "high_detected_anchor_low_rescue_machine_support": (
            "high detected anchors, low candidate load"
        ),
        "overlay_not_required_machine_supported": "overlay not required",
        "seed_specific_overlay_not_required_machine_supported": (
            "seed overlay not required"
        ),
        "product_accepts_and_visual_supports": "matrix + visual support",
        "product_rejects_but_visual_supports": "not written + visual support",
        "product_accepts_but_evidence_conflicts": "matrix + evidence conflict",
        "product_rejects_and_evidence_blocks": "not written + blocks",
        "product_primary_backfilled": "matrix written",
        "product_rescued_context_only": "candidate only",
        "product_not_backfilled": "not written",
        "candidate_context": "candidate only",
        "rescued": "candidate",
        "review_rescue": "review candidate",
        "gap_fill_rescued": "candidate",
        "not_assessable_missing_overlay": "missing overlay",
        "not_assessable_missing_seed_provenance": "missing seed provenance",
        "not_assessable_join_gap": "join gap",
    }
    if text in replacements:
        return replacements[text]
    return text.replace("_", " ")


def _compact_product_reason(value: str) -> str:
    return _compact_issue_label(value) or "no product reason supplied"


def _family_table_row(
    priority: int,
    family_groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[
        str,
        tuple[ShadowProjectionCell, ...],
    ],
    target_benchmark_contexts: Sequence[TargetBenchmarkContext],
    html_path: Path,
    input_artifacts: object,
) -> list[str]:
    ordered_groups = tuple(sorted(family_groups, key=_group_sort_key))
    group = ordered_groups[0]
    family_projection_cells = _shadow_projection_cells_for_family_groups(
        ordered_groups,
        shadow_projection_cells_by_group=shadow_projection_cells_by_group,
        shadow_projection_cells_by_family=shadow_projection_cells_by_family,
    )
    classes = " ".join(
        _ordered_unique(row.reconciliation_class for row in ordered_groups),
    )
    categories = " ".join(
        _family_filter_categories(ordered_groups, family_projection_cells),
    )
    search_blob = _escape_attr(
        _family_search_blob(
            ordered_groups,
            target_benchmark_contexts,
            family_projection_cells,
        ),
    )
    row = [
        (
            '<tr class="family-section-row" data-family-row '
            f'data-family="{_escape_attr(group.feature_family_id)}" '
            f'data-class="{_escape_attr(classes)}" '
            f'data-category="{_escape_attr(categories)}" '
            f'data-search="{search_blob}">'
        ),
        f'<td class="cell-priority" data-label="rank">{priority}</td>',
        (
            '<th class="cell-family family-context-cell" scope="row" '
            'colspan="4" data-label="family / hypothesis">'
            f'<span class="family-id">{_escape(group.feature_family_id)}</span>'
            f"{_family_tag_html(ordered_groups)}"
            f"{_family_anchor_summary_html(ordered_groups)}"
            f"{_family_target_summary_html(target_benchmark_contexts)}"
            f"{_family_pattern_status_html(ordered_groups)}"
            "</th>"
        ),
        (
            '<td class="cell-overlay" data-label="overlay">'
            f"{_family_pattern_link_html(ordered_groups, html_path, input_artifacts)}"
            "</td>"
        ),
        '<td class="cell-details" data-label="chain">',
        "</td>",
        "</tr>",
    ]
    href_counts, first_index_by_href = _overlay_href_context(ordered_groups, html_path)
    if _consolidated_seed_alias_family(ordered_groups):
        row.extend(
            _consolidated_seed_alias_rows(
                priority,
                ordered_groups,
                representatives_by_group=representatives_by_group,
                shadow_policy_cells_by_group=shadow_policy_cells_by_group,
                shadow_policy_cells_by_family=shadow_policy_cells_by_family,
                shadow_projection_cells_by_group=shadow_projection_cells_by_group,
                shadow_projection_cells_by_family=shadow_projection_cells_by_family,
                target_benchmark_contexts=target_benchmark_contexts,
                html_path=html_path,
                input_artifacts=input_artifacts,
                href_counts=href_counts,
                first_index_by_href=first_index_by_href,
            )
        )
        return row
    for index, seed_group in enumerate(ordered_groups, start=1):
        row.extend(
            _seed_decision_rows(
                priority,
                index,
                seed_group,
                representatives_by_group=representatives_by_group,
                shadow_policy_cells_by_group=shadow_policy_cells_by_group,
                shadow_policy_cells_by_family=shadow_policy_cells_by_family,
                shadow_projection_cells_by_group=shadow_projection_cells_by_group,
                shadow_projection_cells_by_family=shadow_projection_cells_by_family,
                target_benchmark_contexts=target_benchmark_contexts,
                html_path=html_path,
                input_artifacts=input_artifacts,
                href_counts=href_counts,
                first_index_by_href=first_index_by_href,
                total_seed_groups=len(ordered_groups),
            )
        )
    return row


def _consolidated_seed_alias_rows(
    priority: int,
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[
        str,
        tuple[ShadowProjectionCell, ...],
    ],
    target_benchmark_contexts: Sequence[TargetBenchmarkContext],
    html_path: Path,
    input_artifacts: object,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
) -> list[str]:
    base = groups[0]
    detail_id = _detail_row_id(f"{base.feature_family_id}-hypothesis", priority)
    shadow_cells = _shadow_policy_cells_for_family_groups(
        groups,
        shadow_policy_cells_by_group=shadow_policy_cells_by_group,
        shadow_policy_cells_by_family=shadow_policy_cells_by_family,
    )
    projection_cells = _shadow_projection_cells_for_family_groups(
        groups,
        shadow_projection_cells_by_group=shadow_projection_cells_by_group,
        shadow_projection_cells_by_family=shadow_projection_cells_by_family,
    )
    representatives = _representatives_for_groups(groups, representatives_by_group)
    category = " ".join(_family_filter_categories(groups, projection_cells))
    search_blob = _family_search_blob(groups, (), projection_cells)
    return [
        (
            '<tr class="seed-decision-row consolidated-seed-row" '
            f'data-family-section="{_escape_attr(base.feature_family_id)}" '
            f'data-class="{_escape_attr(base.reconciliation_class)}" '
            f'data-category="{_escape_attr(category)}" '
            f'data-detail-row="{_escape_attr(detail_id)}" '
            f'data-search="{_escape_attr(search_blob)}">'
        ),
        (
            '<td class="cell-priority seed-rank" data-label="rank">'
            f"{priority}.1</td>"
        ),
        (
            '<th class="cell-family seed-cell" scope="row" '
            'data-label="family / hypothesis">'
            f'<span class="seed-summary">m/z {_escape(_seed_mz_range(groups))} '
            f'· RT {_escape(_seed_rt_range(groups))}</span>'
            f'<span class="seed-window">window '
            f'{_escape(_seed_window_range(groups))}</span>'
            "</th>"
        ),
        (
            '<td class="cell-state" data-label="state">'
            f"{_state_html_for_shadow(base, shadow_cells, projection_cells)}</td>"
        ),
        (
            '<td class="cell-issue" data-label="issue">'
            f"{_top_issue_html(base)}</td>"
        ),
        (
            '<td class="cell-counts" data-label="impact">'
            f"{_consolidated_counts_html(groups, projection_cells)}"
            "</td>"
        ),
        (
            '<td class="cell-overlay" data-label="overlay">'
            + _consolidated_overlay_cell_html(
                groups,
                html_path=html_path,
                input_artifacts=input_artifacts,
                href_counts=href_counts,
                first_index_by_href=first_index_by_href,
            )
            + "</td>"
        ),
        '<td class="cell-details" data-label="chain">',
        (
            '<button type="button" class="detail-toggle" '
            'aria-expanded="false" '
            f'aria-controls="{_escape_attr(detail_id)}" '
            f'data-detail-toggle="{_escape_attr(detail_id)}">Open</button>'
        ),
        "</td>",
        "</tr>",
        (
            f'<tr class="detail-row" id="{_escape_attr(detail_id)}" '
            f'data-family-section="{_escape_attr(base.feature_family_id)}" '
            f'data-detail-for="{_escape_attr(base.feature_family_id)}" hidden>'
        ),
        '<td colspan="7">',
        '<div class="detail-drawer">',
        '<div class="detail-drawer-head">',
        "<strong>Consolidated hypothesis evidence chain</strong>",
        (
            f"<span>{_escape(_seed_alias_count_label(len(groups)))}；"
            "seed aliases collapsed under one product hypothesis；"
            "這些 rows 不是獨立 peak decisions。</span>"
        ),
        "</div>",
        _consolidated_seed_alias_details_html(
            groups,
            representatives,
            shadow_policy_cells=shadow_cells,
            shadow_projection_cells=projection_cells,
            target_benchmark_contexts=target_benchmark_contexts,
            html_path=html_path,
            input_artifacts=input_artifacts,
        ),
        "</div>",
        "</td>",
        "</tr>",
    ]


def _consolidated_seed_alias_family(
    groups: Sequence[ReconciliationGroup],
) -> bool:
    if len(groups) <= 1:
        return False
    return any(
        "primary_family_consolidated"
        in split_semicolon_labels(group.family_evidence)
        for group in groups
    )


def _seed_alias_count_label(count: int) -> str:
    if count >= _HIGH_SEED_ALIAS_COUNT:
        return f"{count} seed aliases · high alias count"
    return f"{count} seed aliases"


def _representatives_for_groups(
    groups: Sequence[ReconciliationGroup],
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
) -> tuple[RepresentativeCell, ...]:
    representatives: list[RepresentativeCell] = []
    for group in groups:
        representatives.extend(
            representatives_by_group.get(
                (group.feature_family_id, group.seed_group_id),
                (),
            ),
        )
    return tuple(sorted(representatives, key=_representative_sort_key))


def _seed_mz_range(groups: Sequence[ReconciliationGroup]) -> str:
    return _numeric_range_text(group.seed_mz for group in groups)


def _seed_rt_range(groups: Sequence[ReconciliationGroup]) -> str:
    return _numeric_range_text(group.seed_rt for group in groups)


def _seed_window_range(groups: Sequence[ReconciliationGroup]) -> str:
    starts: list[str] = []
    ends: list[str] = []
    for group in groups:
        if "-" not in group.seed_rt_window:
            continue
        start, end = group.seed_rt_window.split("-", 1)
        starts.append(start)
        ends.append(end)
    if not starts or not ends:
        return "unknown"
    return f"{_numeric_range_start(starts)}-{_numeric_range_end(ends)}"


def _numeric_range_text(values: Iterable[str]) -> str:
    parsed = _parsed_numeric_values(values)
    if not parsed:
        return "unknown"
    low = min(parsed, key=lambda item: item[0])
    high = max(parsed, key=lambda item: item[0])
    if low[0] == high[0]:
        return low[1]
    return f"{low[1]}-{high[1]}"


def _numeric_range_start(values: Iterable[str]) -> str:
    parsed = _parsed_numeric_values(values)
    if not parsed:
        return "unknown"
    return min(parsed, key=lambda item: item[0])[1]


def _numeric_range_end(values: Iterable[str]) -> str:
    parsed = _parsed_numeric_values(values)
    if not parsed:
        return "unknown"
    return max(parsed, key=lambda item: item[0])[1]


def _parsed_numeric_values(values: Iterable[str]) -> tuple[tuple[float, str], ...]:
    parsed: list[tuple[float, str]] = []
    for value in values:
        text = text_value(value)
        number = optional_float(text)
        if number is None:
            continue
        parsed.append((number, text))
    return tuple(parsed)


def _consolidated_counts_html(
    groups: Sequence[ReconciliationGroup],
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    if shadow_projection_cells:
        return _projection_counts_html(groups[0], shadow_projection_cells)
    detected = max((group.detected_cell_count for group in groups), default=0)
    rescued = sum(group.rescued_cell_count for group in groups)
    duplicate = max(
        (group.duplicate_assigned_cell_count for group in groups),
        default=0,
    )
    provisional = sum(group.provisional_cell_count for group in groups)
    return _impact_counts_html(
        detected=detected,
        rescued=rescued,
        duplicate=duplicate,
        provisional=provisional,
        aria_label=(
            "Consolidated product hypothesis impact. "
            "NL anchors are family detected required-tag anchors; "
            "Candidate-only and Review are summed seed-alias "
            "candidate/provisional cells, not matrix-written counts; "
            "Dup is family duplicate-assigned "
            "cell context."
        ),
    )


def _consolidated_overlay_cell_html(
    groups: Sequence[ReconciliationGroup],
    *,
    html_path: Path,
    input_artifacts: object,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
) -> str:
    del href_counts, first_index_by_href
    unique_groups = []
    seen_hrefs: set[str] = set()
    for group in groups:
        href = _href_for_path(group.overlay_png_path, html_path)
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        unique_groups.append(group)
    if not unique_groups:
        if any(_overlay_not_required_by_gate(group) for group in groups):
            return _overlay_not_required_status_html("no consolidated overlay")
        return _missing_overlay_status_html(
            input_artifacts,
            "no consolidated overlay",
        )
    hypothesis_link = _hypothesis_overlay_link_html(unique_groups[0], html_path)
    if hypothesis_link:
        return hypothesis_link
    link = _overlay_link_html(
        unique_groups[0],
        html_path,
        label="family context",
        caption=(
            f"{unique_groups[0].feature_family_id} | consolidated MS1 "
            "family context"
        ),
    )
    if not link:
        return _missing_overlay_status_html(
            input_artifacts,
            "no consolidated overlay",
        )
    if len(unique_groups) <= 1:
        return link
    return (
        f"{link}<br>"
        '<span class="overlay-scope" '
        'title="Alias-level PNGs share the same family MS1 context; '
        'open details for every alias path.">'
        f"{len(unique_groups)} alias overlays share the same MS1 family context"
        "</span>"
    )


def _consolidated_seed_alias_details_html(
    groups: Sequence[ReconciliationGroup],
    representatives: Sequence[RepresentativeCell],
    *,
    shadow_policy_cells: Sequence[ShadowPolicyCell],
    shadow_projection_cells: Sequence[ShadowProjectionCell],
    target_benchmark_contexts: Sequence[TargetBenchmarkContext],
    html_path: Path,
    input_artifacts: object,
) -> str:
    base = groups[0]
    return (
        _consolidated_review_answer_html(groups, input_artifacts, html_path)
        +
        '<p class="chain-note">'
        "seed aliases collapsed under one product hypothesis because the "
        "alignment review marked this family as primary_family_consolidated. "
        "The aliases remain below as provenance; they are not separate peak "
        "decisions.</p>"
        + _seed_alias_table_html(groups, html_path, input_artifacts)
        + _projection_accept_cells_html(groups, shadow_projection_cells, html_path)
        + _details_html(
            base,
            representatives,
            shadow_policy_cells=shadow_policy_cells,
            shadow_projection_cells=shadow_projection_cells,
            target_benchmark_contexts=target_benchmark_contexts,
            html_path=html_path,
            input_artifacts=input_artifacts,
            include_seed_context=False,
        )
    )


def _consolidated_review_answer_html(
    groups: Sequence[ReconciliationGroup],
    input_artifacts: object,
    html_path: Path,
) -> str:
    base = groups[0]
    overlay_text = _consolidated_overlay_readout(groups, input_artifacts, html_path)
    alias_warning = (
        "<p>High alias count: review the consolidated overlay and seed table before "
        "treating this as a simple one-seed backfill.</p>"
        if len(groups) >= _HIGH_SEED_ALIAS_COUNT
        else ""
    )
    return (
        '<section class="review-answer">'
        "<strong>Reviewer readout</strong>"
        "<p>"
        "This row is one consolidated MS1 hypothesis, not "
        f"{len(groups)} independent peak decisions. "
        "Product state is "
        f"{_escape(_compact_issue_label(base.product_behavior_state))}; "
        "evidence state is "
        f"{_escape(_compact_issue_label(base.evidence_authority_state))}. "
        f"Overlay status: {_escape(overlay_text)}."
        "</p>"
        f"{alias_warning}"
        "</section>"
    )


def _consolidated_overlay_readout(
    groups: Sequence[ReconciliationGroup],
    input_artifacts: object,
    html_path: Path,
) -> str:
    if any(_hypothesis_overlay_path(group, html_path) for group in groups):
        return "hypothesis overlay available"
    if any(_href_for_path(group.overlay_png_path, html_path) for group in groups):
        return "family context available, hypothesis overlay not generated"
    return _missing_overlay_reason_text(input_artifacts)


def _projection_accept_cells_html(
    groups: Sequence[ReconciliationGroup],
    cells: Sequence[ShadowProjectionCell],
    html_path: Path,
) -> str:
    accepted = tuple(
        cell
        for cell in sorted(cells, key=_shadow_projection_cell_sort_key)
        if _is_projected_new_accept(cell)
    )
    if not accepted:
        return ""
    groups_by_seed = {group.seed_group_id: group for group in groups}
    rows = "".join(
        "<tr>"
        f"<td>{_escape(cell.sample_stem)}</td>"
        "<td>"
        f"{_projection_accept_seed_hint_html(groups_by_seed.get(cell.seed_group_id))}"
        f"<code>{_escape(cell.seed_group_id)}</code>"
        "</td>"
        "<td>"
        f"{_projection_matrix_state_html(cell.current_matrix_written)}"
        " -> "
        f"{_projection_matrix_state_html(cell.projected_matrix_written)}"
        "</td>"
        "<td>"
        f"{_component_list_html(cell.shadow_reasons) or 'none'}"
        f"{_shadow_projection_warnings_html(cell.shadow_warnings)}"
        "</td>"
        f"<td>{_shadow_projection_evidence_html(cell)}</td>"
        f"<td>{_shadow_projection_overlay_link_html(cell, html_path)}</td>"
        "</tr>"
        for cell in accepted
    )
    return (
        '<section class="projection-accept-index">'
        "<h3>Projection write cells</h3>"
        '<p class="chain-note">'
        "Only blank candidate cells that shadow projection would "
        "turn into writes are listed here; projection_only, product output is "
        "unchanged.</p>"
        '<div class="seed-alias-table-wrap">'
        '<table class="seed-alias-table projection-accept-table">'
        "<thead><tr>"
        '<th scope="col">sample</th>'
        '<th scope="col">seed request</th>'
        '<th scope="col">decision</th>'
        '<th scope="col">reason / warning</th>'
        '<th scope="col">MS1 product rule / optional context</th>'
        '<th scope="col">overlay</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        "</section>"
    )


def _projection_accept_seed_hint_html(group: ReconciliationGroup | None) -> str:
    if group is None:
        return '<span class="seed-summary">seed not matched in gallery row</span>'
    return (
        '<span class="seed-summary">'
        f"m/z {_escape(group.seed_mz or 'unknown')} · "
        f"RT {_escape(group.seed_rt or 'unknown')} · "
        f"window {_escape(group.seed_rt_window or 'unknown')}"
        "</span>"
    )


def _seed_alias_table_html(
    groups: Sequence[ReconciliationGroup],
    html_path: Path,
    input_artifacts: object,
) -> str:
    href_counts, first_index_by_href = _overlay_href_context(groups, html_path)
    rows = "".join(
        "<tr>"
        f"<td>alias {index}</td>"
        f"<td>{_escape(group.seed_mz or 'unknown')}</td>"
        f"<td>{_escape(group.seed_rt or 'unknown')}</td>"
        f"<td>{_escape(group.seed_rt_window or 'unknown')}</td>"
        f"<td>{_escape(_compact_issue_label(_seed_issue_text(group)))}</td>"
        "<td>"
        + _seed_overlay_cell_html(
            group,
            seed_index=index,
            html_path=html_path,
            href_counts=href_counts,
            first_index_by_href=first_index_by_href,
            total_seed_groups=len(groups),
            input_artifacts=input_artifacts,
        )
        + "</td>"
        f'<td><code>{_escape(group.seed_group_id)}</code></td>'
        "</tr>"
        for index, group in enumerate(groups, start=1)
    )
    return (
        '<div class="seed-alias-table-wrap">'
        '<table class="seed-alias-table">'
        "<thead><tr>"
        '<th scope="col">alias</th>'
        '<th scope="col">m/z</th>'
        '<th scope="col">RT</th>'
        '<th scope="col">window</th>'
        '<th scope="col">issue</th>'
        '<th scope="col">overlay</th>'
        '<th scope="col">seed request</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _seed_decision_rows(
    priority: int,
    seed_index: int,
    group: ReconciliationGroup,
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[
        str,
        tuple[ShadowProjectionCell, ...],
    ],
    target_benchmark_contexts: Sequence[TargetBenchmarkContext],
    html_path: Path,
    input_artifacts: object,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
    total_seed_groups: int,
) -> list[str]:
    detail_id = _detail_row_id(
        f"{group.feature_family_id}-seed-{seed_index}",
        priority,
    )
    shadow_cells = _shadow_policy_cells_for_group(
        group,
        shadow_policy_cells_by_group=shadow_policy_cells_by_group,
        shadow_policy_cells_by_family=shadow_policy_cells_by_family,
        allow_family_fallback=False,
    )
    projection_cells = _shadow_projection_cells_for_group(
        group,
        shadow_projection_cells_by_group=shadow_projection_cells_by_group,
        shadow_projection_cells_by_family=shadow_projection_cells_by_family,
        allow_family_fallback=False,
    )
    representatives = representatives_by_group.get(
        (group.feature_family_id, group.seed_group_id),
        (),
    )
    category = " ".join(
        _ordered_unique(
            (
                *_group_filter_categories(group),
                *_shadow_projection_filter_categories(projection_cells),
            ),
        ),
    )
    return [
        (
            '<tr class="seed-decision-row" data-family-section="'
            f'{_escape_attr(group.feature_family_id)}" '
            f'data-class="{_escape_attr(group.reconciliation_class)}" '
            f'data-category="{_escape_attr(category)}" '
            f'data-detail-row="{_escape_attr(detail_id)}" '
            f'data-search="{_escape_attr(_search_blob(group, projection_cells))}">'
        ),
        (
            '<td class="cell-priority seed-rank" data-label="rank">'
            f"{priority}.{seed_index}</td>"
        ),
        (
            '<th class="cell-family seed-cell" scope="row" '
            'data-label="family / hypothesis">'
            f'<span class="seed-summary">m/z {_escape(group.seed_mz or "unknown")} '
            f'· RT {_escape(group.seed_rt or "unknown")}</span>'
            f'<span class="seed-window">window '
            f'{_escape(group.seed_rt_window or "unknown")}</span>'
            "</th>"
        ),
        (
            '<td class="cell-state" data-label="state">'
            f"{_state_html_for_shadow(group, shadow_cells, projection_cells)}</td>"
        ),
        (
            '<td class="cell-issue" data-label="issue">'
            f"{_top_issue_html(group)}</td>"
        ),
        (
            '<td class="cell-counts" data-label="impact">'
            f"{_counts_html(group, projection_cells)}"
            "</td>"
        ),
        (
            '<td class="cell-overlay" data-label="overlay">'
            + _seed_overlay_cell_html(
                group,
                seed_index=seed_index,
                html_path=html_path,
                href_counts=href_counts,
                first_index_by_href=first_index_by_href,
                total_seed_groups=total_seed_groups,
                input_artifacts=input_artifacts,
            )
            + "</td>"
        ),
        '<td class="cell-details" data-label="chain">',
        (
            '<button type="button" class="detail-toggle" '
            'aria-expanded="false" '
            f'aria-controls="{_escape_attr(detail_id)}" '
            f'data-detail-toggle="{_escape_attr(detail_id)}">Open</button>'
        ),
        "</td>",
        "</tr>",
        (
            f'<tr class="detail-row" id="{_escape_attr(detail_id)}" '
            f'data-family-section="{_escape_attr(group.feature_family_id)}" '
            f'data-detail-for="{_escape_attr(group.seed_group_id)}" hidden>'
        ),
        '<td colspan="7">',
        '<div class="detail-drawer">',
        '<div class="detail-drawer-head">',
        '<strong>Hypothesis evidence chain</strong>',
        (
            '<span>Family 是 pattern context；'
            "這裡才是 hypothesis 的 support/blocker，"
            "seed 只作為 request provenance。</span>"
        ),
        "</div>",
        _details_html(
            group,
            representatives,
            shadow_policy_cells=shadow_cells,
            shadow_projection_cells=projection_cells,
            target_benchmark_contexts=target_benchmark_contexts,
            html_path=html_path,
            input_artifacts=input_artifacts,
        ),
        "</div>",
        "</td>",
        "</tr>",
    ]


def _detail_row_id(family_id: str, priority: int) -> str:
    token = re.sub(r"[^a-zA-Z0-9_-]+", "-", family_id).strip("-").lower()
    return f"family-detail-{priority}-{token or 'item'}"


def _family_pattern_state_html(groups: Sequence[ReconciliationGroup]) -> str:
    with_context = _family_context_available(groups)
    return (
        '<div class="state-stack" aria-label="family pattern context">'
        '<div class="state-line">'
        '<span class="state-key">map</span>'
        f"{_badge('pattern_context_only')}"
        "</div>"
        '<div class="state-line">'
        '<span class="state-key">use</span>'
        f"{_badge('pattern_available' if with_context else 'pattern_unavailable')}"
        "</div>"
        "</div>"
    )


def _family_pattern_status_html(groups: Sequence[ReconciliationGroup]) -> str:
    status = (
        "context available"
        if _family_context_available(groups)
        else "context unavailable"
    )
    return f'<span class="pattern-status">{_escape(status)} · context only</span>'


def _family_context_available(groups: Sequence[ReconciliationGroup]) -> bool:
    return any(
        _safe_href(text_value(group.family_pattern_png_path))
        or _safe_href(text_value(group.overlay_png_path))
        for group in groups
    )


def _family_anchor_summary_html(groups: Sequence[ReconciliationGroup]) -> str:
    family_detected = max((group.detected_cell_count for group in groups), default=0)
    seed_parts = []
    for index, group in enumerate(groups, start=1):
        if group.seed_detected_anchor_count:
            seed_parts.append(f"seed {index} D={group.seed_detected_anchor_count}")
    if seed_parts:
        label = f"anchors D={family_detected} · " + " · ".join(seed_parts)
    elif family_detected:
        label = f"anchors D={family_detected} · seed match unknown"
    else:
        label = "anchors D=0 · not eligible"
    if family_detected == 1:
        label += " · single-anchor review"
    return f'<span class="anchor-status">{_escape(label)}</span>'


def _family_pattern_issue_html(groups: Sequence[ReconciliationGroup]) -> str:
    issues = _ordered_unique(
        _compact_issue_label(group.family_pattern_verdict)
        for group in groups
        if group.family_pattern_verdict
    )
    if issues:
        detail = " / ".join(issues)
        detail_class = "context"
    else:
        detail = "seed-specific decisions below"
        detail_class = "support"
    return (
        '<div class="top-issue family-pattern-issue">'
        f"{_badge('pattern_context_only')}"
        f'<span class="issue-text {detail_class}" title="{_escape_attr(detail)}">'
        f"{_escape(detail)}</span>"
        "</div>"
    )


def _seed_table_row_html(
    index: int,
    group: ReconciliationGroup,
    *,
    html_path: Path,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
    input_artifacts: object,
) -> str:
    overlay_html = _seed_overlay_cell_html(
        group,
        seed_index=index,
        html_path=html_path,
        href_counts=href_counts,
        first_index_by_href=first_index_by_href,
        total_seed_groups=max(len(first_index_by_href), 1),
        input_artifacts=input_artifacts,
    )
    return (
        "<tr>"
        f'<td><span title="{_escape_attr(group.seed_group_id)}">'
        f"seed {index}</span></td>"
        f"<td>{_escape(group.seed_mz)}</td>"
        f"<td>{_escape(group.seed_rt)} · {_escape(group.seed_rt_window)}</td>"
        f"<td>{_badge(group.evidence_authority_state)}</td>"
        f"<td>{_badge(group.reconciliation_class)}</td>"
        f"<td>{_escape(_compact_issue_label(_seed_issue_text(group)))}</td>"
        f"<td>{overlay_html}</td>"
        "</tr>"
    )


def _family_details_html(
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    html_path: Path,
    input_artifacts: object,
) -> str:
    if len(groups) == 1:
        group = groups[0]
        shadow_cells = _shadow_policy_cells_for_group(
            group,
            shadow_policy_cells_by_group=shadow_policy_cells_by_group,
            shadow_policy_cells_by_family=shadow_policy_cells_by_family,
            allow_family_fallback=True,
        )
        return (
            '<div class="family-details single-seed">'
            + _details_html(
                group,
                representatives_by_group.get(
                    (group.feature_family_id, group.seed_group_id),
                    (),
                ),
                shadow_policy_cells=shadow_cells,
                html_path=html_path,
                input_artifacts=input_artifacts,
                include_seed_context=False,
            )
            + "</div>"
        )
    href_counts, first_index_by_href = _overlay_href_context(groups, html_path)
    seed_rows = "".join(
        _seed_table_row_html(
            index,
            group,
            html_path=html_path,
            href_counts=href_counts,
            first_index_by_href=first_index_by_href,
            input_artifacts=input_artifacts,
        )
        for index, group in enumerate(groups, start=1)
    )
    seed_details = "".join(
        '<details class="seed-subdetails">'
        f'<summary title="{_escape_attr(group.seed_group_id)}">'
        f"{_escape(_seed_detail_summary(group, index))}</summary>"
        + _details_html(
            group,
            representatives_by_group.get(
                (group.feature_family_id, group.seed_group_id),
                (),
            ),
            shadow_policy_cells=_shadow_policy_cells_for_group(
                group,
                shadow_policy_cells_by_group=shadow_policy_cells_by_group,
                shadow_policy_cells_by_family=shadow_policy_cells_by_family,
                allow_family_fallback=False,
            ),
            html_path=html_path,
            input_artifacts=input_artifacts,
        )
        + "</details>"
        for index, group in enumerate(groups, start=1)
    )
    return (
        '<div class="family-details">'
        '<div class="seed-table-wrap">'
        '<table class="seed-table">'
        "<thead><tr>"
        '<th scope="col">seed</th>'
        '<th scope="col">mz</th>'
        '<th scope="col">rt / window</th>'
        '<th scope="col">evidence state</th>'
        '<th scope="col">class</th>'
        '<th scope="col">main issue</th>'
        '<th scope="col">overlay</th>'
        "</tr></thead>"
        f"<tbody>{seed_rows}</tbody>"
        "</table>"
        "</div>"
        f"{seed_details}"
        "</div>"
    )


def _seed_issue_text(group: ReconciliationGroup) -> str:
    return (
        group.top_blocker
        or ";".join(group.missing_evidence)
        or group.top_support_component
        or group.reconciliation_class
    )


def _seed_detail_summary(group: ReconciliationGroup, index: int) -> str:
    issue = _compact_issue_label(_seed_issue_text(group))
    return f"H{index} · RT {group.seed_rt or 'unknown'} · {issue}"


def _details_html(
    group: ReconciliationGroup,
    representatives: Sequence[RepresentativeCell],
    *,
    shadow_policy_cells: Sequence[ShadowPolicyCell] = (),
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
    target_benchmark_contexts: Sequence[TargetBenchmarkContext] = (),
    html_path: Path,
    input_artifacts: object,
    include_seed_context: bool = True,
) -> str:
    seed_context_item = (
        _chain_item_html(
            "seed / request",
            "dependent context",
            (
                f"basis={_escape(group.seed_group_basis)}<br>"
                f"m/z={_escape(group.seed_mz or 'unknown')} · "
                f"RT={_escape(group.seed_rt or 'unknown')} · "
                f"window={_escape(group.seed_rt_window or 'unknown')} · "
                f"ppm={_escape(group.seed_ppm or 'unknown')}"
            ),
        )
        if include_seed_context
        else ""
    )
    secondary_items = (
        seed_context_item
        + _chain_item_html(
            "Target benchmark",
            _target_benchmark_compact_summary(
                target_benchmark_contexts,
                input_artifacts,
            ),
            _target_benchmark_contexts_html(
                target_benchmark_contexts,
                input_artifacts,
            ),
            css_class="target-benchmark-chain",
        )
        + _chain_item_html(
            "source artifacts",
            "provenance",
            _source_artifacts_html(group.source_artifacts, input_artifacts, html_path),
        )
    )
    return (
        _review_answer_html(
            group,
            html_path,
            input_artifacts,
            shadow_projection_cells=shadow_projection_cells,
        )
        + _detail_summary_html(
            group,
            representatives,
            html_path=html_path,
            input_artifacts=input_artifacts,
            shadow_policy_cells=shadow_policy_cells,
            shadow_projection_cells=shadow_projection_cells,
        )
        + '<div class="details-grid evidence-chain">'
        + _chain_item_html(
            "product behavior",
            group.product_behavior_state,
            (
                f"{_badge(group.product_behavior_state)}"
                '<p class="chain-note">'
                f"{_escape(_compact_product_reason(group.top_product_reason))}"
                "</p>"
            ),
        )
        + _chain_item_html(
            "RT / alignment context",
            "context",
            _component_list_html(group.dependent_context_components)
            or (
                '<p class="chain-note">'
                "No dependent RT/alignment component supplied.</p>"
            ),
        )
        + _chain_item_html(
            "Hypothesis MS1 evidence",
            "visual evidence",
            _overlay_evidence_notes_html(group.overlay_evidence_notes)
            or '<p class="chain-note">No overlay metric notes supplied.</p>',
        )
        + (
            _chain_item_html(
                "Shadow production projection",
                _shadow_projection_compact_summary(shadow_projection_cells),
                _shadow_projection_cells_html(shadow_projection_cells, html_path),
                css_class="shadow-projection-chain",
            )
            if shadow_projection_cells
            else ""
        )
        + (
            _chain_item_html(
                _shadow_policy_chain_title(shadow_projection_cells),
                _shadow_policy_chain_subtitle(
                    shadow_policy_cells,
                    shadow_projection_cells,
                ),
                _shadow_policy_cells_html(
                    shadow_policy_cells,
                    html_path,
                    legacy_reference=bool(shadow_projection_cells),
                ),
                css_class="shadow-policy-chain",
            )
            if shadow_policy_cells or shadow_projection_cells
            else ""
        )
        + _chain_item_html(
            "Optional Candidate MS2 / review context",
            "not a backfill gate",
            _component_list_html(group.product_grade_support_components)
            or _component_list_html(group.review_only_visual_components)
            or '<p class="chain-note">No optional MS2/review context supplied.</p>',
        )
        + _chain_item_html(
            "blockers / missing evidence",
            "fail closed",
            _component_list_html(
                (
                    *group.blocker_components,
                    *group.missing_evidence,
                    *group.source_warnings,
                ),
            )
            or (
                '<p class="chain-note">'
                "No blocker or missing-evidence token supplied.</p>"
            ),
        )
        + _chain_item_html(
            "representative cells",
            f"{len(representatives)} cells",
            _representative_cells_table_html(representatives),
        )
        + _secondary_chain_details_html(
            "provenance / benchmark",
            "seed request, target benchmark, source artifacts",
            secondary_items,
        )
        + "</div>"
    )


def _detail_summary_html(
    group: ReconciliationGroup,
    representatives: Sequence[RepresentativeCell],
    *,
    html_path: Path,
    input_artifacts: object,
    shadow_policy_cells: Sequence[ShadowPolicyCell],
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    support_summary = _escape(
        _component_summary_text(_support_summary_items(group), "none"),
    )
    blocker_summary = _escape(
        _component_summary_text(_blocker_summary_items(group), "none"),
    )
    return (
        '<div class="detail-summary-grid" aria-label="hypothesis summary">'
        + _detail_summary_card_html(
            "decision",
            "current product / evidence state",
            (
                '<div class="summary-line"><span>Product</span>'
                f"{_badge(group.product_behavior_state)}</div>"
                '<div class="summary-line"><span>Evidence</span>'
                f"{_badge(group.evidence_authority_state)}</div>"
            ),
        )
        + _detail_summary_card_html(
            "reason",
            "support / blocker",
            (
                f"<p><strong>support</strong> {support_summary}</p>"
                f"<p><strong>blocker</strong> {blocker_summary}</p>"
            ),
        )
        + _detail_summary_card_html(
            "visual evidence",
            _visual_summary_subtitle(group),
            _detail_visual_summary_html(group, html_path, input_artifacts),
        )
        + _detail_summary_card_html(
            "cell impact",
            f"{len(representatives)} representative cells",
            (
                _counts_html(group, shadow_projection_cells)
                + _cell_impact_legend_note_html(group, shadow_projection_cells)
                + _shadow_projection_summary_note_html(shadow_projection_cells)
                + _shadow_policy_summary_note_html(shadow_policy_cells)
            ),
        )
        + _cid_nl_review_focus_card_html(group)
        + _cid_nl_discovery_identity_card_html(group, representatives)
        + "</div>"
    )


def _cid_nl_review_focus_card_html(group: ReconciliationGroup) -> str:
    if not _is_cid_nl_successor_review_group(group):
        return ""
    return _detail_summary_card_html(
        "Review focus",
        "separate feature inclusion from identity authority",
        (
            "<p><strong>Feature inclusion question</strong> "
            "Does CID-NL/MS2 evidence plus MS1 trace context support carrying "
            "this successor as an untargeted feature candidate?</p>"
            "<p><strong>Identity authority question</strong> "
            "Should source and successor be replaced, merged, deduped, or "
            "kept as co-existing features? Current answer: review only.</p>"
        ),
    )


def _cid_nl_discovery_identity_card_html(
    group: ReconciliationGroup,
    representatives: Sequence[RepresentativeCell],
) -> str:
    if not _is_cid_nl_successor_review_group(group):
        return ""
    return _detail_summary_card_html(
        "Feature / identity relationship",
        "source row -> successor hypothesis",
        (
            "<p><strong>Source/successor relationship</strong></p>"
            + _cid_nl_identity_transition_list_html(group, representatives)
            + "<p><strong>successor cell decisions</strong></p>"
            + _cid_nl_successor_decision_list_html(representatives)
        ),
    )


def _detail_summary_card_html(title: str, subtitle: str, body_html: str) -> str:
    return (
        '<section class="detail-summary-card">'
        f"<h3>{_escape(title)}</h3>"
        f'<p class="summary-subtitle">{_escape(subtitle)}</p>'
        f'<div class="summary-body">{body_html}</div>'
        "</section>"
    )


def _review_answer_html(
    group: ReconciliationGroup,
    html_path: Path,
    input_artifacts: object,
    *,
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    support = _component_summary_text(_support_summary_items(group), "none")
    blocker = _component_summary_text(_blocker_summary_items(group), "none")
    overlay = _hypothesis_overlay_link_html(group, html_path)
    family_context = _overlay_link_html(
        group,
        html_path,
        label="family context",
    )
    if overlay and _is_cid_nl_successor_review_group(group):
        overlay_text = "MS1 context PNG available; not NL-tag evidence"
    elif overlay:
        overlay_text = "hypothesis overlay available"
    elif family_context and _is_cid_nl_differential_review_group(group):
        overlay_text = "hypothesis differential overlay available"
    elif family_context:
        overlay_text = "family context only, hypothesis overlay not generated"
    else:
        overlay_text = _missing_overlay_reason_text(input_artifacts)
    decision_text = _review_answer_decision_text(group, shadow_projection_cells)
    return (
        '<section class="review-answer">'
        "<strong>Reviewer readout</strong>"
        f"<p>{_escape(decision_text)}</p>"
        '<p class="review-answer-meta">'
        f"Support: {_escape(support)}. "
        f"Blocker or missing item: {_escape(blocker)}. "
        f"Overlay status: {_escape(overlay_text)}."
        "</p>"
        "</section>"
    )


def _review_answer_decision_text(
    group: ReconciliationGroup,
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    if _is_cid_nl_successor_review_group(group):
        return (
            "結論：CID-NL adoption review only；"
            f"Write {group.rescued_cell_count}、"
            f"Preserve {group.detected_cell_count}、"
            f"Omit {group.provisional_cell_count}。"
            "這不是 active default matrix，也不是 ProductWriter authority。"
        )
    if shadow_projection_cells:
        current = sum(cell.current_matrix_written for cell in shadow_projection_cells)
        review = sum(cell.review_rescued_cell for cell in shadow_projection_cells)
        write = sum(
            cell.shadow_decision == "accept" and cell.projected_matrix_written
            for cell in shadow_projection_cells
        )
        block = sum(cell.shadow_decision == "block" for cell in shadow_projection_cells)
        context = sum(
            cell.shadow_decision == "context" for cell in shadow_projection_cells
        )
        if write:
            return (
                f"結論：會寫入 {write} 個新 matrix value。"
                f"目前已寫入 {current} 個，review candidate {review} 個。"
            )
        if current:
            return (
                f"結論：目前 production snapshot 已寫入 {current} 個 value；"
                "這一列沒有新的 activation write。"
            )
        if block:
            return (
                f"結論：未寫入 matrix；{block} 個 cell 被 hard blocker 擋下。"
                f"Review candidate {review} 個。"
            )
        if context:
            return (
                f"結論：未寫入 matrix；{context} 個 cell 仍是 review-only "
                "candidate。這代表 MS1/visual evidence 支持同峰候選，但還沒有 "
                "product-authorized standard-peak same-peak chain。"
            )
    product = _compact_issue_label(group.product_behavior_state)
    evidence = _compact_issue_label(group.evidence_authority_state)
    return f"結論：Product={product}；Evidence={evidence}。"


def _support_summary_items(group: ReconciliationGroup) -> tuple[str, ...]:
    return tuple(
        _ordered_unique(
            (
                group.top_support_component,
                *group.product_grade_support_components,
                *group.review_only_visual_components,
            ),
        ),
    )


def _blocker_summary_items(group: ReconciliationGroup) -> tuple[str, ...]:
    return tuple(
        _ordered_unique(
            (
                group.top_blocker,
                *group.blocker_components,
                *group.missing_evidence,
                *group.source_warnings,
            ),
        ),
    )


def _component_summary_text(items: Sequence[str], fallback: str) -> str:
    cleaned = _ordered_unique(text_value(item) for item in items if text_value(item))
    if not cleaned:
        return fallback
    summary = " / ".join(_compact_issue_label(item) for item in cleaned[:3])
    if len(cleaned) > 3:
        summary += f" / +{len(cleaned) - 3}"
    return summary


def _visual_summary_subtitle(group: ReconciliationGroup) -> str:
    if _is_cid_nl_successor_review_group(group):
        return "MS1 feature context / identity review only"
    return "hypothesis evidence / family context"


def _detail_visual_summary_html(
    group: ReconciliationGroup,
    html_path: Path,
    input_artifacts: object,
) -> str:
    link = _hypothesis_overlay_link_html(group, html_path) or _overlay_link_html(
        group,
        html_path,
        label="family context",
    )
    link_html = (
        f'<p class="summary-link">{link}</p>'
        if link
        else (
            '<p class="chain-note">'
            f"{_escape(_missing_overlay_reason_text(input_artifacts))}.</p>"
        )
    )
    note_text = _component_summary_text(group.overlay_evidence_notes, "no metric notes")
    return (
        link_html
        + _anchor_review_context_html(group)
        + '<p class="chain-note">'
        + _escape(note_text)
        + "</p>"
    )


def _anchor_review_context_html(group: ReconciliationGroup) -> str:
    if _is_cid_nl_successor_review_group(group):
        return (
            '<p class="review-note">CID-NL feature review: Candidate/Existing/Omit '
            "counts come from the diagnostic decision packet. Overlay orange "
            "detected/rescued traces are MS1 trace status only; they do not prove "
            "NL-tag coverage, force source/successor replacement, or grant "
            "ProductWriter authority.</p>"
        )
    if group.seed_detected_anchor_count == 0:
        return (
            '<p class="review-note">No detected NL anchor on this hypothesis; '
            "treat as provenance/context, not a backfill candidate.</p>"
        )
    if group.seed_detected_anchor_count == 1:
        return (
            '<p class="review-note">Single detected NL anchor: visual evidence is '
            "review-only unless product-grade support closes the gap.</p>"
        )
    return (
        '<p class="review-note">'
        f"{_escape(group.seed_detected_anchor_count)} detected NL anchors on this "
        "hypothesis.</p>"
    )


def _shadow_policy_summary_note_html(
    cells: Sequence[ShadowPolicyCell],
) -> str:
    summary = _shadow_policy_compact_summary(cells)
    if not summary:
        return ""
    return f'<p class="chain-note">shadow policy: {_escape(summary)}</p>'


def _shadow_policy_state_label(shadow_summary: str, projection_summary: str) -> str:
    if projection_summary:
        return f"legacy reference: {shadow_summary}"
    return shadow_summary


def _shadow_policy_chain_title(
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    if shadow_projection_cells:
        return "Legacy MS1+RT shadow policy"
    return "MS1+RT shadow policy"


def _shadow_policy_chain_subtitle(
    shadow_policy_cells: Sequence[ShadowPolicyCell],
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    summary = _shadow_policy_compact_summary(shadow_policy_cells) or "not supplied"
    if shadow_projection_cells and summary != "not supplied":
        return f"reference only · {summary}"
    return summary


def _cell_impact_legend_note_html(
    group: ReconciliationGroup,
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    if shadow_projection_cells:
        return (
            '<p class="chain-note">'
            "Current=目前 production snapshot 已寫入的 cells；"
            "Review=只有 review/candidate context，尚未寫入 matrix；"
            "Write=這輪 projection/activation 可寫入的新 cells；"
            "Block=hard blockers。Context/review-only 不會直接改 matrix。</p>"
        )
    if _is_cid_nl_successor_review_group(group):
        return (
            '<p class="chain-note">Write=successor adoption candidate writes；'
            "Preserve=successor baseline already has a detected value, so no "
            "Backfill write；Omit=no safe successor write target。"
            "These are authority-review counts, not NL-tag coverage and not "
            "active matrix writes.</p>"
        )
    return (
        '<p class="chain-note">NL=detected required-tag anchors；'
        "Candidate-only=目前 hypothesis 的候選 cells，不代表已寫入 matrix；"
        "Dup=family duplicate-assigned cell context；"
        "Review=仍需人工判斷的 provisional cells。</p>"
    )


def _shadow_projection_summary_note_html(
    cells: Sequence[ShadowProjectionCell],
) -> str:
    summary = _shadow_projection_compact_summary(cells)
    if not summary:
        return ""
    return f'<p class="chain-note">shadow projection: {_escape(summary)}</p>'


def _cid_nl_identity_transition_list_html(
    group: ReconciliationGroup,
    representatives: Sequence[RepresentativeCell],
) -> str:
    counts = Counter(
        _identity_transition_text(cell)
        for cell in representatives
        if cell.source_peak_hypothesis_id or cell.successor_peak_hypothesis_id
    )
    if not counts:
        if any(
            item.startswith("target_guardrail:")
            for item in group.dependent_context_components
        ):
            return (
                '<p class="chain-note">'
                "Target benchmark context only: this verifies Discovery "
                "recovered or preserved the target family, not a Backfill "
                "old-to-successor write candidate.</p>"
            )
        return (
            '<p class="chain-note">'
            "No old-to-successor identity mapping supplied.</p>"
        )
    return _summary_count_list_html(counts)


def _cid_nl_successor_decision_list_html(
    representatives: Sequence[RepresentativeCell],
) -> str:
    counts = Counter(
        cell.successor_decision for cell in representatives if cell.successor_decision
    )
    if not counts:
        return '<p class="chain-note">No successor decision supplied.</p>'
    return _summary_count_list_html(counts)


def _summary_count_list_html(counts: Counter[str]) -> str:
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    limit = 6
    visible = items[:limit]
    extra = len(items) - limit
    html = (
        '<ul class="component-list identity-transition-list">'
        + "".join(
            f"<li>{_escape(label)} <span class=\"muted\">x{count}</span></li>"
            for label, count in visible
        )
    )
    if extra > 0:
        html += f'<li class="muted">+{extra} more</li>'
    return html + "</ul>"


def _identity_transition_text(cell: RepresentativeCell) -> str:
    if not (cell.source_peak_hypothesis_id or cell.successor_peak_hypothesis_id):
        return ""
    old_peak = cell.source_peak_hypothesis_id or "<unknown>"
    successor = cell.successor_peak_hypothesis_id or "<none>"
    return f"{old_peak} -> {successor}"


def _secondary_chain_details_html(title: str, subtitle: str, body_html: str) -> str:
    return (
        '<details class="chain-item secondary-chain">'
        "<summary>"
        f"<span>{_escape(title)}</span>"
        f'<small>{_escape(subtitle)}</small>'
        "</summary>"
        f'<div class="secondary-chain-body">{body_html}</div>'
        "</details>"
    )


def _overlay_evidence_notes_html(notes: Sequence[str]) -> str:
    if not notes:
        return ""
    items = "".join(f"<li>{_escape(note)}</li>" for note in notes)
    return (
        '<div class="detail-block"><strong>overlay evidence metrics</strong>'
        f'<ul class="metric-list">{items}</ul></div>'
    )


def _shadow_policy_cells_html(
    cells: Sequence[ShadowPolicyCell],
    html_path: Path,
    *,
    legacy_reference: bool = False,
) -> str:
    if not cells:
        return (
            '<p class="chain-note">'
            "No shadow policy cell rows supplied for this seed group.</p>"
        )
    rows = "".join(
        "<tr>"
        f"<td>{_escape(cell.sample_stem)}</td>"
        f"<td>{_badge(cell.current_product_cell_state)}</td>"
        f"<td>{_badge(cell.shadow_policy_decision)}</td>"
        "<td>"
        f"{_escape(cell.decision_reason or 'no reason supplied')}"
        f"{_shadow_policy_gap_html(cell.production_gap)}"
        "</td>"
        "<td>"
        f"{_escape(_shadow_metric_text(cell))}"
        "</td>"
        "<td>"
        f"{_shadow_policy_evidence_html(cell)}"
        "</td>"
        f"<td>{_shadow_policy_overlay_link_html(cell, html_path)}</td>"
        "</tr>"
        for cell in sorted(cells, key=_shadow_policy_cell_sort_key)
    )
    return (
        '<p class="chain-note">'
        f"{_shadow_policy_intro_text(legacy_reference)}</p>"
        '<div class="shadow-policy-table-wrap">'
        '<table class="shadow-policy-table">'
        "<thead><tr>"
        '<th scope="col">sample</th>'
        '<th scope="col">current</th>'
        '<th scope="col">shadow decision</th>'
        '<th scope="col">reason / gap</th>'
        '<th scope="col">own-max evidence</th>'
        '<th scope="col">support / blockers</th>'
        '<th scope="col">overlay</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _shadow_policy_intro_text(legacy_reference: bool) -> str:
    if legacy_reference:
        return (
            "legacy_reference_only；這裡保留舊 MS1 own-max + RT shadow policy "
            "作為比較來源。若與 Shadow production projection 不一致，"
            "以 projection table 追 current production decision / projected "
            "decision sidecar。"
        )
    return (
        "diagnostic_only；這裡只描述 MS1 own-max + RT shadow policy "
        "會如何解讀既有 candidate cells，不會修改 product output。"
    )


def _shadow_projection_cells_html(
    cells: Sequence[ShadowProjectionCell],
    html_path: Path,
) -> str:
    if not cells:
        return (
            '<p class="chain-note">'
            "No shadow production projection rows supplied for this seed group.</p>"
        )
    rows = "".join(
        "<tr>"
        f"<td>{_escape(cell.sample_stem)}</td>"
        f"<td>{_projection_matrix_state_html(cell.current_matrix_written)}</td>"
        f"<td>{_badge(cell.current_production_status)}</td>"
        f"<td>{_badge(cell.shadow_decision)}</td>"
        f"<td>{_projection_matrix_state_html(cell.projected_matrix_written)}</td>"
        "<td>"
        f"{_component_list_html(cell.shadow_reasons) or 'none'}"
        f"{_shadow_projection_warnings_html(cell.shadow_warnings)}"
        "</td>"
        "<td>"
        f"{_shadow_projection_evidence_html(cell)}"
        "</td>"
        f"<td>{_shadow_projection_overlay_link_html(cell, html_path)}</td>"
        "</tr>"
        for cell in sorted(cells, key=_shadow_projection_cell_sort_key)
    )
    return (
        '<p class="chain-note">'
        "shadow_projection_only；這裡顯示 current production decision snapshot "
        "與 projected decision 的差異；alignment_matrix.tsv 目前只做來源 hash，"
        "仍不會直接修改 product output。</p>"
        '<div class="shadow-policy-table-wrap">'
        '<table class="shadow-policy-table shadow-projection-table">'
        "<thead><tr>"
        '<th scope="col">sample</th>'
        '<th scope="col">current decision</th>'
        '<th scope="col">current state</th>'
        '<th scope="col">shadow decision</th>'
        '<th scope="col">projected decision</th>'
        '<th scope="col">reasons / warnings</th>'
        '<th scope="col">evidence</th>'
        '<th scope="col">overlay</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _projection_matrix_state_html(written: bool) -> str:
    return _badge("write" if written else "blank")


def _shadow_projection_warnings_html(warnings: Sequence[str]) -> str:
    if not warnings:
        return ""
    return (
        '<div class="warning-list"><span>warnings</span>'
        f"{_component_list_html(warnings)}</div>"
    )


def _shadow_projection_metric_text(cell: ShadowProjectionCell) -> str:
    parts = []
    if cell.detected_anchor_count:
        parts.append(f"anchors={cell.detected_anchor_count}")
    if cell.request_window_overlap:
        parts.append(f"request window={cell.request_window_overlap}")
    if cell.local_global_ratio:
        parts.append(f"local/global={cell.local_global_ratio}")
    if cell.evidence_gate_status:
        parts.append(f"gate={cell.evidence_gate_status}")
    return " · ".join(parts) or "not supplied"


def _shadow_projection_evidence_html(cell: ShadowProjectionCell) -> str:
    metric = _escape(_shadow_projection_metric_text(cell))
    if not cell.product_authority_chain:
        return metric
    return (
        metric
        + '<div class="projection-authority-chain">'
        + "<span>MS1 product rule / optional context chain</span> "
        + _escape(cell.product_authority_chain)
        + "</div>"
    )


def _shadow_policy_gap_html(value: str) -> str:
    gap = text_value(value)
    if not gap:
        return ""
    return f'<br><span class="gap-label">gap</span> {_badge(gap)}'


def _shadow_metric_text(cell: ShadowPolicyCell) -> str:
    parts = []
    if cell.own_max_shape_supported_fraction:
        parts.append(f"own-max={cell.own_max_shape_supported_fraction}")
    if cell.absolute_trace_apex_cluster_fraction:
        parts.append(f"apex cluster={cell.absolute_trace_apex_cluster_fraction}")
    if cell.evidence_gate_status:
        parts.append(f"gate={cell.evidence_gate_status}")
    return " · ".join(parts) or "not supplied"


def _shadow_policy_evidence_html(cell: ShadowPolicyCell) -> str:
    items = _ordered_unique(
        (
            *split_semicolon_labels(cell.support_components),
            *split_semicolon_labels(cell.blockers),
            *split_semicolon_labels(cell.missing_evidence),
            cell.overlay_family_verdict,
        ),
    )
    return _component_list_html(items) or "none"


def _chain_item_html(
    title: str,
    state: str,
    body_html: str,
    *,
    css_class: str = "",
) -> str:
    class_attr = "chain-item" + (f" {css_class}" if css_class else "")
    return (
        f'<section class="{_escape_attr(class_attr)}">'
        '<div class="chain-head">'
        f"<h3>{_escape(title)}</h3>"
        f'<span class="chain-state">{_escape(_compact_issue_label(state))}</span>'
        "</div>"
        f'<div class="chain-body">{body_html}</div>'
        "</section>"
    )


def _component_list_html(items: Sequence[str]) -> str:
    cleaned = _ordered_unique(text_value(item) for item in items if text_value(item))
    if not cleaned:
        return ""
    return (
        '<ul class="component-list">'
        + "".join(f"<li>{_escape(_compact_issue_label(item))}</li>" for item in cleaned)
        + "</ul>"
    )


def _representative_cells_table_html(
    representatives: Sequence[RepresentativeCell],
) -> str:
    rep_rows = "".join(
        "<tr>"
        f"<td>{_escape(';'.join(cell.representative_roles))}</td>"
        f"<td>{_escape(cell.sample_stem)}</td>"
        f"<td>{_escape(_compact_issue_label(cell.cell_status))}</td>"
        f"<td>{_escape(cell.scan_support_score)}</td>"
        f"<td>{_escape(cell.apex_delta_sec)}</td>"
        f"<td>{_escape(cell.representative_reason)}</td>"
        "</tr>"
        for cell in representatives
    )
    if not rep_rows:
        rep_rows = (
            '<tr><td colspan="6">沒有可安全選出的 representative cell。</td></tr>'
        )
    return (
        '<table class="rep-table">'
        "<thead><tr>"
        '<th scope="col">roles</th><th scope="col">sample</th>'
        '<th scope="col">status</th><th scope="col">scan support</th>'
        '<th scope="col">apex delta</th><th scope="col">reason</th>'
        "</tr></thead>"
        f"<tbody>{rep_rows}</tbody></table>"
    )






def _product_cell_state(row: Mapping[str, str], group_state: str) -> str:
    if _cell_writes_primary_matrix(row):
        return "primary_matrix"
    if _cell_has_primary_area_context(row):
        return "candidate_context"
    if group_state == "product_rescued_context_only":
        return "candidate_context"
    return group_state


def _apex_delta_sec(row: Mapping[str, str], seed_record: _SeedRecord) -> str:
    direct = text_value(row.get("backfill_apex_delta_sec") or row.get("rt_delta_sec"))
    if direct:
        return direct
    apex = optional_float(row.get("apex_rt"))
    seed_rt = optional_float(seed_record.seed_rt)
    if apex is None or seed_rt is None:
        return ""
    return f"{(apex - seed_rt) * 60:.6g}"


def _source_row_key(family: str, row: Mapping[str, str]) -> str:
    sample = text_value(row.get("sample_stem")) or "unknown_sample"
    status = text_value(row.get("status")) or "unknown_status"
    return f"{family}::{sample}::{status}"


def _top_product_reason(row: Mapping[str, str]) -> str:
    for column in ("identity_reason", "primary_evidence", "reason", "row_flags"):
        value = text_value(row.get(column))
        if value:
            return value
    return ""


def _tag_or_class(
    review_row: Mapping[str, str],
    seed_aware_row: Mapping[str, str],
) -> str:
    for value in (
        review_row.get("neutral_loss_tag"),
        seed_aware_row.get("review_classification"),
        review_row.get("group_construction_role"),
    ):
        parsed = text_value(value)
        if parsed:
            return parsed
    return ""


def _first_label(values: Sequence[str]) -> str:
    return values[0] if values else ""


def _search_blob(
    group: ReconciliationGroup,
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    return " ".join(
        (
            group.feature_family_id,
            group.seed_group_id,
            group.product_behavior_state,
            group.evidence_authority_state,
            group.reconciliation_class,
            group.top_support_component,
            group.top_blocker,
            ";".join(group.missing_evidence),
            ";".join(group.source_warnings),
            _shadow_projection_search_blob(shadow_projection_cells),
        ),
    )


def _family_search_blob(
    groups: Sequence[ReconciliationGroup],
    target_benchmark_contexts: Sequence[TargetBenchmarkContext] = (),
    shadow_projection_cells: Sequence[ShadowProjectionCell] = (),
) -> str:
    target_text = " ".join(
        " ".join(
            (
                context.target_label,
                context.role,
                context.status,
                context.selected_feature_id,
            ),
        )
        for context in target_benchmark_contexts
    )
    return " ".join(
        (
            *(_search_blob(group) for group in groups),
            target_text,
            _shadow_projection_search_blob(shadow_projection_cells),
        ),
    )


def _shadow_projection_search_blob(
    cells: Sequence[ShadowProjectionCell],
) -> str:
    terms: list[str] = []
    for cell in cells:
        terms.extend(
            (
                cell.feature_family_id,
                cell.seed_group_id,
                cell.sample_stem,
                cell.current_production_status,
                cell.shadow_decision,
                cell.projection_authority,
                cell.product_authority_chain,
                ";".join(cell.shadow_reasons),
                ";".join(cell.shadow_warnings),
            ),
        )
        if _is_projected_new_accept(cell):
            terms.extend(("projection_accept", "projected_new_write"))
    return " ".join(term for term in terms if term)




def _count_token_prefix(counts: object, prefix: str) -> int:
    if not isinstance(counts, Mapping):
        return 0
    return sum(
        int(value)
        for key, value in counts.items()
        if isinstance(key, str) and key.startswith(prefix)
    )
