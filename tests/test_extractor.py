import csv
from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import NLResult
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


@pytest.fixture(autouse=True)
def _disable_reader_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "xic_extractor.extractor.preflight_raw_reader",
        lambda _dll_dir: [],
        raising=False,
    )


def test_run_raises_before_processing_when_reader_preflight_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "xic_extractor.extractor.preflight_raw_reader",
        lambda _dll_dir: ["pythonnet is not installed"],
        raising=False,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        lambda *_args: pytest.fail(
            "open_raw should not be called after preflight failure"
        ),
    )

    with pytest.raises(RawReaderError, match="pythonnet is not installed"):
        _run(config, [_target("Analyte")])

    assert not config.output_csv.exists()
    assert not config.diagnostics_csv.exists()


def test_run_writes_success_rows_with_area_columns_and_optional_nl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None), _target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(8.5, 1200.0, 3400.25), _ok_peak(9.5, 2200.0, 4400.75)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("WARN", 12.34, None, 3, 0, 2)]),
    )

    output = _run(config, targets, progress_callback=lambda *_args: None)

    rows = _read_csv(config.output_csv)
    assert list(rows[0].keys()) == [
        "SampleName",
        "NoNL_RT",
        "NoNL_Int",
        "NoNL_Area",
        "NoNL_PeakStart",
        "NoNL_PeakEnd",
        "NoNL_PeakWidth",
        "WithNL_RT",
        "WithNL_Int",
        "WithNL_Area",
        "WithNL_PeakStart",
        "WithNL_PeakEnd",
        "WithNL_PeakWidth",
        "WithNL_NL",
    ]
    assert rows == [
        {
            "SampleName": "SampleA",
            "NoNL_RT": "8.5000",
            "NoNL_Int": "1200",
            "NoNL_Area": "3400.25",
            "NoNL_PeakStart": "8.0000",
            "NoNL_PeakEnd": "9.0000",
            "NoNL_PeakWidth": "1.0000",
            "WithNL_RT": "9.5000",
            "WithNL_Int": "2200",
            "WithNL_Area": "4400.75",
            "WithNL_PeakStart": "9.0000",
            "WithNL_PeakEnd": "10.0000",
            "WithNL_PeakWidth": "1.0000",
            "WithNL_NL": "WARN_12.3ppm",
        }
    ]
    # WithNL target triggers NL_ANCHOR_FALLBACK; no error diagnostics.
    assert all(
        d["Issue"] == "NL_ANCHOR_FALLBACK" for d in _read_csv(config.diagnostics_csv)
    )
    assert len(output.file_results) == 1
    assert all(d.issue == "NL_ANCHOR_FALLBACK" for d in output.diagnostics)
    assert _read_csv(config.output_csv.with_name("xic_results_long.csv")) == [
        {
            "SampleName": "SampleA",
            "Group": "Other",
            "Target": "NoNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "8.5000",
            "Area": "3400.25",
            "NL": "",
            "Int": "1200",
            "PeakStart": "8.0000",
            "PeakEnd": "9.0000",
            "PeakWidth": "1.0000",
            "Confidence": "HIGH",
            "Reason": "",
        },
        {
            "SampleName": "SampleA",
            "Group": "Other",
            "Target": "WithNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "9.5000",
            "Area": "4400.75",
            "NL": "WARN_12.3ppm",
            "Int": "2200",
            "PeakStart": "9.0000",
            "PeakEnd": "10.0000",
            "PeakWidth": "1.0000",
            "Confidence": "HIGH",
            "Reason": "",
        },
    ]


def test_run_does_not_write_intermediate_csv_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path, keep_intermediate_csv=False)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1200.0, 3400.25)]),
    )

    output = _run(config, targets)

    assert len(output.file_results) == 1
    assert not config.output_csv.exists()
    assert not config.output_csv.with_name("xic_results_long.csv").exists()
    assert not config.diagnostics_csv.exists()


def test_run_loads_scoring_inputs_from_config_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    config = ExtractionConfig(
        **{
            **config.__dict__,
            "injection_order_source": tmp_path / "sample_info.csv",
            "rt_prior_library_path": tmp_path / "rt_prior_library.csv",
            "config_hash": "abcd1234",
        }
    )
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    calls: dict[str, object] = {}
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1200.0, 3400.25)]),
    )

    def _read_injection_order(path: Path) -> dict[str, int]:
        calls["injection_order_path"] = path
        return {"SampleA": 1}

    def _load_library(path: Path, config_hash: str) -> dict[tuple[str, str], object]:
        calls["library_args"] = (path, config_hash)
        return {}

    monkeypatch.setattr(
        "xic_extractor.extractor.read_injection_order",
        _read_injection_order,
    )
    monkeypatch.setattr("xic_extractor.extractor.load_library", _load_library)

    _run(config, targets)

    assert calls["injection_order_path"] == config.injection_order_source
    assert calls["library_args"] == (
        config.rt_prior_library_path,
        config.config_hash,
    )


def test_run_falls_back_to_main_pass_when_prepass_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True), _target("Analyte", istd_pair="ISTD")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [
                _ok_peak(9.05, 1500.0, 2000.0),
                _ok_peak(9.07, 1200.0, 1800.0),
            ]
        ),
    )

    output = _run(config, targets)

    assert output.file_results[0].results["ISTD"].peak_result.peak is not None
    assert output.file_results[0].results["Analyte"].peak_result.peak is not None


def test_prepass_excludes_flagged_istd_anchor_from_prior_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from xic_extractor.extractor import ExtractionResult, _extract_istd_anchors_only

    config = _config(tmp_path)
    raw_path = config.data_dir / "SampleA.raw"
    raw_path.write_text("", encoding="utf-8")
    target = _target("ISTD", is_istd=True)
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())

    def _fake_extract_one_target(
        raw,
        config,
        sample_name,
        target,
        *,
        reference_rt,
        strict_preferred_rt,
        results,
        diagnostics,
        shape_metrics_by_label,
        **kwargs,
    ) -> float | None:
        results[target.label] = ExtractionResult(
            peak_result=_ok_peak(
                9.05,
                1500.0,
                2000.0,
                quality_flags=("too_broad",),
            ),
            nl=None,
            target_label=target.label,
            role="ISTD",
        )
        return 9.05

    monkeypatch.setattr(
        "xic_extractor.extractor._extract_one_target",
        _fake_extract_one_target,
    )

    anchors, results, diagnostics, shape_metrics = _extract_istd_anchors_only(
        config,
        [target],
        raw_path,
    )

    assert anchors == {}
    assert results[target.label].peak_result.peak is not None
    assert diagnostics == []
    assert shape_metrics == {}


def test_run_reextracts_istd_in_main_pass_to_keep_scoring_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True)]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: (
            {"ISTD": 9.05},
            {},
            [],
            {},
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [
                _ok_peak(
                    9.05,
                    1500.0,
                    2000.0,
                    confidence="LOW",
                    reason="concerns: rt_prior (major)",
                    severities=((2, "rt_prior"),),
                )
            ]
        ),
    )

    output = _run(config, targets)

    result = output.file_results[0].results["ISTD"]
    assert result.confidence == "LOW"
    assert result.reason == "concerns: rt_prior (major)"
    assert result.severities == ((2, "rt_prior"),)


def test_run_writes_nd_for_peak_failure_but_keeps_nl_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_failed_peak("PEAK_NOT_FOUND", n_points=15, max_smoothed=1234.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.2, None, 3, 0, 2)]),
    )

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["WithNL_RT"] == "ND"
    assert rows[0]["WithNL_Int"] == "ND"
    assert rows[0]["WithNL_Area"] == "ND"
    assert rows[0]["WithNL_PeakStart"] == "ND"
    assert rows[0]["WithNL_PeakEnd"] == "ND"
    assert rows[0]["WithNL_PeakWidth"] == "ND"
    assert rows[0]["WithNL_NL"] == "OK"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == "PEAK_NOT_FOUND"
    assert diagnostics[0]["Target"] == "WithNL"
    assert "prominence" in diagnostics[0]["Reason"]
    assert "max=1234" in diagnostics[0]["Reason"]


def test_run_leaves_confidence_blank_for_nd_rows_with_failed_nl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_failed_peak("PEAK_NOT_FOUND", n_points=15, max_smoothed=1234.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("NL_FAIL", 78.4, None, 10, 1, 3)]),
    )

    output = _run(config, targets)

    long_rows = _read_csv(config.output_csv.with_name("xic_results_long.csv"))
    assert long_rows == [
        {
            "SampleName": "SampleA",
            "Group": "Other",
            "Target": "WithNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "ND",
            "Area": "ND",
            "NL": "NL_FAIL",
            "Int": "ND",
            "PeakStart": "ND",
            "PeakEnd": "ND",
            "PeakWidth": "ND",
            "Confidence": "",
            "Reason": "",
        }
    ]
    assert output.file_results[0].results["WithNL"].confidence == ""


def test_run_leaves_confidence_blank_for_file_error_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "Bad.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        _open_raw_factory(errors={"Bad.raw": RuntimeError("file locked")}),
    )

    _run(config, targets)

    long_rows = _read_csv(config.output_csv.with_name("xic_results_long.csv"))
    assert long_rows == [
        {
            "SampleName": "Bad",
            "Group": "Other",
            "Target": "WithNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "ERROR",
            "Area": "ERROR",
            "NL": "ERROR",
            "Int": "ERROR",
            "PeakStart": "ERROR",
            "PeakEnd": "ERROR",
            "PeakWidth": "ERROR",
            "Confidence": "",
            "Reason": "",
        }
    ]


def test_run_writes_file_error_row_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "Bad.raw").write_text("", encoding="utf-8")
    (config.data_dir / "Good.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None), _target("WithNL")]
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        _open_raw_factory(errors={"Bad.raw": RuntimeError("file locked")}),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0), _ok_peak(9.5, 1100.0, 2100.0)]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.0, None, 2, 0, 1)]),
    )

    output = _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0] == {
        "SampleName": "Bad",
        "NoNL_RT": "ERROR",
        "NoNL_Int": "ERROR",
        "NoNL_Area": "ERROR",
        "NoNL_PeakStart": "ERROR",
        "NoNL_PeakEnd": "ERROR",
        "NoNL_PeakWidth": "ERROR",
        "WithNL_RT": "ERROR",
        "WithNL_Int": "ERROR",
        "WithNL_Area": "ERROR",
        "WithNL_PeakStart": "ERROR",
        "WithNL_PeakEnd": "ERROR",
        "WithNL_PeakWidth": "ERROR",
        "WithNL_NL": "ERROR",
    }
    assert rows[1]["SampleName"] == "Good"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["SampleName"] == "Bad"
    assert diagnostics[0]["Target"] == ""
    assert diagnostics[0]["Issue"] == "FILE_ERROR"
    assert "file locked" in diagnostics[0]["Reason"]
    assert output.file_results[0].error is not None


@pytest.mark.parametrize(
    ("peak_status", "n_points", "max_smoothed", "issue", "reason_part"),
    [
        ("NO_SIGNAL", 0, None, "NO_SIGNAL", "XIC empty"),
        ("WINDOW_TOO_SHORT", 7, None, "WINDOW_TOO_SHORT", "Only 7 scans"),
        ("PEAK_NOT_FOUND", 15, 25.0, "PEAK_NOT_FOUND", "prominence"),
    ],
)
def test_run_writes_peak_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    peak_status: str,
    n_points: int,
    max_smoothed: float | None,
    issue: str,
    reason_part: str,
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [
                _failed_peak(
                    peak_status,
                    n_points=n_points,
                    max_smoothed=max_smoothed,
                )
            ]
        ),
    )

    _run(config, targets)

    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == issue
    assert diagnostics[0]["Target"] == "NoNL"
    assert reason_part in diagnostics[0]["Reason"]


@pytest.mark.parametrize(
    ("nl_result", "issue", "reason_part"),
    [
        (NLResult("NL_FAIL", 78.4, None, 10, 1, 3), "NL_FAIL", "best match 78.4 ppm"),
        (
            NLResult("NL_FAIL", None, None, 10, 1, 3),
            "NL_FAIL",
            "not detected in any matched scan",
        ),
        (NLResult("NO_MS2", None, None, 42, 2, 0), "NO_MS2", "42 valid MS2 scans"),
    ],
)
def test_run_writes_neutral_loss_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nl_result: NLResult,
    issue: str,
    reason_part: str,
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0)]),
    )
    monkeypatch.setattr("xic_extractor.extractor.check_nl", _nl_sequence([nl_result]))

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["WithNL_NL"] == nl_result.to_token()
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == issue
    assert diagnostics[0]["Target"] == "WithNL"
    assert reason_part in diagnostics[0]["Reason"]


def test_istd_no_ms2_keeps_ms1_peak_and_writes_confidence_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True)]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(9.05, 1200.0, 3400.25)]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("NO_MS2", None, None, 12, 0, 0)]),
    )

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["ISTD_RT"] == "9.0500"
    assert rows[0]["ISTD_Int"] == "1200"
    assert rows[0]["ISTD_Area"] == "3400.25"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert any(
        record["Target"] == "ISTD"
        and record["Issue"] == "NO_MS2"
        for record in diagnostics
    )
    assert any(
        record["Target"] == "ISTD"
        and record["Issue"] == "ISTD_CONFIDENCE"
        and "confidence=MEDIUM" in record["Reason"]
        and "flags=NO_MS2" in record["Reason"]
        and "MS1 peak retained" in record["Reason"]
        for record in diagnostics
    )


def test_run_reports_progress_and_stops_between_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "A.raw").write_text("", encoding="utf-8")
    (config.data_dir / "B.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    progress_calls: list[tuple[int, int, str]] = []
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0)]),
    )

    output = _run(
        config,
        targets,
        progress_callback=lambda current, total, filename: progress_calls.append(
            (current, total, filename)
        ),
        should_stop=lambda: bool(progress_calls),
    )

    assert progress_calls == [(1, 2, "A.raw")]
    assert [file_result.sample_name for file_result in output.file_results] == ["A"]
    assert [row["SampleName"] for row in _read_csv(config.output_csv)] == ["A"]


def test_paired_analyte_uses_strict_anchor_peak_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [
        _target("Analyte", istd_pair="ISTD"),
        _target("ISTD", is_istd=True),
    ]
    strict_flags: list[bool] = []

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([13.70, 13.70, 13.75]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _capturing_peak_sequence(
            [_ok_peak(13.70, 2000.0, 3000.0), _ok_peak(13.75, 500.0, 800.0)],
            strict_flags,
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence(
            [
                NLResult("OK", 1.0, 13.70, 1, 0, 1),
                NLResult("OK", 1.0, 13.75, 1, 0, 1),
            ]
        ),
    )

    _run(config, targets)

    assert strict_flags == [False, True]


def test_istd_anchor_rechecks_target_center_when_strongest_anchor_is_far(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True)]
    anchor_reference_rts: list[float | None] = []
    preferred_rts: list[float | None] = []

    def _fake_find_nl_anchor_rt(*_args, **kwargs) -> float:
        anchor_reference_rts.append(kwargs["reference_rt"])
        return 7.08 if kwargs["reference_rt"] is None else 8.94

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
        scoring_context_builder: object | None = None,
        istd_confidence_note: str | None = None,
    ) -> PeakDetectionResult:
        preferred_rts.append(preferred_rt)
        return _ok_peak(8.94, 1200.0, 3400.25)

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _fake_find_nl_anchor_rt,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _fake_find_peak_and_area,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.0, 8.94, 1, 0, 1)]),
    )

    _run(config, targets)

    assert anchor_reference_rts == [None, 9.0]
    assert preferred_rts == [8.94]


def test_istd_anchor_keeps_strongest_anchor_when_it_is_near_target_center(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True)]
    anchor_reference_rts: list[float | None] = []
    preferred_rts: list[float | None] = []

    def _fake_find_nl_anchor_rt(*_args, **kwargs) -> float:
        anchor_reference_rts.append(kwargs["reference_rt"])
        return 8.55

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
        scoring_context_builder: object | None = None,
        istd_confidence_note: str | None = None,
    ) -> PeakDetectionResult:
        preferred_rts.append(preferred_rt)
        return _ok_peak(8.55, 1200.0, 3400.25)

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _fake_find_nl_anchor_rt,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _fake_find_peak_and_area,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.0, 8.55, 1, 0, 1)]),
    )

    _run(config, targets)

    assert anchor_reference_rts == [None]
    assert preferred_rts == [8.55]


def test_istd_peak_not_found_retries_with_wider_anchor_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("ISTD", is_istd=True)]
    raw = _RecordingRaw()

    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        lambda *_args, **_kwargs: raw,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([9.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [
                _failed_peak("PEAK_NOT_FOUND", n_points=15, max_smoothed=1234.0),
                _ok_peak(9.05, 1200.0, 3400.25),
            ]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.0, 9.0, 1, 0, 1)]),
    )

    output = _run(config, targets)

    result = output.file_results[0].results["ISTD"]
    assert result.peak_result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.05, abs=0.001)
    assert raw.windows == [(8.0, 10.0), (7.0, 11.0)]


def test_paired_analyte_keeps_mismatched_target_anchor_peak_as_low(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [
        _target("Analyte", istd_pair="ISTD"),
        _target("ISTD", is_istd=True),
    ]

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([13.70, 13.70, 13.75]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(13.70, 2000.0, 3000.0), _ok_peak(13.06, 5000.0, 8000.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence(
            [
                NLResult("OK", 1.0, 13.70, 1, 0, 1),
                NLResult("OK", 1.0, 13.75, 1, 0, 1),
            ]
        ),
    )

    output = _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["Analyte_RT"] == "13.0600"
    assert rows[0]["Analyte_Int"] == "5000"
    assert rows[0]["Analyte_Area"] == "8000.00"
    long_rows = _read_csv(config.output_csv.with_name("xic_results_long.csv"))
    analyte_row = next(row for row in long_rows if row["Target"] == "Analyte")
    assert analyte_row["Confidence"] == "LOW"
    assert "anchor mismatch" in analyte_row["Reason"]
    assert output.file_results[0].results["Analyte"].confidence == "LOW"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert any(
        record["Target"] == "Analyte"
        and record["Issue"] == "ANCHOR_RT_MISMATCH"
        and "Paired analyte peak RT 13.060" in record["Reason"]
        and "target NL anchor at 13.750" in record["Reason"]
        and "allowed ±0.25 min" in record["Reason"]
        for record in diagnostics
    )


def test_paired_analyte_accepts_peak_close_to_target_anchor_even_if_farther_from_istd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [
        _target("Analyte", istd_pair="ISTD"),
        _target("ISTD", is_istd=True),
    ]

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([13.70, 13.70, 13.95]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(13.70, 2000.0, 3000.0), _ok_peak(13.95, 5000.0, 8000.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence(
            [
                NLResult("OK", 1.0, 13.70, 1, 0, 1),
                NLResult("OK", 1.0, 13.95, 1, 0, 1),
            ]
        ),
    )

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["Analyte_RT"] == "13.9500"
    assert rows[0]["Analyte_Area"] == "8000.00"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert not any(
        record["Target"] == "Analyte" and record["Issue"] == "ANCHOR_RT_MISMATCH"
        for record in diagnostics
    )


def test_paired_analyte_fallback_keeps_mismatched_istd_anchor_peak_as_low(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [
        _target("Analyte", istd_pair="ISTD"),
        _target("ISTD", is_istd=True),
    ]

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor._extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([13.70, 13.70, None]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(13.70, 2000.0, 3000.0), _ok_peak(14.31, 5000.0, 8000.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence(
            [
                NLResult("OK", 1.0, 13.70, 1, 0, 1),
                NLResult("NL_FAIL", None, None, 1, 0, 1),
            ]
        ),
    )

    output = _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["Analyte_RT"] == "14.3100"
    assert rows[0]["Analyte_Area"] == "8000.00"
    long_rows = _read_csv(config.output_csv.with_name("xic_results_long.csv"))
    analyte_row = next(row for row in long_rows if row["Target"] == "Analyte")
    assert analyte_row["Confidence"] == "LOW"
    assert "anchor mismatch" in analyte_row["Reason"]
    assert output.file_results[0].results["Analyte"].confidence == "LOW"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert any(
        record["Target"] == "Analyte"
        and record["Issue"] == "ANCHOR_RT_MISMATCH"
        and "Paired analyte peak RT 14.310" in record["Reason"]
        and "ISTD anchor at 13.700" in record["Reason"]
        and "allowed ±0.50 min" in record["Reason"]
        for record in diagnostics
    )


def _run(config: ExtractionConfig, targets: list[Target], **kwargs):
    from xic_extractor.extractor import run

    return run(config, targets, **kwargs)


def _config(tmp_path: Path, *, keep_intermediate_csv: bool = True) -> ExtractionConfig:
    data_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    dll_dir = tmp_path / "dll"
    data_dir.mkdir()
    output_dir.mkdir()
    dll_dir.mkdir()
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        keep_intermediate_csv=keep_intermediate_csv,
    )


def _target(
    label: str,
    *,
    neutral_loss_da: float | None = 116.0474,
    is_istd: bool = False,
    istd_pair: str = "",
) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=neutral_loss_da,
        nl_ppm_warn=20.0 if neutral_loss_da is not None else None,
        nl_ppm_max=50.0 if neutral_loss_da is not None else None,
        is_istd=is_istd,
        istd_pair=istd_pair,
    )


def _ok_peak(
    rt: float,
    intensity: float,
    area: float,
    *,
    confidence: str | None = None,
    reason: str | None = None,
    severities: tuple[tuple[int, str], ...] = (),
    quality_flags: tuple[str, ...] = (),
) -> PeakDetectionResult:
    peak = PeakResult(
        rt=rt,
        intensity=intensity,
        intensity_smoothed=intensity,
        area=area,
        peak_start=rt - 0.5,
        peak_end=rt + 0.5,
    )
    candidate = PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=intensity,
        selection_apex_index=7,
        raw_apex_rt=rt,
        raw_apex_intensity=intensity,
        raw_apex_index=7,
        prominence=intensity * 0.5,
        quality_flags=quality_flags,
        region_scan_count=15,
        region_duration_min=1.0,
        region_edge_ratio=1.5,
    )
    return PeakDetectionResult(
        status="OK",
        peak=peak,
        n_points=15,
        max_smoothed=intensity,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence=confidence,
        reason=reason,
        severities=severities,
    )


def _failed_peak(
    status: str, *, n_points: int, max_smoothed: float | None
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status=status,
        peak=None,
        n_points=n_points,
        max_smoothed=max_smoothed,
        n_prominent_peaks=0,
    )


def _peak_sequence(results: list[PeakDetectionResult]):
    pending = list(results)

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
        scoring_context_builder: object | None = None,
        istd_confidence_note: str | None = None,
    ) -> PeakDetectionResult:
        return pending.pop(0)

    return _fake_find_peak_and_area


def _capturing_peak_sequence(
    results: list[PeakDetectionResult],
    strict_flags: list[bool],
):
    pending = list(results)

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
        scoring_context_builder: object | None = None,
        istd_confidence_note: str | None = None,
    ) -> PeakDetectionResult:
        strict_flags.append(strict_preferred_rt)
        return pending.pop(0)

    return _fake_find_peak_and_area


def _anchor_sequence(results: list[float | None]):
    pending = list(results)

    def _fake_find_nl_anchor_rt(*_args, **_kwargs) -> float | None:
        return pending.pop(0)

    return _fake_find_nl_anchor_rt


def _nl_sequence(results: list[NLResult]):
    pending = list(results)

    def _fake_check_nl(*_args, **_kwargs) -> NLResult:
        return pending.pop(0)

    return _fake_check_nl


def _open_raw_factory(*, errors: dict[str, Exception] | None = None):
    error_by_name = errors or {}

    def _fake_open_raw(path: Path, dll_dir: Path):
        if path.name in error_by_name:
            raise error_by_name[path.name]
        return _FakeRaw()

    return _fake_open_raw


class _FakeRaw:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.asarray([rt_min, rt_max], dtype=float), np.asarray(
            [1.0, 2.0], dtype=float
        )

    def iter_ms2_scans(self, rt_min: float, rt_max: float):
        return iter([])


class _RecordingRaw(_FakeRaw):
    def __init__(self) -> None:
        self.windows: list[tuple[float, float]] = []

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        self.windows.append((rt_min, rt_max))
        return super().extract_xic(mz, rt_min, rt_max, ppm_tol)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))
