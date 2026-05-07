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


def _class_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
