from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.check_productization_authority import (
    DEFAULT_INDEX,
    DEFAULT_MANIFEST,
    DEFAULT_SCHEMA,
    check_productization_authority,
    main,
)


def test_productization_authority_checker_accepts_repo_artifacts() -> None:
    assert main([]) == 0


def test_productization_authority_checker_rejects_forbidden_scope(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)

    _mutate_first_non_write_row_to_forbidden_scope(index)

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
        repo_root=tmp_path,
    )

    assert any("unregistered authority scope" in problem for problem in problems)
    assert any("forbidden authority scopes present" in problem for problem in problems)


def _mutate_first_non_write_row_to_forbidden_scope(index: Path) -> None:
    with index.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        rows = list(reader)
    for row in rows:
        if row["write_authority"] == "FALSE":
            row["write_authority"] = "TRUE"
            row["may_touch_matrix"] = "TRUE"
            row["explanation_only"] = "FALSE"
            row["product_authority_scope"] = "all_stability"
            break
    else:
        raise AssertionError("fixture index has no non-write rows")
    with index.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
