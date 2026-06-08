import csv
from pathlib import Path

import pytest

from tools.diagnostics import diagnostic_io as shim_diagnostic_io
from xic_extractor.diagnostics import diagnostic_io as canonical_diagnostic_io
from xic_extractor.diagnostics.diagnostic_io import (
    bool_value,
    format_diagnostic_value,
    optional_float,
    optional_int,
    read_delimited_rows,
    read_tsv_required,
    required_indexes,
    split_semicolon_labels,
    text_value,
    write_delimited_rows,
    write_tsv,
)


def test_tools_diagnostic_io_shim_reexports_canonical_helpers() -> None:
    assert (
        shim_diagnostic_io.read_tsv_required
        is canonical_diagnostic_io.read_tsv_required
    )
    assert shim_diagnostic_io.write_tsv is canonical_diagnostic_io.write_tsv
    assert shim_diagnostic_io.text_value is canonical_diagnostic_io.text_value


def test_read_delimited_rows_fails_with_clear_missing_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.tsv"
    path.write_text("family_id\nFAM001\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns: sample"):
        read_delimited_rows(path, required_columns=("family_id", "sample"))


def test_write_tsv_preserves_field_order_and_formats_values(tmp_path: Path) -> None:
    path = tmp_path / "rows.tsv"

    write_tsv(
        path,
        (
            {
                "family_id": "FAM001",
                "present": True,
                "missing": None,
                "score": 1.23456789,
            },
        ),
        ("family_id", "present", "missing", "score"),
    )

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    assert rows == [
        ["family_id", "present", "missing", "score"],
        ["FAM001", "TRUE", "", "1.23457"],
    ]


def test_write_tsv_can_preserve_lf_line_terminator(tmp_path: Path) -> None:
    path = tmp_path / "rows.tsv"

    write_tsv(
        path,
        ({"family_id": "FAM001"},),
        ("family_id",),
        lineterminator="\n",
    )

    assert path.read_bytes() == b"family_id\nFAM001\n"


def test_write_delimited_rows_supports_csv_output(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"

    write_delimited_rows(path, ({"sample": "S1", "value": 2.0},), ("sample", "value"))

    assert path.read_text(encoding="utf-8").splitlines() == [
        "sample,value",
        "S1,2",
    ]


def test_format_diagnostic_value_hides_nan() -> None:
    assert format_diagnostic_value(float("nan")) == ""


def test_read_tsv_required_accepts_utf8_sig_and_validates_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.tsv"
    path.write_text(
        "\ufeffsample\ttarget\tvalue\nS1\tA\t1.2\n",
        encoding="utf-8",
    )

    assert read_tsv_required(path, ("sample", "target")) == (
        {"sample": "S1", "target": "A", "value": "1.2"},
    )

    with pytest.raises(ValueError, match="missing required columns: missing"):
        read_tsv_required(path, ("sample", "missing"))


def test_shared_scalar_parsers_match_diagnostic_loader_contracts() -> None:
    assert optional_float(" 1.25 ") == 1.25
    assert optional_float("'-8.6973") == -8.6973
    assert optional_float(float("inf")) is None
    assert optional_float("not numeric") is None
    assert optional_int("3.9") == 3
    assert optional_int("") is None
    assert bool_value("TRUE") is True
    assert bool_value("yes") is True
    assert bool_value("0") is False
    assert bool_value("maybe") is None
    assert text_value(None) == ""
    assert text_value("  A  ") == "A"
    assert split_semicolon_labels(" a ; ; b ") == ["a", "b"]


def test_required_indexes_reports_sheet_and_missing_columns() -> None:
    assert required_indexes(("Label", "m/z", None), ("Label", "m/z"), "Targets") == {
        "Label": 0,
        "m/z": 1,
    }

    with pytest.raises(ValueError, match="Targets.*missing required columns: Role"):
        required_indexes(("Label",), ("Label", "Role"), "Targets")
