from __future__ import annotations

from typing import TYPE_CHECKING

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.output import csv_writers
from xic_extractor.output.peak_candidate_boundaries import (
    write_peak_candidate_boundaries_for_file_results,
)
from xic_extractor.output.peak_candidates import write_peak_candidates_for_file_results

if TYPE_CHECKING:
    from xic_extractor.extractor import RunOutput


def write_outputs(
    config: ExtractionConfig,
    targets: list[Target],
    output: RunOutput,
) -> None:
    if config.emit_peak_candidates:
        write_peak_candidates_for_file_results(
            config.output_csv.with_name("peak_candidates.tsv"),
            output.file_results,
        )
        write_peak_candidate_boundaries_for_file_results(
            config.output_csv.with_name("peak_candidate_boundaries.tsv"),
            output.file_results,
        )
    if not config.keep_intermediate_csv:
        return
    csv_writers.write_all(
        config,
        targets,
        output.file_results,
        output.diagnostics,
        emit_score_breakdown=config.emit_score_breakdown,
    )
