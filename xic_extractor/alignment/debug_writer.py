from __future__ import annotations

import csv
from pathlib import Path

from xic_extractor.alignment.output_rows import escape_excel_formula
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    OwnerAssignment,
)


def write_event_to_ms1_owner_tsv(
    path: Path,
    assignments: tuple[OwnerAssignment, ...],
) -> Path:
    rows = [
        {
            "candidate_id": assignment.candidate_id,
            "owner_id": assignment.owner_id or "",
            "assignment_status": assignment.assignment_status,
            "reason": assignment.reason,
        }
        for assignment in assignments
    ]
    return _write_tsv(
        path,
        ("candidate_id", "owner_id", "assignment_status", "reason"),
        rows,
    )


def write_ambiguous_ms1_owners_tsv(
    path: Path,
    records: tuple[AmbiguousOwnerRecord, ...],
) -> Path:
    rows = [
        {
            "ambiguity_id": record.ambiguity_id,
            "sample_stem": record.sample_stem,
            "candidate_ids": ";".join(record.candidate_ids),
            "reason": record.reason,
        }
        for record in records
    ]
    return _write_tsv(
        path,
        ("ambiguity_id", "sample_stem", "candidate_ids", "reason"),
        rows,
    )


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: escape_excel_formula(row.get(column, ""))
                    for column in fieldnames
                },
            )
    return path
