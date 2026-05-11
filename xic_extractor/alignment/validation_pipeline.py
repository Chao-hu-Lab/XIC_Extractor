from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.legacy_io import (
    LoadedMatrix,
    load_combine_fix_xlsx,
    load_fh_alignment_tsv,
    load_metabcombiner_tsv,
    load_xic_alignment,
)
from xic_extractor.alignment.validation_compare import (
    FeatureMatch,
    SummaryMetric,
    match_legacy_source,
    summarize_global,
    summarize_legacy_source,
)
from xic_extractor.alignment.validation_writer import (
    write_legacy_matches_tsv,
    write_validation_summary_tsv,
)


@dataclass(frozen=True)
class AlignmentValidationOutputs:
    summary_tsv: Path
    matches_tsv: Path


def run_alignment_validation(
    *,
    alignment_review: Path,
    alignment_matrix: Path,
    output_dir: Path,
    legacy_fh_tsv: Path | None = None,
    legacy_metabcombiner_tsv: Path | None = None,
    legacy_combine_fix_xlsx: Path | None = None,
    match_ppm: float = 20.0,
    match_rt_sec: float = 60.0,
    sample_scope: str = "xic",
    match_distance_warn_median: float = 0.5,
    match_distance_warn_p90: float = 0.8,
) -> AlignmentValidationOutputs:
    legacy_matrices = _load_legacy_matrices(
        legacy_fh_tsv=legacy_fh_tsv,
        legacy_metabcombiner_tsv=legacy_metabcombiner_tsv,
        legacy_combine_fix_xlsx=legacy_combine_fix_xlsx,
    )
    if not legacy_matrices:
        raise ValueError("at least one legacy source is required")

    xic = load_xic_alignment(alignment_review, alignment_matrix)
    all_matches: list[FeatureMatch] = []
    all_metrics: list[SummaryMetric] = []
    for legacy in legacy_matrices:
        matches = match_legacy_source(
            xic,
            legacy,
            match_ppm=match_ppm,
            match_rt_sec=match_rt_sec,
            sample_scope=sample_scope,
        )
        all_matches.extend(matches)
        all_metrics.extend(
            summarize_legacy_source(
                xic,
                legacy,
                matches,
                sample_scope=sample_scope,
                match_ppm=match_ppm,
                match_rt_sec=match_rt_sec,
                match_distance_warn_median=match_distance_warn_median,
                match_distance_warn_p90=match_distance_warn_p90,
            )
        )
    all_metrics.extend(summarize_global(tuple(all_metrics)))

    outputs = AlignmentValidationOutputs(
        summary_tsv=output_dir / "alignment_validation_summary.tsv",
        matches_tsv=output_dir / "alignment_legacy_matches.tsv",
    )
    _write_outputs_atomic(outputs, tuple(all_metrics), tuple(all_matches))
    return outputs


def _load_legacy_matrices(
    *,
    legacy_fh_tsv: Path | None,
    legacy_metabcombiner_tsv: Path | None,
    legacy_combine_fix_xlsx: Path | None,
) -> tuple[LoadedMatrix, ...]:
    matrices: list[LoadedMatrix] = []
    if legacy_fh_tsv is not None:
        matrices.append(load_fh_alignment_tsv(legacy_fh_tsv))
    if legacy_metabcombiner_tsv is not None:
        matrices.extend(load_metabcombiner_tsv(legacy_metabcombiner_tsv))
    if legacy_combine_fix_xlsx is not None:
        matrices.append(load_combine_fix_xlsx(legacy_combine_fix_xlsx))
    return tuple(matrices)


def _write_outputs_atomic(
    outputs: AlignmentValidationOutputs,
    metrics: tuple[SummaryMetric, ...],
    matches: tuple[FeatureMatch, ...],
) -> None:
    final_paths = (outputs.summary_tsv, outputs.matches_tsv)
    temp_paths = [_temp_path(final_path) for final_path in final_paths]
    backup_paths = [_backup_path(final_path) for final_path in final_paths]
    backups: list[tuple[Path, Path]] = []
    replaced_paths: list[Path] = []
    try:
        write_validation_summary_tsv(_temp_path(outputs.summary_tsv), metrics)
        write_legacy_matches_tsv(_temp_path(outputs.matches_tsv), matches)
        for final_path in final_paths:
            backup_path = _backup_path(final_path)
            backup_path.unlink(missing_ok=True)
            if final_path.exists():
                final_path.replace(backup_path)
                backups.append((final_path, backup_path))
        for final_path in final_paths:
            _temp_path(final_path).replace(final_path)
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
