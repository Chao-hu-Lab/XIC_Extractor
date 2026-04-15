import csv
import gc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import NLResult, check_nl
from xic_extractor.raw_reader import RawReaderError, open_raw, preflight_raw_reader
from xic_extractor.signal_processing import (
    PeakDetectionResult,
    PeakResult,
    find_peak_and_area,
)

DiagnosticIssue = Literal[
    "PEAK_NOT_FOUND",
    "NO_SIGNAL",
    "WINDOW_TOO_SHORT",
    "NL_FAIL",
    "NO_MS2",
    "FILE_ERROR",
]

_MS1_SUFFIXES = ("RT", "Int", "Area", "PeakStart", "PeakEnd", "PeakWidth")
_DIAGNOSTIC_FIELDS = ("SampleName", "Target", "Issue", "Reason")
_LONG_OUTPUT_FIELDS = (
    "SampleName",
    "Group",
    "Target",
    "Role",
    "ISTD Pair",
    "RT",
    "Area",
    "NL",
    "Int",
    "PeakStart",
    "PeakEnd",
    "PeakWidth",
)


@dataclass(frozen=True)
class DiagnosticRecord:
    sample_name: str
    target_label: str
    issue: DiagnosticIssue
    reason: str


@dataclass(frozen=True)
class ExtractionResult:
    peak_result: PeakDetectionResult
    nl: NLResult | None


@dataclass
class FileResult:
    sample_name: str
    results: dict[str, ExtractionResult]
    error: str | None = None


@dataclass
class RunOutput:
    file_results: list[FileResult]
    diagnostics: list[DiagnosticRecord]


def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> RunOutput:
    reader_errors = preflight_raw_reader(config.dll_dir)
    if reader_errors:
        raise RawReaderError(" ".join(reader_errors))

    raw_paths = sorted(config.data_dir.glob("*.raw"))
    file_results: list[FileResult] = []
    diagnostics: list[DiagnosticRecord] = []
    total = len(raw_paths)

    for index, raw_path in enumerate(raw_paths, start=1):
        if should_stop is not None and should_stop():
            break

        file_result, file_diagnostics = _process_file(config, targets, raw_path)
        file_results.append(file_result)
        diagnostics.extend(file_diagnostics)

        if progress_callback is not None:
            progress_callback(index, total, raw_path.name)
        if index % 50 == 0:
            gc.collect()

    output = RunOutput(file_results=file_results, diagnostics=diagnostics)
    _write_output_csv(config, targets, file_results)
    _write_long_output_csv(config, targets, file_results)
    _write_diagnostics_csv(config, diagnostics)
    return output


def _process_file(
    config: ExtractionConfig, targets: list[Target], raw_path: Path
) -> tuple[FileResult, list[DiagnosticRecord]]:
    sample_name = raw_path.stem
    try:
        with open_raw(raw_path, config.dll_dir) as raw:
            results: dict[str, ExtractionResult] = {}
            diagnostics: list[DiagnosticRecord] = []
            for target in targets:
                rt, intensity = raw.extract_xic(
                    target.mz, target.rt_min, target.rt_max, target.ppm_tol
                )
                peak_result = find_peak_and_area(rt, intensity, config)
                nl_result = _check_target_nl(raw, target, config)
                result = ExtractionResult(peak_result=peak_result, nl=nl_result)
                results[target.label] = result
                diagnostics.extend(
                    _build_diagnostics(sample_name, target, result, config)
                )
            return FileResult(sample_name=sample_name, results=results), diagnostics
    except Exception as exc:
        reason = f"Failed to open .raw: {type(exc).__name__}: {exc}"
        return (
            FileResult(sample_name=sample_name, results={}, error=reason),
            [
                DiagnosticRecord(
                    sample_name=sample_name,
                    target_label="",
                    issue="FILE_ERROR",
                    reason=reason,
                )
            ],
        )


def _check_target_nl(
    raw: Any, target: Target, config: ExtractionConfig
) -> NLResult | None:
    if target.neutral_loss_da is None:
        return None
    if target.nl_ppm_warn is None or target.nl_ppm_max is None:
        return None
    return check_nl(
        raw,
        precursor_mz=target.mz,
        rt_min=target.rt_min,
        rt_max=target.rt_max,
        neutral_loss_da=target.neutral_loss_da,
        nl_ppm_warn=target.nl_ppm_warn,
        nl_ppm_max=target.nl_ppm_max,
        ms2_precursor_tol_da=config.ms2_precursor_tol_da,
        nl_min_intensity_ratio=config.nl_min_intensity_ratio,
    )


def _build_diagnostics(
    sample_name: str,
    target: Target,
    result: ExtractionResult,
    config: ExtractionConfig,
) -> list[DiagnosticRecord]:
    records: list[DiagnosticRecord] = []
    if result.peak_result.status != "OK":
        records.append(
            DiagnosticRecord(
                sample_name=sample_name,
                target_label=target.label,
                issue=result.peak_result.status,
                reason=_peak_reason(target, result.peak_result, config),
            )
        )

    if result.nl is not None and result.nl.status in {"NL_FAIL", "NO_MS2"}:
        records.append(
            DiagnosticRecord(
                sample_name=sample_name,
                target_label=target.label,
                issue=result.nl.status,
                reason=_nl_reason(target, result.nl, config),
            )
        )
    return records


def _peak_reason(
    target: Target, peak_result: PeakDetectionResult, config: ExtractionConfig
) -> str:
    if peak_result.status == "NO_SIGNAL":
        return (
            f"XIC empty in window [{target.rt_min}, {target.rt_max}] for "
            f"m/z {target.mz} +/- {target.ppm_tol:g} ppm"
        )
    if peak_result.status == "WINDOW_TOO_SHORT":
        return (
            f"Only {peak_result.n_points} scans in window; "
            f"savgol requires >= {config.smooth_window}"
        )
    max_value = _format_optional_number(peak_result.max_smoothed)
    prominence_pct = config.peak_min_prominence_ratio * 100
    return (
        "No peak met prominence >= "
        f"{prominence_pct:g}% of max smoothed (max={max_value})"
    )


def _nl_reason(target: Target, nl: NLResult, config: ExtractionConfig) -> str:
    if nl.status == "NO_MS2":
        return (
            f"No MS2 scan targeting precursor {target.mz} +/- "
            f"{config.ms2_precursor_tol_da:g} Da within RT "
            f"[{target.rt_min}, {target.rt_max}]; "
            f"{nl.valid_ms2_scan_count} valid MS2 scans in window "
            f"({nl.parse_error_count} parse errors)"
        )

    limit = target.nl_ppm_max if target.nl_ppm_max is not None else 0.0
    if nl.best_ppm is not None:
        return (
            f"Precursor {target.mz} triggered {nl.matched_scan_count} MS2 scans; "
            f"best NL product {nl.best_ppm:.1f} ppm (limit {limit:g} ppm)"
        )

    diagnostic_ppm = max(3.0 * limit, 500.0)
    return (
        f"Precursor {target.mz} triggered {nl.matched_scan_count} MS2 scans; "
        f"no product within {diagnostic_ppm:g} ppm diagnostic window"
    )


def _write_output_csv(
    config: ExtractionConfig, targets: list[Target], file_results: list[FileResult]
) -> None:
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _output_fieldnames(targets)
    with config.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for file_result in file_results:
            writer.writerow(_output_row(file_result, targets))


def _write_diagnostics_csv(
    config: ExtractionConfig, diagnostics: list[DiagnosticRecord]
) -> None:
    config.diagnostics_csv.parent.mkdir(parents=True, exist_ok=True)
    with config.diagnostics_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_DIAGNOSTIC_FIELDS)
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


def _write_long_output_csv(
    config: ExtractionConfig, targets: list[Target], file_results: list[FileResult]
) -> None:
    path = config.output_csv.with_name("xic_results_long.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LONG_OUTPUT_FIELDS)
        writer.writeheader()
        for file_result in file_results:
            writer.writerows(_long_output_rows(file_result, targets))


def _long_output_rows(
    file_result: FileResult, targets: list[Target]
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
        }
        if file_result.error is not None:
            _set_long_ms1_values(row, "ERROR")
            row["NL"] = "ERROR" if target.neutral_loss_da is not None else ""
        else:
            result = file_result.results[target.label]
            _set_long_peak_values(row, result.peak_result.peak)
            row["NL"] = (
                result.nl.to_token()
                if target.neutral_loss_da is not None and result.nl is not None
                else ""
            )
        rows.append(row)
    return rows


def _set_long_ms1_values(row: dict[str, str], value: str) -> None:
    row["RT"] = value
    row["Area"] = value
    row["Int"] = value
    row["PeakStart"] = value
    row["PeakEnd"] = value
    row["PeakWidth"] = value


def _set_long_peak_values(row: dict[str, str], peak: PeakResult | None) -> None:
    if peak is None:
        _set_long_ms1_values(row, "ND")
        return
    row["RT"] = f"{peak.rt:.4f}"
    row["Area"] = f"{peak.area:.2f}"
    row["Int"] = f"{peak.intensity:.0f}"
    row["PeakStart"] = f"{peak.peak_start:.4f}"
    row["PeakEnd"] = f"{peak.peak_end:.4f}"
    row["PeakWidth"] = _format_peak_width(peak)


def _output_fieldnames(targets: list[Target]) -> list[str]:
    fieldnames = ["SampleName"]
    for target in targets:
        fieldnames.extend(_target_fieldnames(target))
    return fieldnames


def _target_fieldnames(target: Target) -> list[str]:
    fieldnames = [f"{target.label}_{suffix}" for suffix in _MS1_SUFFIXES]
    if target.neutral_loss_da is not None:
        fieldnames.append(f"{target.label}_NL")
    return fieldnames


def _output_row(file_result: FileResult, targets: list[Target]) -> dict[str, str]:
    row = {"SampleName": file_result.sample_name}
    for target in targets:
        if file_result.error is not None:
            _set_target_values(row, target, "ERROR")
            continue

        result = file_result.results[target.label]
        _set_peak_values(row, target, result.peak_result.peak)
        if target.neutral_loss_da is not None:
            row[f"{target.label}_NL"] = result.nl.to_token() if result.nl else "ND"
    return row


def _set_target_values(row: dict[str, str], target: Target, value: str) -> None:
    for suffix in _MS1_SUFFIXES:
        row[f"{target.label}_{suffix}"] = value
    if target.neutral_loss_da is not None:
        row[f"{target.label}_NL"] = value


def _set_peak_values(
    row: dict[str, str], target: Target, peak: PeakResult | None
) -> None:
    if peak is None:
        for suffix in _MS1_SUFFIXES:
            row[f"{target.label}_{suffix}"] = "ND"
        return

    row[f"{target.label}_RT"] = f"{peak.rt:.4f}"
    row[f"{target.label}_Int"] = f"{peak.intensity:.0f}"
    row[f"{target.label}_Area"] = f"{peak.area:.2f}"
    row[f"{target.label}_PeakStart"] = f"{peak.peak_start:.4f}"
    row[f"{target.label}_PeakEnd"] = f"{peak.peak_end:.4f}"
    row[f"{target.label}_PeakWidth"] = _format_peak_width(peak)


def _format_peak_width(peak: PeakResult) -> str:
    return f"{abs(peak.peak_end - peak.peak_start):.4f}"


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:g}"


def _sample_group(name: str) -> str:
    normalized = name.upper()
    if normalized.startswith("TUMOR"):
        return "Tumor"
    if normalized.startswith("NORMAL"):
        return "Normal"
    if normalized.startswith("BENIGNFAT"):
        return "Benignfat"
    return "QC"
