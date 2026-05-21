from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.rt_ms1_backfill_cross_evidence import main
from xic_extractor.instrument_qc.rt_ms1_backfill_cross_evidence_io import (
    build_rt_ms1_cross_evidence_from_files,
)

RT_COLUMNS = [
    "feature_id",
    "source_cell_key",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "row_classification",
    "supporting_biological_istd_label",
    "review_reason",
]

SEED_COLUMNS = [
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "review_classification",
    "recommended_next_action",
    "review_reason",
    "png_paths",
]


def test_cross_evidence_requires_rt_and_ms1_support(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[
            _rt_row("FAM001", "rt_supported_shadow_candidate"),
            _rt_row("FAM002", "rt_supported_shadow_candidate"),
        ],
        seed_rows=[
            _seed_row("FAM001", "seed_shape_supported_review_candidate"),
            _seed_row("FAM002", "neighbor_interference_review"),
        ],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    rows = {row.feature_family_id: row for row in result.rows}
    assert (
        rows["FAM001"].combined_classification
        == "rt_ms1_supported_review_candidate"
    )
    assert (
        rows["FAM002"].combined_classification
        == "rt_supported_ms1_interference_review"
    )
    assert rows["FAM002"].recommended_next_action == "manual_review_required"
    assert result.rt_family_count == 2
    assert result.matched_family_count == 2


def test_ms1_supported_rt_uncertain_and_missing_context(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_model_uncertain")],
        seed_rows=[
            _seed_row("FAM001", "seed_shape_supported_review_candidate"),
            _seed_row("FAM003", "seed_shape_supported_review_candidate"),
        ],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    rows = {row.feature_family_id: row for row in result.rows}
    assert rows["FAM001"].combined_classification == "ms1_supported_rt_uncertain_review"
    assert rows["FAM003"].combined_classification == "ms1_supported_rt_context_missing"


def test_rt_only_does_not_override_shape_insufficient_ms1(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_supported_shadow_candidate")],
        seed_rows=[_seed_row("FAM001", "shape_insufficient_review")],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    row = result.rows[0]
    assert row.combined_classification == "rt_only_review"
    assert row.recommended_next_action == "generate_or_review_seed_specific_overlay"


def test_cli_writes_outputs(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_supported_shadow_candidate")],
        seed_rows=[_seed_row("FAM001", "seed_shape_supported_review_candidate")],
    )
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--rt-shadow-rows-tsv",
            str(rt_tsv),
            "--seed-aware-families-tsv",
            str(seed_tsv),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (output_dir / "rt_ms1_backfill_cross_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["counts_by_classification"] == {
        "rt_ms1_supported_review_candidate": 1
    }
    assert payload["matched_family_count"] == 1
    markdown = (output_dir / "rt_ms1_backfill_cross_evidence.md").read_text(
        encoding="utf-8"
    )
    assert "rt_ms1_supported_review_candidate" in markdown


def test_missing_required_columns_fail_clearly(tmp_path: Path) -> None:
    rt_tsv = tmp_path / "rt.tsv"
    seed_tsv = tmp_path / "seed.tsv"
    _write_tsv(rt_tsv, ["feature_id"], [{"feature_id": "FAM001"}])
    _write_tsv(seed_tsv, SEED_COLUMNS, [_seed_row("FAM001", "not_assessable")])

    exit_code = main(
        [
            "--rt-shadow-rows-tsv",
            str(rt_tsv),
            "--seed-aware-families-tsv",
            str(seed_tsv),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 2


def _write_inputs(
    tmp_path: Path,
    *,
    rt_rows: list[dict[str, str]],
    seed_rows: list[dict[str, str]],
) -> tuple[Path, Path]:
    rt_tsv = tmp_path / "rt_shadow_rows.tsv"
    seed_tsv = tmp_path / "seed_families.tsv"
    _write_tsv(rt_tsv, RT_COLUMNS, rt_rows)
    _write_tsv(seed_tsv, SEED_COLUMNS, seed_rows)
    return rt_tsv, seed_tsv


def _rt_row(family_id: str, classification: str) -> dict[str, str]:
    return {
        "feature_id": family_id,
        "source_cell_key": f"{family_id}|QC1",
        "sample_stem": "QC1",
        "feature_mz": "283.154",
        "raw_feature_rt_min": "10.5",
        "row_classification": classification,
        "supporting_biological_istd_label": "15N5-8-oxodG",
        "review_reason": "fixture",
    }


def _seed_row(family_id: str, classification: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "family_center_mz": "283.154",
        "family_center_rt": "10.5",
        "detected_count": "5",
        "accepted_rescue_count": "79",
        "accepted_cell_count": "84",
        "review_classification": classification,
        "recommended_next_action": "fixture",
        "review_reason": "fixture",
        "png_paths": "overlay.png",
    }


def _write_tsv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
