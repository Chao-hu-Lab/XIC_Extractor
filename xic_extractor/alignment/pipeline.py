from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xic_extractor.alignment.backfill import (
    MS1BackfillSource,
    backfill_alignment_matrix,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.alignment.debug_writer import (
    write_ambiguous_ms1_owners_tsv,
    write_event_to_ms1_owner_tsv,
)
from xic_extractor.alignment.family_integration import integrate_feature_family_matrix
from xic_extractor.alignment.feature_family import build_ms1_feature_families
from xic_extractor.alignment.html_report import write_alignment_review_html
from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.output_levels import (
    AlignmentOutputLevel,
    artifact_names_for_output_level,
)
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import (
    cluster_sample_local_owners,
    review_only_features_from_ambiguous_records,
)
from xic_extractor.alignment.owner_matrix import build_owner_alignment_matrix
from xic_extractor.alignment.ownership import (
    OwnershipBuildResult,
    build_sample_local_owners,
)
from xic_extractor.alignment.tsv_writer import (
    write_alignment_cells_tsv,
    write_alignment_matrix_tsv,
    write_alignment_review_tsv,
    write_alignment_status_matrix_tsv,
)
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx
from xic_extractor.config import ExtractionConfig


class AlignmentRawHandle(MS1BackfillSource, Protocol):
    pass


RawOpener = Callable[[Path, Path], AbstractContextManager[AlignmentRawHandle]]
TsvWriter = Callable[[Path, AlignmentMatrix], Path]


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


def run_alignment(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    output_level: AlignmentOutputLevel = "machine",
    emit_alignment_cells: bool = False,
    emit_alignment_status_matrix: bool = False,
    raw_opener: RawOpener | None = None,
) -> AlignmentRunOutputs:
    batch = read_discovery_batch_index(discovery_batch_index)
    candidates = tuple(
        candidate
        for sample_stem in batch.sample_order
        for candidate in read_discovery_candidates_csv(
            batch.candidate_csvs[sample_stem]
        )
    )
    opener = raw_opener or _default_raw_opener

    with ExitStack() as stack:
        raw_sources = {
            sample_stem: stack.enter_context(opener(raw_path, dll_dir))
            for sample_stem, raw_path in _existing_raw_paths(
                sample_order=batch.sample_order,
                raw_files=batch.raw_files,
                raw_dir=raw_dir,
            ).items()
        }
        ownership = build_sample_local_owners(
            candidates,
            raw_sources=raw_sources,
            alignment_config=alignment_config,
            peak_config=peak_config,
        )
        owner_features = cluster_sample_local_owners(
            ownership.owners,
            config=alignment_config,
        )
        owner_features = (
            *owner_features,
            *review_only_features_from_ambiguous_records(
                ownership.ambiguous_records,
                start_index=len(owner_features) + 1,
            ),
        )
        rescued_cells = build_owner_backfill_cells(
            owner_features,
            sample_order=batch.sample_order,
            raw_sources=raw_sources,
            alignment_config=alignment_config,
            peak_config=peak_config,
        )
        matrix = build_owner_alignment_matrix(
            owner_features,
            sample_order=batch.sample_order,
            ambiguous_by_sample={},
            rescued_cells=rescued_cells,
        )
        outputs = _output_paths(
            output_dir,
            output_level=output_level,
            emit_alignment_cells=emit_alignment_cells,
            emit_alignment_status_matrix=emit_alignment_status_matrix,
        )
        _write_outputs_atomic(
            outputs,
            matrix,
            metadata=_metadata(
                discovery_batch_index=discovery_batch_index,
                raw_dir=raw_dir,
                dll_dir=dll_dir,
                output_level=output_level,
                peak_config=peak_config,
            ),
            ownership=ownership,
        )
        return outputs


def _build_event_first_matrix(
    clusters,
    *,
    sample_order,
    raw_sources,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignmentMatrix:
    event_matrix = backfill_alignment_matrix(
        clusters,
        sample_order=sample_order,
        raw_sources=raw_sources,
        alignment_config=alignment_config,
        peak_config=peak_config,
    )
    families = build_ms1_feature_families(
        clusters,
        event_matrix=event_matrix,
        config=alignment_config,
    )
    return integrate_feature_family_matrix(
        families,
        sample_order=sample_order,
        raw_sources=raw_sources,
        alignment_config=alignment_config,
        peak_config=peak_config,
    )


def _existing_raw_paths(
    *,
    sample_order: tuple[str, ...],
    raw_files: dict[str, Path | None],
    raw_dir: Path,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for sample_stem in sample_order:
        raw_file = raw_files.get(sample_stem)
        candidates: list[Path] = []
        if raw_file is not None and str(raw_file):
            candidates.append(raw_dir / raw_file.name)
        candidates.append(raw_dir / f"{sample_stem}.raw")
        for candidate in candidates:
            if candidate.exists():
                paths[sample_stem] = candidate
                break
    return paths


def _output_paths(
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
    )


def _write_outputs_atomic(
    outputs: AlignmentRunOutputs,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
    ownership: OwnershipBuildResult,
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
            (outputs.matrix_tsv, lambda path: write_alignment_matrix_tsv(path, matrix)),
        )
    if outputs.review_tsv is not None:
        output_paths_and_writers.append(
            (outputs.review_tsv, lambda path: write_alignment_review_tsv(path, matrix)),
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


def _metadata(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_level: AlignmentOutputLevel,
    peak_config: ExtractionConfig,
) -> dict[str, str]:
    return {
        "schema_version": "alignment-results-v1",
        "discovery_batch_index": str(discovery_batch_index),
        "raw_dir": str(raw_dir),
        "dll_dir": str(dll_dir),
        "output_level": output_level,
        "resolver_mode": peak_config.resolver_mode,
    }


def _default_raw_opener(
    raw_path: Path,
    dll_dir: Path,
) -> AbstractContextManager[AlignmentRawHandle]:
    from xic_extractor.raw_reader import open_raw

    return open_raw(raw_path, dll_dir)
