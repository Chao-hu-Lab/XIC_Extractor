from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from xic_extractor.extraction.peak_region_selection_shadow import (
    PEAK_REGION_SELECTION_BLAST_RADIUS_HEADERS,
    PEAK_REGION_SELECTION_SHADOW_HEADERS,
    PEAK_REGION_SELECTION_SHADOW_SUMMARY_HEADERS,
    build_peak_region_selection_blast_radius_rows,
    build_peak_region_selection_shadow_rows,
    build_peak_region_selection_shadow_summary_rows,
)


class FileResultWithPeakCandidateBoundaries(Protocol):
    @property
    def peak_candidate_boundary_rows(self) -> Sequence[Mapping[str, str]]: ...


def write_peak_region_selection_shadow_tsv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
    *,
    enabled: bool = True,
) -> None:
    _write_tsv(path, rows, PEAK_REGION_SELECTION_SHADOW_HEADERS, enabled=enabled)


def write_peak_region_selection_shadow_for_file_results(
    path: Path,
    file_results: Sequence[FileResultWithPeakCandidateBoundaries],
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    boundary_rows: list[Mapping[str, str]] = []
    for file_result in file_results:
        boundary_rows.extend(file_result.peak_candidate_boundary_rows)

    rows = build_peak_region_selection_shadow_rows(boundary_rows)
    write_peak_region_selection_shadow_tsv(path, rows, enabled=enabled)
    _write_tsv(
        path.with_name("peak_region_selection_shadow_summary.tsv"),
        build_peak_region_selection_shadow_summary_rows(rows),
        PEAK_REGION_SELECTION_SHADOW_SUMMARY_HEADERS,
        enabled=enabled,
    )
    _write_tsv(
        path.with_name("peak_region_selection_shadow_blast_radius.tsv"),
        build_peak_region_selection_blast_radius_rows(rows),
        PEAK_REGION_SELECTION_BLAST_RADIUS_HEADERS,
        enabled=enabled,
    )


def _write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
    headers: Sequence[str],
    *,
    enabled: bool,
) -> None:
    if not enabled:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=headers,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_sanitize_row(row, headers))


def _sanitize_row(
    row: Mapping[str, str],
    headers: Sequence[str],
) -> dict[str, str]:
    return {
        header: _sanitize_field(str(row.get(header, "")))
        for header in headers
    }


def _sanitize_field(value: str) -> str:
    return " ".join(value.replace("\t", " ").splitlines())
