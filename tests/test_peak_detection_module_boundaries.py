import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_peak_detection_models_own_result_dataclasses() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.models")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    model_path = ROOT / "xic_extractor" / "peak_detection" / "models.py"

    signal_classes = _class_names(signal_processing_path)
    model_classes = _class_names(model_path)

    expected_models = {
        "PeakResult",
        "PeakCandidate",
        "LocalMinimumRegionQuality",
        "PeakCandidatesResult",
        "PeakDetectionResult",
    }
    assert expected_models <= model_classes
    assert expected_models.isdisjoint(signal_classes)

    model_source = model_path.read_text(encoding="utf-8")
    assert "scipy" not in model_source
    assert "peak_scoring" not in model_source


def test_peak_detection_integration_owns_area_and_apex_helpers() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.integration")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    integration_path = ROOT / "xic_extractor" / "peak_detection" / "integration.py"

    signal_functions = _function_names(signal_processing_path)
    integration_functions = _function_names(integration_path)

    expected_helpers = {
        "raw_apex_index",
        "integrate_area_counts_seconds",
        "peak_bounds",
    }
    assert expected_helpers <= integration_functions
    assert {
        "_raw_apex_index",
        "_integrate_area_counts_seconds",
        "_peak_bounds",
    }.isdisjoint(signal_functions)

    integration_source = integration_path.read_text(encoding="utf-8")
    assert "peak_scoring" not in integration_source
    assert "ExtractionConfig" not in integration_source


def test_peak_detection_selection_owns_candidate_choice_helpers() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.selection")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    selection_path = ROOT / "xic_extractor" / "peak_detection" / "selection.py"

    signal_functions = _function_names(signal_processing_path)
    selection_functions = _function_names(selection_path)

    assert {"select_candidate", "selection_rt_for_scored_candidates"} <= (
        selection_functions
    )
    assert {
        "_select_candidate",
        "_selection_rt_for_scored_candidates",
    }.isdisjoint(signal_functions)

    selection_source = selection_path.read_text(encoding="utf-8")
    assert "ExtractionConfig" not in selection_source
    assert "scipy" not in selection_source


def test_peak_detection_trace_quality_owns_quality_signals() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.trace_quality")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    trace_quality_path = (
        ROOT / "xic_extractor" / "peak_detection" / "trace_quality.py"
    )

    signal_functions = _function_names(signal_processing_path)
    trace_quality_functions = _function_names(trace_quality_path)

    assert {
        "local_minimum_region_quality",
        "trace_continuity_score",
        "passes_local_peak_height_filters",
    } <= trace_quality_functions
    assert {
        "_local_minimum_region_quality",
        "_trace_continuity_score",
        "_passes_local_peak_height_filters",
    }.isdisjoint(signal_functions)

    trace_quality_source = trace_quality_path.read_text(encoding="utf-8")
    assert "peak_scoring" not in trace_quality_source
    assert "find_peaks" not in trace_quality_source


def test_peak_detection_legacy_savgol_owns_default_candidate_formation() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.legacy_savgol")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    legacy_path = ROOT / "xic_extractor" / "peak_detection" / "legacy_savgol.py"

    signal_functions = _function_names(signal_processing_path)
    legacy_functions = _function_names(legacy_path)

    assert "find_peak_candidates_legacy_savgol" in legacy_functions
    assert {
        "_find_peak_candidates_legacy_savgol",
        "_prominence_threshold",
        "_build_candidate",
    }.isdisjoint(signal_functions)

    legacy_source = legacy_path.read_text(encoding="utf-8")
    assert "savgol_filter" in legacy_source
    assert "find_peaks" in legacy_source
    assert "peak_scoring" not in legacy_source
    assert "local_minimum" not in legacy_source


def test_peak_detection_local_minimum_owns_region_candidate_formation() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.local_minimum")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    local_minimum_path = (
        ROOT / "xic_extractor" / "peak_detection" / "local_minimum.py"
    )

    signal_functions = _function_names(signal_processing_path)
    local_functions = _function_names(local_minimum_path)

    assert {
        "find_peak_candidates_local_minimum",
        "_local_peak_indices",
        "_local_minimum_regions",
        "_should_split_local_region",
        "_build_local_minimum_candidate",
    } <= local_functions
    assert {
        "_find_peak_candidates_local_minimum",
        "_local_minimum_threshold",
        "_local_peak_indices",
        "_local_minimum_regions",
        "_left_threshold_boundary",
        "_right_threshold_boundary",
        "_valley_index",
        "_should_split_local_region",
        "_build_local_minimum_candidate",
    }.isdisjoint(signal_functions)

    local_source = local_minimum_path.read_text(encoding="utf-8")
    assert "find_peaks" in local_source
    assert "savgol_filter" not in local_source
    assert "peak_scoring" not in local_source


def test_peak_detection_recovery_owns_preferred_rt_recovery_policy() -> None:
    assert importlib.util.find_spec("xic_extractor.peak_detection.recovery")

    signal_processing_path = ROOT / "xic_extractor" / "signal_processing.py"
    recovery_path = ROOT / "xic_extractor" / "peak_detection" / "recovery.py"

    signal_functions = _function_names(signal_processing_path)
    recovery_functions = _function_names(recovery_path)

    assert {
        "preferred_rt_recovery",
        "relaxed_local_minimum_recovery_config",
        "select_preferred_recovery_candidate",
    } <= recovery_functions
    assert {
        "_preferred_rt_recovery",
        "_relaxed_local_minimum_recovery_config",
        "_select_preferred_recovery_candidate",
    }.isdisjoint(signal_functions)

    recovery_source = recovery_path.read_text(encoding="utf-8")
    assert "peak_scoring" not in recovery_source
    assert "find_peaks" not in recovery_source
    assert "savgol_filter" not in recovery_source


def _class_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
