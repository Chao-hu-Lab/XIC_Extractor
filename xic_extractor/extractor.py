from collections.abc import Callable
from dataclasses import dataclass

from xic_extractor import neutral_loss, raw_reader, signal_processing
from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.scoring_factory import selected_candidate
from xic_extractor.output.messages import (
    DiagnosticIssue,
    DiagnosticRecord,
)
from xic_extractor.rt_prior_library import LibraryEntry

open_raw = raw_reader.open_raw
CandidateMS2Evidence = neutral_loss.CandidateMS2Evidence
NLResult = neutral_loss.NLResult
check_nl = neutral_loss.check_nl
collect_candidate_ms2_evidence = neutral_loss.collect_candidate_ms2_evidence
find_nl_anchor_rt = neutral_loss.find_nl_anchor_rt
PeakDetectionResult = signal_processing.PeakDetectionResult
PeakResult = signal_processing.PeakResult
find_peak_and_area = signal_processing.find_peak_and_area

__all__ = [
    "DiagnosticIssue",
    "DiagnosticRecord",
    "ExtractionResult",
    "FileResult",
    "RunOutput",
    "run",
]
@dataclass(frozen=True)
class ExtractionResult:
    peak_result: PeakDetectionResult
    nl: NLResult | None
    candidate_ms2_evidence: CandidateMS2Evidence | None = None
    target_label: str = ""
    role: str = ""
    istd_pair: str = ""
    confidence: str = ""
    reason: str = ""
    severities: tuple[tuple[int, str], ...] = ()
    prior_rt: float | None = None
    prior_source: str = ""
    quality_penalty: int = 0
    quality_flags: tuple[str, ...] = ()
    score_breakdown: tuple[tuple[str, str], ...] = ()

    @property
    def peak(self) -> PeakResult | None:
        return self.peak_result.peak

    @property
    def nl_result(self) -> NLResult | None:
        return self.nl

    @property
    def nl_token(self) -> str | None:
        if self.candidate_ms2_evidence is not None:
            return self.candidate_ms2_evidence.to_token()
        if self.nl is not None:
            return self.nl.to_token()
        return None

    @property
    def total_severity(self) -> int:
        return sum(severity for severity, _ in self.severities) + self.quality_penalty

    @property
    def reported_rt(self) -> float | None:
        """User-facing RT uses the selected candidate apex when available."""
        candidate = selected_candidate(self.peak_result)
        if candidate is not None:
            return candidate.selection_apex_rt
        peak = self.peak
        if peak is None:
            return None
        return peak.rt


@dataclass
class FileResult:
    sample_name: str
    results: dict[str, ExtractionResult]
    group: str | None = None
    error: str | None = None

    @property
    def extraction_results(self) -> list[ExtractionResult]:
        return list(self.results.values())


@dataclass
class RunOutput:
    file_results: list[FileResult]
    diagnostics: list[DiagnosticRecord]


@dataclass
class RawFileExtractionResult:
    raw_index: int
    sample_name: str
    file_result: FileResult
    diagnostics: list[DiagnosticRecord]


def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    from xic_extractor.extraction.pipeline import run_pipeline

    return run_pipeline(
        config,
        targets,
        progress_callback=progress_callback,
        should_stop=should_stop,
        injection_order=injection_order,
        rt_prior_library=rt_prior_library,
    )
