from __future__ import annotations

import csv
from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.models import (
    IDENTITY_COHERENCE_FILES,
    DiagnosticBundle,
    TsvRows,
)


def bundle_from_output_dir(output_dir: Path) -> DiagnosticBundle:
    identity_dir = output_dir / "identity_coherence"
    return DiagnosticBundle(
        requests_tsv=identity_dir / IDENTITY_COHERENCE_FILES["requests_tsv"],
        decisions_tsv=identity_dir / IDENTITY_COHERENCE_FILES["decisions_tsv"],
        cell_evidence_tsv=identity_dir
        / IDENTITY_COHERENCE_FILES["cell_evidence_tsv"],
        controls_tsv=identity_dir / IDENTITY_COHERENCE_FILES["controls_tsv"],
        summary_md=identity_dir / IDENTITY_COHERENCE_FILES["summary_md"],
    )


def read_tsv_rows(path: Path) -> TsvRows:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, dialect="excel-tab")
        rows = tuple(tuple(row) for row in reader)
    if not rows:
        raise ValueError(f"{path}: empty TSV")
    return TsvRows(header=rows[0], rows=rows[1:])


def read_tsv_dict_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        return tuple(dict(row) for row in reader)


def tsv_digest(rows: TsvRows) -> str:
    return f"header={len(rows.header)} rows={len(rows.rows)}"
