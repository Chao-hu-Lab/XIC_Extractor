from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xic_extractor.alignment.backfill import (
    MS1BackfillSource,
    backfill_alignment_matrix,
)
from xic_extractor.alignment.clustering import cluster_candidates
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.tsv_writer import (
    write_alignment_cells_tsv,
    write_alignment_matrix_tsv,
    write_alignment_review_tsv,
    write_alignment_status_matrix_tsv,
)
from xic_extractor.config import ExtractionConfig


class AlignmentRawHandle(MS1BackfillSource, Protocol):
    pass


RawOpener = Callable[[Path, Path], AbstractContextManager[AlignmentRawHandle]]
TsvWriter = Callable[[Path, AlignmentMatrix], Path]


@dataclass(frozen=True)
class AlignmentRunOutputs:
    review_tsv: Path
    matrix_tsv: Path
    cells_tsv: Path | None = None
    status_matrix_tsv: Path | None = None


def run_alignment(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
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
    clusters = cluster_candidates(candidates, config=alignment_config)
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
        matrix = backfill_alignment_matrix(
            clusters,
            sample_order=batch.sample_order,
            raw_sources=raw_sources,
            alignment_config=alignment_config,
            peak_config=peak_config,
        )
        outputs = _output_paths(
            output_dir,
            emit_alignment_cells=emit_alignment_cells,
            emit_alignment_status_matrix=emit_alignment_status_matrix,
        )
        _write_outputs_atomic(outputs, matrix)
        return outputs


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
    emit_alignment_cells: bool,
    emit_alignment_status_matrix: bool,
) -> AlignmentRunOutputs:
    return AlignmentRunOutputs(
        review_tsv=output_dir / "alignment_review.tsv",
        matrix_tsv=output_dir / "alignment_matrix.tsv",
        cells_tsv=output_dir / "alignment_cells.tsv" if emit_alignment_cells else None,
        status_matrix_tsv=(
            output_dir / "alignment_matrix_status.tsv"
            if emit_alignment_status_matrix
            else None
        ),
    )


def _write_outputs_atomic(
    outputs: AlignmentRunOutputs,
    matrix: AlignmentMatrix,
) -> None:
    output_paths_and_writers: list[tuple[Path, TsvWriter]] = [
        (outputs.review_tsv, write_alignment_review_tsv),
        (outputs.matrix_tsv, write_alignment_matrix_tsv),
    ]
    if outputs.cells_tsv is not None:
        output_paths_and_writers.append((outputs.cells_tsv, write_alignment_cells_tsv))
    if outputs.status_matrix_tsv is not None:
        output_paths_and_writers.append(
            (outputs.status_matrix_tsv, write_alignment_status_matrix_tsv)
        )

    temp_paths = [
        final_path.with_name(f"{final_path.name}.tmp")
        for final_path, _writer in output_paths_and_writers
    ]
    try:
        for final_path, writer in output_paths_and_writers:
            temp_path = final_path.with_name(f"{final_path.name}.tmp")
            writer(temp_path, matrix)
        for final_path, _writer in output_paths_and_writers:
            temp_path = final_path.with_name(f"{final_path.name}.tmp")
            temp_path.replace(final_path)
    except Exception:
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)
        raise


def _default_raw_opener(
    raw_path: Path,
    dll_dir: Path,
) -> AbstractContextManager[AlignmentRawHandle]:
    from xic_extractor.raw_reader import open_raw

    return open_raw(raw_path, dll_dir)
