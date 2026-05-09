import csv
from dataclasses import fields
from pathlib import Path

from xic_extractor.discovery.csv_writer import (
    _format_csv_value,
    write_discovery_candidates_csv,
)
from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DISCOVERY_PROVENANCE_COLUMNS,
    DISCOVERY_REVIEW_COLUMNS,
    DiscoveryCandidate,
    DiscoverySeed,
    DiscoverySeedGroup,
    DiscoverySettings,
    NeutralLossProfile,
)

EXPECTED_REVIEW_COLUMNS = (
    "review_priority",
    "candidate_id",
    "precursor_mz",
    "product_mz",
    "observed_neutral_loss_da",
    "best_seed_rt",
    "seed_event_count",
    "ms1_peak_found",
    "ms1_apex_rt",
    "ms1_area",
    "ms2_product_max_intensity",
    "reason",
)

EXPECTED_PROVENANCE_COLUMNS = (
    "raw_file",
    "sample_stem",
    "best_ms2_scan_id",
    "seed_scan_ids",
    "neutral_loss_tag",
    "configured_neutral_loss_da",
    "neutral_loss_mass_error_ppm",
    "rt_seed_min",
    "rt_seed_max",
    "ms1_search_rt_min",
    "ms1_search_rt_max",
    "ms1_seed_delta_min",
    "ms1_peak_rt_start",
    "ms1_peak_rt_end",
    "ms1_height",
    "ms1_trace_quality",
)


def _candidate(
    *,
    review_priority: str = "MEDIUM",
    candidate_id: str = "candidate-1",
    sample_stem: str = "Sample_1",
    reason: str = "neutral loss seed",
    raw_file: Path = Path("C:/data/Sample_1.raw"),
    best_seed_rt: float = 7.83,
    seed_event_count: int = 1,
    ms1_area: float | None = 88765.4,
    ms2_product_max_intensity: float = 12000.0,
    ms1_peak_found: bool = True,
    seed_scan_ids: tuple[int, ...] = (6095,),
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        review_priority=review_priority,  # type: ignore[arg-type]
        candidate_id=candidate_id,
        precursor_mz=258.108512345,
        product_mz=142.061112345,
        observed_neutral_loss_da=116.0474,
        best_seed_rt=best_seed_rt,
        seed_event_count=seed_event_count,
        ms1_peak_found=ms1_peak_found,
        ms1_apex_rt=7.841234,
        ms1_area=ms1_area,
        ms2_product_max_intensity=ms2_product_max_intensity,
        reason=reason,
        raw_file=raw_file,
        sample_stem=sample_stem,
        best_ms2_scan_id=6095,
        seed_scan_ids=seed_scan_ids,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        neutral_loss_mass_error_ppm=2.584321,
        rt_seed_min=7.80,
        rt_seed_max=7.86,
        ms1_search_rt_min=7.60,
        ms1_search_rt_max=8.06,
        ms1_seed_delta_min=0.011234,
        ms1_peak_rt_start=7.701234,
        ms1_peak_rt_end=7.981234,
        ms1_height=4500.5,
        ms1_trace_quality="GOOD",
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_discovery_review_columns_are_stable_csv_contract() -> None:
    assert DISCOVERY_REVIEW_COLUMNS == EXPECTED_REVIEW_COLUMNS


def test_discovery_provenance_columns_are_stable_csv_contract() -> None:
    assert DISCOVERY_PROVENANCE_COLUMNS == EXPECTED_PROVENANCE_COLUMNS


def test_discovery_candidate_columns_start_with_review_columns() -> None:
    assert DISCOVERY_CANDIDATE_COLUMNS[:12] == DISCOVERY_REVIEW_COLUMNS
    assert DISCOVERY_CANDIDATE_COLUMNS[12:] == DISCOVERY_PROVENANCE_COLUMNS


def test_write_discovery_candidates_csv_creates_parent_and_writes_header(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "nested" / "discovery_candidates.csv"

    result_path = write_discovery_candidates_csv(output_path, [_candidate()])

    assert result_path == output_path
    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == list(DISCOVERY_CANDIDATE_COLUMNS)


def test_write_discovery_candidates_csv_writes_header_for_empty_candidates(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"

    write_discovery_candidates_csv(output_path, [])

    with output_path.open(newline="", encoding="utf-8") as handle:
        assert list(csv.reader(handle)) == [list(DISCOVERY_CANDIDATE_COLUMNS)]


def test_write_discovery_candidates_csv_sorts_review_queue_rows(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"
    candidates = [
        _candidate(
            review_priority="LOW",
            candidate_id="low",
            seed_event_count=99,
            ms2_product_max_intensity=99999.0,
            ms1_area=99999.0,
            best_seed_rt=1.0,
        ),
        _candidate(
            review_priority="HIGH",
            candidate_id="high-low-count",
            seed_event_count=2,
            ms2_product_max_intensity=99999.0,
            ms1_area=99999.0,
            best_seed_rt=1.0,
        ),
        _candidate(
            review_priority="HIGH",
            candidate_id="high-count-intensity",
            seed_event_count=3,
            ms2_product_max_intensity=20000.0,
            ms1_area=1.0,
            best_seed_rt=2.0,
        ),
        _candidate(
            review_priority="HIGH",
            candidate_id="high-count-intensity-area-early",
            seed_event_count=3,
            ms2_product_max_intensity=30000.0,
            ms1_area=100.0,
            best_seed_rt=4.0,
        ),
        _candidate(
            review_priority="HIGH",
            candidate_id="high-count-intensity-area-none",
            seed_event_count=3,
            ms2_product_max_intensity=30000.0,
            ms1_area=None,
            best_seed_rt=1.0,
        ),
        _candidate(
            review_priority="HIGH",
            candidate_id="high-count-intensity-area-late",
            seed_event_count=3,
            ms2_product_max_intensity=30000.0,
            ms1_area=100.0,
            best_seed_rt=5.0,
        ),
        _candidate(review_priority="MEDIUM", candidate_id="medium"),
    ]

    write_discovery_candidates_csv(output_path, candidates)

    assert [row["candidate_id"] for row in _read_csv(output_path)] == [
        "high-count-intensity-area-early",
        "high-count-intensity-area-late",
        "high-count-intensity-area-none",
        "high-count-intensity",
        "high-low-count",
        "medium",
        "low",
    ]


def test_write_discovery_candidates_csv_formats_review_values_stably(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"
    candidate = _candidate(ms1_peak_found=False, ms1_area=None)

    write_discovery_candidates_csv(output_path, [candidate])

    row = _read_csv(output_path)[0]
    assert row["precursor_mz"] == "258.109"
    assert row["product_mz"] == "142.061"
    assert row["observed_neutral_loss_da"] == "116.047"
    assert row["best_seed_rt"] == "7.83"
    assert row["neutral_loss_mass_error_ppm"] == "2.58432"
    assert row["ms1_area"] == ""
    assert row["ms2_product_max_intensity"] == "12000"
    assert row["ms1_peak_found"] == "FALSE"
    assert row["ms1_apex_rt"] == "7.84123"
    assert row["raw_file"] == "C:\\data\\Sample_1.raw"


def test_write_discovery_candidates_csv_serializes_seed_scan_ids(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"
    candidate = _candidate(seed_scan_ids=(6095, 6100, 6112))

    write_discovery_candidates_csv(output_path, [candidate])

    assert _read_csv(output_path)[0]["seed_scan_ids"] == "6095;6100;6112"


def test_seed_scan_ids_formatter_does_not_join_string_characters() -> None:
    assert _format_csv_value("seed_scan_ids", (6095, 6100, 6112)) == "6095;6100;6112"
    assert _format_csv_value("seed_scan_ids", "6095;6100;6112") == "6095;6100;6112"


def test_write_discovery_candidates_csv_uses_csv_escaping(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"
    candidate = _candidate(
        sample_stem='Sample, "quoted"',
        reason='neutral loss, requires "review"',
    )

    write_discovery_candidates_csv(output_path, [candidate])

    row = _read_csv(output_path)[0]
    assert row["sample_stem"] == 'Sample, "quoted"'
    assert row["reason"] == 'neutral loss, requires "review"'


def test_write_discovery_candidates_csv_escapes_excel_formula_strings(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "discovery_candidates.csv"
    candidate = _candidate(
        raw_file=Path("=cmd.raw"),
        sample_stem="+sample",
        reason="@review",
    )

    write_discovery_candidates_csv(output_path, [candidate])

    row = _read_csv(output_path)[0]
    assert row["raw_file"] == "'=cmd.raw"
    assert row["sample_stem"] == "'+sample"
    assert row["reason"] == "'@review"


def test_discovery_settings_require_neutral_loss_profile() -> None:
    profile = NeutralLossProfile("DNA_dR", 116.0474)

    settings = DiscoverySettings(neutral_loss_profile=profile)

    assert settings.neutral_loss_profile == profile
    assert settings.nl_tolerance_ppm == 20.0
    assert settings.precursor_mz_tolerance_ppm == 20.0
    assert settings.product_mz_tolerance_ppm == 20.0
    assert settings.product_search_ppm == 50.0
    assert settings.nl_min_intensity_ratio == 0.01
    assert settings.seed_rt_gap_min == 0.20
    assert settings.ms1_search_padding_min == 0.20
    assert settings.rt_min == 0.0
    assert settings.rt_max == 999.0
    assert settings.resolver_mode == "local_minimum"


def test_discovery_seed_preserves_full_ms2_seed_contract() -> None:
    raw_file = Path("C:/data/TumorBC2312_DNA.raw")

    seed = DiscoverySeed(
        raw_file=raw_file,
        sample_stem="TumorBC2312_DNA",
        scan_number=6095,
        rt=7.83,
        precursor_mz=258.1085,
        product_mz=142.0611,
        product_intensity=12000.0,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0471,
        observed_loss_error_ppm=2.58,
    )

    assert seed.raw_file == raw_file
    assert seed.sample_stem == "TumorBC2312_DNA"
    assert seed.scan_number == 6095
    assert seed.rt == 7.83
    assert seed.precursor_mz == 258.1085
    assert seed.product_mz == 142.0611
    assert seed.product_intensity == 12000.0
    assert seed.neutral_loss_tag == "DNA_dR"
    assert seed.configured_neutral_loss_da == 116.0474
    assert seed.observed_neutral_loss_da == 116.0471
    assert seed.observed_loss_error_ppm == 2.58


def test_discovery_seed_group_preserves_group_contract_without_best_seed() -> None:
    raw_file = Path("C:/data/TumorBC2312_DNA.raw")
    seed = DiscoverySeed(
        raw_file=raw_file,
        sample_stem="TumorBC2312_DNA",
        scan_number=6095,
        rt=7.83,
        precursor_mz=258.1085,
        product_mz=142.0611,
        product_intensity=12000.0,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0471,
        observed_loss_error_ppm=2.58,
    )

    group = DiscoverySeedGroup(
        raw_file=raw_file,
        sample_stem="TumorBC2312_DNA",
        seeds=(seed,),
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        precursor_mz=258.1085,
        product_mz=142.0611,
        observed_neutral_loss_da=116.0471,
        neutral_loss_mass_error_ppm=2.58,
        rt_seed_min=7.80,
        rt_seed_max=7.86,
    )

    assert tuple(field.name for field in fields(DiscoverySeedGroup)) == (
        "raw_file",
        "sample_stem",
        "seeds",
        "neutral_loss_tag",
        "configured_neutral_loss_da",
        "precursor_mz",
        "product_mz",
        "observed_neutral_loss_da",
        "neutral_loss_mass_error_ppm",
        "rt_seed_min",
        "rt_seed_max",
    )
    assert group.raw_file == raw_file
    assert group.sample_stem == "TumorBC2312_DNA"
    assert group.seeds == (seed,)
    assert group.neutral_loss_tag == "DNA_dR"
    assert group.configured_neutral_loss_da == 116.0474
    assert group.precursor_mz == 258.1085
    assert group.product_mz == 142.0611
    assert group.observed_neutral_loss_da == 116.0471
    assert group.neutral_loss_mass_error_ppm == 2.58
    assert group.rt_seed_min == 7.80
    assert group.rt_seed_max == 7.86


def test_discovery_candidate_from_values_uses_sample_and_best_seed_scan_id() -> None:
    raw_file = Path("C:/data/TumorBC2312_DNA.raw")
    best_seed = DiscoverySeed(
        raw_file=raw_file,
        sample_stem="TumorBC2312_DNA",
        scan_number=6095,
        rt=7.83,
        precursor_mz=258.1085,
        product_mz=142.0611,
        product_intensity=12000.0,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0471,
        observed_loss_error_ppm=2.58,
    )

    candidate = DiscoveryCandidate.from_values(
        raw_file=raw_file,
        sample_stem="TumorBC2312_DNA",
        precursor_mz=258.1085,
        product_mz=142.0611,
        observed_neutral_loss_da=116.0471,
        best_seed=best_seed,
        seed_scan_ids=(6095,),
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        neutral_loss_mass_error_ppm=2.58,
        rt_seed_min=7.80,
        rt_seed_max=7.86,
        ms1_search_rt_min=7.60,
        ms1_search_rt_max=8.06,
        ms1_seed_delta_min=0.01,
        ms1_peak_rt_start=7.70,
        ms1_peak_rt_end=7.98,
        ms1_height=4500.0,
        ms1_trace_quality="GOOD",
        seed_event_count=1,
        ms1_peak_found=True,
        ms1_apex_rt=7.84,
        ms1_area=88765.4,
        ms2_product_max_intensity=12000.0,
        review_priority="HIGH",
        reason="neutral loss seed",
    )

    assert candidate.candidate_id == "TumorBC2312_DNA#6095"
    assert candidate.review_priority == "HIGH"
    assert candidate.reason == "neutral loss seed"
    assert candidate.seed_scan_ids == (6095,)
    assert candidate.raw_file == raw_file
    assert candidate.sample_stem == "TumorBC2312_DNA"
    assert candidate.best_ms2_scan_id == 6095
    assert candidate.best_seed_rt == 7.83
    assert candidate.precursor_mz == 258.1085
    assert candidate.product_mz == 142.0611
    assert candidate.observed_neutral_loss_da == 116.0471
    assert candidate.seed_event_count == 1
    assert candidate.ms1_peak_found is True
    assert candidate.neutral_loss_tag == "DNA_dR"
    assert candidate.configured_neutral_loss_da == 116.0474
    assert candidate.neutral_loss_mass_error_ppm == 2.58
    assert candidate.rt_seed_min == 7.80
    assert candidate.rt_seed_max == 7.86
    assert candidate.ms1_search_rt_min == 7.60
    assert candidate.ms1_search_rt_max == 8.06
    assert candidate.ms1_seed_delta_min == 0.01
    assert candidate.ms1_peak_rt_start == 7.70
    assert candidate.ms1_peak_rt_end == 7.98
    assert candidate.ms1_apex_rt == 7.84
    assert candidate.ms1_area == 88765.4
    assert candidate.ms1_height == 4500.0
    assert candidate.ms1_trace_quality == "GOOD"
    assert candidate.ms2_product_max_intensity == 12000.0
