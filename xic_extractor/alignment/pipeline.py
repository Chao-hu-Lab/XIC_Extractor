from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

from xic_extractor.alignment.backfill import (
    backfill_alignment_matrix,
)
from xic_extractor.alignment.claim_registry import apply_ms1_peak_claim_registry
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.alignment.edge_scoring import (
    DriftLookupProtocol,
    OwnerEdgeEvidence,
)
from xic_extractor.alignment.family_integration import integrate_feature_family_matrix
from xic_extractor.alignment.feature_family import build_ms1_feature_families
from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.ms1_index_source import OwnerBackfillXicBackend
from xic_extractor.alignment.output_levels import AlignmentOutputLevel
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import (
    cluster_sample_local_owners,
    review_only_features_from_ambiguous_records,
)
from xic_extractor.alignment.owner_matrix import build_owner_alignment_matrix
from xic_extractor.alignment.ownership import build_sample_local_owners
from xic_extractor.alignment.pipeline_outputs import (
    AlignmentRunOutputs,
    alignment_metadata,
    output_paths,
    write_outputs_atomic,
)
from xic_extractor.alignment.pre_backfill_consolidation import (
    consolidate_pre_backfill_identity_families,
    recenter_pre_backfill_identity_families,
)
from xic_extractor.alignment.primary_consolidation import (
    consolidate_primary_family_rows,
)
from xic_extractor.alignment.process_backend import (
    run_owner_backfill_process,
    run_owner_build_process,
)
from xic_extractor.alignment.raw_sources import (
    AlignmentRawHandle as _AlignmentRawHandle,
)
from xic_extractor.alignment.raw_sources import (
    RawOpener,
    RawSourceTimingStats,
    TimedRawSource,
    default_raw_opener,
    existing_raw_paths,
    record_raw_source_timing_stats,
    record_timed_raw_sources,
    timed_owner_backfill_sources,
    timed_raw_sources,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.timing import TimingRecorder

_RawSourceTimingStats = RawSourceTimingStats
_TimedRawSource = TimedRawSource
AlignmentRawHandle = _AlignmentRawHandle


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
    owner_backfill_xic_backend: OwnerBackfillXicBackend = "raw",
    preconsolidate_owner_families: bool = False,
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
            "owner_backfill_xic_backend": owner_backfill_xic_backend,
            "preconsolidate_owner_families": preconsolidate_owner_families,
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
                timed_raw_sources_ = timed_raw_sources(
                    raw_sources,
                    recorder=recorder,
                    stage="alignment.build_owners.extract_xic",
                )
                ownership = build_sample_local_owners(
                    candidates,
                    raw_sources=timed_raw_sources_,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                record_timed_raw_sources(timed_raw_sources_, recorder=recorder)
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
        if preconsolidate_owner_families:
            with recorder.stage("alignment.pre_backfill_consolidation"):
                owner_features = consolidate_pre_backfill_identity_families(
                    owner_features,
                    config=alignment_config,
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
                    owner_backfill_xic_backend=owner_backfill_xic_backend,
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
                (
                    backfill_raw_sources,
                    validation_raw_sources,
                    timing_stats,
                ) = timed_owner_backfill_sources(
                    raw_sources,
                    backend=owner_backfill_xic_backend,
                    recorder=recorder,
                    stage="alignment.owner_backfill.extract_xic",
                )
                validation_kwargs = (
                    {"validation_raw_sources": validation_raw_sources}
                    if validation_raw_sources is not None
                    else {}
                )
                rescued_cells = build_owner_backfill_cells(
                    owner_features,
                    sample_order=batch.sample_order,
                    raw_sources=backfill_raw_sources,
                    **validation_kwargs,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
                record_raw_source_timing_stats(timing_stats, recorder=recorder)
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
        with recorder.stage("alignment.pre_backfill_recenter"):
            matrix = recenter_pre_backfill_identity_families(matrix)
        with recorder.stage("alignment.write_outputs"):
            _write_outputs_atomic(
                outputs,
                matrix,
                metadata=_metadata(
                    discovery_batch_index=discovery_batch_index,
                    raw_dir=raw_dir,
                    dll_dir=dll_dir,
                    owner_backfill_xic_backend=owner_backfill_xic_backend,
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


_existing_raw_paths = existing_raw_paths
_output_paths = output_paths
_write_outputs_atomic = write_outputs_atomic
_metadata = alignment_metadata
_default_raw_opener = default_raw_opener
