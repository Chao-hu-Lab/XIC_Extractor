"""Run standard-peak machine-gate backfill productization."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics import (
    family_ms1_alignment_experiment_batch,
    family_ms1_overlay_batch,
    shadow_production_projection,
    shift_aware_backfill_calibration_pack,
    shift_aware_standard_peak_gate_calibration,
    standard_peak_backfill_productization,
    standard_peak_ms1_authority_bundle,
)
from xic_extractor.diagnostics.backfill_reconciliation_gallery import (
    run_reconciliation_gallery,
)
from xic_extractor.diagnostics.diagnostic_io import (
    read_tsv_required,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.timing import TimingRecorder


@dataclass(frozen=True)
class OverlaySourceResolution:
    summary_tsv: Path
    mode: str
    evidence_source_mode: str
    queue_row_count: int | None = None
    requested_limit: int | None = None
    effective_limit: int | None = None
    metrics: dict[str, Any] | None = None


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = run_machine_pipeline(
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            review_queue_tsv=args.review_queue_tsv,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
            retained_gate_tsv=args.retained_gate_tsv,
            reconciliation_groups_tsv=args.reconciliation_groups_tsv,
            output_dir=args.output_dir,
            overlay_output_dir=args.overlay_output_dir,
            source_run_id=args.source_run_id,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
            reconciliation_gallery_html=args.reconciliation_gallery_html,
            write_gallery=args.write_gallery,
            gallery_output_dir=args.gallery_output_dir,
            start_rank=args.start_rank,
            limit=args.limit,
            reuse_existing=args.reuse_existing,
            ppm=args.ppm,
            max_highlight_rescued=args.max_highlight_rescued,
            write_overlay_pdf=args.write_overlay_pdf,
            min_shape_r=args.min_shape_r,
            publication_mode=args.publication_mode,
            evidence_only=args.evidence_only,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"standard-peak machine pipeline summary JSON: {summary}")
    return 0


def run_machine_pipeline(
    *,
    overlay_batch_summary_tsv: Path | None = None,
    review_queue_tsv: Path | None = None,
    raw_dir: Path | None = None,
    dll_dir: Path | None = None,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    alignment_matrix_tsv: Path,
    alignment_matrix_identity_tsv: Path,
    retained_gate_tsv: Path,
    reconciliation_groups_tsv: Path | None = None,
    output_dir: Path,
    overlay_output_dir: Path | None = None,
    source_run_id: str = "",
    backfill_seed_audit_tsv: Path | None = None,
    reconciliation_gallery_html: Path | None = None,
    write_gallery: bool = False,
    gallery_output_dir: Path | None = None,
    start_rank: int = 1,
    limit: int | None = None,
    reuse_existing: bool = False,
    ppm: float = 20.0,
    max_highlight_rescued: int = 8,
    write_overlay_pdf: bool = False,
    min_shape_r: float = (
        shift_aware_backfill_calibration_pack.DEFAULT_STANDARD_PEAK_MIN_SHAPE_R
    ),
    publication_mode: str = "deep-audit",
    evidence_only: bool = False,
    timing_recorder: TimingRecorder | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    recorder = timing_recorder or TimingRecorder.disabled("standard_peak")
    with recorder.stage(
        "standard_peak.overlay_batch",
        metrics={
            "publication_mode": publication_mode,
            "evidence_only": evidence_only,
            "start_rank": start_rank,
            "limit": limit or "",
        },
    ) as scope:
        overlay_source = _resolve_overlay_batch_summary_tsv(
            overlay_batch_summary_tsv=overlay_batch_summary_tsv,
            review_queue_tsv=review_queue_tsv,
            alignment_cells_tsv=alignment_cells_tsv,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            overlay_output_dir=overlay_output_dir,
            start_rank=start_rank,
            limit=limit,
            reuse_existing=reuse_existing,
            ppm=ppm,
            max_highlight_rescued=max_highlight_rescued,
            write_overlay_pdf=write_overlay_pdf,
            evidence_only=evidence_only,
        )
        scope.metrics["overlay_source_mode"] = overlay_source.mode
        scope.metrics["evidence_source_mode"] = overlay_source.evidence_source_mode
        scope.metrics["effective_limit"] = overlay_source.effective_limit or ""
        if overlay_source.metrics:
            scope.metrics.update(overlay_source.metrics)
    overlay_batch_summary_tsv = overlay_source.summary_tsv
    overlay_summary = _summarize_overlay_batch(overlay_batch_summary_tsv)
    with recorder.stage("standard_peak.reconciliation_groups") as scope:
        reconciliation_groups_tsv = _resolve_reconciliation_groups_tsv(
            reconciliation_groups_tsv=reconciliation_groups_tsv,
            alignment_review_tsv=alignment_review_tsv,
            alignment_cells_tsv=alignment_cells_tsv,
            alignment_matrix_tsv=alignment_matrix_tsv,
            backfill_seed_audit_tsv=backfill_seed_audit_tsv,
            overlay_batch_summary_tsv=overlay_batch_summary_tsv,
            retained_gate_tsv=retained_gate_tsv,
            output_dir=output_dir,
            source_run_id=source_run_id,
        )
        scope.metrics["reconciliation_groups_tsv"] = str(reconciliation_groups_tsv)
    shift_dir = output_dir / "shift_aware_alignment_experiment"
    pack_dir = output_dir / "shift_aware_calibration_pack"
    gate_dir = output_dir / "shift_aware_standard_peak_gate"
    authority_dir = output_dir / "standard_peak_ms1_authority_bundle"
    projection_dir = output_dir / "shadow_projection"
    productization_dir = output_dir / "standard_peak_productization"
    gallery_dir = gallery_output_dir or output_dir / "reconciliation_gallery"

    render_shift_aware_images = publication_mode != "matrix-only"
    with recorder.stage(
        "standard_peak.shift_aware_batch",
        metrics={
            "render_images": render_shift_aware_images,
            "start_rank": start_rank,
            "limit": limit or "",
        },
    ) as scope:
        shift_rows, shift_summary = (
            family_ms1_alignment_experiment_batch.run_alignment_experiment_batch(
                overlay_batch_summary_tsv=overlay_batch_summary_tsv,
                cell_evidence_tsv=alignment_cells_tsv,
                output_dir=shift_dir,
                start_rank=start_rank,
                limit=limit,
                reuse_existing=reuse_existing,
                render_images=render_shift_aware_images,
                timing_recorder=recorder,
            )
        )
        scope.metrics["selected_row_count"] = shift_summary.get("selected_row_count", 0)
        scope.metrics["successful_row_count"] = shift_summary.get(
            "successful_shift_aware_row_count",
            0,
        )
    shift_summary = dict(shift_summary)
    shift_batch_tsv = shift_dir / "family_ms1_alignment_experiment_batch_summary.tsv"
    shift_batch_json = shift_dir / "family_ms1_alignment_experiment_batch_summary.json"
    with recorder.stage(
        "standard_peak.shift_aware_summary_write",
        metrics={"row_count": len(shift_rows)},
    ):
        write_tsv(
            shift_batch_tsv,
            shift_rows,
            family_ms1_alignment_experiment_batch.SUMMARY_COLUMNS,
        )
        shift_batch_json.write_text(
            json.dumps(shift_summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    with recorder.stage("standard_peak.calibration_pack"):
        _run_step(
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
                    "--output-dir",
                    str(pack_dir),
                    *_optional_path_arg(
                        "--reconciliation-gallery-html",
                        reconciliation_gallery_html,
                    ),
                ],
            ),
        )
    pack_tsv = pack_dir / "shift_aware_backfill_calibration_pack.tsv"
    with recorder.stage("standard_peak.standard_peak_gate"):
        _run_step(
            "shift-aware standard-peak gate",
            shift_aware_standard_peak_gate_calibration.main(
                [
                    "--manual-pack-tsv",
                    str(pack_tsv),
                    "--output-dir",
                    str(gate_dir),
                ],
            ),
        )
    gate_tsv = gate_dir / "shift_aware_standard_peak_gate_calibration.tsv"
    with recorder.stage("standard_peak.ms1_authority_bundle"):
        _run_step(
            "standard-peak MS1 authority bundle",
            standard_peak_ms1_authority_bundle.main(
                [
                    "--standard-peak-gate-tsv",
                    str(gate_tsv),
                    "--overlay-batch-summary-tsv",
                    str(overlay_batch_summary_tsv),
                    "--authority-mode",
                    "machine-gate",
                    "--output-dir",
                    str(authority_dir),
                ],
            ),
        )
    authorized_ms1_tsv = authority_dir / (
        "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
    )
    with recorder.stage("standard_peak.shadow_projection"):
        _run_step(
            "shadow production projection",
            shadow_production_projection.main(
                [
                    "--alignment-review-tsv",
                    str(alignment_review_tsv),
                    "--alignment-cells-tsv",
                    str(alignment_cells_tsv),
                    "--retained-gate-tsv",
                    str(retained_gate_tsv),
                    "--alignment-matrix-tsv",
                    str(alignment_matrix_tsv),
                    "--alignment-matrix-identity-tsv",
                    str(alignment_matrix_identity_tsv),
                    "--overlay-batch-summary-tsv",
                    str(overlay_batch_summary_tsv),
                    "--ms1-pattern-coherence-tsv",
                    str(authorized_ms1_tsv),
                    "--source-run-id",
                    source_run_id,
                    "--output-dir",
                    str(projection_dir),
                ],
            ),
        )
    projection_cells_tsv = projection_dir / "shadow_production_projection_cells.tsv"
    product_args = [
        "--shadow-projection-cells-tsv",
        str(projection_cells_tsv),
        "--alignment-matrix-tsv",
        str(alignment_matrix_tsv),
        "--alignment-matrix-identity-tsv",
        str(alignment_matrix_identity_tsv),
        "--alignment-review-tsv",
        str(alignment_review_tsv),
        "--alignment-cells-tsv",
        str(alignment_cells_tsv),
        "--overlay-batch-summary-tsv",
        str(overlay_batch_summary_tsv),
        "--shift-aware-standard-peak-gate-tsv",
        str(gate_tsv),
        "--retained-backfill-evidence-gate-tsv",
        str(retained_gate_tsv),
        "--source-run-id",
        source_run_id,
        "--output-dir",
        str(productization_dir),
    ]
    if backfill_seed_audit_tsv is not None:
        product_args.extend(["--backfill-seed-audit-tsv", str(backfill_seed_audit_tsv)])
    if write_gallery:
        product_args.append("--write-gallery")
        product_args.extend(["--gallery-output-dir", str(gallery_dir)])
    with recorder.stage("standard_peak.productization"):
        _run_step(
            "standard-peak productization",
            standard_peak_backfill_productization.main(product_args),
        )
    productization_summary = _load_json_mapping(
        productization_dir / "standard_peak_backfill_productization_summary.json",
    )

    summary_path = output_dir / "standard_peak_backfill_machine_pipeline_summary.json"
    status, status_reasons = _pipeline_status(
        overlay_summary=overlay_summary,
        shift_summary=shift_summary,
        productization_summary=productization_summary,
    )
    summary: dict[str, Any] = {
        "schema_version": "standard_peak_backfill_machine_pipeline_v0",
        "status": status,
        "status_reasons": status_reasons,
        "source_run_id": source_run_id,
        "publication_mode": publication_mode,
        "min_shape_r": min_shape_r,
        "overlay_batch_summary_tsv": str(overlay_batch_summary_tsv),
        "overlay_source_mode": overlay_source.mode,
        "evidence_source_mode": overlay_source.evidence_source_mode,
        "overlay_queue_row_count": overlay_source.queue_row_count,
        "start_rank": start_rank,
        "requested_limit": overlay_source.requested_limit,
        "effective_overlay_limit": overlay_source.effective_limit,
        "overlay_selected_row_count": overlay_summary["selected_row_count"],
        "overlay_success_count": overlay_summary["success_count"],
        "overlay_failed_count": overlay_summary["failed_count"],
        "overlay_status_counts": overlay_summary["status_counts"],
        "rendered_image_count": overlay_summary["rendered_image_count"],
        "reconciliation_groups_tsv": str(reconciliation_groups_tsv),
        "shift_aware_alignment_experiment_dir": str(shift_dir),
        "shift_aware_render_images": render_shift_aware_images,
        "shift_aware_selected_row_count": shift_summary.get("selected_row_count", 0),
        "shift_aware_successful_row_count": shift_summary.get(
            "successful_shift_aware_row_count",
            0,
        ),
        "shift_aware_status_counts": shift_summary.get("status_counts", {}),
        "shift_aware_calibration_pack_tsv": str(pack_tsv),
        "shift_aware_standard_peak_gate_tsv": str(gate_tsv),
        "authorized_ms1_pattern_tsv": str(authorized_ms1_tsv),
        "shadow_projection_cells_tsv": str(projection_cells_tsv),
        "productization_summary_json": str(
            productization_dir / "standard_peak_backfill_productization_summary.json",
        ),
        "activated_matrix_tsv": str(
            productization_dir / "activated_matrix" / "alignment_matrix.tsv",
        ),
        "activation_value_delta_tsv": str(
            productization_dir / "activated_matrix" / "activation_value_delta.tsv",
        ),
        "activation_acceptance_status": productization_summary.get(
            "activation_acceptance_status",
            "",
        ),
        "activation_application_status": productization_summary.get(
            "activation_application_status",
            "",
        ),
        "selected_activation_row_count": productization_summary.get(
            "selected_activation_row_count",
            0,
        ),
        "matrix_cells_written": productization_summary.get("matrix_cells_written", 0),
        "activation_value_delta_written_count": productization_summary.get(
            "activation_value_delta_written_count",
            0,
        ),
        "product_behavior_changed": productization_summary.get(
            "product_behavior_changed",
            "",
        ),
        "reconciliation_gallery_html": (
            str(gallery_dir / "backfill_evidence_reconciliation_gallery.html")
            if write_gallery
            else ""
        ),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary_path


def _resolve_overlay_batch_summary_tsv(
    *,
    overlay_batch_summary_tsv: Path | None,
    review_queue_tsv: Path | None,
    alignment_cells_tsv: Path,
    raw_dir: Path | None,
    dll_dir: Path | None,
    output_dir: Path,
    overlay_output_dir: Path | None,
    start_rank: int,
    limit: int | None,
    reuse_existing: bool,
    ppm: float,
    max_highlight_rescued: int,
    write_overlay_pdf: bool,
    evidence_only: bool,
) -> OverlaySourceResolution:
    if overlay_batch_summary_tsv is not None:
        conflicting = [
            name
            for name, value in (
                ("--review-queue-tsv", review_queue_tsv),
                ("--raw-dir", raw_dir),
                ("--dll-dir", dll_dir),
                ("--overlay-output-dir", overlay_output_dir),
            )
            if value is not None
        ]
        if conflicting:
            raise ValueError(
                "Choose one source mode: use --overlay-batch-summary-tsv "
                "for existing overlay evidence, or use review queue + RAW/DLL "
                f"to render overlays. Conflicting inputs: {', '.join(conflicting)}",
            )
        return OverlaySourceResolution(
            summary_tsv=overlay_batch_summary_tsv,
            mode="existing_overlay_summary",
            evidence_source_mode="existing_overlay_summary",
            requested_limit=limit,
            effective_limit=limit,
        )
    if review_queue_tsv is None or raw_dir is None or dll_dir is None:
        missing = [
            name
            for name, value in (
                ("--review-queue-tsv", review_queue_tsv),
                ("--raw-dir", raw_dir),
                ("--dll-dir", dll_dir),
            )
            if value is None
        ]
        raise ValueError(
            "Provide --overlay-batch-summary-tsv, or provide "
            f"{', '.join(missing)} so the pipeline can render overlays.",
        )
    queue_rows = read_tsv_required(
        review_queue_tsv,
        ("feature_family_id",),
    )
    remaining = len(queue_rows) - start_rank + 1
    if remaining < 1:
        raise ValueError(
            f"--start-rank {start_rank} is outside review queue row count "
            f"{len(queue_rows)}.",
        )
    effective_limit = remaining if limit is None else limit
    overlay_dir = overlay_output_dir or output_dir / "family_ms1_overlay_batch"
    overlay_metrics: dict[str, Any] = {}
    overlay_rows = family_ms1_overlay_batch.run_overlay_batch(
        review_queue_tsv=review_queue_tsv,
        alignment_cells=alignment_cells_tsv,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=overlay_dir,
        limit=effective_limit,
        start_rank=start_rank,
        ppm=ppm,
        max_highlight_rescued=max_highlight_rescued,
        reuse_existing=reuse_existing,
        write_pdf=write_overlay_pdf,
        evidence_only=evidence_only,
        metrics=overlay_metrics,
    )
    family_ms1_overlay_batch._write_outputs(
        overlay_dir,
        overlay_rows,
        metrics=overlay_metrics,
    )
    failed = [row for row in overlay_rows if row["status"] == "failed"]
    _run_step("family MS1 overlay batch", 2 if failed else 0)
    return OverlaySourceResolution(
        summary_tsv=overlay_dir / "family_ms1_overlay_batch_summary.tsv",
        mode=(
            "evidence_from_review_queue"
            if evidence_only
            else "rendered_from_review_queue"
        ),
        evidence_source_mode="evidence_only" if evidence_only else "rendered_images",
        queue_row_count=len(queue_rows),
        requested_limit=limit,
        effective_limit=effective_limit,
        metrics=overlay_metrics,
    )


def _resolve_reconciliation_groups_tsv(
    *,
    reconciliation_groups_tsv: Path | None,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    alignment_matrix_tsv: Path,
    backfill_seed_audit_tsv: Path | None,
    overlay_batch_summary_tsv: Path,
    retained_gate_tsv: Path,
    output_dir: Path,
    source_run_id: str,
) -> Path:
    if reconciliation_groups_tsv is not None:
        return reconciliation_groups_tsv
    outputs = run_reconciliation_gallery(
        alignment_review_tsv=alignment_review_tsv,
        alignment_cells_tsv=alignment_cells_tsv,
        output_dir=output_dir / "reconciliation_group_index",
        alignment_matrix_tsv=alignment_matrix_tsv,
        backfill_seed_audit_tsv=backfill_seed_audit_tsv,
        overlay_batch_summary_tsvs=(overlay_batch_summary_tsv,),
        retained_backfill_gate_tsv=retained_gate_tsv,
        source_run_id=source_run_id,
    )
    return outputs.groups_tsv


def _run_step(label: str, code: int) -> None:
    if code != 0:
        raise ValueError(f"{label} failed with exit code {code}")


def _summarize_overlay_batch(path: Path) -> dict[str, Any]:
    rows = read_tsv_required(path, ("status", "rank", "feature_family_id"))
    status_counts = Counter(text_value(row.get("status")) for row in rows)
    rendered_image_count = sum(1 for row in rows if text_value(row.get("png_path")))
    return {
        "selected_row_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "success_count": status_counts.get("success", 0),
        "failed_count": status_counts.get("failed", 0),
        "rendered_image_count": rendered_image_count,
    }


def _load_json_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pipeline_status(
    *,
    overlay_summary: dict[str, Any],
    shift_summary: dict[str, Any],
    productization_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if int(overlay_summary.get("selected_row_count", 0) or 0) <= 0:
        reasons.append("overlay_no_selected_rows")
    if int(overlay_summary.get("failed_count", 0) or 0) > 0:
        reasons.append("overlay_failed_rows")
    if int(overlay_summary.get("success_count", 0) or 0) <= 0:
        reasons.append("overlay_no_success_rows")
    shift_status_counts = shift_summary.get("status_counts", {})
    if isinstance(shift_status_counts, dict):
        if int(shift_status_counts.get("failed", 0) or 0) > 0:
            reasons.append("shift_aware_failed_rows")
        if int(shift_status_counts.get("skipped", 0) or 0) > 0:
            reasons.append("shift_aware_skipped_rows")
    if int(shift_summary.get("successful_shift_aware_row_count", 0) or 0) <= 0:
        reasons.append("shift_aware_no_success_rows")
    if text_value(productization_summary.get("status")) != "pass":
        reasons.append("productization_not_pass")
    if text_value(productization_summary.get("activation_acceptance_status")) != "pass":
        reasons.append("activation_acceptance_not_pass")
    if text_value(productization_summary.get("activation_application_status")) not in {
        "applied",
        "not_requested",
        "",
    }:
        reasons.append("activation_application_not_applied")
    return ("pass" if not reasons else "incomplete", reasons)


def _optional_path_arg(flag: str, path: Path | None) -> list[str]:
    return [] if path is None else [flag, str(path)]


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay-batch-summary-tsv", type=Path)
    parser.add_argument(
        "--review-queue-tsv",
        type=Path,
        help=(
            "Optional alignment_retained_backfill_overlay_review_queue.tsv. "
            "When supplied with RAW/DLL paths, the pipeline renders overlays "
            "before running the machine gate."
        ),
    )
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--dll-dir", type=Path)
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--alignment-cells-tsv", type=Path, required=True)
    parser.add_argument("--alignment-matrix-tsv", type=Path, required=True)
    parser.add_argument("--alignment-matrix-identity-tsv", type=Path, required=True)
    parser.add_argument("--retained-gate-tsv", type=Path, required=True)
    parser.add_argument(
        "--reconciliation-groups-tsv",
        type=Path,
        help=(
            "Optional existing backfill_evidence_reconciliation_groups.tsv. "
            "If omitted, the pipeline builds one from the current inputs."
        ),
    )
    parser.add_argument("--backfill-seed-audit-tsv", type=Path)
    parser.add_argument("--reconciliation-gallery-html", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overlay-output-dir", type=Path)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Optional chunk size. In review-queue mode, omitting this renders "
            "all rows from --start-rank to the end of the queue instead of "
            "falling back to the overlay-batch default."
        ),
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help=(
            "Reuse existing overlay and shift-aware alignment experiment "
            "outputs when their provenance matches the current request."
        ),
    )
    parser.add_argument("--ppm", type=float, default=20.0)
    parser.add_argument("--max-highlight-rescued", type=int, default=8)
    parser.add_argument(
        "--write-overlay-pdf",
        action="store_true",
        help="Also write overlay PDFs. PNG-only is the default for large runs.",
    )
    parser.add_argument(
        "--min-shape-r",
        type=float,
        default=(
            shift_aware_backfill_calibration_pack.DEFAULT_STANDARD_PEAK_MIN_SHAPE_R
        ),
    )
    parser.add_argument(
        "--publication-mode",
        choices=("matrix-only", "review-gallery", "deep-audit"),
        default="deep-audit",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help=(
            "Generate compact trace/evidence artifacts from the review queue "
            "without rendering family overlay PNG/PDF files."
        ),
    )
    parser.add_argument("--write-gallery", action="store_true")
    parser.add_argument("--gallery-output-dir", type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
