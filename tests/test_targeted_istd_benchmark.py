from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from tools.diagnostics import targeted_istd_benchmark as benchmark


def test_benchmark_classifies_pass_miss_split_and_inactive_tag(tmp_path: Path):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    _write_targeted_workbook(
        targeted,
        targets=[
            _target("pass_istd", 100.0, 10.0, 11.0, 50.0, 116.0474),
            _target("miss_istd", 200.0, 20.0, 21.0, 80.0, 116.0474),
            _target("split_istd", 300.0, 30.0, 31.0, 180.0, 116.0474),
            _target("rna_istd", 400.0, 40.0, 41.0, 268.0, 132.0423),
        ],
        samples=("S1", "S2", "S3", "S4"),
    )
    _write_alignment_run(
        alignment,
        review_rows=[
            _review_row("FAM_PASS", 100.0, 10.5, 50.0, 116.0474, True),
            _review_row("FAM_SPLIT_A", 300.0, 30.4, 180.0, 116.0474, True),
            _review_row("FAM_SPLIT_B", 300.0, 30.6, 180.0, 116.0474, True),
            _review_row("FAM_RNA", 400.0, 40.5, 268.0, 132.0423, True),
        ],
        matrix_rows=[
            _matrix_row("FAM_PASS", (100.0, 1000.0, 10000.0, 100000.0)),
            _matrix_row("FAM_SPLIT_A", (1.0, 2.0, 3.0, 4.0)),
            _matrix_row("FAM_SPLIT_B", (1.0, 2.0, 3.0, 4.0)),
            _matrix_row("FAM_RNA", (1.0, 2.0, 3.0, 4.0)),
        ],
        cell_rows=[
            _cell_row("FAM_PASS", "S1", 10.50, 100.0),
            _cell_row("FAM_PASS", "S2", 10.51, 1000.0),
            _cell_row("FAM_PASS", "S3", 10.52, 10000.0),
            _cell_row("FAM_PASS", "S4", 10.53, 100000.0),
        ],
    )

    _outputs, summaries = benchmark.run_targeted_istd_benchmark(
        targeted_workbook=targeted,
        alignment_dir=alignment,
        output_dir=tmp_path / "benchmark",
    )

    by_label = {row.target_label: row for row in summaries}
    assert by_label["pass_istd"].status == "PASS"
    assert round(by_label["pass_istd"].log_area_pearson or 0.0, 12) == 1.0
    assert round(by_label["pass_istd"].log_area_spearman or 0.0, 12) == 1.0
    assert by_label["miss_istd"].failure_modes == ("MISS",)
    assert by_label["split_istd"].failure_modes == ("SPLIT",)
    assert by_label["rna_istd"].active_tag is False
    assert by_label["rna_istd"].failure_modes == ("FALSE_POSITIVE_TAG",)


def test_main_writes_outputs_and_returns_one_when_gate_fails(tmp_path: Path):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    output_dir = tmp_path / "benchmark"
    _write_targeted_workbook(
        targeted,
        targets=[_target("miss_istd", 200.0, 20.0, 21.0, 80.0, 116.0474)],
        samples=("S1", "S2", "S3"),
    )
    _write_alignment_run(
        alignment,
        review_rows=[
            _review_row("FAM_DECOY", 500.0, 50.0, 384.0, 116.0474, True),
        ],
        matrix_rows=[
            _matrix_row("FAM_DECOY", (1.0, 2.0, 3.0), samples=("S1", "S2", "S3")),
        ],
        cell_rows=[
            _cell_row("FAM_DECOY", "S1", 50.0, 1.0),
        ],
        samples=("S1", "S2", "S3"),
    )

    code = benchmark.main(
        [
            "--targeted-workbook",
            str(targeted),
            "--alignment-dir",
            str(alignment),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert code == 1
    assert (output_dir / "targeted_istd_benchmark_summary.tsv").exists()
    payload = json.loads(
        (output_dir / "targeted_istd_benchmark.json").read_text(encoding="utf-8"),
    )
    assert payload["overall_status"] == "FAIL"
    assert payload["active_fail_count"] == 1


def test_main_reports_missing_required_workbook_column(
    tmp_path: Path,
    capsys,
):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    _write_targeted_workbook(
        targeted,
        targets=[_target("d3-5-medC", 245.0, 11.0, 13.0, 129.0, 116.0474)],
        samples=("S1", "S2", "S3"),
        omit_target_columns={"NL (Da)"},
    )
    _write_alignment_run(alignment, review_rows=[], matrix_rows=[], cell_rows=[])

    code = benchmark.main(
        [
            "--targeted-workbook",
            str(targeted),
            "--alignment-dir",
            str(alignment),
            "--output-dir",
            str(tmp_path / "benchmark"),
        ],
    )

    assert code == 2
    assert "NL (Da)" in capsys.readouterr().err


def test_provisional_discovery_candidate_is_not_primary_hit(tmp_path: Path):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    _write_targeted_workbook(
        targeted,
        targets=[_target("d3-5-medC", 245.0, 11.0, 13.0, 129.0, 116.0474)],
        samples=("S1", "S2", "S3"),
    )
    row = _review_row("FAM_PROV", 245.0, 12.0, 129.0, 116.0474, True)
    row["identity_decision"] = "provisional_discovery"
    _write_alignment_run(
        alignment,
        review_rows=[row],
        matrix_rows=[
            _matrix_row(
                "FAM_PROV",
                (10.0, 100.0, 1000.0),
                samples=("S1", "S2", "S3"),
            ),
        ],
        cell_rows=[
            _cell_row("FAM_PROV", "S1", 12.00, 10.0),
            _cell_row("FAM_PROV", "S2", 12.01, 100.0),
            _cell_row("FAM_PROV", "S3", 12.02, 1000.0),
        ],
        samples=("S1", "S2", "S3"),
    )

    _outputs, summaries = benchmark.run_targeted_istd_benchmark(
        targeted_workbook=targeted,
        alignment_dir=alignment,
        output_dir=tmp_path / "benchmark",
    )

    assert summaries[0].primary_match_count == 0
    assert summaries[0].failure_modes == ("MISS",)


def test_sample_normalization_maps_qc_underscore_names(tmp_path: Path):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    _write_targeted_workbook(
        targeted,
        targets=[_target("d3-5-medC", 245.0, 11.0, 13.0, 129.0, 116.0474)],
        samples=("QC_1", "QC_2", "QC_3"),
    )
    _write_alignment_run(
        alignment,
        review_rows=[_review_row("FAM001", 245.0, 12.0, 129.0, 116.0474, True)],
        matrix_rows=[
            _matrix_row(
                "FAM001",
                (10.0, 100.0, 1000.0),
                samples=("QC1", "QC2", "QC3"),
            ),
        ],
        cell_rows=[
            _cell_row("FAM001", "QC1", 12.00, 10.0),
            _cell_row("FAM001", "QC2", 12.01, 100.0),
            _cell_row("FAM001", "QC3", 12.02, 1000.0),
        ],
        samples=("QC1", "QC2", "QC3"),
    )

    _outputs, summaries = benchmark.run_targeted_istd_benchmark(
        targeted_workbook=targeted,
        alignment_dir=alignment,
        output_dir=tmp_path / "benchmark",
    )

    assert summaries[0].paired_area_n == 3


def test_active_istd_can_pass_with_primary_isotope_shift_fallback(tmp_path: Path):
    targeted = tmp_path / "targeted.xlsx"
    alignment = tmp_path / "alignment"
    isotope_shift = benchmark.ISOTOPE_SHIFT_DA
    _write_targeted_workbook(
        targeted,
        targets=[_target("d4_istd", 300.0, 23.0, 24.0, 184.0, 116.0474)],
        samples=("S1", "S2", "S3", "S4"),
    )
    _write_alignment_run(
        alignment,
        review_rows=[
            _review_row(
                "FAM_M1",
                300.0 + isotope_shift,
                23.5,
                184.0 + isotope_shift,
                116.0474,
                True,
            ),
            _review_row(
                "FAM_MINUS_DECOY",
                300.0 - isotope_shift + 0.002,
                23.5,
                184.0 - isotope_shift + 0.002,
                116.0474,
                True,
            ),
        ],
        matrix_rows=[
            _matrix_row("FAM_M1", (10.0, 100.0, 1000.0, 10000.0)),
            _matrix_row("FAM_MINUS_DECOY", (1.0, 2.0, 3.0, 4.0)),
        ],
        cell_rows=[
            _cell_row("FAM_M1", "S1", 23.51, 10.0),
            _cell_row("FAM_M1", "S2", 23.52, 100.0),
            _cell_row("FAM_M1", "S3", 23.53, 1000.0),
            _cell_row("FAM_M1", "S4", 23.54, 10000.0),
            _cell_row("FAM_MINUS_DECOY", "S1", 23.51, 1.0),
            _cell_row("FAM_MINUS_DECOY", "S2", 23.52, 2.0),
            _cell_row("FAM_MINUS_DECOY", "S3", 23.53, 3.0),
            _cell_row("FAM_MINUS_DECOY", "S4", 23.54, 4.0),
        ],
    )

    outputs, summaries = benchmark.run_targeted_istd_benchmark(
        targeted_workbook=targeted,
        alignment_dir=alignment,
        output_dir=tmp_path / "benchmark",
    )

    assert summaries[0].status == "PASS"
    assert summaries[0].selected_feature_id == "FAM_M1"
    matches = _read_tsv(outputs.matches_tsv)
    assert matches[0]["match_type"] == "isotope_shift"
    assert abs(float(matches[0]["mass_shift_da"]) - isotope_shift) < 1e-4


def _target(
    label: str,
    mz: float,
    rt_min: float,
    rt_max: float,
    product: float,
    nl: float,
) -> dict[str, object]:
    return {
        "Label": label,
        "Role": "ISTD",
        "ISTD Pair": None,
        "m/z": mz,
        "RT min": rt_min,
        "RT max": rt_max,
        "ppm tol": 20.0,
        "NL (Da)": nl,
        "Expected product m/z": product,
        "NL ppm warn": 20.0,
        "NL ppm max": 50.0,
    }


def _write_targeted_workbook(
    path: Path,
    *,
    targets: list[dict[str, object]],
    samples: tuple[str, ...],
    omit_target_columns: set[str] | None = None,
) -> None:
    omit_target_columns = omit_target_columns or set()
    workbook = Workbook()
    targets_sheet = workbook.active
    targets_sheet.title = "Targets"
    target_header = [
        "Label",
        "Role",
        "ISTD Pair",
        "m/z",
        "RT min",
        "RT max",
        "ppm tol",
        "NL (Da)",
        "Expected product m/z",
        "NL ppm warn",
        "NL ppm max",
    ]
    target_header = [
        column for column in target_header if column not in omit_target_columns
    ]
    targets_sheet.append(target_header)
    for target in targets:
        targets_sheet.append([target.get(column) for column in target_header])

    results = workbook.create_sheet("XIC Results")
    results.append(
        [
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
            "Confidence",
            "Reason",
        ]
    )
    for sample_index, sample in enumerate(samples, start=1):
        for target_index, target in enumerate(targets):
            rt = float(target["RT min"]) + 0.5 + sample_index * 0.01
            area = 10.0 ** sample_index
            results.append(
                [
                    sample if target_index == 0 else None,
                    "QC",
                    target["Label"],
                    "ISTD",
                    None,
                    rt,
                    area,
                    "ok",
                    1000,
                    rt - 0.05,
                    rt + 0.05,
                    0.1,
                    "HIGH",
                    "",
                ]
            )
    workbook.save(path)


def _write_alignment_run(
    path: Path,
    *,
    review_rows: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
    cell_rows: list[dict[str, object]],
    samples: tuple[str, ...] = ("S1", "S2", "S3", "S4"),
) -> None:
    path.mkdir(parents=True)
    _write_tsv(path / "alignment_review.tsv", review_rows, REVIEW_COLUMNS)
    matrix_columns = (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *samples,
    )
    _write_tsv(path / "alignment_matrix.tsv", matrix_rows, matrix_columns)
    _write_tsv(path / "alignment_cells.tsv", cell_rows, CELL_COLUMNS)


REVIEW_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "include_in_primary_matrix",
    "identity_decision",
)

CELL_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
)


def _review_row(
    family_id: str,
    mz: float,
    rt: float,
    product: float,
    nl: float,
    primary: bool,
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": mz,
        "family_center_rt": rt,
        "family_product_mz": product,
        "family_observed_neutral_loss_da": nl,
        "include_in_primary_matrix": str(primary).upper(),
    }


def _matrix_row(
    family_id: str,
    values: tuple[float, ...],
    *,
    samples: tuple[str, ...] = ("S1", "S2", "S3", "S4"),
) -> dict[str, object]:
    row: dict[str, object] = {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": "",
        "family_center_rt": "",
    }
    for sample, value in zip(samples, values, strict=True):
        row[sample] = value
    return row


def _cell_row(
    family_id: str,
    sample: str,
    apex_rt: float,
    area: float,
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": "detected",
        "area": area,
        "apex_rt": apex_rt,
    }


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: tuple[str, ...],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
