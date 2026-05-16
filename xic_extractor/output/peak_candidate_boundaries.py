from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from xic_extractor.extraction.peak_candidate_boundaries import (
    PEAK_CANDIDATE_BOUNDARY_HEADERS,
    PeakCandidateBoundaryRow,
)


class FileResultWithPeakCandidateBoundaries(Protocol):
    @property
    def peak_candidate_boundary_rows(self) -> Sequence[Mapping[str, str]]: ...


def write_peak_candidate_boundaries_tsv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PEAK_CANDIDATE_BOUNDARY_HEADERS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_sanitize_row(row))


def write_peak_candidate_boundaries_for_file_results(
    path: Path,
    file_results: Sequence[FileResultWithPeakCandidateBoundaries],
    *,
    enabled: bool = True,
) -> None:
    rows: list[Mapping[str, str]] = []
    for file_result in file_results:
        rows.extend(file_result.peak_candidate_boundary_rows)
    write_peak_candidate_boundaries_tsv(path, rows, enabled=enabled)


def _sanitize_row(row: Mapping[str, str]) -> PeakCandidateBoundaryRow:
    return {
        header: _sanitize_field(str(row.get(header, "")))
        for header in PEAK_CANDIDATE_BOUNDARY_HEADERS
    }


def _sanitize_field(value: str) -> str:
    return " ".join(value.replace("\t", " ").splitlines())
