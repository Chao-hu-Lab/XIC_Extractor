from pathlib import Path

from openpyxl import Workbook

from scripts.local_minimum_param_sweep import read_manual_truth


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
