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

from xic_extractor.diagnostics.diagnostic_io import (
    bool_value,
    optional_float,
    read_tsv_required,
    split_semicolon_labels,
    text_value,
    write_tsv,
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
    detected_cell_count: int = 0
    rescued_cell_count: int = 0
    provisional_cell_count: int = 0
    top_product_reason: str = ""
    top_support_component: str = ""
    top_blocker: str = ""
    missing_evidence: tuple[str, ...] = ()
    overlay_png_path: str = ""
    overlay_trace_json_path: str = ""
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
        source_run_id=source_run_id,
    )
    input_artifacts.update(
        _input_artifact_hashes(
            alignment_review_tsv=alignment_review_tsv,
            alignment_cells_tsv=alignment_cells_tsv,
            alignment_matrix_tsv=alignment_matrix_tsv,
            candidate_gate_tsv=candidate_gate_tsv,
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
                seed_aware_row=seed_aware_by_family.get(family, {}),
                candidate_gate_row=candidate_by_family.get(family, {}),
                source_hashes=source_hashes,
                has_tier2_trace_evidence=family in tier2_families,
            )
            product_behavior = _product_behavior(review, family_cells)
            product_reason = _top_product_reason(review)
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
                detected_cell_count=_count_cells(family_cells, "detected"),
                rescued_cell_count=_count_cells(family_cells, "rescued"),
                provisional_cell_count=_count_provisional(family_cells),
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
    return ReconciliationIndex(
        groups=tuple(groups),
        representative_cells=tuple(representatives),
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
    representatives_by_group = _representatives_by_group(index.representative_cells)
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
        *_filter_html(total_families=len(_family_groups(groups))),
    ]
    if not groups:
        lines.append(
            '<p class="empty-state">沒有 backfill family/seed group 可審閱。</p>',
        )
    else:
        lines.extend(
            _table_html(
                groups,
                representatives_by_group=representatives_by_group,
                html_path=path,
                input_artifacts=index.summary.get("input_artifacts", {}),
            ),
        )
        lines.extend(_lightbox_html())
    lines.extend(["</main>", _lightbox_script(), "</body>", "</html>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _input_artifact_hashes(**paths: Path | None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path in paths.items():
        if path is None:
            continue
        hashes[f"{key.removesuffix('_tsv')}_sha256"] = _sha256_file(path)
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
    seed_specific = [
        dict(row)
        for row in rows
        if text_value(row.get("seed_group_id")) == seed_group_id
    ]
    if seed_specific:
        return tuple(seed_specific)
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


def _classify_evidence(
    *,
    family: str,
    seed_record: _SeedRecord,
    family_cells: Sequence[Mapping[str, str]],
    group_cells: Sequence[Mapping[str, str]],
    has_matrix_context: bool,
    seed_samples: frozenset[str],
    overlay_rows: Sequence[Mapping[str, str]],
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
    overlay_evidence_notes.extend(
        _anchor_peak_overlay_notes(
            family=family,
            scoring_cells=family_cells,
            note_cells=group_cells,
            overlay_trace_json_path=overlay_trace_json_path,
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
    elif "missing_seed_provenance" in missing or "missing_overlay" in missing:
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
        "overlay_evidence_notes": tuple(_ordered_unique(overlay_evidence_notes)),
    }


def _overlay_evidence_notes(row: Mapping[str, str]) -> tuple[str, ...]:
    labels = (
        ("absolute_own_max_shape_supported_fraction", "own-max shape support"),
        ("absolute_trace_apex_cluster_fraction", "absolute apex cluster"),
        ("shape_supported_fraction", "apex-aligned shape support"),
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
    if include_primary and rescued_cells or primary_rescued:
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
        *_artifact_links(output_paths, html_path=html_path),
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


def _filter_html(*, total_families: int) -> list[str]:
    return [
        '<section class="filters" aria-label="table filters">',
        '<label for="categoryFilter">Focus</label>',
        '<select id="categoryFilter" data-filter-control>',
        '<option value="">All rows</option>',
        *[
            f'<option value="{_escape_attr(value)}">{_escape(label)}</option>'
            for value, label in _REVIEW_CATEGORY_LABELS.items()
        ],
        "</select>",
        '<label for="searchBox">Search</label>',
        '<input id="searchBox" type="search" data-search-control '
        'aria-label="Search family, seed group, support, blocker">',
        (
            '<span class="result-count" data-result-count '
            f'data-total-families="{total_families}">'
            f"顯示 {total_families} / {total_families} families</span>"
        ),
        "</section>",
    ]


def _table_html(
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    html_path: Path,
    input_artifacts: object,
) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="review-table" aria-describedby="galleryTableDescription">',
        '<caption id="galleryTableDescription">'
        "Family-first backfill evidence review queue. "
        "Seed groups and representative cells are collapsed in each row details."
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
        '<th scope="col">family / seed</th>',
        '<th scope="col">state</th>',
        '<th scope="col">issue</th>',
        (
            '<th scope="col"><span title="D=detected cells, '
            'R=rescued/backfilled cells, P=provisional cells">'
            "cells D/R/P</span></th>"
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


def _review_category(reconciliation_class: str) -> str:
    return _REVIEW_CATEGORY_BY_CLASS.get(reconciliation_class, "needs_review")


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
    return (
        '<div class="state-stack" aria-label="product and evidence state">'
        '<div class="state-line">'
        '<span class="state-key">prod</span>'
        f"{_badge(group.product_behavior_state)}"
        "</div>"
        '<div class="state-line">'
        '<span class="state-key">evd</span>'
        f"{_badge(group.evidence_authority_state)}"
        "</div>"
        "</div>"
    )


def _counts_html(group: ReconciliationGroup) -> str:
    return (
        '<dl class="count-stack" '
        'aria-label="cells: D detected, R rescued or backfilled, P provisional">'
        f'<div title="detected"><dt>D</dt><dd>{group.detected_cell_count}</dd></div>'
        f'<div title="rescued/backfilled">'
        f"<dt>R</dt><dd>{group.rescued_cell_count}</dd></div>"
        f'<div title="provisional">'
        f"<dt>P</dt><dd>{group.provisional_cell_count}</dd></div>"
        "</dl>"
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
    html_path: Path,
    input_artifacts: object,
) -> list[str]:
    ordered_groups = tuple(sorted(family_groups, key=_group_sort_key))
    group = ordered_groups[0]
    classes = " ".join(
        _ordered_unique(row.reconciliation_class for row in ordered_groups),
    )
    categories = " ".join(
        _ordered_unique(
            _review_category(row.reconciliation_class) for row in ordered_groups
        ),
    )
    seed_summary = _family_seed_summary(ordered_groups)
    window_summary = _family_window_summary(ordered_groups)
    detail_summary = _family_detail_summary(
        ordered_groups,
        representatives_by_group=representatives_by_group,
    )
    detail_id = _detail_row_id(group.feature_family_id, priority)
    row = [
        (
            '<tr data-family-row '
            f'data-family="{_escape_attr(group.feature_family_id)}" '
            f'data-class="{_escape_attr(classes)}" '
            f'data-category="{_escape_attr(categories)}" '
            f'data-detail-row="{_escape_attr(detail_id)}" '
            f'data-search="{_escape_attr(_family_search_blob(ordered_groups))}">'
        ),
        f'<td class="cell-priority" data-label="rank">{priority}</td>',
        (
            '<th class="cell-family" scope="row" data-label="family / seed">'
            f'<span class="family-id">{_escape(group.feature_family_id)}</span>'
            f"{_family_tag_html(ordered_groups)}"
            f'<span class="seed-summary">{_escape(seed_summary)}</span>'
            f'<span class="seed-window">{_escape(window_summary)}</span>'
            "</th>"
        ),
        (
            '<td class="cell-state" data-label="state">'
            f"{_state_html(group)}</td>"
        ),
        (
            '<td class="cell-issue" data-label="issue">'
            f"{_top_issue_html(group)}</td>"
        ),
        (
            '<td class="cell-counts" data-label="cells D/R/P">'
            f"{_counts_html(group)}"
            "</td>"
        ),
        (
            '<td class="cell-overlay" data-label="overlay">'
            f"{_family_overlay_links(ordered_groups, html_path)}</td>"
        ),
        '<td class="cell-details" data-label="chain">',
        (
            '<button type="button" class="detail-toggle" '
            'aria-expanded="false" '
            f'aria-controls="{_escape_attr(detail_id)}" '
            f'data-detail-toggle="{_escape_attr(detail_id)}">Open</button>'
        ),
        f'<span class="detail-hint">{_escape(detail_summary)}</span>',
        "</td>",
        "</tr>",
        (
            f'<tr class="detail-row" id="{_escape_attr(detail_id)}" '
            f'data-detail-for="{_escape_attr(group.feature_family_id)}" hidden>'
        ),
        '<td colspan="7">',
        '<div class="detail-drawer">',
        '<div class="detail-drawer-head">',
        '<strong>Evidence chain</strong>',
        (
            '<span>cells D/R/P 是 cell counts；'
            "這裡顯示 seed group、representative cells、"
            "support/blocker provenance。</span>"
        ),
        "</div>",
        _family_details_html(
            ordered_groups,
            representatives_by_group=representatives_by_group,
            html_path=html_path,
            input_artifacts=input_artifacts,
        ),
        "</div>",
        "</td>",
        "</tr>",
    ]
    return row


def _detail_row_id(family_id: str, priority: int) -> str:
    token = re.sub(r"[^a-zA-Z0-9_-]+", "-", family_id).strip("-").lower()
    return f"family-detail-{priority}-{token or 'item'}"


def _family_overlay_links(
    groups: Sequence[ReconciliationGroup],
    html_path: Path,
) -> str:
    links: list[str] = []
    seen_hrefs: set[str] = set()
    for index, group in enumerate(groups, start=1):
        href = _href_for_path(group.overlay_png_path, html_path)
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        link = _overlay_link_html(
            group,
            html_path,
            label="PNG" if len(groups) == 1 else f"PNG {index}",
        )
        if link:
            links.append(link)
    return "<br>".join(links) if links else "no overlay"


def _overlay_link_html(
    group: ReconciliationGroup,
    html_path: Path,
    *,
    label: str = "PNG",
) -> str:
    png_href = _href_for_path(group.overlay_png_path, html_path)
    if not png_href:
        return ""
    return (
        f'<a class="png-link" href="{_escape_attr(png_href)}" '
        f'data-lightbox-src="{_escape_attr(png_href)}" '
        f'data-lightbox-caption="{_escape_attr(group.feature_family_id)} | '
        f'{_escape_attr(group.seed_group_id)}">{_escape(label)}</a>'
    )


def _family_details_html(
    groups: Sequence[ReconciliationGroup],
    *,
    representatives_by_group: Mapping[tuple[str, str], tuple[RepresentativeCell, ...]],
    html_path: Path,
    input_artifacts: object,
) -> str:
    if len(groups) == 1:
        group = groups[0]
        return (
            '<div class="family-details single-seed">'
            + _details_html(
                group,
                representatives_by_group.get(
                    (group.feature_family_id, group.seed_group_id),
                    (),
                ),
                html_path=html_path,
                input_artifacts=input_artifacts,
                include_seed_context=False,
            )
            + "</div>"
        )
    seed_rows = "".join(
        "<tr>"
        f'<td><span title="{_escape_attr(group.seed_group_id)}">'
        f"seed {index}</span></td>"
        f"<td>{_escape(group.seed_mz)}</td>"
        f"<td>{_escape(group.seed_rt)} · {_escape(group.seed_rt_window)}</td>"
        f"<td>{_badge(group.evidence_authority_state)}</td>"
        f"<td>{_badge(group.reconciliation_class)}</td>"
        f"<td>{_escape(_compact_issue_label(_seed_issue_text(group)))}</td>"
        f"<td>{_overlay_link_html(group, html_path) or 'no overlay'}</td>"
        "</tr>"
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
    return f"seed {index} · RT {group.seed_rt or 'unknown'} · {issue}"


def _details_html(
    group: ReconciliationGroup,
    representatives: Sequence[RepresentativeCell],
    *,
    html_path: Path,
    input_artifacts: object,
    include_seed_context: bool = True,
) -> str:
    seed_context_html = (
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
    return (
        '<div class="details-grid evidence-chain">'
        + seed_context_html
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
            "Gaussian15 own-max MS1 shape",
            "visual evidence",
            _overlay_evidence_notes_html(group.overlay_evidence_notes)
            or '<p class="chain-note">No overlay metric notes supplied.</p>',
        )
        + _chain_item_html(
            "Candidate MS2 / NL or product-grade support",
            group.evidence_authority_state,
            _component_list_html(group.product_grade_support_components)
            or _component_list_html(group.review_only_visual_components)
            or '<p class="chain-note">No product-grade support component supplied.</p>',
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
        + _chain_item_html(
            "source artifacts",
            "provenance",
            _source_artifacts_html(group.source_artifacts, input_artifacts, html_path),
        )
        + "</div>"
    )


def _overlay_evidence_notes_html(notes: Sequence[str]) -> str:
    if not notes:
        return ""
    items = "".join(f"<li>{_escape(note)}</li>" for note in notes)
    return (
        '<div class="detail-block"><strong>overlay evidence metrics</strong>'
        f'<ul class="metric-list">{items}</ul></div>'
    )


def _chain_item_html(title: str, state: str, body_html: str) -> str:
    return (
        '<section class="chain-item">'
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
        '<h2 id="lightboxTitle">Overlay PNG</h2>',
        '<p id="lightboxCaption" class="lightbox-caption"></p>',
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
  const caption = modal.querySelector('.lightbox-caption');
  const direct = modal.querySelector('.lightbox-direct');
  const close = modal.querySelector('.lightbox-close');
  let previousFocus = null;
  const openModal = (link) => {
    previousFocus = document.activeElement;
    image.src = link.dataset.lightboxSrc;
    image.alt = link.dataset.lightboxCaption || 'overlay PNG';
    caption.textContent = link.dataset.lightboxCaption || '';
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
      const button = row.querySelector('[data-detail-toggle]');
      const detailRow = document.getElementById(row.dataset.detailRow);
      if (!visible && button && detailRow) setDetailOpen(button, false);
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
.review-table th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #e9eef3;
  color: #243240;
  white-space: nowrap;
}
.review-table tbody tr:nth-child(even) { --row-bg: var(--surface-muted); }
.review-table tbody tr:hover { --row-bg: #eef6fb; }
.review-table th:nth-child(1),
.review-table td:nth-child(1) {
  position: sticky;
  left: 0;
  z-index: 3;
  text-align: center;
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
}
.review-table th:nth-child(2),
.review-table tbody th[scope="row"] {
  position: sticky;
  left: 54px;
  z-index: 3;
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
.cell-state,
.cell-issue {
  vertical-align: middle;
}
.state-stack {
  display: grid;
  gap: 5px;
  align-content: center;
}
.state-line {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
}
.state-key {
  color: var(--muted);
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
  text-transform: uppercase;
}
.cell-state .badge {
  justify-self: start;
  max-width: 100%;
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
.rep-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rep-table th,
.rep-table td {
  padding: 6px;
  border: 1px solid var(--line-soft);
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
    }
    return labels.get(value, text_value(value).replace("_", " "))


def _search_blob(group: ReconciliationGroup) -> str:
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
        ),
    )


def _family_search_blob(groups: Sequence[ReconciliationGroup]) -> str:
    return " ".join(_search_blob(group) for group in groups)


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


def _count_token_prefix(counts: object, prefix: str) -> int:
    if not isinstance(counts, Mapping):
        return 0
    return sum(
        int(value)
        for key, value in counts.items()
        if isinstance(key, str) and key.startswith(prefix)
    )
