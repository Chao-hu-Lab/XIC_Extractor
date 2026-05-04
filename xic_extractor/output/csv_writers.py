import csv
from collections.abc import Mapping, Sequence
from typing import Protocol

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import NLResult
from xic_extractor.output.schema import (
    DIAGNOSTIC_HEADERS,
    LONG_HEADERS,
    MS1_SUFFIXES,
    SCORE_BREAKDOWN_HEADERS,
)
from xic_extractor.sample_groups import classify_sample_group
from xic_extractor.signal_processing import PeakDetectionResult, PeakResult


class DiagnosticRecordLike(Protocol):
    @property
    def sample_name(self) -> str: ...

    @property
    def target_label(self) -> str: ...

    @property
    def issue(self) -> str: ...

    @property
    def reason(self) -> str: ...


class ExtractionResultLike(Protocol):
    @property
    def peak_result(self) -> PeakDetectionResult: ...

    @property
    def nl(self) -> NLResult | None: ...

    @property
    def target_label(self) -> str: ...

    @property
    def confidence(self) -> str: ...

    @property
    def reason(self) -> str: ...

    @property
    def severities(self) -> tuple[tuple[int, str], ...]: ...

    @property
    def prior_rt(self) -> float | None: ...

    @property
    def prior_source(self) -> str: ...

    @property
    def quality_penalty(self) -> int: ...

    @property
    def quality_flags(self) -> tuple[str, ...]: ...

    @property
    def reported_rt(self) -> float | None: ...

    @property
    def total_severity(self) -> int: ...


class FileResultLike(Protocol):
    @property
    def sample_name(self) -> str: ...

    @property
    def results(self) -> Mapping[str, ExtractionResultLike]: ...

    @property
    def error(self) -> str | None: ...

    @property
    def extraction_results(self) -> Sequence[ExtractionResultLike]: ...


def write_all(
    config: ExtractionConfig,
    targets: Sequence[Target],
    file_results: Sequence[FileResultLike],
    diagnostics: Sequence[DiagnosticRecordLike],
    *,
    emit_score_breakdown: bool,
) -> None:
    write_wide_csv(config, targets, file_results)
    write_long_csv(config, targets, file_results)
    write_diagnostics_csv(config, diagnostics)
    if emit_score_breakdown:
        write_score_breakdown_csv(config, file_results)


def write_wide_csv(
    config: ExtractionConfig,
    targets: Sequence[Target],
    file_results: Sequence[FileResultLike],
) -> None:
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _output_fieldnames(targets)
    with config.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for file_result in file_results:
            writer.writerow(_output_row(file_result, targets))


def write_diagnostics_csv(
    config: ExtractionConfig, diagnostics: Sequence[DiagnosticRecordLike]
) -> None:
    config.diagnostics_csv.parent.mkdir(parents=True, exist_ok=True)
    with config.diagnostics_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=DIAGNOSTIC_HEADERS)
        writer.writeheader()
        for record in diagnostics:
            writer.writerow(
                {
                    "SampleName": record.sample_name,
                    "Target": record.target_label,
                    "Issue": record.issue,
                    "Reason": record.reason,
                }
            )


def write_long_csv(
    config: ExtractionConfig,
    targets: Sequence[Target],
    file_results: Sequence[FileResultLike],
) -> None:
    path = config.output_csv.with_name("xic_results_long.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=LONG_HEADERS)
        writer.writeheader()
        for file_result in file_results:
            writer.writerows(_long_output_rows(file_result, targets))


def _long_output_rows(
    file_result: FileResultLike, targets: Sequence[Target]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for target in targets:
        row = {
            "SampleName": file_result.sample_name,
            "Group": _sample_group(file_result.sample_name),
            "Target": target.label,
            "Role": "ISTD" if target.is_istd else "Analyte",
            "ISTD Pair": target.istd_pair,
            "RT": "",
            "Area": "",
            "NL": "",
            "Int": "",
            "PeakStart": "",
            "PeakEnd": "",
            "PeakWidth": "",
            "Confidence": "",
            "Reason": "",
        }
        if file_result.error is not None:
            _set_long_ms1_values(row, "ERROR")
            row["NL"] = "ERROR" if target.neutral_loss_da is not None else ""
        else:
            result = file_result.results[target.label]
            _set_long_peak_values(row, result)
            row["NL"] = (
                result.nl.to_token()
                if target.neutral_loss_da is not None and result.nl is not None
                else ""
            )
            row["Confidence"] = result.confidence
            row["Reason"] = result.reason
        rows.append(row)
    return rows


def write_score_breakdown_csv(
    config: ExtractionConfig, file_results: Sequence[FileResultLike]
) -> None:
    path = config.output_csv.with_name("xic_score_breakdown.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_BREAKDOWN_HEADERS)
        writer.writeheader()
        for file_result in file_results:
            writer.writerows(_score_breakdown_rows(file_result))


def _score_breakdown_rows(file_result: FileResultLike) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in file_result.extraction_results:
        severities = {label: severity for severity, label in result.severities}
        rows.append(
            {
                "SampleName": file_result.sample_name,
                "Target": result.target_label,
                "symmetry": _format_optional_severity(severities.get("symmetry")),
                "local_sn": _format_optional_severity(severities.get("local_sn")),
                "nl_support": _format_optional_severity(
                    severities.get("nl_support")
                ),
                "rt_prior": _format_optional_severity(severities.get("rt_prior")),
                "rt_centrality": _format_optional_severity(
                    severities.get("rt_centrality")
                ),
                "noise_shape": _format_optional_severity(
                    severities.get("noise_shape")
                ),
                "peak_width": _format_optional_severity(
                    severities.get("peak_width")
                ),
                "Quality Penalty": str(result.quality_penalty),
                "Quality Flags": ",".join(result.quality_flags),
                "Total Severity": str(result.total_severity),
                "Confidence": result.confidence,
                "Prior RT": _format_optional_number(result.prior_rt),
                "Prior Source": result.prior_source,
            }
        )
    return rows


def _format_optional_severity(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:g}"


def _set_long_ms1_values(row: dict[str, str], value: str) -> None:
    row["RT"] = value
    row["Area"] = value
    row["Int"] = value
    row["PeakStart"] = value
    row["PeakEnd"] = value
    row["PeakWidth"] = value


def _set_long_peak_values(row: dict[str, str], result: ExtractionResultLike) -> None:
    peak = result.peak_result.peak
    if peak is None:
        _set_long_ms1_values(row, "ND")
        return
    reported_rt = result.reported_rt
    row["RT"] = f"{reported_rt:.4f}" if reported_rt is not None else "ND"
    row["Area"] = f"{peak.area:.2f}"
    row["Int"] = f"{peak.intensity:.0f}"
    row["PeakStart"] = f"{peak.peak_start:.4f}"
    row["PeakEnd"] = f"{peak.peak_end:.4f}"
    row["PeakWidth"] = _format_peak_width(peak)


def _output_fieldnames(targets: Sequence[Target]) -> list[str]:
    fieldnames = ["SampleName"]
    for target in targets:
        fieldnames.extend(_target_fieldnames(target))
    return fieldnames


def _target_fieldnames(target: Target) -> list[str]:
    fieldnames = [f"{target.label}_{suffix}" for suffix in MS1_SUFFIXES]
    if target.neutral_loss_da is not None:
        fieldnames.append(f"{target.label}_NL")
    return fieldnames


def _output_row(
    file_result: FileResultLike, targets: Sequence[Target]
) -> dict[str, str]:
    row = {"SampleName": file_result.sample_name}
    for target in targets:
        if file_result.error is not None:
            _set_target_values(row, target, "ERROR")
            continue

        result = file_result.results[target.label]
        _set_peak_values(row, target, result)
        if target.neutral_loss_da is not None:
            row[f"{target.label}_NL"] = result.nl.to_token() if result.nl else "ND"
    return row


def _set_target_values(row: dict[str, str], target: Target, value: str) -> None:
    for suffix in MS1_SUFFIXES:
        row[f"{target.label}_{suffix}"] = value
    if target.neutral_loss_da is not None:
        row[f"{target.label}_NL"] = value


def _set_peak_values(
    row: dict[str, str],
    target: Target,
    result: ExtractionResultLike,
) -> None:
    peak = result.peak_result.peak
    if peak is None:
        for suffix in MS1_SUFFIXES:
            row[f"{target.label}_{suffix}"] = "ND"
        return

    reported_rt = result.reported_rt
    row[f"{target.label}_RT"] = (
        f"{reported_rt:.4f}" if reported_rt is not None else "ND"
    )
    row[f"{target.label}_Int"] = f"{peak.intensity:.0f}"
    row[f"{target.label}_Area"] = f"{peak.area:.2f}"
    row[f"{target.label}_PeakStart"] = f"{peak.peak_start:.4f}"
    row[f"{target.label}_PeakEnd"] = f"{peak.peak_end:.4f}"
    row[f"{target.label}_PeakWidth"] = _format_peak_width(peak)


def _format_peak_width(peak: PeakResult) -> str:
    return f"{abs(peak.peak_end - peak.peak_start):.4f}"


def _sample_group(name: str) -> str:
    return classify_sample_group(name)
