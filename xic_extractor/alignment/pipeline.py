from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, ExitStack, suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from xic_extractor.alignment.backfill import (
    MS1BackfillSource,
    backfill_alignment_matrix,
)
from xic_extractor.alignment.claim_registry import apply_ms1_peak_claim_registry
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.alignment.debug_writer import (
    write_ambiguous_ms1_owners_tsv,
    write_event_to_ms1_owner_tsv,
    write_owner_edge_evidence_tsv,
)
from xic_extractor.alignment.edge_scoring import (
    DriftLookupProtocol,
    OwnerEdgeEvidence,
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
from xic_extractor.alignment.primary_consolidation import (
    consolidate_primary_family_rows,
)
from xic_extractor.alignment.process_backend import (
    run_owner_backfill_process,
    run_owner_build_process,
)
from xic_extractor.alignment.tsv_writer import (
    write_alignment_cells_tsv,
    write_alignment_matrix_tsv,
    write_alignment_review_tsv,
    write_alignment_status_matrix_tsv,
)
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.timing import TimingRecorder
from xic_extractor.xic_models import XICTrace


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
    edge_evidence_tsv: Path | None = None


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
    raw_workers: int = 1,
    raw_xic_batch_size: int = 1,
    drift_lookup: DriftLookupProtocol | None = None,
    timing_recorder: TimingRecorder | None = None,
) -> AlignmentRunOutputs:
    if raw_workers < 1:
        raise ValueError("raw_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    recorder = timing_recorder or TimingRecorder.disabled("alignment")
    recorder.record(
        "alignment.run_config",
        elapsed_sec=0.0,
        metrics={
            "raw_workers": raw_workers,
            "raw_xic_batch_size": raw_xic_batch_size,
            "output_level": output_level,
            "drift_prior_source": (
                drift_lookup.source if drift_lookup is not None else "none"
            ),
        },
    )
    with recorder.stage("alignment.read_batch_index"):
        batch = read_discovery_batch_index(discovery_batch_index)
    with recorder.stage("alignment.read_candidates") as stage:
        candidates = tuple(
            candidate
            for sample_stem in batch.sample_order
            for candidate in read_discovery_candidates_csv(
                batch.candidate_csvs[sample_stem]
            )
        )
        stage.metrics["candidate_count"] = len(candidates)
    opener = raw_opener or _default_raw_opener
    outputs = _output_paths(
        output_dir,
        output_level=output_level,
        emit_alignment_cells=emit_alignment_cells,
        emit_alignment_status_matrix=emit_alignment_status_matrix,
    )

    with ExitStack() as stack:
        raw_paths = _existing_raw_paths(
            sample_order=batch.sample_order,
            raw_files=batch.raw_files,
            raw_dir=raw_dir,
        )
        with recorder.stage("alignment.open_raw_sources") as stage:
            if raw_workers > 1:
                raw_sources = {}
                stage.metrics["raw_count"] = len(raw_paths)
                stage.metrics["mode"] = "process_workers"
            else:
                raw_sources = {
                    sample_stem: stack.enter_context(opener(raw_path, dll_dir))
                    for sample_stem, raw_path in raw_paths.items()
                }
                stage.metrics["raw_count"] = len(raw_sources)
        with recorder.stage("alignment.build_owners"):
            if raw_workers > 1:
                owner_output = run_owner_build_process(
                    candidates,
                    sample_order=batch.sample_order,
                    raw_paths=raw_paths,
                    dll_dir=dll_dir,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    max_workers=raw_workers,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                ownership = owner_output.ownership
                for stats in owner_output.timing_stats:
                    recorder.record(
                        "alignment.build_owners.extract_xic",
                        elapsed_sec=stats.elapsed_sec,
                        sample_stem=stats.sample_stem,
                        metrics={
                            "extract_xic_count": stats.extract_xic_count,
                            "extract_xic_batch_count": stats.extract_xic_batch_count,
                            "raw_chromatogram_call_count": (
                                stats.raw_chromatogram_call_count
                            ),
                            "point_count": stats.point_count,
                        },
                    )
            else:
                timed_raw_sources = _timed_raw_sources(
                    raw_sources,
                    recorder=recorder,
                    stage="alignment.build_owners.extract_xic",
                )
                ownership = build_sample_local_owners(
                    candidates,
                    raw_sources=timed_raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                _record_timed_raw_sources(timed_raw_sources, recorder=recorder)
        edge_evidence: list[OwnerEdgeEvidence] | None = (
            []
            if outputs.edge_evidence_tsv is not None or drift_lookup is not None
            else None
        )
        with recorder.stage("alignment.cluster_owners"):
            if edge_evidence is None:
                owner_features = cluster_sample_local_owners(
                    ownership.owners,
                    config=alignment_config,
                )
            else:
                owner_features = cluster_sample_local_owners(
                    ownership.owners,
                    config=alignment_config,
                    drift_lookup=drift_lookup,
                    edge_evidence_sink=edge_evidence,
                )
            owner_features = (
                *owner_features,
                *review_only_features_from_ambiguous_records(
                    ownership.ambiguous_records,
                    start_index=len(owner_features) + 1,
                ),
            )
        with recorder.stage("alignment.owner_backfill"):
            if raw_workers > 1:
                process_output = run_owner_backfill_process(
                    owner_features,
                    sample_order=batch.sample_order,
                    raw_paths=raw_paths,
                    dll_dir=dll_dir,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    max_workers=raw_workers,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                rescued_cells = process_output.cells
                for backfill_stats in process_output.timing_stats:
                    recorder.record(
                        "alignment.owner_backfill.extract_xic",
                        elapsed_sec=backfill_stats.elapsed_sec,
                        sample_stem=backfill_stats.sample_stem,
                        metrics={
                            "extract_xic_count": backfill_stats.extract_xic_count,
                            "extract_xic_batch_count": (
                                backfill_stats.extract_xic_batch_count
                            ),
                            "raw_chromatogram_call_count": (
                                backfill_stats.raw_chromatogram_call_count
                            ),
                            "point_count": backfill_stats.point_count,
                        },
                    )
            else:
                timed_raw_sources = _timed_raw_sources(
                    raw_sources,
                    recorder=recorder,
                    stage="alignment.owner_backfill.extract_xic",
                )
                rescued_cells = build_owner_backfill_cells(
                    owner_features,
                    sample_order=batch.sample_order,
                    raw_sources=timed_raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                _record_timed_raw_sources(timed_raw_sources, recorder=recorder)
        with recorder.stage("alignment.build_matrix"):
            matrix = build_owner_alignment_matrix(
                owner_features,
                sample_order=batch.sample_order,
                ambiguous_by_sample={},
                rescued_cells=rescued_cells,
            )
        with recorder.stage("alignment.claim_registry"):
            matrix = apply_ms1_peak_claim_registry(matrix, alignment_config)
        with recorder.stage("alignment.primary_consolidation"):
            matrix = consolidate_primary_family_rows(matrix, alignment_config)
        with recorder.stage("alignment.write_outputs"):
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
                alignment_config=alignment_config,
                edge_evidence=edge_evidence or (),
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


@dataclass
class _RawSourceTimingStats:
    sample_stem: str
    stage: str
    elapsed_sec: float = 0.0
    extract_xic_count: int = 0
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0
    point_count: int = 0


class _TimedRawSource:
    def __init__(
        self,
        source: AlignmentRawHandle,
        *,
        stats: _RawSourceTimingStats,
        timer: Callable[[], float] = perf_counter,
    ) -> None:
        self._source = source
        self._stats = stats
        self._timer = timer

    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        raw_call_count_before = _raw_chromatogram_call_count(self._source)
        start = self._timer()
        try:
            rt, intensity = self._source.extract_xic(mz, rt_min, rt_max, ppm_tol)
        finally:
            self._stats.extract_xic_count += 1
            self._stats.extract_xic_batch_count += 1
            self._stats.elapsed_sec += self._timer() - start
            self._stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                _raw_chromatogram_call_count(self._source),
            )
        self._stats.point_count += _trace_point_count(rt)
        return rt, intensity

    def extract_xic_many(self, requests):
        requests = tuple(requests)
        if hasattr(self._source, "extract_xic_many"):
            raw_call_count_before = _raw_chromatogram_call_count(self._source)
            start = self._timer()
            try:
                traces = tuple(self._source.extract_xic_many(requests))
            finally:
                self._stats.elapsed_sec += self._timer() - start
            self._stats.extract_xic_count += len(requests)
            self._stats.extract_xic_batch_count += 1 if requests else 0
            self._stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                _raw_chromatogram_call_count(self._source),
            )
            self._stats.point_count += sum(len(trace.intensity) for trace in traces)
            return traces

        traces: list[XICTrace] = []
        for request in requests:
            rt, intensity = self.extract_xic(
                request.mz,
                request.rt_min,
                request.rt_max,
                request.ppm_tol,
            )
            traces.append(XICTrace.from_arrays(rt, intensity))
        return tuple(traces)

    def scan_window_for_request(self, request):
        return self._source.scan_window_for_request(request)


def _timed_raw_sources(
    raw_sources: dict[str, AlignmentRawHandle],
    *,
    recorder: TimingRecorder,
    stage: str,
) -> dict[str, _TimedRawSource]:
    return {
        sample_stem: _TimedRawSource(
            source,
            stats=_RawSourceTimingStats(sample_stem=sample_stem, stage=stage),
        )
        for sample_stem, source in raw_sources.items()
    }


def _record_timed_raw_sources(
    raw_sources: dict[str, _TimedRawSource],
    *,
    recorder: TimingRecorder,
) -> None:
    for source in raw_sources.values():
        stats = source._stats
        if stats.extract_xic_count == 0:
            continue
        recorder.record(
            stats.stage,
            elapsed_sec=stats.elapsed_sec,
            sample_stem=stats.sample_stem,
            metrics={
                "extract_xic_count": stats.extract_xic_count,
                "extract_xic_batch_count": stats.extract_xic_batch_count,
                "raw_chromatogram_call_count": stats.raw_chromatogram_call_count,
                "point_count": stats.point_count,
            },
        )


def _trace_point_count(trace: object) -> int:
    try:
        return len(trace)  # type: ignore[arg-type]
    except TypeError:
        return 0


def _raw_chromatogram_call_count(source: object) -> int | None:
    value = getattr(source, "raw_chromatogram_call_count", None)
    if isinstance(value, int):
        return value
    return None


def _raw_call_delta(before: int | None, after: int | None) -> int:
    if before is None or after is None:
        return 0
    return max(0, after - before)


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
        edge_evidence_tsv=(
            output_dir / "owner_edge_evidence.tsv"
            if "owner_edge_evidence.tsv" in artifacts
            else None
        ),
    )


def _write_outputs_atomic(
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
