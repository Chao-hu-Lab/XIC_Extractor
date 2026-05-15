from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.debug_writer import (
    write_ambiguous_ms1_owners_tsv,
    write_event_to_ms1_owner_tsv,
    write_owner_edge_evidence_tsv,
)
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence
from xic_extractor.alignment.html_report import write_alignment_review_html
from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.ms1_index_source import OwnerBackfillXicBackend
from xic_extractor.alignment.output_levels import (
    AlignmentOutputLevel,
    artifact_names_for_output_level,
)
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.tsv_writer import (
    write_alignment_cells_tsv,
    write_alignment_matrix_tsv,
    write_alignment_review_tsv,
    write_alignment_status_matrix_tsv,
)
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx
from xic_extractor.config import ExtractionConfig


@dataclass(frozen=True)
class AlignmentRunOutputs:
    workbook: Path | None = None
    review_html: Path | None = None
    review_tsv: Path | None = None
    matrix_tsv: Path | None = None
    cells_tsv: Path | None = None
    status_matrix_tsv: Path | None = None
    event_to_owner_tsv: Path | None = None
    ambiguous_owners_tsv: Path | None = None
    edge_evidence_tsv: Path | None = None


def output_paths(
    output_dir: Path,
    *,
    output_level: AlignmentOutputLevel,
    emit_alignment_cells: bool,
    emit_alignment_status_matrix: bool,
) -> AlignmentRunOutputs:
    artifacts = set(artifact_names_for_output_level(output_level))
    if emit_alignment_cells:
        artifacts.add("alignment_cells.tsv")
    if emit_alignment_status_matrix:
        artifacts.add("alignment_matrix_status.tsv")
    return AlignmentRunOutputs(
        workbook=(
            output_dir / "alignment_results.xlsx"
            if "alignment_results.xlsx" in artifacts
            else None
        ),
        review_html=(
            output_dir / "review_report.html"
            if "review_report.html" in artifacts
            else None
        ),
        review_tsv=(
            output_dir / "alignment_review.tsv"
            if "alignment_review.tsv" in artifacts
            else None
        ),
        matrix_tsv=(
            output_dir / "alignment_matrix.tsv"
            if "alignment_matrix.tsv" in artifacts
            else None
        ),
        cells_tsv=(
            output_dir / "alignment_cells.tsv"
            if "alignment_cells.tsv" in artifacts
            else None
        ),
        status_matrix_tsv=(
            output_dir / "alignment_matrix_status.tsv"
            if "alignment_matrix_status.tsv" in artifacts
            else None
        ),
        event_to_owner_tsv=(
            output_dir / "event_to_ms1_owner.tsv"
            if "event_to_ms1_owner.tsv" in artifacts
            else None
        ),
        ambiguous_owners_tsv=(
            output_dir / "ambiguous_ms1_owners.tsv"
            if "ambiguous_ms1_owners.tsv" in artifacts
            else None
        ),
        edge_evidence_tsv=(
            output_dir / "owner_edge_evidence.tsv"
            if "owner_edge_evidence.tsv" in artifacts
            else None
        ),
    )


def alignment_metadata(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    owner_backfill_xic_backend: OwnerBackfillXicBackend,
    output_level: AlignmentOutputLevel,
    peak_config: ExtractionConfig,
) -> dict[str, str]:
    return {
        "schema_version": "alignment-results-v1",
        "discovery_batch_index": str(discovery_batch_index),
        "raw_dir": str(raw_dir),
        "dll_dir": str(dll_dir),
        "owner_backfill_xic_backend": owner_backfill_xic_backend,
        "output_level": output_level,
        "resolver_mode": peak_config.resolver_mode,
    }


def write_outputs_atomic(
    outputs: AlignmentRunOutputs,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
    ownership: OwnershipBuildResult,
    alignment_config: AlignmentConfig,
    edge_evidence: Sequence[OwnerEdgeEvidence] = (),
) -> None:
    output_paths_and_writers: list[tuple[Path, Callable[[Path], Path]]] = []
    if outputs.workbook is not None:
        output_paths_and_writers.append(
            (
                outputs.workbook,
                lambda path: write_alignment_results_xlsx(
                    path,
                    matrix,
                    metadata=metadata,
                    alignment_config=alignment_config,
                ),
            ),
        )
    if outputs.review_html is not None:
        output_paths_and_writers.append(
            (
                outputs.review_html,
                lambda path: write_alignment_review_html(path, matrix),
            ),
        )
    if outputs.matrix_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.matrix_tsv,
                lambda path: write_alignment_matrix_tsv(
                    path,
                    matrix,
                    alignment_config=alignment_config,
                ),
            ),
        )
    if outputs.review_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.review_tsv,
                lambda path: write_alignment_review_tsv(
                    path,
                    matrix,
                    alignment_config=alignment_config,
                ),
            ),
        )
    if outputs.cells_tsv is not None:
        output_paths_and_writers.append(
            (outputs.cells_tsv, lambda path: write_alignment_cells_tsv(path, matrix)),
        )
    if outputs.status_matrix_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.status_matrix_tsv,
                lambda path: write_alignment_status_matrix_tsv(path, matrix),
            )
        )
    if outputs.event_to_owner_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.event_to_owner_tsv,
                lambda path: write_event_to_ms1_owner_tsv(path, ownership.assignments),
            ),
        )
    if outputs.ambiguous_owners_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.ambiguous_owners_tsv,
                lambda path: write_ambiguous_ms1_owners_tsv(
                    path,
                    ownership.ambiguous_records,
                ),
            ),
        )
    if outputs.edge_evidence_tsv is not None:
        output_paths_and_writers.append(
            (
                outputs.edge_evidence_tsv,
                lambda path: write_owner_edge_evidence_tsv(path, edge_evidence),
            ),
        )

    temp_paths = [
        _temp_path(final_path) for final_path, _writer in output_paths_and_writers
    ]
    backup_paths = [
        _backup_path(final_path) for final_path, _writer in output_paths_and_writers
    ]
    backups: list[tuple[Path, Path]] = []
    replaced_paths: list[Path] = []
    try:
        for final_path, writer in output_paths_and_writers:
            temp_path = _temp_path(final_path)
            writer(temp_path)
        for final_path, _writer in output_paths_and_writers:
            backup_path = _backup_path(final_path)
            backup_path.unlink(missing_ok=True)
            if final_path.exists():
                final_path.replace(backup_path)
                backups.append((final_path, backup_path))
        for final_path, _writer in output_paths_and_writers:
            temp_path = _temp_path(final_path)
            temp_path.replace(final_path)
            replaced_paths.append(final_path)
        for _final_path, backup_path in backups:
            with suppress(OSError):
                backup_path.unlink(missing_ok=True)
    except Exception:
        for final_path in replaced_paths:
            final_path.unlink(missing_ok=True)
        for final_path, backup_path in reversed(backups):
            if backup_path.exists():
                final_path.unlink(missing_ok=True)
                backup_path.replace(final_path)
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)
        for backup_path in backup_paths:
            backup_path.unlink(missing_ok=True)
        raise


def _temp_path(final_path: Path) -> Path:
    return final_path.with_name(f"{final_path.name}.tmp")


def _backup_path(final_path: Path) -> Path:
    return final_path.with_name(f"{final_path.name}.bak")
