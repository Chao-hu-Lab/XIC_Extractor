from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from xic_extractor.output.selected_envelope_diagnostics import (
    write_selected_envelope_diagnostics_for_file_results,
    write_selected_envelope_diagnostics_tsv,
)
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
)


@dataclass(frozen=True)
class _FileResult:
    selected_envelope_diagnostic_rows: Sequence[Mapping[str, str]]


def test_write_selected_envelope_diagnostics_tsv_serializes_rows_safely(
    tmp_path: Path,
) -> None:
    path = tmp_path / "selected_envelope_diagnostics.tsv"
    row = {
        header: ""
        for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS
    }
    row.update(
        {
            "sample_name": "SampleA\tbad",
            "target_label": "Analyte\nbad",
            "selected_candidate_id": "candidate-001",
            "selected_boundary_mode": "selected_full_envelope",
            "row_boundary_decision": "accept_candidate",
        }
    )

    write_selected_envelope_diagnostics_tsv(path, [row])

    rows = _read_tsv(path)
    assert list(rows[0]) == list(SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS)
    assert rows[0]["sample_name"] == "SampleA bad"
    assert rows[0]["target_label"] == "Analyte bad"
    assert rows[0]["selected_candidate_id"] == "candidate-001"


def test_write_selected_envelope_diagnostics_for_file_results(
    tmp_path: Path,
) -> None:
    path = tmp_path / "selected_envelope_diagnostics.tsv"
    row = {
        header: ""
        for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS
    }
    row["sample_name"] = "SampleA"
    row["selected_candidate_id"] = "candidate-001"

    write_selected_envelope_diagnostics_for_file_results(path, [_FileResult([row])])

    assert _read_tsv(path)[0]["sample_name"] == "SampleA"


def test_write_selected_envelope_diagnostics_tsv_honors_disabled_flag(
    tmp_path: Path,
) -> None:
    path = tmp_path / "selected_envelope_diagnostics.tsv"

    write_selected_envelope_diagnostics_tsv(
        path,
        [{"sample_name": "SampleA"}],
        enabled=False,
    )

    assert not path.exists()


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
