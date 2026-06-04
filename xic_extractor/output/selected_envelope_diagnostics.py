from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
    SelectedEnvelopeDiagnosticRow,
)


class FileResultWithSelectedEnvelopeDiagnostics(Protocol):
    @property
    def selected_envelope_diagnostic_rows(
        self,
    ) -> Sequence[Mapping[str, str]]: ...


def write_selected_envelope_diagnostics_tsv(
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
            fieldnames=SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_sanitize_row(row))


def write_selected_envelope_diagnostics_for_file_results(
    path: Path,
    file_results: Sequence[FileResultWithSelectedEnvelopeDiagnostics],
    *,
    enabled: bool = True,
) -> None:
    rows: list[Mapping[str, str]] = []
    for file_result in file_results:
        rows.extend(file_result.selected_envelope_diagnostic_rows)
    write_selected_envelope_diagnostics_tsv(path, rows, enabled=enabled)


def _sanitize_row(row: Mapping[str, str]) -> SelectedEnvelopeDiagnosticRow:
    return {
        header: _sanitize_field(str(row.get(header, "")))
        for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS
    }


def _sanitize_field(value: str) -> str:
    return " ".join(value.replace("\t", " ").splitlines())
