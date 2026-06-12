import csv
from pathlib import Path

import pytest

from xic_extractor.instrument_qc.rt_transfer_audit import (
    BiologicalIstdTransferAuditRow,
    build_biological_istd_transfer_audit_rows,
    classify_biological_istd_transfer,
)
from xic_extractor.instrument_qc.rt_transfer_audit_io import (
    BIOLOGICAL_ISTD_TRANSFER_COLUMNS,
    write_biological_istd_transfer_audit_tsv,
)


def test_transfer_supported_when_direction_and_magnitude_match() -> None:
    row = classify_biological_istd_transfer(
        target_label="d3-5-medC",
        biological_qc_row=_bio(count=7, slope=0.009, rt_range=0.9),
        clean_standard_row=_clean(count=4, slope=0.010, rt_range=1.0),
    )

    assert row.transfer_status == "transfer_supported"
    assert row.direction_status == "same_direction"
    assert row.slope_magnitude_ratio == pytest.approx(0.9)


def test_direction_supported_when_biological_matrix_changes_magnitude() -> None:
    row = classify_biological_istd_transfer(
        target_label="d3-N6-medA",
        biological_qc_row=_bio(count=7, slope=0.021, rt_range=2.1),
        clean_standard_row=_clean(count=4, slope=0.010, rt_range=1.0),
    )

    assert row.transfer_status == "direction_supported_magnitude_shifted"
    assert row.direction_status == "same_direction"


def test_transfer_not_supported_when_clean_standard_is_flat() -> None:
    row = classify_biological_istd_transfer(
        target_label="d3-5-hmdC",
        biological_qc_row=_bio(count=7, slope=-0.005, rt_range=0.9),
        clean_standard_row=_clean(count=4, slope=-0.00005, rt_range=0.65),
    )

    assert row.transfer_status == "transfer_not_supported"
    assert row.direction_status == "bio_drift_clean_flat"


def test_transfer_not_supported_when_directions_disagree() -> None:
    row = classify_biological_istd_transfer(
        target_label="ISTD-X",
        biological_qc_row=_bio(count=7, slope=0.006, rt_range=0.5),
        clean_standard_row=_clean(count=4, slope=-0.006, rt_range=0.5),
    )

    assert row.transfer_status == "transfer_not_supported"
    assert row.direction_status == "opposite_direction"


def test_insufficient_biological_istd_wins_before_clean_evidence() -> None:
    row = classify_biological_istd_transfer(
        target_label="d3-N6-medA",
        biological_qc_row=_bio(count=5, slope=0.021, rt_range=2.1),
        clean_standard_row=_clean(count=4, slope=0.010, rt_range=1.0),
    )

    assert row.transfer_status == "insufficient_biological_istd"


def test_missing_clean_standard_is_reported_explicitly() -> None:
    row = classify_biological_istd_transfer(
        target_label="ISTD-not-in-clean-standards",
        biological_qc_row=_bio(count=7, slope=0.003, rt_range=0.4),
        clean_standard_row=None,
    )

    assert row.transfer_status == "insufficient_clean_standard"
    assert row.clean_standard_count is None


def test_build_transfer_rows_joins_by_target_label_and_compound() -> None:
    rows = build_biological_istd_transfer_audit_rows(
        biological_qc_rows=(
            {"target_label": "A", **_bio(count=7, slope=0.01, rt_range=0.5)},
            {"target_label": "B", **_bio(count=7, slope=-0.01, rt_range=0.5)},
        ),
        clean_standard_rows=(
            {"compound": "A", **_clean(count=4, slope=0.01, rt_range=0.5)},
        ),
    )

    by_target = {row.target_label: row for row in rows}

    assert by_target["A"].transfer_status == "transfer_supported"
    assert by_target["B"].transfer_status == "insufficient_clean_standard"


def test_write_biological_istd_transfer_audit_tsv_preserves_schema_and_values(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "transfer.tsv"

    write_biological_istd_transfer_audit_tsv(
        path,
        (
            BiologicalIstdTransferAuditRow(
                target_label="d3-5-medC",
                transfer_status="transfer_supported",
                direction_status="same_direction",
                biological_qc_count=7,
                clean_standard_count=4,
                biological_rt_range_min=0.9,
                clean_rt_delta_range_min=1.0,
                biological_slope_min_per_injection=0.009,
                clean_slope_min_per_injection=0.010,
                slope_magnitude_ratio=0.9,
                clean_warning_count=1,
                review_reason="Clean and biological slopes match.",
            ),
        ),
    )

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames == BIOLOGICAL_ISTD_TRANSFER_COLUMNS
        rows = list(reader)

    assert rows[0]["biological_slope_min_per_injection"] == "0.009"
    assert rows[0]["clean_slope_min_per_injection"] == "0.01"
    assert rows[0]["slope_magnitude_ratio"] == "0.9"
    assert rows[0]["clean_warning_count"] == "1"


def test_write_biological_istd_transfer_audit_tsv_writes_header_without_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "empty.tsv"

    write_biological_istd_transfer_audit_tsv(path, ())

    assert path.read_text(encoding="utf-8").splitlines() == [
        "\t".join(BIOLOGICAL_ISTD_TRANSFER_COLUMNS)
    ]


def _bio(*, count: int, slope: float, rt_range: float) -> dict[str, str]:
    return {
        "benchmark_eligible_count": str(count),
        "rt_slope_min_per_injection": str(slope),
        "rt_range_min": str(rt_range),
    }


def _clean(*, count: int, slope: float, rt_range: float) -> dict[str, str]:
    return {
        "point_count": str(count),
        "rt_slope_min_per_injection": str(slope),
        "rt_delta_range_min": str(rt_range),
        "warning_count": "0",
    }
