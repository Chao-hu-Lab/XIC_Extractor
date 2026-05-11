import ast
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_alignment_public_api_exports_plan2_contract():
    before = set(sys.modules)

    import xic_extractor.alignment as alignment

    assert alignment.__all__ == (
        "AlignmentConfig",
        "AlignmentCluster",
        "AlignedCell",
        "AlignmentMatrix",
        "CellStatus",
        "cluster_candidates",
        "backfill_alignment_matrix",
    )
    assert {
        name for name in dir(alignment) if not name.startswith("_")
    } == set(alignment.__all__)
    newly_imported = set(sys.modules) - before
    assert "xic_extractor.discovery.pipeline" not in newly_imported
    assert "xic_extractor.extraction" not in newly_imported
    assert "xic_extractor.extractor" not in newly_imported
    assert "xic_extractor.raw_reader" not in newly_imported


def test_alignment_modules_do_not_import_pipeline_or_io_boundaries():
    alignment_dir = Path(__file__).parents[1] / "xic_extractor" / "alignment"
    banned_roots = (
        "gui",
        "scripts",
        "xic_extractor.discovery.pipeline",
        "xic_extractor.discovery.csv_writer",
        "xic_extractor.extraction",
        "xic_extractor.extractor",
        "xic_extractor.output",
    )

    violations = []
    for path in alignment_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for imported_name in _imported_module_names(node):
                if (
                    imported_name.startswith("xic_extractor.raw_reader")
                    and path.name != "pipeline.py"
                ):
                    violations.append((path.name, imported_name))
                elif imported_name.startswith(banned_roots):
                    violations.append((path.name, imported_name))

    assert violations == []


def test_import_boundary_detects_package_attribute_imports():
    tree = ast.parse(
        "from xic_extractor import extraction, extractor\n"
        "from xic_extractor import raw_reader\n"
    )
    imported_names = [
        imported_name
        for node in ast.walk(tree)
        for imported_name in _imported_module_names(node)
    ]

    assert "xic_extractor.extraction" in imported_names
    assert "xic_extractor.extractor" in imported_names
    assert "xic_extractor.raw_reader" in imported_names


def _imported_module_names(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        imported_names = [node.module]
        imported_names.extend(
            f"{node.module}.{alias.name}"
            for alias in node.names
            if alias.name != "*"
        )
        return imported_names
    return []


def test_default_config_matches_v1_alignment_contract():
    from xic_extractor.alignment import AlignmentConfig

    config = AlignmentConfig()

    assert config.preferred_ppm == 20.0
    assert config.max_ppm == 50.0
    assert config.preferred_rt_sec == 60.0
    assert config.max_rt_sec == 180.0
    assert config.product_mz_tolerance_ppm == 20.0
    assert config.observed_loss_tolerance_ppm == 20.0
    assert config.mz_bucket_neighbor_radius == 2
    assert config.anchor_priorities == ("HIGH",)
    assert config.anchor_min_evidence_score == 60
    assert config.anchor_min_seed_events == 2
    assert config.anchor_min_scan_support_score == 0.5
    assert config.rt_unit == "min"
    assert config.fragmentation_model == "cid_nl"


def test_alignment_config_duplicate_fold_defaults_are_conservative():
    from xic_extractor.alignment import AlignmentConfig

    config = AlignmentConfig()

    assert config.duplicate_fold_ppm == 5.0
    assert config.duplicate_fold_rt_sec == 2.0
    assert config.duplicate_fold_product_ppm == 10.0
    assert config.duplicate_fold_observed_loss_ppm == 10.0
    assert config.duplicate_fold_min_detected_overlap == 0.80
    assert config.duplicate_fold_min_shared_detected_count == 3
    assert config.duplicate_fold_min_detected_jaccard == 0.60
    assert config.duplicate_fold_min_present_overlap == 0.80


@pytest.mark.parametrize(
    "kwargs",
    [
        {"preferred_ppm": 0.0},
        {"max_ppm": -1.0},
        {"preferred_ppm": 51.0, "max_ppm": 50.0},
        {"preferred_rt_sec": 0.0},
        {"max_rt_sec": -1.0},
        {"preferred_rt_sec": 181.0, "max_rt_sec": 180.0},
        {"product_mz_tolerance_ppm": 0.0},
        {"observed_loss_tolerance_ppm": -1.0},
    ],
)
def test_invalid_tolerance_windows_are_rejected(kwargs):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duplicate_fold_ppm", 0.0),
        ("duplicate_fold_rt_sec", 0.0),
        ("duplicate_fold_product_ppm", 0.0),
        ("duplicate_fold_observed_loss_ppm", 0.0),
        ("duplicate_fold_min_detected_overlap", -0.1),
        ("duplicate_fold_min_detected_overlap", 1.1),
        ("duplicate_fold_min_shared_detected_count", 0),
        ("duplicate_fold_min_detected_jaccard", -0.1),
        ("duplicate_fold_min_detected_jaccard", 1.1),
        ("duplicate_fold_min_present_overlap", -0.1),
        ("duplicate_fold_min_present_overlap", 1.1),
    ],
)
def test_alignment_config_rejects_invalid_duplicate_fold_values(field, value):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError, match=field):
        AlignmentConfig(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "preferred_ppm",
        "max_ppm",
        "preferred_rt_sec",
        "max_rt_sec",
        "product_mz_tolerance_ppm",
        "observed_loss_tolerance_ppm",
    ],
)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_tolerance_windows_are_rejected(field, value):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "preferred_ppm",
        "max_ppm",
        "preferred_rt_sec",
        "max_rt_sec",
        "product_mz_tolerance_ppm",
        "observed_loss_tolerance_ppm",
    ],
)
def test_bool_tolerance_windows_are_rejected(field):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**{field: True})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"anchor_priorities": ()},
        {"anchor_priorities": ["HIGH"]},
        {"anchor_priorities": "HIGH"},
        {"anchor_priorities": ("BAD",)},
        {"anchor_priorities": ("HIGH", "BAD")},
        {"anchor_priorities": ([],)},
        {"anchor_min_evidence_score": -1},
        {"anchor_min_evidence_score": 101},
        {"anchor_min_evidence_score": True},
        {"anchor_min_evidence_score": 60.5},
        {"anchor_min_evidence_score": math.nan},
        {"anchor_min_evidence_score": math.inf},
        {"anchor_min_seed_events": 0},
        {"anchor_min_seed_events": math.nan},
        {"anchor_min_seed_events": math.inf},
        {"anchor_min_seed_events": 1.5},
        {"anchor_min_seed_events": True},
        {"anchor_min_scan_support_score": -0.1},
        {"anchor_min_scan_support_score": 1.1},
        {"anchor_min_scan_support_score": True},
        {"anchor_min_scan_support_score": math.nan},
        {"anchor_min_scan_support_score": math.inf},
        {"anchor_min_scan_support_score": "0.5"},
        {"mz_bucket_neighbor_radius": 0},
        {"mz_bucket_neighbor_radius": -1},
        {"mz_bucket_neighbor_radius": math.nan},
        {"mz_bucket_neighbor_radius": math.inf},
        {"mz_bucket_neighbor_radius": 1.5},
        {"mz_bucket_neighbor_radius": True},
        {"rt_unit": "sec"},
        {"fragmentation_model": "hcd"},
    ],
)
def test_invalid_anchor_and_v1_fixed_fields_are_rejected(kwargs):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**kwargs)


def test_cluster_candidates_returns_empty_tuple_for_empty_input():
    from xic_extractor.alignment import cluster_candidates

    assert cluster_candidates([]) == ()


def test_cluster_candidates_clusters_non_empty_input_from_public_import():
    from xic_extractor.alignment import cluster_candidates

    clusters = cluster_candidates(
        [
            SimpleNamespace(
                candidate_id="nl141-sample-a",
                neutral_loss_tag="NL141",
                review_priority="LOW",
                evidence_score=50,
                seed_event_count=1,
                ms1_peak_found=True,
                ms1_scan_support_score=0.5,
                ms1_area=100.0,
                neutral_loss_mass_error_ppm=0.0,
                precursor_mz=500.0,
                product_mz=359.0,
                observed_neutral_loss_da=141.0,
                best_seed_rt=5.0,
                ms1_apex_rt=5.0,
                sample_stem="sample-a",
            ),
        ],
    )

    assert tuple(cluster.cluster_id for cluster in clusters) == ("ALN000001",)
