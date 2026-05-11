import csv
from pathlib import Path

from xic_extractor.alignment.validation_compare import FeatureMatch, SummaryMetric
from xic_extractor.alignment.validation_writer import (
    write_legacy_matches_tsv,
    write_validation_summary_tsv,
)


def test_write_validation_summary_tsv_header_formatting_and_escape(tmp_path: Path):
    path = tmp_path / "alignment_validation_summary.tsv"
    metrics = (
        SummaryMetric(
            source="=source",
            metric="median_distance_score",
            value=0.123456789,
            threshold=None,
            status="OK",
            note="+note",
        ),
    )

    write_validation_summary_tsv(path, metrics)
    rows = _read_tsv(path)

    assert list(rows[0]) == ["source", "metric", "value", "threshold", "status", "note"]
    assert rows[0] == {
        "source": "'=source",
        "metric": "median_distance_score",
        "value": "0.123457",
        "threshold": "",
        "status": "OK",
        "note": "'+note",
    }


def test_write_legacy_matches_tsv_header_formatting_and_escape(tmp_path: Path):
    path = tmp_path / "alignment_legacy_matches.tsv"
    matches = (
        FeatureMatch(
            source="@source",
            xic_cluster_id="=ALN000001",
            legacy_feature_id="-LEGACY001",
            xic_mz=242.114444,
            legacy_mz=242.114555,
            mz_delta_ppm=0.4584123,
            xic_rt=12.35,
            legacy_rt=12.36,
            rt_delta_sec=0.6,
            distance_score=0.03,
            shared_sample_count=3,
            xic_present_count=2,
            legacy_present_count=2,
            both_present_count=1,
            xic_only_count=1,
            legacy_only_count=1,
            both_missing_count=0,
            present_jaccard=None,
            log_area_pearson=0.987654321,
            status="REVIEW",
            note="presence pattern mismatch",
        ),
    )

    write_legacy_matches_tsv(path, matches)
    rows = _read_tsv(path)

    assert list(rows[0]) == [
        "source",
        "xic_cluster_id",
        "legacy_feature_id",
        "xic_mz",
        "legacy_mz",
        "mz_delta_ppm",
        "xic_rt",
        "legacy_rt",
        "rt_delta_sec",
        "distance_score",
        "shared_sample_count",
        "xic_present_count",
        "legacy_present_count",
        "both_present_count",
        "xic_only_count",
        "legacy_only_count",
        "both_missing_count",
        "present_jaccard",
        "log_area_pearson",
        "status",
        "note",
    ]
    assert rows[0]["source"] == "'@source"
    assert rows[0]["xic_cluster_id"] == "'=ALN000001"
    assert rows[0]["legacy_feature_id"] == "'-LEGACY001"
    assert rows[0]["xic_mz"] == "242.114"
    assert rows[0]["mz_delta_ppm"] == "0.458412"
    assert rows[0]["present_jaccard"] == ""
    assert rows[0]["log_area_pearson"] == "0.987654"


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
