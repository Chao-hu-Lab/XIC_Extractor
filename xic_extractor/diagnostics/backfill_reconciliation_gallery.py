"""Backfill evidence reconciliation indexes and gallery rendering."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xic_extractor.diagnostics.backfill_shadow_policy import (
    BACKFILL_SHADOW_POLICY_COLUMNS,
)
from xic_extractor.diagnostics.diagnostic_io import (
    bool_value,
    optional_float,
    read_tsv_required,
    split_semicolon_labels,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.shadow_production_projection import (
    SHADOW_PRODUCTION_PROJECTION_COLUMNS,
)

SCHEMA_VERSION = "backfill_evidence_reconciliation_v0"

GROUP_TSV_COLUMNS = (
    "schema_version",
    "priority_rank",
    "feature_family_id",
    "seed_group_id",
    "seed_group_basis",
    "seed_mz",
    "seed_rt",
    "seed_rt_window",
    "seed_ppm",
    "tag_or_class",
    "product_behavior_state",
    "evidence_authority_state",
    "reconciliation_class",
    "detected_cell_count",
    "rescued_cell_count",
    "provisional_cell_count",
    "top_product_reason",
    "top_support_component",
    "top_blocker",
    "missing_evidence",
    "overlay_png_path",
    "overlay_trace_json_path",
    "source_artifacts",
    "source_warnings",
)

REPRESENTATIVE_CELL_TSV_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "seed_group_id",
    "representative_roles",
    "sample_stem",
    "cell_status",
    "product_cell_state",
    "shape_similarity",
    "scan_support_score",
    "apex_delta_sec",
    "boundary_overlap",
    "interference_signal",
    "representative_reason",
    "source_row_key",
)

EVIDENCE_AUTHORITY_STATES = (
    "product_grade_support",
    "review_only_visual_support",
    "dependent_context_only",
    "human_visual_judgment_only",
    "evidence_blocks_backfill",
    "evidence_inconclusive",
    "not_assessable",
)

RECONCILIATION_CLASSES = (
    "product_accepts_and_product_grade_supports",
    "product_accepts_and_visual_supports",
    "product_rejects_but_product_grade_supports",
    "product_rejects_but_visual_supports",
    "product_accepts_but_evidence_conflicts",
    "product_rejects_and_evidence_blocks",
    "evidence_inconclusive",
    "not_assessable_missing_overlay",
    "not_assessable_missing_seed_provenance",
    "not_assessable_join_gap",
)

RECONCILIATION_CLASS_PRIORITY = (
    "product_rejects_but_product_grade_supports",
    "product_rejects_but_visual_supports",
    "product_accepts_but_evidence_conflicts",
    "not_assessable_missing_overlay",
    "not_assessable_missing_seed_provenance",
    "not_assessable_join_gap",
    "evidence_inconclusive",
    "product_accepts_and_visual_supports",
    "product_accepts_and_product_grade_supports",
    "product_rejects_and_evidence_blocks",
)

_CLASS_PRIORITY = {
    name: index for index, name in enumerate(RECONCILIATION_CLASS_PRIORITY)
}
_REVIEW_CATEGORY_LABELS = {
    "needs_review": "Needs review",
    "accepted_supported": "Accepted + supported",
    "conflict_or_blocked": "Conflict / blocked",
    "missing_evidence": "Missing evidence",
}
_DEFAULT_FILTER_CATEGORY = "product_rows"
_HTML_FULL_RENDER_GROUP_LIMIT = 1500
_HTML_INCONCLUSIVE_SAMPLE_LIMIT = 200
_REVIEW_FILTER_LABELS = {
    "product_rows": "Product rows",
    "projection_accepts": "Projection accepts",
    **_REVIEW_CATEGORY_LABELS,
    "debug_rows": "Duplicate / audit debug",
}
_REVIEW_CATEGORY_SUMMARY_LABELS = {
    "needs_review": "Review",
    "accepted_supported": "Accepted",
    "conflict_or_blocked": "Conflict",
    "missing_evidence": "Missing",
}
_REVIEW_CATEGORY_BY_CLASS = {
    "product_rejects_but_product_grade_supports": "needs_review",
    "product_rejects_but_visual_supports": "needs_review",
    "evidence_inconclusive": "needs_review",
    "product_accepts_and_product_grade_supports": "accepted_supported",
    "product_accepts_and_visual_supports": "accepted_supported",
    "product_accepts_but_evidence_conflicts": "conflict_or_blocked",
    "product_rejects_and_evidence_blocks": "conflict_or_blocked",
    "not_assessable_missing_overlay": "missing_evidence",
    "not_assessable_missing_seed_provenance": "missing_evidence",
    "not_assessable_join_gap": "missing_evidence",
}
_ROLE_PRIORITY = {
    "strongest_support": 0,
    "strongest_blocker": 1,
    "lowest_similarity": 2,
    "highest_interference": 3,
    "seed_representative": 4,
    "product_disagreement_example": 5,
}
_URL_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
_DANGEROUS_SCHEMES = {"javascript", "data", "vbscript"}
_HUMAN_REVIEW_PREFIXES = ("review_required_",)
_HUMAN_REVIEW_TOKENS = {
    "neighbor_interference_review",
    "shape_insufficient_review",
}
_ANCHOR_SHAPE_SUPPORTED_REASON = (
    "family_ms1_overlay_anchor_peak_own_max_shape_supported"
)
_ANCHOR_SHAPE_REVIEW_REASON = (
    "family_ms1_overlay_anchor_peak_shape_below_threshold"
)
_REQUIRED_ALIGNMENT_REVIEW_COLUMNS = (
    "feature_family_id",
    "group_construction_role",
    "neutral_loss_tag",
    "detected_count",
    "quantifiable_detected_count",
    "identity_decision",
    "identity_confidence",
    "primary_evidence",
    "identity_reason",
    "quantifiable_rescue_count",
    "accepted_rescue_count",
    "include_in_primary_matrix",
    "row_flags",
    "reason",
)
_REQUIRED_ALIGNMENT_CELLS_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "primary_matrix_area_source",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "trace_quality",
    "scan_support_score",
    "gap_fill_state",
    "gap_fill_reason",
)
_REQUIRED_ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "backfill_seed_mz",
    "backfill_seed_rt",
    "backfill_request_rt_min",
    "backfill_request_rt_max",
    "backfill_request_ppm",
)
_REQUIRED_TARGETED_ISTD_BENCHMARK_SUMMARY_COLUMNS = (
    "target_label",
    "role",
    "active_tag",
    "targeted_positive_count",
    "selected_feature_id",
    "untargeted_positive_count",
    "coverage_minimum",
    "status",
    "failure_modes",
)
_INPUT_ARTIFACT_LABEL_BY_KEY = {
    "alignment_review_tsv": "alignment_review.tsv",
    "alignment_cells_tsv": "alignment_cells.tsv",
    "alignment_matrix_tsv": "alignment_matrix.tsv",
    "backfill_seed_audit_tsv": "alignment_owner_backfill_seed_audit.tsv",
    "overlay_batch_summary_tsvs": "family_ms1_overlay_batch_summary.tsv",
    "seed_aware_family_tsv": "seed_aware_backfill_review_families.tsv",
    "seed_aware_summary_tsv": "seed_aware_backfill_review_summary.tsv",
    "candidate_gate_tsv": "alignment_production_candidate_gate.tsv",
    "tier2_trace_evidence_tsv": "alignment_tier2_trace_evidence.tsv",
    "shadow_policy_cells_tsv": "backfill_shadow_policy_cells.tsv",
    "shadow_projection_cells_tsv": "shadow_production_projection_cells.tsv",
    "targeted_istd_benchmark_summary_tsv": "targeted_istd_benchmark_summary.tsv",
}


@dataclass(frozen=True)
class RepresentativeCell:
    feature_family_id: str
    seed_group_id: str
    representative_roles: tuple[str, ...]
    sample_stem: str
    cell_status: str
    product_cell_state: str = ""
    shape_similarity: str = ""
    scan_support_score: str = ""
    apex_delta_sec: str = ""
    boundary_overlap: str = ""
    interference_signal: str = ""
    representative_reason: str = ""
    source_row_key: str = ""


@dataclass(frozen=True)
class ShadowPolicyCell:
    feature_family_id: str
    seed_group_id: str
    sample_stem: str
    current_product_cell_state: str
    shadow_policy_decision: str
    decision_reason: str
    production_gap: str = ""
    diagnostic_authority: str = ""
    cell_status: str = ""
    evidence_gate_status: str = ""
    overlay_family_verdict: str = ""
    own_max_shape_supported_fraction: str = ""
    absolute_trace_apex_cluster_fraction: str = ""
    support_components: str = ""
    blockers: str = ""
    missing_evidence: str = ""
    overlay_png_path: str = ""


@dataclass(frozen=True)
class ShadowProjectionCell:
    feature_family_id: str
    seed_group_id: str
    sample_stem: str
    current_raw_status: str
    current_production_status: str
    current_rescue_tier: str
    current_matrix_written: bool
    current_matrix_value: str
    current_blank_reason: str
    current_matrix_source: str
    review_rescued_cell: bool
    shadow_decision: str
    shadow_reasons: tuple[str, ...] = ()
    shadow_warnings: tuple[str, ...] = ()
    projected_matrix_written: bool = False
    projected_matrix_value: str = ""
    projection_authority: str = ""
    product_authority_chain: str = ""
    detected_anchor_count: str = ""
    rescued_cell_count: str = ""
    request_window_overlap: str = ""
    local_global_ratio: str = ""
    evidence_gate_status: str = ""
    support_components: tuple[str, ...] = ()
    hard_blockers: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    overlay_verdict: str = ""
    overlay_png_path: str = ""


@dataclass(frozen=True)
class TargetBenchmarkContext:
    target_label: str
    role: str
    active_tag: str
    status: str
    selected_feature_id: str
    primary_feature_ids: tuple[str, ...] = ()
    targeted_positive_count: str = ""
    untargeted_positive_count: str = ""
    coverage_minimum: str = ""
    failure_modes: tuple[str, ...] = ()
    note: str = ""

    @property
    def feature_family_ids(self) -> tuple[str, ...]:
        return tuple(
            _ordered_unique((*self.primary_feature_ids, self.selected_feature_id)),
        )


@dataclass(frozen=True)
class ReconciliationGroup:
    feature_family_id: str
    seed_group_id: str
    seed_group_basis: str
    seed_mz: str = ""
    seed_rt: str = ""
    seed_rt_window: str = ""
    seed_ppm: str = ""
    tag_or_class: str = ""
    product_behavior_state: str = "product_unknown"
    evidence_authority_state: str = "not_assessable"
    reconciliation_class: str = "evidence_inconclusive"
    include_in_primary_matrix: bool = False
    identity_decision: str = ""
    row_flags: str = ""
    family_evidence: str = ""
    accepted_cell_count: int = 0
    detected_cell_count: int = 0
    rescued_cell_count: int = 0
    provisional_cell_count: int = 0
    seed_detected_anchor_count: int = 0
    duplicate_assigned_cell_count: int = 0
    cell_total_count: int = 0
    top_product_reason: str = ""
    top_support_component: str = ""
    top_blocker: str = ""
    missing_evidence: tuple[str, ...] = ()
    overlay_png_path: str = ""
    overlay_trace_json_path: str = ""
    family_pattern_png_path: str = ""
    family_pattern_trace_json_path: str = ""
    family_pattern_verdict: str = ""
    overlay_evidence_notes: tuple[str, ...] = ()
    source_artifacts: tuple[str, ...] = ()
    source_warnings: tuple[str, ...] = ()
    product_grade_support_components: tuple[str, ...] = ()
    review_only_visual_components: tuple[str, ...] = ()
    dependent_context_components: tuple[str, ...] = ()
    blocker_components: tuple[str, ...] = ()
    representative_cells: tuple[RepresentativeCell, ...] = ()


@dataclass(frozen=True)
class ReconciliationIndex:
    groups: tuple[ReconciliationGroup, ...]
    representative_cells: tuple[RepresentativeCell, ...]
    shadow_policy_cells: tuple[ShadowPolicyCell, ...] = ()
    shadow_projection_cells: tuple[ShadowProjectionCell, ...] = ()
    target_benchmark_contexts: tuple[TargetBenchmarkContext, ...] = ()
    summary: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationOutputs:
    groups_tsv: Path
    representative_cells_tsv: Path
    summary_json: Path
    gallery_html: Path


@dataclass(frozen=True)
class _SeedRecord:
    seed_group_id: str
    seed_group_basis: str
    seed_mz: str = ""
    seed_rt: str = ""
    rt_start: str = ""
    rt_end: str = ""
    ppm: str = ""
    samples: frozenset[str] = frozenset()

    @property
    def seed_rt_window(self) -> str:
        if self.rt_start or self.rt_end:
            return f"{self.rt_start or 'unknown'}-{self.rt_end or 'unknown'}"
        return ""


def run_reconciliation_gallery(
    *,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    output_dir: Path,
    alignment_matrix_tsv: Path | None = None,
    backfill_seed_audit_tsv: Path | None = None,
    overlay_batch_summary_tsvs: Sequence[Path] = (),
    seed_aware_family_tsv: Path | None = None,
    seed_aware_summary_tsv: Path | None = None,
    candidate_gate_tsv: Path | None = None,
    tier2_trace_evidence_tsv: Path | None = None,
    shadow_policy_cells_tsv: Path | None = None,
    shadow_projection_cells_tsv: Path | None = None,
    targeted_istd_benchmark_summary_tsv: Path | None = None,
    source_run_id: str = "",
) -> ReconciliationOutputs:
    """Load existing artifacts, write reconciliation indexes, and render HTML."""

    review_rows = _read_required_tsv(
        alignment_review_tsv,
        _REQUIRED_ALIGNMENT_REVIEW_COLUMNS,
    )
    cell_rows = _read_required_tsv(
        alignment_cells_tsv,
        _REQUIRED_ALIGNMENT_CELLS_COLUMNS,
    )
    matrix_rows = (
        _read_required_tsv(alignment_matrix_tsv, ())
        if alignment_matrix_tsv is not None
        else ()
    )
    seed_audit_rows = (
        _read_required_tsv(
            backfill_seed_audit_tsv,
            _REQUIRED_ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
        )
        if backfill_seed_audit_tsv is not None
        else ()
    )
    overlay_rows: list[dict[str, str]] = []
    for path in overlay_batch_summary_tsvs:
        overlay_rows.extend(
            _read_required_tsv(
                path,
                (
                    "feature_family_id",
                    "family_verdict",
                    "png_path",
                ),
            ),
        )
    seed_aware_family_rows = (
        _read_required_tsv(
            seed_aware_family_tsv,
            ("feature_family_id", "review_classification"),
        )
        if seed_aware_family_tsv is not None
        else ()
    )
    seed_aware_summary_rows = (
        _read_required_tsv(seed_aware_summary_tsv, ("feature_family_id",))
        if seed_aware_summary_tsv is not None
        else ()
    )
    candidate_gate_rows = (
        _read_required_tsv(
            candidate_gate_tsv,
            (
                "feature_family_id",
                "candidate_gate_status",
                "support_components",
                "challenge_blockers",
            ),
        )
        if candidate_gate_tsv is not None
        else ()
    )
    tier2_trace_evidence_rows = (
        _read_required_tsv(tier2_trace_evidence_tsv, ("feature_family_id",))
        if tier2_trace_evidence_tsv is not None
        else ()
    )
    shadow_policy_rows = (
        _read_required_tsv(
            shadow_policy_cells_tsv,
            BACKFILL_SHADOW_POLICY_COLUMNS,
        )
        if shadow_policy_cells_tsv is not None
        else ()
    )
    shadow_projection_rows = (
        _read_required_tsv(
            shadow_projection_cells_tsv,
            SHADOW_PRODUCTION_PROJECTION_COLUMNS,
        )
        if shadow_projection_cells_tsv is not None
        else ()
    )
    target_benchmark_rows = (
        _read_required_tsv(
            targeted_istd_benchmark_summary_tsv,
            _REQUIRED_TARGETED_ISTD_BENCHMARK_SUMMARY_COLUMNS,
        )
        if targeted_istd_benchmark_summary_tsv is not None
        else ()
    )
    input_artifacts = _input_artifact_summary(
        alignment_review_tsv=alignment_review_tsv,
        alignment_cells_tsv=alignment_cells_tsv,
        alignment_matrix_tsv=alignment_matrix_tsv,
        backfill_seed_audit_tsv=backfill_seed_audit_tsv,
        overlay_batch_summary_tsvs=overlay_batch_summary_tsvs,
        seed_aware_family_tsv=seed_aware_family_tsv,
        seed_aware_summary_tsv=seed_aware_summary_tsv,
        candidate_gate_tsv=candidate_gate_tsv,
        tier2_trace_evidence_tsv=tier2_trace_evidence_tsv,
        shadow_policy_cells_tsv=shadow_policy_cells_tsv,
        shadow_projection_cells_tsv=shadow_projection_cells_tsv,
        targeted_istd_benchmark_summary_tsv=targeted_istd_benchmark_summary_tsv,
        source_run_id=source_run_id,
    )
    input_artifacts.update(
        _input_artifact_hashes(
            alignment_review_tsv=alignment_review_tsv,
            alignment_cells_tsv=alignment_cells_tsv,
            alignment_matrix_tsv=alignment_matrix_tsv,
            backfill_seed_audit_tsv=backfill_seed_audit_tsv,
            overlay_batch_summary_tsvs=overlay_batch_summary_tsvs,
            seed_aware_family_tsv=seed_aware_family_tsv,
            seed_aware_summary_tsv=seed_aware_summary_tsv,
            candidate_gate_tsv=candidate_gate_tsv,
            tier2_trace_evidence_tsv=tier2_trace_evidence_tsv,
            shadow_policy_cells_tsv=shadow_policy_cells_tsv,
            shadow_projection_cells_tsv=shadow_projection_cells_tsv,
            targeted_istd_benchmark_summary_tsv=targeted_istd_benchmark_summary_tsv,
        ),
    )
    index = build_reconciliation_index(
        review_rows=review_rows,
        cell_rows=cell_rows,
        alignment_matrix_rows=matrix_rows,
        seed_audit_rows=seed_audit_rows,
        overlay_rows=overlay_rows,
        seed_aware_family_rows=seed_aware_family_rows,
        seed_aware_summary_rows=seed_aware_summary_rows,
        candidate_gate_rows=candidate_gate_rows,
        tier2_trace_evidence_rows=tier2_trace_evidence_rows,
        shadow_policy_rows=shadow_policy_rows,
        shadow_projection_rows=shadow_projection_rows,
        target_benchmark_rows=target_benchmark_rows,
        input_artifacts=input_artifacts,
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
    seed_aware_family_rows: Iterable[Mapping[str, str]] = (),
    seed_aware_summary_rows: Iterable[Mapping[str, str]] = (),
    candidate_gate_rows: Iterable[Mapping[str, str]] = (),
    tier2_trace_evidence_rows: Iterable[Mapping[str, str]] = (),
    shadow_policy_rows: Iterable[Mapping[str, str]] = (),
    shadow_projection_rows: Iterable[Mapping[str, str]] = (),
    target_benchmark_rows: Iterable[Mapping[str, str]] = (),
    input_artifacts: Mapping[str, object] | None = None,
) -> ReconciliationIndex:
    """Return deterministic reconciliation groups, representative cells, and summary."""

    reviews = [dict(row) for row in review_rows]
    cells = [dict(row) for row in cell_rows]
    matrices = [dict(row) for row in alignment_matrix_rows]
    seeds = [dict(row) for row in seed_audit_rows]
    overlays = [dict(row) for row in overlay_rows]
    seed_aware = [dict(row) for row in seed_aware_family_rows]
    seed_aware_summary = [dict(row) for row in seed_aware_summary_rows]
    candidates = [dict(row) for row in candidate_gate_rows]
    tier2 = [dict(row) for row in tier2_trace_evidence_rows]
    shadow_policy_cells = tuple(
        _shadow_policy_cell_from_row(row) for row in shadow_policy_rows
    )
    shadow_projection_cells = tuple(
        _shadow_projection_cell_from_row(row) for row in shadow_projection_rows
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
    overlays_by_family = _group_by_family(overlays)
    seed_aware_by_family = _first_by_family(seed_aware)
    candidate_by_family = _first_by_family(candidates)
    source_hashes = _source_hashes_from_input_artifacts(input_artifacts or {})
    tier2_families = {
        text_value(row.get("feature_family_id"))
        for row in tier2
        if row.get("feature_family_id")
    }
    family_ids, excluded_family_counts = _candidate_family_ids(
        reviews=reviews,
        cells=cells,
        seeds=seeds,
        seed_aware=seed_aware,
        seed_aware_summary=seed_aware_summary,
        candidates=candidates,
    )

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
            group_cells = _cells_for_seed_record(family_cells, seed_record)
            evidence = _classify_evidence(
                family=family,
                seed_record=seed_record,
                family_cells=family_cells,
                group_cells=group_cells,
                has_matrix_context=family in matrix_families,
                seed_samples=seed_samples_by_family.get(family, frozenset()),
                overlay_rows=_overlay_rows_for_seed_group(
                    overlays_by_family.get(family, ()),
                    seed_group_id=seed_record.seed_group_id,
                ),
                legacy_overlay_rows=_legacy_overlay_rows(
                    overlays_by_family.get(family, ()),
                ),
                seed_aware_row=seed_aware_by_family.get(family, {}),
                candidate_gate_row=candidate_by_family.get(family, {}),
                source_hashes=source_hashes,
                has_tier2_trace_evidence=family in tier2_families,
            )
            product_behavior = _product_behavior(review, family_cells)
            product_reason = _top_product_reason(review)
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
                ),
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
                source_artifacts=tuple(evidence["source_artifacts"]),
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
    summary["target_benchmark_context_counts"] = _target_benchmark_context_counts(
        target_contexts,
    )
    return ReconciliationIndex(
        groups=tuple(groups),
        representative_cells=tuple(representatives),
        shadow_policy_cells=shadow_policy_cells,
        shadow_projection_cells=shadow_projection_cells,
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
    groups = sorted(index.groups, key=_group_sort_key)
    projection_accept_keys = _shadow_projection_accept_group_keys(
        index.shadow_projection_cells,
    )
    html_groups = _html_render_groups(
        groups,
        projection_accept_keys=projection_accept_keys,
    )
    html_group_keys = {
        (group.feature_family_id, group.seed_group_id) for group in html_groups
    }
    html_family_ids = {group.feature_family_id for group in html_groups}
    html_shadow_policy_cells = tuple(
        cell
        for cell in index.shadow_policy_cells
        if (cell.feature_family_id, cell.seed_group_id) in html_group_keys
    )
    html_shadow_projection_cells = tuple(
        cell
        for cell in index.shadow_projection_cells
        if (cell.feature_family_id, cell.seed_group_id) in html_group_keys
    )
    representatives_by_group = _representatives_by_group(index.representative_cells)
    shadow_by_group = _shadow_policy_cells_by_group(html_shadow_policy_cells)
    shadow_by_family = _shadow_policy_cells_by_family(html_shadow_policy_cells)
    projection_by_group = _shadow_projection_cells_by_group(
        html_shadow_projection_cells,
    )
    projection_by_family = _shadow_projection_cells_by_family(
        html_shadow_projection_cells,
    )
    target_context_by_family = _target_benchmark_contexts_by_family(
        tuple(
            context
            for context in index.target_benchmark_contexts
            if any(family in html_family_ids for family in context.feature_family_ids)
        ),
    )
    lines = [
        "<!doctype html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Backfill evidence reconciliation gallery</title>",
        "<style>",
        _gallery_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>Backfill Evidence Reconciliation</h1>",
        *_summary_html(index, output_paths, html_path=path),
        *_html_scope_notice(groups, html_groups),
        *_filter_html(
            total_families=len(_family_groups(html_groups)),
            default_visible_families=_default_visible_family_count(html_groups),
        ),
    ]
    if not html_groups:
        lines.append(
            '<p class="empty-state">沒有 backfill family/seed group 可審閱。</p>',
        )
    else:
        lines.extend(
            _table_html(
                html_groups,
                representatives_by_group=representatives_by_group,
                shadow_policy_cells_by_group=shadow_by_group,
                shadow_policy_cells_by_family=shadow_by_family,
                shadow_projection_cells_by_group=projection_by_group,
                shadow_projection_cells_by_family=projection_by_family,
                target_benchmark_contexts_by_family=target_context_by_family,
                html_path=path,
                input_artifacts=index.summary.get("input_artifacts", {}),
            ),
        )
        lines.extend(_lightbox_html())
    lines.extend(["</main>", _lightbox_script(), "</body>", "</html>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _html_render_groups(
    groups: Sequence[ReconciliationGroup],
    *,
    projection_accept_keys: set[tuple[str, str]] | None = None,
) -> tuple[ReconciliationGroup, ...]:
    projection_accept_keys = projection_accept_keys or set()
    sorted_groups = tuple(sorted(groups, key=_group_sort_key))
    if len(sorted_groups) <= _HTML_FULL_RENDER_GROUP_LIMIT:
        return sorted_groups
    priority_groups = [
        group
        for group in sorted_groups
        if _html_priority_group(group, projection_accept_keys=projection_accept_keys)
    ]
    priority_keys = {
        (group.feature_family_id, group.seed_group_id) for group in priority_groups
    }
    inconclusive_sample = [
        group
        for group in sorted_groups
        if (group.feature_family_id, group.seed_group_id) not in priority_keys
    ][: _HTML_INCONCLUSIVE_SAMPLE_LIMIT]
    return tuple(sorted((*priority_groups, *inconclusive_sample), key=_group_sort_key))


def _html_priority_group(
    group: ReconciliationGroup,
    *,
    projection_accept_keys: set[tuple[str, str]],
) -> bool:
    return (
        (group.feature_family_id, group.seed_group_id) in projection_accept_keys
        or group.reconciliation_class != "evidence_inconclusive"
        or bool(group.overlay_png_path)
        or bool(group.overlay_trace_json_path)
        or bool(group.family_pattern_png_path)
        or bool(group.family_pattern_trace_json_path)
        or group.evidence_authority_state == "human_visual_judgment_only"
    )


def _shadow_projection_accept_group_keys(
    cells: Sequence[ShadowProjectionCell],
) -> set[tuple[str, str]]:
    return {
        (cell.feature_family_id, cell.seed_group_id)
        for cell in cells
        if _is_projected_new_accept(cell)
    }


def _html_scope_notice(
    all_groups: Sequence[ReconciliationGroup],
    html_groups: Sequence[ReconciliationGroup],
) -> list[str]:
    if len(all_groups) == len(html_groups):
        return []
    hidden = len(all_groups) - len(html_groups)
    return [
        '<div class="html-scope-note" role="note">',
        (
            f"HTML 顯示 {_escape(str(len(html_groups)))} / "
            f"{_escape(str(len(all_groups)))} groups；"
            f"{_escape(str(hidden))} 個低資訊量 inconclusive rows 只保留在 TSV/JSON。"
        ),
        "完整機器索引仍在 groups TSV 與 representatives TSV，產品決策未改變。",
        "</div>",
    ]


def _read_required_tsv(
    path: Path | None,
    required_columns: Sequence[str],
) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    try:
        return read_tsv_required(path, required_columns)
    except FileNotFoundError as exc:
        raise ValueError(f"Required TSV not found: {path}") from exc


def _input_artifact_summary(**paths: object) -> dict[str, object]:
    summary: dict[str, object] = {}
    for key, value in paths.items():
        if isinstance(value, Path):
            summary[key] = str(value)
        elif isinstance(value, Sequence) and not isinstance(value, str):
            summary[key] = [str(item) for item in value if isinstance(item, Path)]
        elif value:
            summary[key] = value
    return summary


def _input_artifact_hashes(**paths: object) -> dict[str, object]:
    hashes: dict[str, object] = {}
    for key, value in paths.items():
        if value is None:
            continue
        if isinstance(value, Path):
            hashes[f"{key.removesuffix('_tsv')}_sha256"] = _sha256_file(value)
            continue
        if isinstance(value, Sequence) and not isinstance(value, str):
            artifact_hashes = [
                {"path": str(path), "sha256": _sha256_file(path)}
                for path in value
                if isinstance(path, Path)
            ]
            if artifact_hashes:
                key_base = key.removesuffix("_tsvs").removesuffix("_tsv")
                hashes[f"{key_base}_hashes"] = artifact_hashes
    return hashes


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _source_hashes_from_input_artifacts(
    input_artifacts: Mapping[str, object],
) -> dict[str, str]:
    return {
        key: text_value(value)
        for key, value in input_artifacts.items()
        if key.endswith("_sha256") and text_value(value)
    }


def _first_by_family(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        family = text_value(row.get("feature_family_id"))
        if family and family not in result:
            result[family] = dict(row)
    return result


def _group_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[dict[str, str], ...]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        family = text_value(row.get("feature_family_id"))
        if family:
            grouped.setdefault(family, []).append(dict(row))
    return {family: tuple(items) for family, items in grouped.items()}


def _overlay_rows_for_seed_group(
    rows: Sequence[Mapping[str, str]],
    *,
    seed_group_id: str,
) -> tuple[dict[str, str], ...]:
    return tuple(
        dict(row)
        for row in rows
        if text_value(row.get("seed_group_id")) == seed_group_id
    )


def _legacy_overlay_rows(
    rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], ...]:
    return tuple(
        dict(row) for row in rows if not text_value(row.get("seed_group_id"))
    )


def _candidate_family_ids(
    *,
    reviews: Sequence[Mapping[str, str]],
    cells: Sequence[Mapping[str, str]],
    seeds: Sequence[Mapping[str, str]],
    seed_aware: Sequence[Mapping[str, str]],
    seed_aware_summary: Sequence[Mapping[str, str]],
    candidates: Sequence[Mapping[str, str]],
) -> tuple[tuple[str, ...], dict[str, int]]:
    candidate_families: set[str] = set()
    detected_families = _detected_family_ids(reviews=reviews, cells=cells)
    for row in reviews:
        family = text_value(row.get("feature_family_id"))
        if not family:
            continue
        if (
            _int_text(row.get("quantifiable_rescue_count")) > 0
            or _int_text(row.get("accepted_rescue_count")) > 0
            or "provisional" in text_value(row.get("row_flags")).lower()
            or "backfill" in text_value(row.get("identity_reason")).lower()
        ):
            candidate_families.add(family)
    for row in cells:
        family = text_value(row.get("feature_family_id"))
        if family and (
            text_value(row.get("status")).lower() == "rescued"
            or "backfill" in text_value(row.get("gap_fill_state")).lower()
        ):
            candidate_families.add(family)
    for row in (*seeds, *seed_aware, *seed_aware_summary, *candidates):
        family = text_value(row.get("feature_family_id"))
        if family:
            candidate_families.add(family)
    eligible = candidate_families & detected_families
    excluded = candidate_families - detected_families
    excluded_counts: dict[str, int] = {}
    if excluded:
        excluded_counts["detected_zero_family"] = len(excluded)
    return tuple(sorted(eligible)), excluded_counts


def _detected_family_ids(
    *,
    reviews: Sequence[Mapping[str, str]],
    cells: Sequence[Mapping[str, str]],
) -> set[str]:
    families: set[str] = set()
    for row in reviews:
        family = text_value(row.get("feature_family_id"))
        if family and (
            _int_text(row.get("detected_count")) > 0
            or _int_text(row.get("quantifiable_detected_count")) > 0
        ):
            families.add(family)
    for row in cells:
        family = text_value(row.get("feature_family_id"))
        if family and text_value(row.get("status")).lower() == "detected":
            families.add(family)
    return families


def _seed_records_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[_SeedRecord, ...]]:
    by_key: dict[tuple[str, str, str, str, str, str], set[str]] = {}
    for row in rows:
        family = text_value(row.get("feature_family_id"))
        if not family:
            continue
        seed_mz = text_value(row.get("backfill_seed_mz"))
        seed_rt = text_value(row.get("backfill_seed_rt"))
        rt_start = text_value(row.get("backfill_request_rt_min"))
        rt_end = text_value(row.get("backfill_request_rt_max"))
        ppm = text_value(row.get("backfill_request_ppm"))
        sample = text_value(row.get("sample_stem"))
        by_key.setdefault(
            (family, seed_mz, seed_rt, rt_start, rt_end, ppm),
            set(),
        ).add(sample)
    grouped: dict[str, list[_SeedRecord]] = {}
    for (family, seed_mz, seed_rt, rt_start, rt_end, ppm), samples in by_key.items():
        grouped.setdefault(family, []).append(
            _SeedRecord(
                seed_group_id=_seed_group_id(
                    family,
                    seed_mz=seed_mz,
                    seed_rt=seed_rt,
                    rt_start=rt_start,
                    rt_end=rt_end,
                    ppm=ppm,
                ),
                seed_group_basis="seed_audit",
                seed_mz=seed_mz,
                seed_rt=seed_rt,
                rt_start=rt_start,
                rt_end=rt_end,
                ppm=ppm,
                samples=frozenset(sample for sample in samples if sample),
            ),
        )
    return {
        family: tuple(sorted(records, key=lambda record: record.seed_group_id))
        for family, records in grouped.items()
    }


def _seed_samples_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, frozenset[str]]:
    samples: dict[str, set[str]] = {}
    for row in rows:
        family = text_value(row.get("feature_family_id"))
        sample = text_value(row.get("sample_stem"))
        if family and sample:
            samples.setdefault(family, set()).add(sample)
    return {family: frozenset(items) for family, items in samples.items()}


def _seed_group_id(
    family: str,
    *,
    seed_mz: str,
    seed_rt: str,
    rt_start: str,
    rt_end: str,
    ppm: str,
) -> str:
    return (
        f"seed::{family}::mz={seed_mz or 'unknown'}::"
        f"rt={seed_rt or 'unknown'}::"
        f"window={rt_start or 'unknown'}-{rt_end or 'unknown'}::"
        f"ppm={ppm or 'unknown'}"
    )


def _fallback_seed_record(family: str) -> _SeedRecord:
    return _SeedRecord(
        seed_group_id=f"family_center::{family}::seed=unknown",
        seed_group_basis="family_center_fallback",
    )


def _cells_for_seed_record(
    rows: Sequence[Mapping[str, str]],
    seed_record: _SeedRecord,
) -> tuple[Mapping[str, str], ...]:
    if not seed_record.samples:
        return tuple(rows)
    matched = [
        row for row in rows if text_value(row.get("sample_stem")) in seed_record.samples
    ]
    return tuple(matched)


def _seed_detected_anchor_count(
    rows: Sequence[Mapping[str, str]],
    *,
    seed_record: _SeedRecord,
    seed_records: Sequence[_SeedRecord],
) -> int:
    seed_rt = optional_float(seed_record.seed_rt)
    seed_rts = tuple(
        (record.seed_group_id, optional_float(record.seed_rt))
        for record in seed_records
        if optional_float(record.seed_rt) is not None
    )
    if seed_rt is None or not seed_rts:
        return _count_cells(rows, "detected") if len(seed_records) == 1 else 0
    count = 0
    for row in rows:
        if text_value(row.get("status")).lower() != "detected":
            continue
        apex_rt = optional_float(row.get("apex_rt"))
        if apex_rt is None:
            continue
        nearest_seed_group_id = min(
            seed_rts,
            key=lambda item: (
                abs(apex_rt - (item[1] if item[1] is not None else apex_rt)),
                item[0],
            ),
        )[0]
        if nearest_seed_group_id == seed_record.seed_group_id:
            count += 1
    return count


def _classify_evidence(
    *,
    family: str,
    seed_record: _SeedRecord,
    family_cells: Sequence[Mapping[str, str]],
    group_cells: Sequence[Mapping[str, str]],
    has_matrix_context: bool,
    seed_samples: frozenset[str],
    overlay_rows: Sequence[Mapping[str, str]],
    legacy_overlay_rows: Sequence[Mapping[str, str]],
    seed_aware_row: Mapping[str, str],
    candidate_gate_row: Mapping[str, str],
    source_hashes: Mapping[str, str],
    has_tier2_trace_evidence: bool,
) -> dict[str, Any]:
    product_grade: list[str] = []
    visual: list[str] = []
    dependent: list[str] = []
    blockers: list[str] = []
    human_review: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    artifacts: list[str] = ["alignment_review.tsv", "alignment_cells.tsv"]
    overlay_png_path = ""
    overlay_trace_json_path = ""
    family_pattern_png_path = ""
    family_pattern_trace_json_path = ""
    family_pattern_verdict = ""
    overlay_evidence_notes: list[str] = []

    if has_matrix_context:
        artifacts.append("alignment_matrix.tsv")
    if seed_record.seed_group_basis == "seed_audit":
        artifacts.append("alignment_owner_backfill_seed_audit.tsv")
        dependent.append("seed_request_provenance")
    else:
        missing.append("missing_seed_provenance")
    if seed_record.samples:
        cell_samples = {text_value(row.get("sample_stem")) for row in family_cells}
        if not seed_record.samples <= cell_samples:
            warnings.append("join_gap_seed_audit_sample_not_in_cells")
            missing.append("join_gap_seed_audit_sample_not_in_cells")
    if not family_cells:
        warnings.append("join_gap_family_missing_alignment_cells")
        missing.append("join_gap_family_missing_alignment_cells")

    candidate_status = text_value(candidate_gate_row.get("candidate_gate_status"))
    candidate_support = split_semicolon_labels(
        candidate_gate_row.get("support_components"),
    )
    candidate_blockers = split_semicolon_labels(
        candidate_gate_row.get("challenge_blockers"),
    )
    candidate_source_warnings = _candidate_gate_source_warnings(
        candidate_gate_row,
        source_hashes,
    )
    if candidate_status:
        artifacts.append("alignment_production_candidate_gate.tsv")
    if has_tier2_trace_evidence:
        artifacts.append("alignment_tier2_trace_evidence.tsv")
    if candidate_source_warnings:
        warnings.extend(candidate_source_warnings)
        missing.extend(candidate_source_warnings)
    if (
        candidate_status == "production_candidate"
        and candidate_support
        and not candidate_blockers
        and not candidate_source_warnings
    ):
        product_grade.extend(candidate_support)
    product_grade.extend(_product_authority_components(group_cells or family_cells))
    if candidate_blockers:
        blockers.extend(candidate_blockers)
        for blocker in candidate_blockers:
            if _is_stale_or_join_token(blocker):
                warnings.append(f"stale_candidate_gate_{blocker}")
                missing.append(f"stale_candidate_gate_{blocker}")

    if seed_aware_row:
        artifacts.append("seed_aware_backfill_review_families.tsv")
        classification = text_value(seed_aware_row.get("review_classification"))
        if classification == "seed_shape_supported_review_candidate":
            visual.append(classification)
        elif classification in {
            "neighbor_interference_review",
            "shape_insufficient_review",
        }:
            human_review.append(classification)
        elif classification == "seed_context_missing":
            missing.append("missing_seed_provenance")
        elif classification == "not_assessable":
            missing.append("missing_overlay")
        overlay_png_path = _first_path(
            seed_aware_row.get("png_paths"),
            seed_aware_row.get("png_path"),
        )
        overlay_trace_json_path = _first_path(seed_aware_row.get("trace_json_paths"))
    for row in overlay_rows:
        artifacts.append("family_ms1_overlay_batch_summary.tsv")
        verdict = text_value(row.get("family_verdict"))
        if verdict == "ms1_shape_supports_family_backfill":
            visual.append(verdict)
        elif _is_human_review_token(verdict):
            human_review.append(verdict)
        elif verdict:
            blockers.append(verdict)
        overlay_png_path = overlay_png_path or _first_path(row.get("png_path"))
        overlay_trace_json_path = overlay_trace_json_path or _first_path(
            row.get("trace_json_path"),
            row.get("json_path"),
            row.get("trace_data_json"),
        )
        overlay_evidence_notes.extend(_overlay_evidence_notes(row))
    if legacy_overlay_rows:
        row = legacy_overlay_rows[0]
        family_pattern_verdict = text_value(row.get("family_verdict"))
        family_pattern_png_path = _first_path(row.get("png_path"))
        family_pattern_trace_json_path = _first_path(
            row.get("trace_json_path"),
            row.get("json_path"),
            row.get("trace_data_json"),
        )
    if not overlay_rows and legacy_overlay_rows:
        if "family_ms1_overlay_batch_summary.tsv" not in artifacts:
            artifacts.append("family_ms1_overlay_batch_summary.tsv")
        row = legacy_overlay_rows[0]
        verdict = text_value(row.get("family_verdict"))
        dependent.append("legacy_family_overlay_context")
        if verdict:
            dependent.append(f"legacy_family_overlay:{verdict}")
        missing.append("missing_seed_specific_overlay")
    overlay_evidence_notes.extend(
        _anchor_peak_overlay_notes(
            family=family,
            scoring_cells=family_cells,
            note_cells=group_cells,
            overlay_trace_json_path=overlay_trace_json_path if overlay_rows else "",
        )
    )
    if (
        not product_grade
        and not visual
        and not blockers
        and not human_review
        and not missing
    ):
        if dependent:
            authority_state = "dependent_context_only"
        else:
            authority_state = "evidence_inconclusive"
    elif any(
        token.startswith(("join_gap_", "stale_"))
        for token in [*missing, *warnings]
    ):
        authority_state = "not_assessable"
    elif (
        "missing_seed_provenance" in missing
        or "missing_overlay" in missing
        or "missing_seed_specific_overlay" in missing
    ):
        authority_state = "not_assessable"
    elif blockers and not product_grade:
        authority_state = "evidence_blocks_backfill"
    elif human_review and not product_grade:
        authority_state = "human_visual_judgment_only"
    elif product_grade:
        authority_state = "product_grade_support"
    elif visual:
        authority_state = "review_only_visual_support"
    else:
        authority_state = "evidence_inconclusive"

    return {
        "authority_state": authority_state,
        "product_grade_support_components": tuple(_ordered_unique(product_grade)),
        "review_only_visual_components": tuple(_ordered_unique(visual)),
        "dependent_context_components": tuple(_ordered_unique(dependent)),
        "blocker_components": tuple(_ordered_unique((*blockers, *human_review))),
        "missing_evidence": tuple(_ordered_unique(missing)),
        "source_artifacts": tuple(_ordered_unique(artifacts)),
        "source_warnings": tuple(_ordered_unique(warnings)),
        "overlay_png_path": overlay_png_path,
        "overlay_trace_json_path": overlay_trace_json_path,
        "family_pattern_png_path": family_pattern_png_path,
        "family_pattern_trace_json_path": family_pattern_trace_json_path,
        "family_pattern_verdict": family_pattern_verdict,
        "overlay_evidence_notes": tuple(_ordered_unique(overlay_evidence_notes)),
    }


def _overlay_evidence_notes(row: Mapping[str, str]) -> tuple[str, ...]:
    labels = (
        ("absolute_own_max_shape_supported_fraction", "own-max shape support"),
        ("absolute_trace_apex_cluster_fraction", "absolute apex cluster"),
        ("shape_supported_fraction", "detected-anchor apex-aligned support"),
        ("local_apex_supported_fraction", "local apex support"),
        ("global_apex_interference_fraction", "global apex interference"),
        ("low_selected_peak_dominance_fraction", "low selected peak dominance"),
    )
    notes = []
    for key, label in labels:
        value = text_value(row.get(key))
        if value:
            notes.append(f"{label}={value}")
    return tuple(notes)


def _product_authority_components(
    rows: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    components: list[str] = []
    for row in rows:
        if text_value(row.get("status")).lower() != "rescued":
            continue
        _append_product_authority_component(
            components,
            row,
            prefix="backfill_ms1",
            label="product_authorized_ms1_pattern",
        )
        _append_product_authority_component(
            components,
            row,
            prefix="backfill_candidate_ms2",
            label="product_authorized_candidate_ms2",
        )
    return tuple(_ordered_unique(components))


def _append_product_authority_component(
    components: list[str],
    row: Mapping[str, str],
    *,
    prefix: str,
    label: str,
) -> None:
    status = text_value(row.get(f"{prefix}_product_authority_status"))
    if status != "product_authorized":
        return
    scope = text_value(row.get(f"{prefix}_product_authority_scope"))
    source = text_value(row.get(f"{prefix}_product_authority_source"))
    if scope != "feature_family_sample" or not source:
        return
    reason = text_value(row.get(f"{prefix}_product_authority_reason")) or source
    components.append(f"{label}:{reason}")


def _anchor_peak_overlay_notes(
    *,
    family: str,
    scoring_cells: Sequence[Mapping[str, str]],
    note_cells: Sequence[Mapping[str, str]],
    overlay_trace_json_path: str,
) -> tuple[str, ...]:
    path = _existing_path_from_text(overlay_trace_json_path)
    if path is None or not scoring_cells or not note_cells:
        return ()
    oracle_keys = tuple(
        (family, sample)
        for row in note_cells
        if (sample := text_value(row.get("sample_stem")))
    )
    if not oracle_keys:
        return ()
    try:
        from xic_extractor.alignment.shared_peak_identity_explanation import (
            ms1_pattern_coherence,
        )

        rows = ms1_pattern_coherence.build_ms1_pattern_coherence_rows_from_cell_rows(
            cell_rows=scoring_cells,
            oracle_keys=oracle_keys,
            family_ms1_overlay_trace_data_jsons=(path,),
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return ("anchor peak evidence=unavailable",)

    status_by_sample = {
        text_value(row.get("sample_stem")): text_value(row.get("status")).lower()
        for row in note_cells
    }
    anchor_rt = next(
        (
            text_value(row.get("anchor_peak_rt"))
            for row in rows
            if row.get("anchor_peak_rt")
        ),
        "",
    )
    if not anchor_rt:
        return ()
    support: list[str] = []
    review: list[str] = []
    blocked: list[str] = []
    for row in rows:
        sample = text_value(row.get("sample_stem"))
        if status_by_sample.get(sample) != "rescued":
            continue
        reason = text_value(row.get("reason"))
        score = text_value(row.get("shape_correlation_score"))
        token = f"{sample}({score})" if score else sample
        if reason == _ANCHOR_SHAPE_SUPPORTED_REASON:
            support.append(token)
        elif reason == _ANCHOR_SHAPE_REVIEW_REASON:
            review.append(token)
        elif reason:
            blocked.append(f"{sample}:{reason}")
    notes = [
        f"anchor peak RT={anchor_rt}",
        "anchor own-max shape threshold=0.5",
    ]
    if support:
        notes.append(
            "anchor same-peak rescued support="
            + _compact_note_items(tuple(support)),
        )
    if review:
        notes.append(
            "anchor same-peak review="
            + _compact_note_items(tuple(review)),
        )
    if blocked:
        notes.append("anchor blocked cells=" + _compact_note_items(tuple(blocked)))
    return tuple(notes)


def _existing_path_from_text(path_text: str) -> Path | None:
    value = text_value(path_text)
    if not value:
        return None
    raw = Path(value)
    for candidate in (raw, Path.cwd() / raw):
        if candidate.exists():
            return candidate.resolve()
    return None


def _compact_note_items(items: Sequence[str], *, limit: int = 4) -> str:
    shown = list(items[:limit])
    remaining = len(items) - len(shown)
    if remaining > 0:
        shown.append(f"+{remaining} more")
    return ", ".join(shown)


def _is_stale_or_join_token(token: str) -> bool:
    lowered = token.lower()
    return "source_hash_mismatch" in lowered or "stale" in lowered or "join" in lowered


def _is_human_review_token(token: str) -> bool:
    lowered = token.lower()
    return lowered.startswith(_HUMAN_REVIEW_PREFIXES) or lowered in _HUMAN_REVIEW_TOKENS


def _candidate_gate_source_warnings(
    candidate_gate_row: Mapping[str, str],
    source_hashes: Mapping[str, str],
) -> tuple[str, ...]:
    if not source_hashes or not candidate_gate_row:
        return ()
    checks = (
        ("review", "source_review_sha256", "alignment_review_sha256"),
        ("cell", "source_cell_sha256", "alignment_cells_sha256"),
        ("matrix", "source_matrix_sha256", "alignment_matrix_sha256"),
    )
    warnings: list[str] = []
    for label, row_key, input_key in checks:
        expected = text_value(source_hashes.get(input_key))
        if not expected:
            continue
        observed = text_value(candidate_gate_row.get(row_key))
        if not observed:
            warnings.append(f"stale_candidate_gate_missing_{label}_sha256")
        elif observed.lower() != expected.lower():
            warnings.append(f"stale_candidate_gate_{label}_sha256_mismatch")
    return tuple(warnings)


def _product_behavior(
    review_row: Mapping[str, str],
    cell_rows: Sequence[Mapping[str, str]],
) -> str:
    if not review_row and not cell_rows:
        return "product_unknown"
    include_primary = bool_value(review_row.get("include_in_primary_matrix"))
    rescued_cells = [
        row for row in cell_rows if text_value(row.get("status")).lower() == "rescued"
    ]
    primary_rescued = any(
        text_value(row.get("primary_matrix_area_source")) for row in rescued_cells
    )
    if include_primary and (rescued_cells or primary_rescued):
        return "product_primary_backfilled"
    if rescued_cells:
        return "product_rescued_context_only"
    identity = text_value(review_row.get("identity_decision")).lower()
    flags = text_value(review_row.get("row_flags")).lower()
    confidence = text_value(review_row.get("identity_confidence")).lower()
    if "provisional" in identity or "provisional" in flags:
        return "product_provisional"
    if "review" in identity or "review" in confidence:
        return "product_review_only"
    return "product_not_backfilled"


def _reconciliation_class(
    product_behavior_state: str,
    evidence_authority_state: str,
    missing_evidence: tuple[str, ...],
    source_warnings: tuple[str, ...],
) -> str:
    tokens = set(missing_evidence) | set(source_warnings)
    if evidence_authority_state == "not_assessable":
        if any(token.startswith(("join_gap_", "stale_")) for token in tokens):
            return "not_assessable_join_gap"
        if "missing_seed_provenance" in tokens:
            return "not_assessable_missing_seed_provenance"
        return "not_assessable_missing_overlay"
    if evidence_authority_state == "evidence_inconclusive":
        return "evidence_inconclusive"
    if evidence_authority_state == "human_visual_judgment_only":
        return "evidence_inconclusive"
    product_accepts = product_behavior_state == "product_primary_backfilled"
    if evidence_authority_state == "product_grade_support":
        return (
            "product_accepts_and_product_grade_supports"
            if product_accepts
            else "product_rejects_but_product_grade_supports"
        )
    if evidence_authority_state == "review_only_visual_support":
        return (
            "product_accepts_and_visual_supports"
            if product_accepts
            else "product_rejects_but_visual_supports"
        )
    if evidence_authority_state == "evidence_blocks_backfill":
        return (
            "product_accepts_but_evidence_conflicts"
            if product_accepts
            else "product_rejects_and_evidence_blocks"
        )
    return "evidence_inconclusive"


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


def _compact_counts_text(counts: Mapping[str, int]) -> str:
    return " · ".join(f"{key} {value}" for key, value in counts.items() if value)


def _target_benchmark_summary_text(
    contexts: Sequence[TargetBenchmarkContext],
    counts: Mapping[str, int],
    input_artifacts: object,
) -> str:
    if contexts:
        return "context only · " + (_compact_counts_text(counts) or "matched")
    if _target_benchmark_supplied(input_artifacts):
        return "context only · no matched target family"
    return "not supplied"


def _summary_html(
    index: ReconciliationIndex,
    output_paths: Mapping[str, Path],
    *,
    html_path: Path,
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


def _summary_item(css_class: str, label: str, value: str) -> str:
    return (
        f'<div class="summary-item {css_class}">'
        f"<span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"
    )


def _artifact_links(
    output_paths: Mapping[str, Path],
    *,
    html_path: Path,
) -> list[str]:
    if not output_paths:
        return []
    links: list[str] = []
    label_by_key = {
        "groups_tsv": "groups TSV",
        "representative_cells_tsv": "representatives TSV",
        "summary_json": "summary JSON",
    }
    for key, path in output_paths.items():
        label = label_by_key.get(key, key.replace("_", " "))
        href = _href_for_path(path, html_path)
        links.append(
            f'<a href="{_escape_attr(href)}" title="{_escape_attr(str(path))}">'
            f"{_escape(label)}</a>",
        )
    return [
        '<div class="artifact-strip" aria-label="generated output artifacts">'
        "<span>Outputs</span>"
        f"{' '.join(links)}"
        "</div>",
    ]


def _target_benchmark_panel_html(
    contexts: Sequence[TargetBenchmarkContext],
    input_artifacts: object,
    counts: Mapping[str, int],
) -> list[str]:
    if not contexts and not _target_benchmark_supplied(input_artifacts):
        return []
    summary = _target_benchmark_summary_text(contexts, counts, input_artifacts)
    return [
        '<details class="provenance-panel target-benchmark-panel" open>',
        f"<summary>Target benchmark · {_escape(summary)}</summary>",
        _target_benchmark_contexts_html(contexts, input_artifacts),
        "</details>",
    ]


def _input_artifact_links(
    input_artifacts: object,
    *,
    html_path: Path,
) -> list[str]:
    if not isinstance(input_artifacts, Mapping):
        return []
    path_rows = _input_artifact_path_rows(input_artifacts)
    source_run_id = text_value(input_artifacts.get("source_run_id"))
    if not path_rows and not source_run_id:
        return []
    file_label = "1 file" if len(path_rows) == 1 else f"{len(path_rows)} files"
    source_label = f" · source={source_run_id}" if source_run_id else ""
    link_items: list[str] = []
    for label, path_text in path_rows:
        link_html = _path_link_html(
            path_text,
            html_path=html_path,
            label=_compact_path_label(path_text),
        )
        link_items.append(
            "<li>"
            f'<span class="artifact-label">{_escape(label)}</span>'
            f"{link_html}"
            "</li>",
        )
    links = "".join(link_items)
    return [
        '<details class="provenance-panel">',
        f"<summary>Input artifacts · {file_label}{_escape(source_label)}</summary>",
        f'<ul class="provenance-list">{links}</ul>',
        "</details>",
    ]


def _source_artifacts_html(
    source_artifacts: Sequence[str],
    input_artifacts: object,
    html_path: Path,
) -> str:
    if not source_artifacts:
        return "none"
    path_map = _input_artifact_paths_by_label(input_artifacts)
    items: list[str] = []
    for artifact in source_artifacts:
        linked_paths = path_map.get(artifact, ())
        if not linked_paths:
            items.append(f"<li>{_escape(artifact)}</li>")
            continue
        for path_text in linked_paths:
            path_link = _path_link_html(
                path_text,
                html_path=html_path,
                label=_compact_path_label(path_text),
            )
            items.append(
                "<li>"
                f"{_escape(artifact)}: "
                f"{path_link}"
                "</li>",
            )
    return '<ul class="path-list">' + "".join(items) + "</ul>"


def _input_artifact_paths_by_label(
    input_artifacts: object,
) -> dict[str, tuple[str, ...]]:
    paths_by_label: dict[str, list[str]] = {}
    if not isinstance(input_artifacts, Mapping):
        return {}
    for label, path_text in _input_artifact_path_rows(input_artifacts):
        paths_by_label.setdefault(label, []).append(path_text)
    return {label: tuple(paths) for label, paths in paths_by_label.items()}


def _input_artifact_path_rows(
    input_artifacts: Mapping[str, object],
) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for key, label in _INPUT_ARTIFACT_LABEL_BY_KEY.items():
        value = input_artifacts.get(key)
        if isinstance(value, Sequence) and not isinstance(value, str):
            rows.extend((label, str(item)) for item in value if item)
        elif value:
            rows.append((label, str(value)))
    return tuple(rows)


def _path_link_html(path_text: str, *, html_path: Path, label: str) -> str:
    href = _href_for_path(path_text, html_path)
    if not href:
        return _escape(label)
    return (
        f'<a href="{_escape_attr(href)}" title="{_escape_attr(path_text)}">'
        f"{_escape(label)}</a>"
    )


def _compact_path_label(path_text: str) -> str:
    parts = [part for part in _slash_path(path_text).split("/") if part]
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return text_value(path_text)


def _href_for_path(value: object, html_path: Path) -> str:
    href = _safe_href(text_value(value))
    if not href:
        return ""
    if _detected_url_scheme(href):
        return _slash_path(href)
    raw_path = Path(href)
    target: Path
    if raw_path.is_absolute():
        target = raw_path
    else:
        resolved_target: Path | None = None
        for candidate in (html_path.parent / raw_path, Path.cwd() / raw_path):
            if candidate.exists():
                resolved_target = candidate.resolve()
                break
        if resolved_target is None:
            return _slash_path(href)
        target = resolved_target
    try:
        return _slash_path(os.path.relpath(target, html_path.parent))
    except ValueError:
        return _slash_path(str(target))


def _slash_path(value: str) -> str:
    return value.replace("\\", "/")


def _filter_html(
    *,
    total_families: int,
    default_visible_families: int,
) -> list[str]:
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
            for value, label in _REVIEW_FILTER_LABELS.items()
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
            "Review=review-rescued target cells, Accept/Block=projected shadow "
            "outcome. Without projection "
            "input: NL/Fill/Dup/Review remain alignment provenance counts, not target "
            'benchmark coverage.">'
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


def _is_projected_new_accept(cell: ShadowProjectionCell) -> bool:
    projected_value = optional_float(cell.projected_matrix_value)
    return (
        cell.shadow_decision == "accept"
        and cell.projected_matrix_written
        and not cell.current_matrix_written
        and projected_value is not None
        and projected_value > 0
    )


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
        f'<span class="issue-text {detail_class}" title="{_escape_attr(detail)}">'
        f"{_escape(_compact_issue_label(detail))}</span>"
        "</div>"
    )


def _state_html(group: ReconciliationGroup) -> str:
    return _state_html_for_shadow(group, ())


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
    return (
        '<div class="state-stack" aria-label="product and evidence state">'
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
    return _impact_counts_html(
        detected=group.detected_cell_count,
        rescued=group.rescued_cell_count,
        duplicate=group.duplicate_assigned_cell_count,
        provisional=group.provisional_cell_count,
        aria_label=(
            "NL anchors are family detected required-tag anchors; "
            "Fill is hypothesis rescued/backfilled cells; "
            "Dup is family duplicate-assigned cell context; "
            "Review is hypothesis provisional cell context. "
            "These are alignment cell provenance counts, not target benchmark coverage."
        ),
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
            "written by the production-decision snapshot; Review is "
            "review-rescued candidate cells; Accept is projected writable cells; "
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
        _count_pill("Current", "current production-decision written cells", current),
        _count_pill("Review", "review-rescued candidate cells", review),
        _count_pill("Accept", "shadow projected accepted cells", accept),
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
        _count_pill("Fill", "hypothesis rescued/backfilled cells", rescued),
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
        "product_accepts_and_visual_supports": "accepts + visual support",
        "product_rejects_but_visual_supports": "rejects + visual support",
        "product_accepts_but_evidence_conflicts": "accepts + evidence conflict",
        "not_assessable_missing_overlay": "missing overlay",
        "not_assessable_missing_seed_provenance": "missing seed provenance",
        "not_assessable_join_gap": "join gap",
    }
    if text in replacements:
        return replacements[text]
    return text.replace("_", " ")


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
            f"{_family_pattern_link_html(ordered_groups, html_path)}</td>"
        ),
        '<td class="cell-details" data-label="chain">',
        '<span class="detail-hint">seed rows below</span>',
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
            '<span class="seed-index">hypothesis H1</span>'
            f'<span class="seed-summary">1 MS1 hypothesis · '
            f"{len(groups)} seed aliases</span>"
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
        (
            '<span class="detail-hint">'
            f"{len(groups)} seed aliases · consolidated hypothesis</span>"
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
            "<span>seed aliases collapsed under one product hypothesis；"
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
            "Fill and Review are summed seed-alias rescued/provisional cells; "
            "Dup is family duplicate-assigned cell context."
        ),
    )


def _consolidated_overlay_cell_html(
    groups: Sequence[ReconciliationGroup],
    *,
    html_path: Path,
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
        return '<span class="overlay-scope muted">no consolidated overlay</span>'
    hypothesis_link = _hypothesis_overlay_link_html(unique_groups[0], html_path)
    family_link = _overlay_link_html(
        unique_groups[0],
        html_path,
        label="family context",
        caption=(
            f"{unique_groups[0].feature_family_id} | family MS1 pattern context"
        ),
    )
    if hypothesis_link and family_link:
        return (
            f"{hypothesis_link}<br>"
            f"{family_link}<br>"
            '<span class="overlay-scope">1 hypothesis evidence · '
            "family context retained</span>"
        )
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
        return '<span class="overlay-scope muted">no consolidated overlay</span>'
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
        '<p class="chain-note">'
        "seed aliases collapsed under one product hypothesis because the "
        "alignment review marked this family as primary_family_consolidated. "
        "The aliases remain below as provenance; they are not separate peak "
        "decisions.</p>"
        + _seed_alias_table_html(groups, html_path)
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
        "<h3>Projection accept cells</h3>"
        '<p class="chain-note">'
        "Only blank review-rescued cells that shadow projection would turn into "
        "writes are listed here; projection_only, product output is unchanged.</p>"
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
            f'<span class="seed-index">H{seed_index}</span>'
            '<span class="seed-summary">1 seed request</span>'
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
        (
            '<span class="detail-hint">'
            f"{_escape(_seed_detail_summary(group, seed_index))}</span>"
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


def _family_target_summary_html(
    contexts: Sequence[TargetBenchmarkContext],
) -> str:
    if not contexts:
        return ""
    labels = [
        f"{context.target_label} {context.status}".strip()
        for context in sorted(contexts, key=_target_benchmark_context_sort_key)
    ]
    label = "target context " + " / ".join(labels[:2])
    if len(labels) > 2:
        label += f" / +{len(labels) - 2}"
    return f'<span class="target-status">{_escape(label)}</span>'


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


def _family_pattern_link_html(
    groups: Sequence[ReconciliationGroup],
    html_path: Path,
) -> str:
    for group in groups:
        href = _href_for_path(group.family_pattern_png_path, html_path)
        if not href:
            continue
        caption = f"{group.feature_family_id} | family MS1 pattern context only"
        return (
            f'<a class="png-link pattern-link" href="{_escape_attr(href)}" '
            f'data-lightbox-src="{_escape_attr(href)}" '
            f'data-lightbox-caption="{_escape_attr(caption)}" '
            'data-lightbox-title="FAMILY CONTEXT" '
            'data-lightbox-interpretation="Absolute RT own-max and raw '
            'intensity context; not a seed-specific decision." '
            'title="family MS1 pattern context only">pattern PNG</a>'
        )
    for group in groups:
        href = _href_for_path(group.overlay_png_path, html_path)
        if not href:
            continue
        caption = f"{group.feature_family_id} | family MS1 context fallback"
        return (
            f'<a class="png-link pattern-link" href="{_escape_attr(href)}" '
            f'data-lightbox-src="{_escape_attr(href)}" '
            f'data-lightbox-caption="{_escape_attr(caption)}" '
            'data-lightbox-title="FAMILY CONTEXT" '
            'data-lightbox-interpretation="Family/header context only; '
            'child-row hypothesis PNG is shown only when generated." '
            'title="family MS1 context fallback">family context</a>'
        )
    return '<span class="overlay-scope muted">no context</span>'


def _family_overlay_links(
    groups: Sequence[ReconciliationGroup],
    html_path: Path,
) -> str:
    links: list[str] = []
    seen_hrefs: set[str] = set()
    unique_items: list[tuple[int, ReconciliationGroup]] = []
    for index, group in enumerate(groups, start=1):
        href = _href_for_path(group.overlay_png_path, html_path)
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        unique_items.append((index, group))
    if not unique_items:
        return "no overlay"
    if len(groups) > 1 and len(unique_items) == 1:
        _, group = unique_items[0]
        link = _overlay_link_html(
            group,
            html_path,
            label="shared family context",
            caption=f"{group.feature_family_id} | shared family MS1 context",
        )
        if link:
            links.append(link)
        links.append(
            '<span class="overlay-scope" '
            'title="This PNG is family-level, not seed-specific.">'
            "shared family context · not seed-specific</span>",
        )
        return "<br>".join(links)
    for index, group in unique_items:
        label = "family context PNG" if len(groups) == 1 else f"H{index} family context"
        link = _overlay_link_html(group, html_path, label=label)
        if link:
            links.append(link)
    return "<br>".join(links) if links else "no overlay"


def _overlay_link_html(
    group: ReconciliationGroup,
    html_path: Path,
    *,
    label: str = "PNG",
    caption: str | None = None,
    scope: str = "FAMILY CONTEXT",
    interpretation: str = (
        "Family-level MS1 context; use hypothesis evidence when available."
    ),
) -> str:
    png_href = _href_for_path(group.overlay_png_path, html_path)
    if not png_href:
        return ""
    lightbox_caption = (
        caption
        if caption is not None
        else f"{group.feature_family_id} | {group.seed_group_id}"
    )
    return (
        f'<a class="png-link" href="{_escape_attr(png_href)}" '
        f'data-lightbox-src="{_escape_attr(png_href)}" '
        f'data-lightbox-caption="{_escape_attr(lightbox_caption)}" '
        f'data-lightbox-title="{_escape_attr(scope)}" '
        f'data-lightbox-interpretation="{_escape_attr(interpretation)}">'
        f"{_escape(label)}</a>"
    )


def _path_overlay_link_html(
    path_text: str,
    html_path: Path,
    *,
    label: str,
    caption: str,
    scope: str,
    interpretation: str,
) -> str:
    png_href = _href_for_path(path_text, html_path)
    if not png_href:
        return ""
    return (
        f'<a class="png-link" href="{_escape_attr(png_href)}" '
        f'data-lightbox-src="{_escape_attr(png_href)}" '
        f'data-lightbox-caption="{_escape_attr(caption)}" '
        f'data-lightbox-title="{_escape_attr(scope)}" '
        f'data-lightbox-interpretation="{_escape_attr(interpretation)}">'
        f"{_escape(label)}</a>"
    )


def _hypothesis_overlay_path(
    group: ReconciliationGroup,
    html_path: Path,
) -> str:
    value = _safe_href(text_value(group.overlay_png_path))
    if not value or _detected_url_scheme(value):
        return ""
    raw_path = Path(value)
    candidates = (
        (raw_path,)
        if raw_path.is_absolute()
        else (html_path.parent / raw_path, Path.cwd() / raw_path)
    )
    for candidate in candidates:
        suffix = candidate.suffix or ".png"
        hypothesis_path = candidate.with_name(f"{candidate.stem}_hypothesis{suffix}")
        if hypothesis_path.exists():
            return str(hypothesis_path)
    return ""


def _hypothesis_overlay_link_html(
    group: ReconciliationGroup,
    html_path: Path,
    *,
    label: str = "hypothesis PNG",
) -> str:
    path = _hypothesis_overlay_path(group, html_path)
    if not path:
        return ""
    caption = (
        f"{group.feature_family_id} | m/z {group.seed_mz or 'unknown'} | "
        f"RT {group.seed_rt or 'unknown'} | detected-anchor hypothesis evidence"
    )
    return _path_overlay_link_html(
        path,
        html_path,
        label=label,
        caption=caption,
        scope="HYPOTHESIS EVIDENCE",
        interpretation=(
            "Detected-anchor apex-aligned MS1 shape plus selected-peak raw intensity."
        ),
    )


def _overlay_href_context(
    groups: Sequence[ReconciliationGroup],
    html_path: Path,
) -> tuple[Counter[str], dict[str, int]]:
    href_counts: Counter[str] = Counter()
    first_index_by_href: dict[str, int] = {}
    for index, group in enumerate(groups, start=1):
        href = _href_for_path(group.overlay_png_path, html_path)
        if not href:
            continue
        href_counts[href] += 1
        first_index_by_href.setdefault(href, index)
    return href_counts, first_index_by_href


def _seed_overlay_cell_html(
    group: ReconciliationGroup,
    *,
    seed_index: int,
    html_path: Path,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
    total_seed_groups: int,
) -> str:
    href = _href_for_path(group.overlay_png_path, html_path)
    if not href:
        return "no overlay"
    hypothesis_link = _hypothesis_overlay_link_html(group, html_path)
    if hypothesis_link:
        family_link = _overlay_link_html(
            group,
            html_path,
            label="family context",
            caption=f"{group.feature_family_id} | family MS1 pattern context",
        )
        if family_link:
            return f"{hypothesis_link}<br>{family_link}"
        return hypothesis_link
    if href_counts.get(href, 0) <= 1:
        label = (
            "family context PNG"
            if total_seed_groups == 1
            else f"H{seed_index} family context"
        )
        return _overlay_link_html(group, html_path, label=label) or "no overlay"
    first_index = first_index_by_href.get(href, seed_index)
    if first_index != seed_index:
        return (
            '<span class="overlay-scope muted" '
            f'title="Same shared family context as H{first_index}; '
            'not seed-specific.">'
            f"same family context as H{first_index}</span>"
        )
    link = _overlay_link_html(
        group,
        html_path,
        label="shared family context",
        caption=f"{group.feature_family_id} | shared family MS1 context",
    )
    if not link:
        return "no overlay"
    return (
        f"{link}<br>"
        '<span class="overlay-scope" '
        'title="This PNG is family-level, not seed-specific.">'
        "shared family context · not hypothesis evidence</span>"
    )


def _seed_table_row_html(
    index: int,
    group: ReconciliationGroup,
    *,
    html_path: Path,
    href_counts: Mapping[str, int],
    first_index_by_href: Mapping[str, int],
) -> str:
    overlay_html = _seed_overlay_cell_html(
        group,
        seed_index=index,
        html_path=html_path,
        href_counts=href_counts,
        first_index_by_href=first_index_by_href,
        total_seed_groups=max(len(first_index_by_href), 1),
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
        _detail_summary_html(
            group,
            representatives,
            html_path=html_path,
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
                f'{_escape(group.top_product_reason or "no product reason supplied")}'
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
        + _chain_item_html(
            "Shadow production projection",
            _shadow_projection_compact_summary(shadow_projection_cells)
            or "not supplied",
            _shadow_projection_cells_html(shadow_projection_cells, html_path),
            css_class="shadow-projection-chain",
        )
        + _chain_item_html(
            _shadow_policy_chain_title(shadow_projection_cells),
            _shadow_policy_chain_subtitle(shadow_policy_cells, shadow_projection_cells),
            _shadow_policy_cells_html(
                shadow_policy_cells,
                html_path,
                legacy_reference=bool(shadow_projection_cells),
            ),
            css_class="shadow-policy-chain",
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
            "hypothesis first, family context second",
            _detail_visual_summary_html(group, html_path),
        )
        + _detail_summary_card_html(
            "cell impact",
            f"{len(representatives)} representative cells",
            (
                _counts_html(group, shadow_projection_cells)
                + _cell_impact_legend_note_html(shadow_projection_cells)
                + _shadow_projection_summary_note_html(shadow_projection_cells)
                + _shadow_policy_summary_note_html(shadow_policy_cells)
            ),
        )
        + "</div>"
    )


def _detail_summary_card_html(title: str, subtitle: str, body_html: str) -> str:
    return (
        '<section class="detail-summary-card">'
        f"<h3>{_escape(title)}</h3>"
        f'<p class="summary-subtitle">{_escape(subtitle)}</p>'
        f'<div class="summary-body">{body_html}</div>'
        "</section>"
    )


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


def _detail_visual_summary_html(group: ReconciliationGroup, html_path: Path) -> str:
    link = _hypothesis_overlay_link_html(group, html_path) or _overlay_link_html(
        group,
        html_path,
        label="family context",
    )
    link_html = (
        f'<p class="summary-link">{link}</p>'
        if link
        else '<p class="chain-note">No overlay PNG supplied.</p>'
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
    shadow_projection_cells: Sequence[ShadowProjectionCell],
) -> str:
    if shadow_projection_cells:
        return (
            '<p class="chain-note">'
            "Current=目前 production decision snapshot 會寫入的 cells；"
            "Review=review-rescued candidate cells；"
            "Accept=shadow projection 認為可寫入的 review cells；"
            "Block=hard blockers；Context=仍需人審/duplicate/debug；"
            "projection_only，不會直接改 matrix。</p>"
        )
    return (
        '<p class="chain-note">NL=detected required-tag anchors；'
        "Fill=目前 hypothesis 的 rescued/backfilled cells；"
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
        "會如何解讀既有 rescued cells，不會修改 product output。"
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


def _shadow_projection_overlay_link_html(
    cell: ShadowProjectionCell,
    html_path: Path,
) -> str:
    png_href = _href_for_path(cell.overlay_png_path, html_path)
    if not png_href:
        return "no overlay"
    caption = f"{cell.feature_family_id} | {cell.seed_group_id} | {cell.sample_stem}"
    return (
        f'<a class="png-link" href="{_escape_attr(png_href)}" '
        f'data-lightbox-src="{_escape_attr(png_href)}" '
        f'data-lightbox-caption="{_escape_attr(caption)}">PNG</a>'
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


def _shadow_policy_overlay_link_html(
    cell: ShadowPolicyCell,
    html_path: Path,
) -> str:
    png_href = _href_for_path(cell.overlay_png_path, html_path)
    if not png_href:
        return "no overlay"
    caption = f"{cell.feature_family_id} | {cell.seed_group_id} | {cell.sample_stem}"
    return (
        f'<a class="png-link" href="{_escape_attr(png_href)}" '
        f'data-lightbox-src="{_escape_attr(png_href)}" '
        f'data-lightbox-caption="{_escape_attr(caption)}">PNG</a>'
    )


def _target_benchmark_compact_summary(
    contexts: Sequence[TargetBenchmarkContext],
    input_artifacts: object,
) -> str:
    if contexts:
        if len(contexts) == 1:
            context = contexts[0]
            label = context.target_label or "target"
            status = context.status or "UNKNOWN"
            coverage = _target_coverage_text(context)
            return f"{label} {status} · {coverage}"
        counts = Counter(context.status or "UNKNOWN" for context in contexts)
        return "matched targets: " + ", ".join(
            f"{status}={count}" for status, count in sorted(counts.items())
        )
    if _target_benchmark_supplied(input_artifacts):
        return "benchmark not matched to this family"
    return "not supplied"


def _target_benchmark_contexts_html(
    contexts: Sequence[TargetBenchmarkContext],
    input_artifacts: object,
) -> str:
    if not contexts:
        if _target_benchmark_supplied(input_artifacts):
            return (
                '<p class="chain-note">'
                "targeted benchmark summary 已提供，但這個 family 沒有對到 "
                "selected/primary target feature；可視為 benchmark context miss，"
                "不是 production identity decision。</p>"
            )
        return (
            '<p class="chain-note">'
            "No targeted benchmark summary supplied for this gallery run.</p>"
        )
    rows = "".join(
        "<tr>"
        f"<td>{_escape(context.target_label)}</td>"
        f"<td>{_escape(context.role)}</td>"
        f"<td>{_badge(context.status or 'UNKNOWN')}</td>"
        f"<td>{_escape(_target_coverage_text(context))}</td>"
        f"<td>{_escape(context.selected_feature_id or 'none')}</td>"
        f"<td>{_escape(';'.join(context.failure_modes) or 'none')}</td>"
        f"<td>{_escape(context.note or 'none')}</td>"
        "</tr>"
        for context in sorted(contexts, key=_target_benchmark_context_sort_key)
    )
    return (
        '<p class="chain-note">'
        "benchmark context only；target benchmark 可作驗收/定位 target context，"
        "但不會改 product identity 或 backfill decision。</p>"
        '<div class="target-benchmark-table-wrap">'
        '<table class="target-benchmark-table">'
        "<thead><tr>"
        '<th scope="col">target</th>'
        '<th scope="col">role</th>'
        '<th scope="col">status</th>'
        '<th scope="col">coverage</th>'
        '<th scope="col">selected family</th>'
        '<th scope="col">failure modes</th>'
        '<th scope="col">note</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _target_coverage_text(context: TargetBenchmarkContext) -> str:
    parts = []
    if context.untargeted_positive_count or context.targeted_positive_count:
        parts.append(
            f"untargeted {context.untargeted_positive_count or '?'}"
            f"/targeted {context.targeted_positive_count or '?'}",
        )
    if context.coverage_minimum:
        parts.append(f"min {context.coverage_minimum}")
    return " · ".join(parts) or "not supplied"


def _target_benchmark_supplied(input_artifacts: object) -> bool:
    return isinstance(input_artifacts, Mapping) and bool(
        input_artifacts.get("targeted_istd_benchmark_summary_tsv"),
    )


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
        f'<span class="chain-state">{_escape(state)}</span>'
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
        + "".join(f"<li>{_escape(item)}</li>" for item in cleaned)
        + "</ul>"
    )


def _representative_cells_table_html(
    representatives: Sequence[RepresentativeCell],
) -> str:
    rep_rows = "".join(
        "<tr>"
        f"<td>{_escape(';'.join(cell.representative_roles))}</td>"
        f"<td>{_escape(cell.sample_stem)}</td>"
        f"<td>{_escape(cell.cell_status)}</td>"
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


def _lightbox_html() -> list[str]:
    return [
        '<div class="lightbox" role="dialog" aria-modal="true" '
        'aria-labelledby="lightboxTitle" aria-describedby="lightboxCaption" hidden>',
        '<div class="lightbox-panel">',
        '<div class="lightbox-header">',
        "<div>",
        '<h2 id="lightboxTitle">MS1 Evidence PNG</h2>',
        '<p id="lightboxCaption" class="lightbox-caption"></p>',
        '<p id="lightboxInterpretation" class="lightbox-interpretation"></p>',
        "</div>",
        '<div class="lightbox-actions">',
        '<a class="lightbox-direct" href="">Open PNG</a>',
        '<button type="button" class="lightbox-close" aria-label="Close PNG lightbox">'
        "Close</button>",
        "</div>",
        "</div>",
        '<img class="lightbox-image" alt="">',
        "</div>",
        "</div>",
    ]


def _lightbox_script() -> str:
    return """
<script>
(() => {
  const modal = document.querySelector('.lightbox');
  if (!modal) return;
  const image = modal.querySelector('.lightbox-image');
  const title = modal.querySelector('#lightboxTitle');
  const caption = modal.querySelector('.lightbox-caption');
  const interpretation = modal.querySelector('.lightbox-interpretation');
  const direct = modal.querySelector('.lightbox-direct');
  const close = modal.querySelector('.lightbox-close');
  let previousFocus = null;
  const openModal = (link) => {
    previousFocus = document.activeElement;
    image.src = link.dataset.lightboxSrc;
    image.alt = link.dataset.lightboxCaption || 'overlay PNG';
    title.textContent = link.dataset.lightboxTitle || 'MS1 Evidence PNG';
    caption.textContent = link.dataset.lightboxCaption || '';
    interpretation.textContent = link.dataset.lightboxInterpretation || '';
    direct.href = link.href || link.dataset.lightboxSrc;
    modal.hidden = false;
    close.focus();
  };
  const closeModal = () => {
    modal.hidden = true;
    image.removeAttribute('src');
    direct.removeAttribute('href');
    if (previousFocus && previousFocus.focus) previousFocus.focus();
  };
  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-lightbox-src]');
    if (!link) return;
    event.preventDefault();
    openModal(link);
  });
  document.addEventListener('keydown', (event) => {
    const activeLink = event.target.closest('[data-lightbox-src]');
    const isOpenKey = event.key === 'Enter' || event.key === ' ' ||
      event.key === 'Spacebar';
    if (activeLink && isOpenKey) {
      event.preventDefault();
      openModal(activeLink);
      return;
    }
    if (modal.hidden) return;
    if (event.key === 'Escape') closeModal();
    if (event.key !== 'Tab') return;
    const focusable = Array.from(
      modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.disabled && element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });
  close.addEventListener('click', closeModal);
  const setDetailOpen = (button, open) => {
    const detailRow = document.getElementById(button.getAttribute('aria-controls'));
    if (!detailRow) return;
    button.setAttribute('aria-expanded', String(open));
    button.textContent = open ? 'Close' : 'Open';
    detailRow.hidden = !open;
    detailRow.classList.toggle('is-open', open);
  };
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-detail-toggle]');
    if (!button) return;
    event.preventDefault();
    setDetailOpen(button, button.getAttribute('aria-expanded') !== 'true');
  });
  const focusFilter = document.querySelector('[data-filter-control]');
  const search = document.querySelector('[data-search-control]');
  const resultCount = document.querySelector('[data-result-count]');
  const familyRows = Array.from(
    document.querySelectorAll('.review-table > tbody > tr[data-family-row]')
  );
  const sectionRows = Array.from(
    document.querySelectorAll('.review-table > tbody > tr[data-family-section]')
  );
  const totalFamilies = familyRows.length;
  const applyFilters = () => {
    const selected = focusFilter ? focusFilter.value : '';
    const term = search ? search.value.toLowerCase() : '';
    let visibleFamilies = 0;
    familyRows.forEach((row) => {
      const rowCategories = (row.dataset.category || '').split(/\\s+/);
      const focusOk = !selected || rowCategories.includes(selected);
      const searchOk = !term || (row.dataset.search || '').toLowerCase().includes(term);
      const visible = focusOk && searchOk;
      if (visible) visibleFamilies += 1;
      row.hidden = !visible;
      sectionRows
        .filter((sectionRow) => sectionRow.dataset.familySection === row.dataset.family)
        .forEach((sectionRow) => {
          if (!visible) {
            const button = sectionRow.querySelector('[data-detail-toggle]');
            if (button) setDetailOpen(button, false);
            sectionRow.hidden = true;
            return;
          }
          if (!sectionRow.classList.contains('detail-row')) {
            sectionRow.hidden = false;
          }
        });
    });
    if (resultCount) {
      resultCount.textContent = `顯示 ${visibleFamilies} / ${totalFamilies} families`;
    }
  };
  if (focusFilter) focusFilter.addEventListener('change', applyFilters);
  if (search) search.addEventListener('input', applyFilters);
  applyFilters();
})();
</script>
"""


def _gallery_css() -> str:
    return """
:root {
  --bg: #f5f7f8;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #17202a;
  --muted: #5a6673;
  --line: #cbd5e1;
  --line-soft: #e2e8f0;
  --focus: #7db3dc;
  --blue: #1d6fa3;
  --green: #16855b;
  --amber: #9a6100;
  --red: #a12b2b;
  --purple: #6f46c7;
  --shadow: 0 8px 24px rgba(23, 32, 42, 0.08);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Segoe UI, Arial, sans-serif;
  line-height: 1.45;
}
main {
  max-width: 1540px;
  margin: 0 auto;
  padding: 28px 30px 44px;
}
h1 { margin: 0 0 14px; font-size: 28px; }
a, button, input, select, summary { outline-offset: 3px; }
a:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible,
summary:focus-visible { outline: 3px solid var(--focus); }
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.summary-item,
.authority-note,
.artifact-strip,
.provenance-panel,
.html-scope-note,
.filters {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.summary-item {
  min-width: 0;
  min-height: 58px;
  padding: 8px 10px;
  border-left: 5px solid var(--blue);
}
.summary-item span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.summary-item strong {
  display: block;
  margin-top: 4px;
  overflow-wrap: anywhere;
}
.authority-note {
  grid-column: 1 / -1;
  margin: 0;
  padding: 9px 11px;
  border-left: 5px solid var(--red);
  color: #742525;
  font-weight: 700;
}
.artifact-strip {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 8px 11px;
}
.artifact-strip span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}
.artifact-strip a {
  font-weight: 700;
}
.provenance-panel {
  grid-column: 1 / -1;
  padding: 0;
}
.provenance-panel > summary {
  padding: 9px 11px;
  cursor: pointer;
  color: #334155;
  overflow-wrap: anywhere;
  white-space: normal;
}
.provenance-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: 8px 14px;
  margin: 0;
  padding: 0 11px 11px;
  list-style: none;
}
.provenance-list li {
  min-width: 0;
}
.artifact-label {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
}
.provenance-list a {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
}
.html-scope-note {
  margin: 0 0 10px;
  padding: 9px 11px;
  border-left: 5px solid var(--blue);
  color: #334155;
  font-weight: 700;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin: 0 0 14px;
  padding: 10px 12px;
}
.filters label { font-weight: 700; }
.filters select,
.filters input {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 5px 8px;
}
.filters input { min-width: min(360px, 100%); }
.result-count {
  margin-left: auto;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}
.table-wrap {
  overflow-x: auto;
  max-width: 1090px;
  margin: 0 auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.review-table {
  width: 1084px;
  min-width: 1084px;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}
.review-table caption {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.review-table .col-priority { width: 54px; }
.review-table .col-family { width: 310px; }
.review-table .col-state { width: 220px; }
.review-table .col-issue { width: 220px; }
.review-table .col-counts { width: 92px; }
.review-table .col-overlay { width: 78px; }
.review-table .col-details { width: 110px; }
.review-table tbody tr {
  --row-bg: var(--surface);
  background: var(--row-bg);
}
.review-table th,
.review-table td {
  padding: 8px 9px;
  border-bottom: 1px solid var(--line-soft);
  text-align: center;
  vertical-align: top;
  overflow-wrap: anywhere;
  background: var(--row-bg, var(--surface));
}
.review-table thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #e9eef3;
  color: #243240;
  white-space: nowrap;
}
.review-table tbody tr:nth-child(even) { --row-bg: var(--surface-muted); }
.review-table tbody tr:hover { --row-bg: #eef6fb; }
.review-table tbody tr.family-section-row {
  --row-bg: #eef3f7;
}
.review-table tbody tr.family-section-row th,
.review-table tbody tr.family-section-row td {
  padding-top: 7px;
  padding-bottom: 7px;
  border-top: 2px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.review-table tbody tr.seed-decision-row {
  --row-bg: var(--surface);
}
.review-table tbody tr.seed-decision-row:nth-of-type(even) {
  --row-bg: var(--surface-muted);
}
.review-table td:nth-child(1) {
  text-align: center;
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
}
.review-table tbody th[scope="row"] {
  box-shadow: 1px 0 0 var(--line-soft);
}
.review-table thead th:nth-child(1),
.review-table thead th:nth-child(2) {
  z-index: 5;
  background: #e2e8f0;
}
.cell-counts,
.cell-overlay,
.cell-details {
  text-align: center;
  vertical-align: middle;
}
.cell-family,
.cell-state,
.cell-issue {
  text-align: center;
}
.seed-rank {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}
.seed-cell {
  border-left: 4px solid #d8e3ec;
}
.seed-index,
.pattern-label,
.pattern-status,
.anchor-status,
.target-status {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 900;
  line-height: 1.25;
  text-transform: uppercase;
}
.pattern-label {
  margin-top: 3px;
  text-transform: none;
}
.family-context-cell {
  text-align: left;
}
.family-context-cell .family-id,
.family-context-cell .family-meta,
.family-context-cell .seed-summary,
.family-context-cell .seed-window,
.family-context-cell .anchor-status,
.family-context-cell .pattern-status,
.family-context-cell .target-status {
  display: inline-block;
  margin: 0 8px 0 0;
  vertical-align: middle;
}
.family-context-cell .anchor-status,
.family-context-cell .pattern-status,
.family-context-cell .target-status {
  padding: 2px 6px;
  border: 1px solid var(--line-soft);
  border-radius: 999px;
  background: #f8fafc;
  line-height: 1.2;
  text-transform: none;
}
.family-context-cell .anchor-status {
  border-left: 4px solid var(--green);
  color: #1c3f31;
}
.family-context-cell .target-status {
  border-left: 4px solid var(--blue);
  color: #173e5c;
}
.cell-state,
.cell-issue {
  vertical-align: middle;
}
.overlay-scope {
  display: inline-block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  line-height: 1.25;
}
.muted {
  color: var(--muted);
}
.state-stack {
  display: grid;
  gap: 5px;
  align-content: center;
}
.state-line {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
}
.state-key {
  color: var(--muted);
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
  text-align: right;
  text-transform: none;
}
.cell-state .badge {
  justify-self: start;
  max-width: 100%;
}
.shadow-pill {
  display: inline-block;
  justify-self: start;
  max-width: 100%;
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-left: 4px solid var(--blue);
  border-radius: 6px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.25;
  white-space: normal;
}
.detail-toggle {
  min-height: 30px;
  padding: 4px 9px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  font-weight: 800;
}
.detail-toggle[aria-expanded="true"] {
  border-color: var(--blue);
  background: #eef6fb;
}
.detail-hint {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}
.review-table .detail-row > td {
  position: static;
  padding: 0;
  text-align: left;
  vertical-align: top;
  background: #f8fafc;
}
.detail-drawer {
  margin: 0;
  padding: 12px;
  border-top: 1px solid var(--line-soft);
  border-left: 4px solid var(--blue);
}
.detail-drawer-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 14px;
  margin-bottom: 10px;
}
.detail-drawer-head span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.family-id {
  display: block;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
  text-align: center;
}
.family-meta,
.seed-summary,
.seed-window {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
  text-align: center;
}
.seed-count {
  display: inline-block;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #f8fafc;
  font-weight: 700;
}
.badge {
  display: inline-block;
  max-width: 100%;
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-left-width: 4px;
  border-radius: 6px;
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: normal;
  white-space: nowrap;
}
.badge.product_grade_support,
.badge.product_primary_backfilled,
.badge.product_accepts_and_product_grade_supports { border-left-color: var(--green); }
.badge.review_only_visual_support,
.badge.product_rejects_but_visual_supports { border-left-color: var(--blue); }
.badge.evidence_blocks_backfill,
.badge.product_accepts_but_evidence_conflicts,
.badge.product_rejects_and_evidence_blocks { border-left-color: var(--red); }
.badge.not_assessable,
.badge.not_assessable_missing_overlay,
.badge.not_assessable_missing_seed_provenance,
.badge.not_assessable_join_gap { border-left-color: var(--amber); }
.badge.evidence_inconclusive,
.badge.human_visual_judgment_only,
.badge.product_rescued_context_only,
.badge.product_provisional { border-left-color: var(--purple); }
.top-issue {
  display: inline-grid;
  justify-items: start;
  gap: 5px;
  max-width: 100%;
  margin-inline: auto;
}
.issue-text {
  display: block;
  max-width: 100%;
  padding-left: 8px;
  border-left: 3px solid var(--line);
  color: #334155;
  line-height: 1.35;
  text-align: left;
}
.issue-text.blocker { border-left-color: var(--red); }
.issue-text.support { border-left-color: var(--green); }
.count-stack {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 0;
  font-variant-numeric: tabular-nums;
}
.count-stack div {
  display: grid;
  justify-items: center;
  gap: 1px;
}
.count-stack dt {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
}
.count-stack dd {
  margin: 0;
  font-weight: 800;
}
details summary {
  cursor: pointer;
  font-weight: 700;
  min-height: 28px;
  line-height: 1.35;
}
.details-grid {
  display: grid;
  gap: 10px;
  padding-top: 8px;
}
.detail-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.detail-summary-card {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  background: #fff;
}
.detail-summary-card h3 {
  margin: 0;
  font-size: 12px;
  text-transform: uppercase;
  color: #334155;
}
.summary-subtitle {
  margin: 3px 0 8px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}
.summary-body p {
  margin: 5px 0;
}
.summary-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}
.summary-line span:first-child {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}
.summary-link {
  margin: 0 0 6px;
}
.detail-block {
  margin: 0;
}
.family-details {
  display: grid;
  gap: 10px;
  padding-top: 8px;
}
.seed-table-wrap {
  overflow-x: auto;
}
.seed-table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  font-size: 12px;
}
.seed-table th,
.seed-table td {
  padding: 6px;
  border: 1px solid var(--line-soft);
}
.seed-table th {
  background: #f1f5f9;
}
.seed-subdetails {
  padding-top: 4px;
}
.path-list,
.metric-list,
.component-list {
  margin: 4px 0 0;
  padding-left: 18px;
}
.metric-list li,
.component-list li {
  margin: 2px 0;
}
.evidence-chain {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.chain-item {
  min-width: 0;
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  background: #fff;
}
.chain-item:nth-last-child(-n + 2) {
  grid-column: 1 / -1;
}
.shadow-policy-chain {
  grid-column: 1 / -1;
}
.secondary-chain {
  grid-column: 1 / -1;
}
.secondary-chain summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  cursor: pointer;
  font-weight: 800;
  background: #f8fafc;
}
.secondary-chain summary small {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}
.secondary-chain-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 10px;
  border-top: 1px solid var(--line-soft);
}
.secondary-chain-body .chain-item {
  background: #fff;
}
.chain-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line-soft);
  background: #f8fafc;
}
.chain-head h3 {
  margin: 0;
  font-size: 13px;
}
.chain-state {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.chain-body {
  padding: 9px 10px;
}
.chain-note {
  margin: 6px 0 0;
  color: #334155;
}
.review-note {
  margin: 6px 0;
  padding-left: 8px;
  border-left: 3px solid var(--warn);
  color: #334155;
  font-weight: 700;
}
.rep-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.shadow-policy-table,
.target-benchmark-table,
.seed-alias-table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  font-size: 12px;
}
.shadow-policy-table-wrap,
.target-benchmark-table-wrap,
.seed-alias-table-wrap {
  overflow-x: auto;
}
.rep-table th,
.rep-table td,
.shadow-policy-table th,
.shadow-policy-table td,
.target-benchmark-table th,
.target-benchmark-table td,
.seed-alias-table th,
.seed-alias-table td {
  padding: 6px;
  border: 1px solid var(--line-soft);
  overflow-wrap: anywhere;
}
.projection-accept-index {
  margin: 10px 0 12px;
}
.projection-accept-index h3 {
  margin: 0 0 4px;
  font-size: 13px;
}
.projection-accept-table {
  min-width: 980px;
}
.projection-authority-chain {
  margin-top: 6px;
  padding-left: 8px;
  border-left: 3px solid var(--ok);
  color: #334155;
  font-weight: 700;
}
.projection-authority-chain span {
  display: block;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: .02em;
  text-transform: uppercase;
}
.gap-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}
.empty-state {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}
.lightbox[hidden] { display: none; }
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.72);
}
.lightbox-panel {
  width: min(1120px, 96vw);
  max-height: 92vh;
  overflow: auto;
  border-radius: 8px;
  background: #fff;
  padding: 0;
}
.lightbox-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line-soft);
  background: #fff;
}
.lightbox-header h2 {
  margin: 0;
  font-size: 20px;
}
.lightbox-caption {
  margin: 3px 0 0;
  color: var(--muted);
}
.lightbox-interpretation {
  margin: 4px 0 0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}
.lightbox-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.lightbox-close {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  font-weight: 700;
}
.lightbox-direct {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #f8fafc;
  font-weight: 700;
}
.lightbox-image {
  display: block;
  width: calc(100% - 28px);
  margin: 14px;
  max-height: 74vh;
  object-fit: contain;
}
@media (max-width: 760px) {
  main { padding: 18px 12px 32px; }
  h1 { font-size: 22px; }
  .review-table { min-width: 1084px; }
  .detail-summary-grid,
  .secondary-chain-body { grid-template-columns: 1fr; }
  .evidence-chain { grid-template-columns: 1fr; }
  .chain-item:nth-last-child(-n + 2) { grid-column: auto; }
  .lightbox-header { display: grid; }
}
"""


def _group_sort_key(group: ReconciliationGroup) -> tuple[int, str, str]:
    return (
        _CLASS_PRIORITY.get(group.reconciliation_class, len(_CLASS_PRIORITY)),
        group.feature_family_id,
        group.seed_group_id,
    )


def _representative_sort_key(cell: RepresentativeCell) -> tuple[str, str, str, int]:
    role = cell.representative_roles[0] if cell.representative_roles else ""
    return (
        cell.feature_family_id,
        cell.seed_group_id,
        cell.sample_stem,
        _ROLE_PRIORITY.get(role, len(_ROLE_PRIORITY)),
    )


def _product_cell_state(row: Mapping[str, str], group_state: str) -> str:
    if text_value(row.get("primary_matrix_area_source")):
        return "primary_matrix"
    if group_state == "product_rescued_context_only":
        return "context_only"
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


def _count_cells(rows: Sequence[Mapping[str, str]], status: str) -> int:
    return sum(1 for row in rows if text_value(row.get("status")).lower() == status)


def _count_provisional(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(
        1
        for row in rows
        if "provisional" in text_value(row.get("gap_fill_state")).lower()
        or "provisional" in text_value(row.get("status")).lower()
    )


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


def _first_path(*values: object) -> str:
    for value in values:
        labels = split_semicolon_labels(value)
        if labels:
            return labels[0]
    return ""


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = text_value(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def _int_text(value: object) -> int:
    parsed = optional_float(value)
    return int(parsed) if parsed is not None else 0


def _safe_href(value: str) -> str:
    sanitized = _remove_control_chars(text_value(value))
    scheme = _detected_url_scheme(sanitized)
    if scheme in _DANGEROUS_SCHEMES:
        return ""
    return sanitized


def _detected_url_scheme(value: str) -> str:
    compact = "".join(ch for ch in text_value(value) if ord(ch) > 32)
    match = _URL_SCHEME_RE.match(compact)
    if not match:
        return ""
    scheme = match.group(1).lower()
    if len(scheme) == 1 and len(compact) >= 3 and compact[1:3] in {":\\", ":/"}:
        return ""
    return scheme


def _remove_control_chars(value: str) -> str:
    return "".join(ch for ch in value if ord(ch) >= 32)


def _escape(value: object) -> str:
    import html

    return html.escape(text_value(value), quote=True)


def _escape_attr(value: object) -> str:
    return _escape(value)


def _badge(value: str) -> str:
    return (
        f'<span class="badge {_escape_attr(value)}" title="{_escape_attr(value)}">'
        f"{_escape(_badge_label(value))}</span>"
    )


def _badge_label(value: str) -> str:
    labels = {
        "product_grade_support": "product-grade",
        "review_only_visual_support": "visual support",
        "dependent_context_only": "context only",
        "human_visual_judgment_only": "human review",
        "evidence_blocks_backfill": "blocks",
        "evidence_inconclusive": "inconclusive",
        "not_assessable": "not assessable",
        "product_accepts_and_product_grade_supports": "accepts + product-grade",
        "product_accepts_and_visual_supports": "accepts + visual",
        "product_rejects_but_product_grade_supports": "rejects + product-grade",
        "product_rejects_but_visual_supports": "rejects + visual",
        "product_accepts_but_evidence_conflicts": "accepts + conflict",
        "product_rejects_and_evidence_blocks": "rejects + blocks",
        "not_assessable_missing_overlay": "missing overlay",
        "not_assessable_missing_seed_provenance": "missing seed",
        "not_assessable_join_gap": "join gap",
        "product_primary_backfilled": "primary backfilled",
        "product_rescued_context_only": "context only",
        "product_provisional": "provisional",
        "product_review_only": "review only",
        "product_not_backfilled": "not backfilled",
        "product_unknown": "unknown",
        "pattern_context_only": "family map",
        "pattern_available": "context available",
        "pattern_unavailable": "context unavailable",
    }
    return labels.get(value, text_value(value).replace("_", " "))


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


def _representatives_by_group(
    cells: Sequence[RepresentativeCell],
) -> dict[tuple[str, str], tuple[RepresentativeCell, ...]]:
    grouped: dict[tuple[str, str], list[RepresentativeCell]] = {}
    for cell in cells:
        grouped.setdefault(
            (cell.feature_family_id, cell.seed_group_id),
            [],
        ).append(cell)
    return {
        key: tuple(sorted(items, key=_representative_sort_key))
        for key, items in grouped.items()
    }


def _shadow_policy_cell_from_row(row: Mapping[str, str]) -> ShadowPolicyCell:
    return ShadowPolicyCell(
        feature_family_id=text_value(row.get("feature_family_id")),
        seed_group_id=text_value(row.get("seed_group_id")),
        sample_stem=text_value(row.get("sample_stem")),
        current_product_cell_state=text_value(row.get("current_product_cell_state")),
        shadow_policy_decision=text_value(row.get("shadow_policy_decision")),
        decision_reason=text_value(row.get("decision_reason")),
        production_gap=text_value(row.get("production_gap")),
        diagnostic_authority=text_value(row.get("diagnostic_authority")),
        cell_status=text_value(row.get("cell_status")),
        evidence_gate_status=text_value(row.get("evidence_gate_status")),
        overlay_family_verdict=text_value(row.get("overlay_family_verdict")),
        own_max_shape_supported_fraction=text_value(
            row.get("own_max_shape_supported_fraction"),
        ),
        absolute_trace_apex_cluster_fraction=text_value(
            row.get("absolute_trace_apex_cluster_fraction"),
        ),
        support_components=text_value(row.get("support_components")),
        blockers=text_value(row.get("blockers")),
        missing_evidence=text_value(row.get("missing_evidence")),
        overlay_png_path=text_value(row.get("overlay_png_path")),
    )


def _shadow_projection_cell_from_row(
    row: Mapping[str, str],
) -> ShadowProjectionCell:
    return ShadowProjectionCell(
        feature_family_id=text_value(row.get("feature_family_id")),
        seed_group_id=text_value(row.get("seed_group_id")),
        sample_stem=text_value(row.get("sample_stem")),
        current_raw_status=text_value(row.get("current_raw_status")),
        current_production_status=text_value(row.get("current_production_status")),
        current_rescue_tier=text_value(row.get("current_rescue_tier")),
        current_matrix_written=bool_value(row.get("current_matrix_written")) is True,
        current_matrix_value=text_value(row.get("current_matrix_value")),
        current_blank_reason=text_value(row.get("current_blank_reason")),
        current_matrix_source=text_value(row.get("current_matrix_source")),
        review_rescued_cell=bool_value(row.get("review_rescued_cell")) is True,
        shadow_decision=text_value(row.get("shadow_decision")),
        shadow_reasons=tuple(split_semicolon_labels(row.get("shadow_reasons"))),
        shadow_warnings=tuple(split_semicolon_labels(row.get("shadow_warnings"))),
        projected_matrix_written=(
            bool_value(row.get("projected_matrix_written")) is True
        ),
        projected_matrix_value=text_value(row.get("projected_matrix_value")),
        projection_authority=text_value(row.get("projection_authority")),
        product_authority_chain=text_value(row.get("product_authority_chain")),
        detected_anchor_count=text_value(row.get("detected_anchor_count")),
        rescued_cell_count=text_value(row.get("rescued_cell_count")),
        request_window_overlap=(
            text_value(row.get("request_window_overlap"))
            or text_value(row.get("same_peak_segment"))
        ),
        local_global_ratio=text_value(row.get("local_global_ratio")),
        evidence_gate_status=text_value(row.get("evidence_gate_status")),
        support_components=tuple(split_semicolon_labels(row.get("support_components"))),
        hard_blockers=tuple(split_semicolon_labels(row.get("hard_blockers"))),
        missing_evidence=tuple(split_semicolon_labels(row.get("missing_evidence"))),
        overlay_verdict=text_value(row.get("overlay_verdict")),
        overlay_png_path=text_value(row.get("overlay_png_path")),
    )


def _target_benchmark_context_from_row(
    row: Mapping[str, str],
) -> TargetBenchmarkContext | None:
    selected_feature_id = text_value(row.get("selected_feature_id"))
    primary_feature_ids = split_semicolon_labels(row.get("primary_feature_ids"))
    if not selected_feature_id and not primary_feature_ids:
        return None
    return TargetBenchmarkContext(
        target_label=text_value(row.get("target_label")),
        role=text_value(row.get("role")),
        active_tag=text_value(row.get("active_tag")),
        status=text_value(row.get("status")),
        selected_feature_id=selected_feature_id,
        primary_feature_ids=primary_feature_ids,
        targeted_positive_count=text_value(row.get("targeted_positive_count")),
        untargeted_positive_count=text_value(row.get("untargeted_positive_count")),
        coverage_minimum=text_value(row.get("coverage_minimum")),
        failure_modes=split_semicolon_labels(row.get("failure_modes")),
        note=text_value(row.get("note")),
    )


def _target_benchmark_contexts_by_family(
    contexts: Sequence[TargetBenchmarkContext],
) -> dict[str, tuple[TargetBenchmarkContext, ...]]:
    grouped: dict[str, list[TargetBenchmarkContext]] = {}
    for context in contexts:
        for family in context.feature_family_ids:
            grouped.setdefault(family, []).append(context)
    return {
        family: tuple(sorted(items, key=_target_benchmark_context_sort_key))
        for family, items in grouped.items()
    }


def _target_benchmark_context_counts(
    contexts: Sequence[TargetBenchmarkContext],
) -> dict[str, int]:
    counts = Counter(context.status or "UNKNOWN" for context in contexts)
    return dict(sorted(counts.items()))


def _target_benchmark_context_sort_key(
    context: TargetBenchmarkContext,
) -> tuple[str, str, str]:
    return (
        context.status,
        context.target_label,
        context.selected_feature_id,
    )


def _shadow_policy_cells_by_group(
    cells: Sequence[ShadowPolicyCell],
) -> dict[tuple[str, str], tuple[ShadowPolicyCell, ...]]:
    grouped: dict[tuple[str, str], list[ShadowPolicyCell]] = {}
    for cell in cells:
        if not cell.feature_family_id or not cell.seed_group_id:
            continue
        grouped.setdefault(
            (cell.feature_family_id, cell.seed_group_id),
            [],
        ).append(cell)
    return {
        key: tuple(sorted(items, key=_shadow_policy_cell_sort_key))
        for key, items in grouped.items()
    }


def _shadow_projection_cells_by_group(
    cells: Sequence[ShadowProjectionCell],
) -> dict[tuple[str, str], tuple[ShadowProjectionCell, ...]]:
    grouped: dict[tuple[str, str], list[ShadowProjectionCell]] = {}
    for cell in cells:
        if not cell.feature_family_id or not cell.seed_group_id:
            continue
        grouped.setdefault(
            (cell.feature_family_id, cell.seed_group_id),
            [],
        ).append(cell)
    return {
        key: tuple(sorted(items, key=_shadow_projection_cell_sort_key))
        for key, items in grouped.items()
    }


def _shadow_policy_cells_by_family(
    cells: Sequence[ShadowPolicyCell],
) -> dict[str, tuple[ShadowPolicyCell, ...]]:
    grouped: dict[str, list[ShadowPolicyCell]] = {}
    for cell in cells:
        if cell.feature_family_id:
            grouped.setdefault(cell.feature_family_id, []).append(cell)
    return {
        family: tuple(sorted(items, key=_shadow_policy_cell_sort_key))
        for family, items in grouped.items()
    }


def _shadow_projection_cells_by_family(
    cells: Sequence[ShadowProjectionCell],
) -> dict[str, tuple[ShadowProjectionCell, ...]]:
    grouped: dict[str, list[ShadowProjectionCell]] = {}
    for cell in cells:
        if cell.feature_family_id:
            grouped.setdefault(cell.feature_family_id, []).append(cell)
    return {
        family: tuple(sorted(items, key=_shadow_projection_cell_sort_key))
        for family, items in grouped.items()
    }


def _shadow_policy_cells_for_family_groups(
    groups: Sequence[ReconciliationGroup],
    *,
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
) -> tuple[ShadowPolicyCell, ...]:
    exact: list[ShadowPolicyCell] = []
    for group in groups:
        exact.extend(
            shadow_policy_cells_by_group.get(
                (group.feature_family_id, group.seed_group_id),
                (),
            ),
        )
    if exact:
        return tuple(sorted(exact, key=_shadow_policy_cell_sort_key))
    family = groups[0].feature_family_id if groups else ""
    return shadow_policy_cells_by_family.get(family, ())


def _shadow_projection_cells_for_family_groups(
    groups: Sequence[ReconciliationGroup],
    *,
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[str, tuple[ShadowProjectionCell, ...]],
) -> tuple[ShadowProjectionCell, ...]:
    exact: list[ShadowProjectionCell] = []
    for group in groups:
        exact.extend(
            shadow_projection_cells_by_group.get(
                (group.feature_family_id, group.seed_group_id),
                (),
            ),
        )
    if exact:
        return tuple(sorted(exact, key=_shadow_projection_cell_sort_key))
    family = groups[0].feature_family_id if groups else ""
    return shadow_projection_cells_by_family.get(family, ())


def _shadow_policy_cells_for_group(
    group: ReconciliationGroup,
    *,
    shadow_policy_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowPolicyCell, ...],
    ],
    shadow_policy_cells_by_family: Mapping[str, tuple[ShadowPolicyCell, ...]],
    allow_family_fallback: bool,
) -> tuple[ShadowPolicyCell, ...]:
    exact = shadow_policy_cells_by_group.get(
        (group.feature_family_id, group.seed_group_id),
        (),
    )
    if exact or not allow_family_fallback:
        return exact
    return shadow_policy_cells_by_family.get(group.feature_family_id, ())


def _shadow_projection_cells_for_group(
    group: ReconciliationGroup,
    *,
    shadow_projection_cells_by_group: Mapping[
        tuple[str, str],
        tuple[ShadowProjectionCell, ...],
    ],
    shadow_projection_cells_by_family: Mapping[str, tuple[ShadowProjectionCell, ...]],
    allow_family_fallback: bool,
) -> tuple[ShadowProjectionCell, ...]:
    exact = shadow_projection_cells_by_group.get(
        (group.feature_family_id, group.seed_group_id),
        (),
    )
    if exact or not allow_family_fallback:
        return exact
    return shadow_projection_cells_by_family.get(group.feature_family_id, ())


def _shadow_policy_compact_summary(
    cells: Sequence[ShadowPolicyCell],
) -> str:
    if not cells:
        return ""
    counts = Counter(cell.shadow_policy_decision for cell in cells)
    labels = (
        ("fill_now", "fill"),
        ("would_fill_under_ms1_rt_policy", "would"),
        ("needs_ms1_same_peak_evidence", "needs MS1"),
        ("blocked", "block"),
    )
    parts = [f"{label} {counts[key]}" for key, label in labels if counts[key]]
    return "shadow: " + " · ".join(parts)


def _shadow_projection_compact_summary(
    cells: Sequence[ShadowProjectionCell],
) -> str:
    if not cells:
        return ""
    counts = Counter(cell.shadow_decision for cell in cells)
    projected_new = sum(
        not cell.current_matrix_written and cell.projected_matrix_written
        for cell in cells
    )
    labels = (
        ("accept", "accept"),
        ("block", "block"),
        ("context", "context"),
    )
    parts = [f"{label} {counts[key]}" for key, label in labels if counts[key]]
    if projected_new:
        parts.append(f"+{projected_new} matrix")
    return "projection: " + " · ".join(parts)


def _shadow_policy_decision_counts(
    cells: Sequence[ShadowPolicyCell],
) -> dict[str, int]:
    counts = Counter(cell.shadow_policy_decision for cell in cells)
    return {key: counts[key] for key in sorted(counts) if key}


def _shadow_projection_decision_counts(
    cells: Sequence[ShadowProjectionCell],
) -> dict[str, int]:
    counts = Counter(cell.shadow_decision for cell in cells)
    return {key: counts[key] for key in sorted(counts) if key}


def _shadow_projection_matrix_counts(
    cells: Sequence[ShadowProjectionCell],
) -> dict[str, int]:
    return {
        "current_decision_written": sum(cell.current_matrix_written for cell in cells),
        "projected_decision_written": sum(
            cell.projected_matrix_written for cell in cells
        ),
        "projected_new_decision_write": sum(
            not cell.current_matrix_written and cell.projected_matrix_written
            for cell in cells
        ),
        "review_rescued_target": sum(cell.review_rescued_cell for cell in cells),
    }


def _shadow_policy_production_gap_counts(
    cells: Sequence[ShadowPolicyCell],
) -> dict[str, int]:
    counts = Counter(cell.production_gap for cell in cells if cell.production_gap)
    return {key: counts[key] for key in sorted(counts) if key}


def _shadow_policy_cell_sort_key(cell: ShadowPolicyCell) -> tuple[str, str, str]:
    return (cell.feature_family_id, cell.seed_group_id, cell.sample_stem)


def _shadow_projection_cell_sort_key(
    cell: ShadowProjectionCell,
) -> tuple[str, str, str]:
    return (cell.feature_family_id, cell.seed_group_id, cell.sample_stem)


def _count_token_prefix(counts: object, prefix: str) -> int:
    if not isinstance(counts, Mapping):
        return 0
    return sum(
        int(value)
        for key, value in counts.items()
        if isinstance(key, str) and key.startswith(prefix)
    )
