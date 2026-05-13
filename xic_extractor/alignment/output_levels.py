from __future__ import annotations

from typing import Literal, cast

AlignmentOutputLevel = Literal["production", "machine", "debug", "validation"]

_ARTIFACTS: dict[AlignmentOutputLevel, tuple[str, ...]] = {
    "production": (
        "alignment_results.xlsx",
        "review_report.html",
    ),
    "machine": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
    ),
    "debug": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_matrix_status.tsv",
        "event_to_ms1_owner.tsv",
        "ambiguous_ms1_owners.tsv",
        "owner_edge_evidence.tsv",
    ),
    "validation": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_matrix_status.tsv",
        "event_to_ms1_owner.tsv",
        "ambiguous_ms1_owners.tsv",
        "owner_edge_evidence.tsv",
    ),
}


def parse_alignment_output_level(value: str) -> AlignmentOutputLevel:
    if value not in _ARTIFACTS:
        raise ValueError(
            "output_level must be one of production, machine, debug, validation",
        )
    return cast(AlignmentOutputLevel, value)


def artifact_names_for_output_level(
    level: AlignmentOutputLevel,
) -> tuple[str, ...]:
    return _ARTIFACTS[level]
