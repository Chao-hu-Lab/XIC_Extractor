import csv
from dataclasses import replace
from pathlib import Path
from typing import Literal

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extractor import DiagnosticRecord, ExtractionResult, FileResult
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.output.csv_writers import (
    _long_output_rows,
    _output_row,
    write_all,
    write_diagnostics_csv,
    write_long_csv,
    write_score_breakdown_csv,
    write_wide_csv,
)
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


def _config(tmp_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_csv=tmp_path / "output" / "xic_results.csv",
        diagnostics_csv=tmp_path / "output" / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        count_no_ms2_as_detected=True,
    )


def _target(label: str, *, neutral_loss_da: float | None = 116.0474) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=neutral_loss_da,
        nl_ppm_warn=20.0 if neutral_loss_da is not None else None,
        nl_ppm_max=50.0 if neutral_loss_da is not None else None,
        is_istd=False,
        istd_pair="",
    )


def _result(*, nl: NLResult | None = None) -> ExtractionResult:
    peak = PeakResult(
        rt=9.03,
        intensity=500.0,
        intensity_smoothed=450.0,
        area=123.45,
        peak_start=8.9,
        peak_end=9.2,
    )
    candidate = PeakCandidate(
        peak=peak,
        selection_apex_rt=9.0,
        selection_apex_intensity=450.0,
        selection_apex_index=10,
        raw_apex_rt=9.03,
        raw_apex_intensity=500.0,
        raw_apex_index=11,
        prominence=100.0,
    )
    peak_result = PeakDetectionResult(
        status="OK",
        peak=peak,
        n_points=12,
        max_smoothed=450.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="LOW",
        reason="concerns: local_sn (minor)",
        severities=((1, "local_sn"),),
    )
    return ExtractionResult(
        peak_result=peak_result,
        nl=nl,
        target_label="WithNL",
        role="Analyte",
        istd_pair="ISTD",
        confidence="LOW",
        reason="concerns: local_sn (minor)",
        severities=((1, "local_sn"),),
        prior_rt=None,
        prior_source="",
        quality_penalty=1,
        quality_flags=("too_broad",),
    )


def _candidate_ms2_evidence(
    status: Literal["OK", "WARN", "NL_FAIL", "NO_MS2"],
    best_loss_ppm: float | None,
) -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=status != "NO_MS2",
        nl_match=status in {"OK", "WARN"},
        nl_status=status,
        trigger_scan_count=1 if status != "NO_MS2" else 0,
        strict_nl_scan_count=1 if status in {"OK", "WARN"} else 0,
        best_loss_ppm=best_loss_ppm,
        best_scan_rt=9.0 if best_loss_ppm is not None else None,
        best_product_base_ratio=0.5 if best_loss_ppm is not None else None,
        alignment_source="region" if status != "NO_MS2" else "none",
    )


def _file_result() -> FileResult:
    return FileResult(
        sample_name="SampleA",
        results={"WithNL": _result(nl=NLResult("WARN", 12.34, None, 3, 0, 2))},
        group=None,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_row_builders_use_smoothed_rt_and_preserve_area() -> None:
    target = _target("WithNL")
    file_result = _file_result()

    wide_row = _output_row(file_result, [target])
    long_row = _long_output_rows(file_result, [target])[0]

    assert wide_row["WithNL_RT"] == "9.0000"
    assert wide_row["WithNL_Area"] == "123.45"
    assert wide_row["WithNL_NL"] == "WARN_12.3ppm"
    assert long_row["RT"] == "9.0000"
    assert long_row["Area"] == "123.45"
    assert long_row["Confidence"] == "LOW"


def test_row_builders_report_selected_candidate_nl_before_target_window_nl() -> None:
    target = _target("WithNL")
    result = _result(nl=NLResult("OK", 1.0, 9.1, 3, 0, 3))
    result = replace(
        result,
        candidate_ms2_evidence=_candidate_ms2_evidence("NL_FAIL", 125.0),
    )
    file_result = FileResult(sample_name="SampleA", results={"WithNL": result})

    wide_row = _output_row(file_result, [target])
    long_row = _long_output_rows(file_result, [target])[0]

    assert wide_row["WithNL_NL"] == "NL_FAIL"
    assert long_row["NL"] == "NL_FAIL"


def test_write_wide_and_long_csv(tmp_path: Path) -> None:
    config = _config(tmp_path)
    target = _target("WithNL")
    file_results = [_file_result()]

    write_wide_csv(config, [target], file_results)
    write_long_csv(config, [target], file_results)

    assert _read_csv(config.output_csv)[0]["WithNL_RT"] == "9.0000"
    assert _read_csv(config.output_csv.with_name("xic_results_long.csv"))[0] == {
        "SampleName": "SampleA",
        "Group": "Other",
        "Target": "WithNL",
        "Role": "Analyte",
        "ISTD Pair": "",
        "RT": "9.0000",
        "Area": "123.45",
        "NL": "WARN_12.3ppm",
        "Int": "500",
        "PeakStart": "8.9000",
        "PeakEnd": "9.2000",
        "PeakWidth": "0.3000",
        "Confidence": "LOW",
        "Reason": "concerns: local_sn (minor)",
    }


def test_write_diagnostics_and_score_breakdown_csv(tmp_path: Path) -> None:
    config = _config(tmp_path)
    file_result = _file_result()
    diagnostics = [
        DiagnosticRecord(
            sample_name="SampleA",
            target_label="WithNL",
            issue="NL_FAIL",
            reason="best match 80 ppm",
        )
    ]

    write_diagnostics_csv(config, diagnostics)
    write_score_breakdown_csv(config, [file_result])

    assert _read_csv(config.diagnostics_csv) == [
        {
            "SampleName": "SampleA",
            "Target": "WithNL",
            "Issue": "NL_FAIL",
            "Reason": "best match 80 ppm",
        }
    ]
    breakdown = _read_csv(config.output_csv.with_name("xic_score_breakdown.csv"))[0]
    assert breakdown["local_sn"] == "1"
    assert breakdown["Quality Penalty"] == "1"
    assert breakdown["Quality Flags"] == "too_broad"
    assert breakdown["Total Severity"] == "2"
    assert breakdown["Prior RT"] == "NA"


def test_write_all_gates_score_breakdown(tmp_path: Path) -> None:
    config = _config(tmp_path)
    target = _target("WithNL")
    file_results = [_file_result()]

    write_all(
        config,
        [target],
        file_results,
        diagnostics=[],
        emit_score_breakdown=False,
    )
    assert config.output_csv.exists()
    assert not config.output_csv.with_name("xic_score_breakdown.csv").exists()

    write_all(
        config,
        [target],
        file_results,
        diagnostics=[],
        emit_score_breakdown=True,
    )
    assert config.output_csv.with_name("xic_score_breakdown.csv").exists()
