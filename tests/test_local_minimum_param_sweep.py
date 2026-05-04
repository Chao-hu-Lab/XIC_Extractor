from pathlib import Path

from openpyxl import Workbook

from scripts.local_minimum_param_sweep import (
    ManualTruthRow,
    ProgramPeakRow,
    build_parameter_sets,
    read_manual_truth,
    score_parameter_set,
)


def test_read_manual_truth_parses_dna_rna_two_raw_blocks(tmp_path: Path) -> None:
    workbook = tmp_path / "manual.xlsx"
    wb = Workbook()
    header_1 = [
        "No.",
        "Name",
        "m/z",
        "NoSplit",
        None,
        None,
        None,
        None,
        "Split",
        None,
        None,
        None,
        None,
    ]
    header_2 = [
        None,
        None,
        None,
        "RT\n(min)",
        "Peak height",
        "Peak area",
        "Peak width\n(min)",
        "Shape",
        "RT\n(min)",
        "Peak height",
        "Peak area",
        "Peak width\n(min)",
        "Shape",
    ]
    ws = wb.active
    ws.title = "DNA"
    ws.append(header_1)
    ws.append(header_2)
    ws.append(
        [
            1,
            "5-hmdC",
            258.1085,
            8.55,
            3430000,
            67300000,
            1.0,
            "正常",
            9.05,
            85900,
            2270000,
            0.95,
            "正常",
        ]
    )
    ws_rna = wb.create_sheet("RNA")
    ws_rna.append(header_1)
    ws_rna.append(header_2)
    ws_rna.append(
        [
            1,
            "m6A",
            282.1197,
            24.8,
            1000,
            20000,
            0.8,
            "正常",
            None,
            None,
            None,
            None,
            None,
        ]
    )
    wb.save(workbook)

    rows = read_manual_truth(workbook)

    assert [(row.sheet, row.sample_name, row.target) for row in rows] == [
        ("DNA", "NoSplit", "5-hmdC"),
        ("DNA", "Split", "5-hmdC"),
        ("RNA", "NoSplit", "m6A"),
    ]
    assert rows[0].manual_rt == 8.55
    assert rows[0].manual_area == 67300000
    assert rows[1].manual_width == 0.95
    assert rows[2].manual_shape == "正常"


def test_score_parameter_set_ranks_by_area_mape_and_tracks_guardrails() -> None:
    truth = [
        ManualTruthRow(
            "DNA",
            "SampleA",
            "ISTD",
            10.0,
            1000.0,
            10000.0,
            0.8,
            "正常",
        ),
        ManualTruthRow(
            "DNA",
            "SampleA",
            "Analyte",
            11.0,
            2000.0,
            20000.0,
            1.0,
            "正常",
        ),
        ManualTruthRow(
            "DNA",
            "SampleA",
            "Missing",
            12.0,
            3000.0,
            30000.0,
            1.0,
            "正常",
        ),
    ]
    peaks = [
        ProgramPeakRow("SampleA", "ISTD", True, 10.02, 900.0, 9000.0, True),
        ProgramPeakRow("SampleA", "Analyte", False, 11.10, 2300.0, 26000.0, True),
    ]

    score = score_parameter_set("candidate", {}, truth, peaks)

    assert score.area_median_abs_pct_error == 0.2
    assert score.area_within_10pct == 1
    assert score.area_within_20pct == 1
    assert score.missing_manual_peaks == 1
    assert score.istd_misses == 0
    assert score.rt_median_abs_delta_min == 0.06
    assert score.rt_max_abs_delta_min == 0.10
    assert score.large_area_misses == 1


def test_build_parameter_sets_includes_legacy_current_and_candidate_grid() -> None:
    parameter_sets = build_parameter_sets(grid="quick")

    names = [item.name for item in parameter_sets]
    assert names[0] == "legacy_savgol"
    assert names[1] == "local_minimum_current"
    assert any(name.startswith("local_minimum_grid_") for name in names)
    assert parameter_sets[0].settings_overrides["resolver_mode"] == "legacy_savgol"
    assert parameter_sets[1].settings_overrides["resolver_mode"] == "local_minimum"
