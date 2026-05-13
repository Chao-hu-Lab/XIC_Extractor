from xic_extractor.alignment.legacy_io import LoadedFeature, LoadedMatrix
from xic_extractor.alignment.validation_compare import (
    match_legacy_source,
    summarize_global,
    summarize_legacy_source,
)


def test_match_legacy_source_requires_ppm_and_rt_thresholds() -> None:
    xic = _matrix(
        "xic_alignment",
        (
            _feature("ALN000001", 100.0, 10.0),
            _feature("ALN000002", 100.0, 10.0),
        ),
    )
    legacy = _matrix(
        "fh_alignment",
        (
            _feature("rt-far", 100.0, 11.1),
            _feature("mz-far", 100.01, 10.0),
        ),
    )

    matches = match_legacy_source(xic, legacy, match_ppm=20.0, match_rt_sec=60.0)

    assert matches == ()


def test_match_legacy_source_is_one_to_one_and_keeps_closest_pair() -> None:
    xic = _matrix(
        "xic_alignment",
        (
            _feature("ALN000001", 100.0000, 10.00),
            _feature("ALN000002", 100.0005, 10.01),
        ),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0004, 10.01),),
    )

    matches = match_legacy_source(xic, legacy, match_ppm=20.0, match_rt_sec=60.0)

    assert [match.xic_cluster_id for match in matches] == ["ALN000002"]
    assert matches[0].legacy_feature_id == "LEGACY001"


def test_match_legacy_source_tie_breaks_by_cluster_and_legacy_id() -> None:
    xic = _matrix(
        "xic_alignment",
        (
            _feature("ALN000002", 100.0, 10.0),
            _feature("ALN000001", 100.0, 10.0),
        ),
    )
    legacy = _matrix(
        "fh_alignment",
        (
            _feature("LEGACY002", 100.0, 10.0),
            _feature("LEGACY001", 100.0, 10.0),
        ),
    )

    matches = match_legacy_source(xic, legacy, match_ppm=20.0, match_rt_sec=60.0)

    assert [(match.xic_cluster_id, match.legacy_feature_id) for match in matches] == [
        ("ALN000001", "LEGACY001"),
        ("ALN000002", "LEGACY002"),
    ]


def test_match_metrics_count_presence_and_sparse_overlap_status() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 242.1144, 12.35, {"S1": 100.0, "S2": None}),),
        sample_order=("S1", "S2"),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 242.1145, 12.36, {"S1": 10.0, "S2": 20.0}),),
        sample_order=("S1", "S2"),
    )

    match = match_legacy_source(xic, legacy, match_ppm=20.0, match_rt_sec=60.0)[0]

    assert match.shared_sample_count == 2
    assert match.xic_present_count == 1
    assert match.legacy_present_count == 2
    assert match.both_present_count == 1
    assert match.xic_only_count == 0
    assert match.legacy_only_count == 1
    assert match.both_missing_count == 0
    assert match.present_jaccard == 0.5
    assert match.log_area_pearson is None
    assert match.status == "OK"
    assert "sparse overlap" in match.note


def test_match_metrics_blank_jaccard_when_both_sides_missing() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": None}),),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S1": None}),),
    )

    match = match_legacy_source(xic, legacy)[0]

    assert match.present_jaccard is None
    assert match.status == "REVIEW"


def test_log_area_pearson_requires_three_paired_positive_values() -> None:
    two_samples_xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": 10.0, "S2": 100.0}),),
        sample_order=("S1", "S2"),
    )
    two_samples_legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S1": 20.0, "S2": 200.0}),),
        sample_order=("S1", "S2"),
    )
    three_samples_xic = _matrix(
        "xic_alignment",
        (
            _feature(
                "ALN000001",
                100.0,
                10.0,
                {"S1": 10.0, "S2": 100.0, "S3": 1000.0},
            ),
        ),
        sample_order=("S1", "S2", "S3"),
    )
    three_samples_legacy = _matrix(
        "fh_alignment",
        (
            _feature(
                "LEGACY001",
                100.0,
                10.0,
                {"S1": 20.0, "S2": 200.0, "S3": 2000.0},
            ),
        ),
        sample_order=("S1", "S2", "S3"),
    )

    assert (
        match_legacy_source(two_samples_xic, two_samples_legacy)[0].log_area_pearson
        is None
    )
    assert (
        match_legacy_source(three_samples_xic, three_samples_legacy)[0].log_area_pearson
        == 1.0
    )


def test_summary_sample_scope_xic_treats_legacy_only_columns_as_out_of_scope() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": 1.0}),),
        sample_order=("S1",),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S1": 1.0, "S2": 1.0}),),
        sample_order=("S1", "S2"),
    )
    matches = match_legacy_source(xic, legacy)

    metrics = _metrics_by_name(
        summarize_legacy_source(xic, legacy, matches, sample_scope="xic")
    )

    assert metrics["failed_sample_match_count"].value == 0
    assert metrics["failed_sample_match_rate"].status == "OK"
    assert metrics["out_of_scope_legacy_sample_count"].value == 1
    assert metrics["out_of_scope_legacy_sample_count"].status == "INFO"


def test_summary_sample_scope_legacy_counts_missing_xic_samples_as_warn() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": 1.0}),),
        sample_order=("S1",),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S1": 1.0, "S2": 1.0}),),
        sample_order=("S1", "S2"),
    )
    matches = match_legacy_source(xic, legacy, sample_scope="legacy")

    metrics = _metrics_by_name(
        summarize_legacy_source(xic, legacy, matches, sample_scope="legacy")
    )

    assert metrics["failed_sample_match_count"].value == 1
    assert metrics["failed_sample_match_rate"].value == 0.5
    assert metrics["failed_sample_match_rate"].status == "WARN"


def test_summary_blocks_when_no_shared_samples_in_scope() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": 1.0}),),
        sample_order=("S1",),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S2": 1.0}),),
        sample_order=("S2",),
    )

    metrics = _metrics_by_name(summarize_legacy_source(xic, legacy, ()))

    assert metrics["shared_sample_count"].value == 0
    assert metrics["shared_sample_count"].status == "BLOCK"


def test_summary_warns_on_distance_score_thresholds() -> None:
    xic = _matrix(
        "xic_alignment",
        (
            _feature("ALN000001", 100.0, 10.0),
            _feature("ALN000002", 200.0, 20.0),
        ),
    )
    legacy = _matrix(
        "fh_alignment",
        (
            _feature("LEGACY001", 100.0, 10.49),
            _feature("LEGACY002", 200.0, 20.9),
        ),
    )
    matches = match_legacy_source(xic, legacy, match_rt_sec=60.0)

    metrics = _metrics_by_name(
        summarize_legacy_source(
            xic,
            legacy,
            matches,
            match_distance_warn_median=0.5,
            match_distance_warn_p90=0.8,
        )
    )

    assert metrics["median_distance_score"].status == "WARN"
    assert metrics["p90_distance_score"].status == "WARN"


def test_summarize_global_reports_replacement_readiness() -> None:
    xic = _matrix(
        "xic_alignment",
        (_feature("ALN000001", 100.0, 10.0, {"S1": 1.0}),),
        sample_order=("S1",),
    )
    legacy = _matrix(
        "fh_alignment",
        (_feature("LEGACY001", 100.0, 10.0, {"S1": 1.0}),),
        sample_order=("S1",),
    )
    metrics = summarize_legacy_source(xic, legacy, match_legacy_source(xic, legacy))
    global_metrics = _metrics_by_name(summarize_global(metrics))

    assert global_metrics["provided_source_count"].value == 1
    assert global_metrics["replacement_readiness"].value == "manual_review_ready"


def _matrix(
    source: str,
    features: tuple[LoadedFeature, ...],
    *,
    sample_order: tuple[str, ...] = ("S1",),
) -> LoadedMatrix:
    return LoadedMatrix(source=source, features=features, sample_order=sample_order)


def _feature(
    feature_id: str,
    mz: float,
    rt_min: float,
    sample_areas: dict[str, float | None] | None = None,
) -> LoadedFeature:
    return LoadedFeature(
        feature_id=feature_id,
        mz=mz,
        rt_min=rt_min,
        sample_areas=sample_areas or {"S1": 1.0},
        metadata={},
    )


def _metrics_by_name(metrics):
    return {metric.metric: metric for metric in metrics}
