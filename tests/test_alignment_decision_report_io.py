import csv
import json
from pathlib import Path

import pytest

from tools.diagnostics.alignment_decision_report_io import read_json, read_tsv


def test_read_tsv_requires_declared_columns(tmp_path: Path) -> None:
    path = tmp_path / "input.tsv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("feature_family_id",),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerow({"feature_family_id": "FAM001"})

    with pytest.raises(ValueError, match="missing required columns: identity_decision"):
        read_tsv(path, required_columns=("feature_family_id", "identity_decision"))


def test_read_tsv_returns_fieldnames_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "input.tsv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("feature_family_id", "identity_decision"),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerow(
            {
                "feature_family_id": "FAM001",
                "identity_decision": "production_family",
            }
        )

    table = read_tsv(path, required_columns=("feature_family_id",))

    assert table.fieldnames == ("feature_family_id", "identity_decision")
    assert table.rows == (
        {
            "feature_family_id": "FAM001",
            "identity_decision": "production_family",
        },
    )


def test_read_json_requires_object_root(tmp_path: Path) -> None:
    path = tmp_path / "input.json"
    path.write_text(json.dumps(["not", "object"]), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON root must be an object"):
        read_json(path)
