from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from .output_models import (
    IdentityCoherenceOutputContext,
    IdentityCoherenceOutputPaths,
    IdentityCoherenceOutputRecord,
)
from .output_projection import (
    project_cell_evidence_row,
    project_control_row,
    project_decision_row,
    project_request_row,
)
from .output_summary import render_identity_coherence_summary
from .output_validation import validate_output_record
from .schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
)


def write_identity_coherence_requests_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_REQUEST_COLUMNS,
        [project_request_row(record.seed_gate) for record in validated],
    )


def write_identity_coherence_decisions_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_DECISION_COLUMNS,
        [project_decision_row(record.row_result.decision) for record in validated],
    )


def write_identity_coherence_cell_evidence_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(validate_output_record(record) for record in records)
    rows: list[dict[str, str]] = []
    for record in validated:
        rows.extend(
            project_cell_evidence_row(cell)
            for cell in record.row_result.cells
        )
    return _write_tsv(path, IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, rows)


def write_identity_coherence_controls_tsv(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> Path:
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_CONTROL_COLUMNS,
        [project_control_row(row) for row in rows],
    )


def write_identity_coherence_outputs(
    output_dir: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
    *,
    context: IdentityCoherenceOutputContext,
    control_rows: Sequence[Mapping[str, object]] = (),
) -> IdentityCoherenceOutputPaths:
    validated = tuple(validate_output_record(record) for record in records)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = IdentityCoherenceOutputPaths(
        requests_tsv=output_dir / "untargeted_identity_coherence_requests.tsv",
        decisions_tsv=output_dir / "untargeted_identity_coherence_decisions.tsv",
        cell_evidence_tsv=(
            output_dir / "untargeted_identity_coherence_cell_evidence.tsv"
        ),
        controls_tsv=output_dir / "untargeted_identity_coherence_controls.tsv",
        summary_md=output_dir / "untargeted_identity_coherence_summary.md",
    )
    write_identity_coherence_requests_tsv(paths.requests_tsv, validated)
    write_identity_coherence_decisions_tsv(paths.decisions_tsv, validated)
    write_identity_coherence_cell_evidence_tsv(paths.cell_evidence_tsv, validated)
    write_identity_coherence_controls_tsv(paths.controls_tsv, control_rows)
    paths.summary_md.write_text(
        render_identity_coherence_summary(
            validated,
            context=context,
            control_rows=control_rows,
        ),
        encoding="utf-8",
    )
    return paths


def _write_tsv(
    path: Path,
    columns: tuple[str, ...],
    rows: Sequence[Mapping[str, str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path
