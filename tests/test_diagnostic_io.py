import csv
from pathlib import Path

import pytest

from tools.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    read_delimited_rows,
    write_tsv,
)


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


def test_format_diagnostic_value_hides_nan() -> None:
    assert format_diagnostic_value(float("nan")) == ""
