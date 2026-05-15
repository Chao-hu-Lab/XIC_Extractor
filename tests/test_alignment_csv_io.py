import csv
from pathlib import Path

import pytest

from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_read_discovery_batch_index_preserves_order_and_resolves_candidate_paths(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_batch_index

    index_path = tmp_path / "batch" / "discovery_batch_index.csv"
    index_path.parent.mkdir()
    _write_csv(
        index_path,
        ("sample_stem", "raw_file", "candidate_csv", "review_csv"),
        [
            {
                "sample_stem": "Sample_B",
                "raw_file": "C:/stale/Sample_B.raw",
                "candidate_csv": "Sample_B/discovery_candidates.csv",
                "review_csv": "Sample_B/discovery_review.csv",
            },
            {
                "sample_stem": "Sample_A",
                "raw_file": "C:/stale/Sample_A.raw",
                "candidate_csv": str(tmp_path / "abs" / "candidates.csv"),
                "review_csv": "",
            },
        ],
    )

    batch = read_discovery_batch_index(index_path)

    assert batch.sample_order == ("Sample_B", "Sample_A")
    assert batch.candidate_csvs["Sample_B"] == (
        index_path.parent / "Sample_B" / "discovery_candidates.csv"
    )
    assert batch.candidate_csvs["Sample_A"] == tmp_path / "abs" / "candidates.csv"
    assert batch.raw_files["Sample_B"] == Path("C:/stale/Sample_B.raw")
    assert batch.raw_files["Sample_A"] == Path("C:/stale/Sample_A.raw")
    assert batch.review_csvs["Sample_B"] == (
        index_path.parent / "Sample_B" / "discovery_review.csv"
    )
    assert batch.review_csvs["Sample_A"] is None


def test_read_discovery_batch_index_unescapes_known_formula_fields(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_batch_index

    index_path = tmp_path / "discovery_batch_index.csv"
    _write_csv(
        index_path,
        ("sample_stem", "raw_file", "candidate_csv", "review_csv"),
        [
            {
                "sample_stem": "'=Sample",
                "raw_file": "'+Sample.raw",
                "candidate_csv": "'-candidates.csv",
                "review_csv": "'@review.csv",
            },
            {
                "sample_stem": "'Ordinary",
                "raw_file": "'plain.raw",
                "candidate_csv": "'plain.csv",
                "review_csv": "'plain_review.csv",
            },
        ],
    )

    batch = read_discovery_batch_index(index_path)

    assert batch.sample_order == ("=Sample", "'Ordinary")
    assert batch.raw_files["=Sample"] == Path("+Sample.raw")
    assert batch.candidate_csvs["=Sample"] == tmp_path / "-candidates.csv"
    assert batch.review_csvs["=Sample"] == tmp_path / "@review.csv"
    assert batch.raw_files["'Ordinary"] == Path("'plain.raw")


def test_read_discovery_candidates_csv_parses_full_candidate_row(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_candidates_csv

    csv_path = tmp_path / "discovery_candidates.csv"
    _write_csv(csv_path, DISCOVERY_CANDIDATE_COLUMNS, [_candidate_row()])

    (candidate,) = read_discovery_candidates_csv(csv_path)

    assert candidate.review_priority == "HIGH"
    assert candidate.evidence_score == 82
    assert candidate.candidate_id == "Sample_1#6095"
    assert candidate.feature_family_id == "Sample_1@F0001"
    assert candidate.feature_superfamily_id == "Sample_1@SF0001"
    assert candidate.precursor_mz == pytest.approx(500.123456)
    assert candidate.product_mz == pytest.approx(384.076056)
    assert candidate.observed_neutral_loss_da == pytest.approx(116.0474)
    assert candidate.best_seed_rt == pytest.approx(8.49)
    assert candidate.seed_event_count == 3
    assert candidate.ms1_peak_found is True
    assert candidate.ms1_apex_rt == pytest.approx(8.48)
    assert candidate.ms1_area == pytest.approx(123456.7)
    assert candidate.ms2_product_max_intensity == pytest.approx(9876.5)
    assert candidate.raw_file == Path("C:/raw/Sample_1.raw")
    assert candidate.sample_stem == "Sample_1"
    assert candidate.best_ms2_scan_id == 6095
    assert candidate.seed_scan_ids == (6095, 6098, 6102)
    assert candidate.ms1_seed_delta_min is None
    assert candidate.ms1_scan_support_score == pytest.approx(0.8)
    assert candidate.matched_tag_names == ("DNA_dR",)
    assert candidate.matched_tag_count == 1
    assert candidate.tag_combine_mode == "single"


def test_read_discovery_candidates_preserves_multi_tag_evidence(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_candidates_csv

    row = _candidate_row(
        selected_tag_count="3",
        matched_tag_count="2",
        matched_tag_names="dR;R",
        primary_tag_name="dR",
        tag_combine_mode="union",
        tag_intersection_status="incomplete",
        tag_evidence_json='{"dR":{"scan_count":1},"R":{"scan_count":1}}',
    )
    csv_path = tmp_path / "discovery_candidates.csv"
    _write_csv(csv_path, DISCOVERY_CANDIDATE_COLUMNS, [row])

    candidates = read_discovery_candidates_csv(csv_path)

    assert candidates[0].matched_tag_names == ("dR", "R")
    assert candidates[0].matched_tag_count == 2
    assert candidates[0].tag_combine_mode == "union"
    assert "scan_count" in candidates[0].tag_evidence_json


def test_read_discovery_candidates_csv_unescapes_known_formula_fields(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_candidates_csv

    row = _candidate_row(
        candidate_id="'=candidate",
        sample_stem="'+sample",
        raw_file="'-raw.raw",
        feature_family_id="'@family",
        feature_superfamily_id="'plain_superfamily",
    )
    csv_path = tmp_path / "discovery_candidates.csv"
    _write_csv(csv_path, DISCOVERY_CANDIDATE_COLUMNS, [row])

    (candidate,) = read_discovery_candidates_csv(csv_path)

    assert candidate.candidate_id == "=candidate"
    assert candidate.sample_stem == "+sample"
    assert candidate.raw_file == Path("-raw.raw")
    assert candidate.feature_family_id == "@family"
    assert candidate.feature_superfamily_id == "'plain_superfamily"


def test_readers_reject_missing_required_columns(tmp_path: Path) -> None:
    from xic_extractor.alignment.csv_io import (
        read_discovery_batch_index,
        read_discovery_candidates_csv,
    )

    batch_path = tmp_path / "discovery_batch_index.csv"
    _write_csv(batch_path, ("sample_stem", "raw_file"), [])
    candidates_path = tmp_path / "discovery_candidates.csv"
    _write_csv(candidates_path, DISCOVERY_CANDIDATE_COLUMNS[:-1], [])

    with pytest.raises(ValueError, match="missing required columns.*candidate_csv"):
        read_discovery_batch_index(batch_path)
    with pytest.raises(ValueError, match="missing required columns"):
        read_discovery_candidates_csv(candidates_path)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("evidence_score", "not-int"),
        ("precursor_mz", "not-float"),
        ("ms1_peak_found", "maybe"),
        ("seed_scan_ids", "1;two"),
    ],
)
def test_read_discovery_candidates_csv_rejects_malformed_typed_fields_with_row_number(
    tmp_path: Path,
    column: str,
    value: str,
) -> None:
    from xic_extractor.alignment.csv_io import read_discovery_candidates_csv

    row = _candidate_row(**{column: value})
    csv_path = tmp_path / "discovery_candidates.csv"
    _write_csv(csv_path, DISCOVERY_CANDIDATE_COLUMNS, [row])

    with pytest.raises(ValueError, match=rf"row 2.*{column}"):
        read_discovery_candidates_csv(csv_path)


def _write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _candidate_row(**overrides: str) -> dict[str, str]:
    row = {
        "review_priority": "HIGH",
        "evidence_tier": "A",
        "evidence_score": "82",
        "ms2_support": "strong",
        "ms1_support": "clean",
        "rt_alignment": "aligned",
        "family_context": "family",
        "candidate_id": "Sample_1#6095",
        "feature_family_id": "Sample_1@F0001",
        "feature_family_size": "2",
        "feature_superfamily_id": "Sample_1@SF0001",
        "feature_superfamily_size": "3",
        "feature_superfamily_role": "representative",
        "feature_superfamily_confidence": "MEDIUM",
        "feature_superfamily_evidence": "peak_boundary_overlap",
        "precursor_mz": "500.123456",
        "product_mz": "384.076056",
        "observed_neutral_loss_da": "116.0474",
        "best_seed_rt": "8.49",
        "seed_event_count": "3",
        "ms1_peak_found": "TRUE",
        "ms1_apex_rt": "8.48",
        "ms1_area": "123456.7",
        "ms2_product_max_intensity": "9876.5",
        "reason": "strict NL seed",
        "raw_file": "C:/raw/Sample_1.raw",
        "sample_stem": "Sample_1",
        "best_ms2_scan_id": "6095",
        "seed_scan_ids": "6095;6098;6102",
        "neutral_loss_tag": "DNA_dR",
        "configured_neutral_loss_da": "116.0474",
        "neutral_loss_mass_error_ppm": "2.5",
        "rt_seed_min": "8.45",
        "rt_seed_max": "8.55",
        "ms1_search_rt_min": "8.25",
        "ms1_search_rt_max": "8.75",
        "ms1_seed_delta_min": "",
        "ms1_peak_rt_start": "8.40",
        "ms1_peak_rt_end": "8.60",
        "ms1_height": "2222.2",
        "ms1_trace_quality": "clean",
        "ms1_scan_support_score": "0.8",
        "selected_tag_count": "1",
        "matched_tag_count": "1",
        "matched_tag_names": "DNA_dR",
        "primary_tag_name": "DNA_dR",
        "tag_combine_mode": "single",
        "tag_intersection_status": "not_required",
        "tag_evidence_json": '{"DNA_dR":{"scan_count":3}}',
    }
    row.update(overrides)
    return row
