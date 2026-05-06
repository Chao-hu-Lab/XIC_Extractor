import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extractor_delegates_backend_orchestration() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.serial_backend")
    assert importlib.util.find_spec("xic_extractor.extraction.process_backend")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    function_names = _function_names(extractor_path)

    assert "_run_serial" not in function_names
    assert "_run_process" not in function_names
    assert "_collect_raw_file_results_process" not in function_names
    assert "_collect_istd_prepass_process" not in function_names
    assert len(extractor_path.read_text(encoding="utf-8").splitlines()) <= 850


def test_backends_delegate_output_dispatch() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.output_dispatch")

    extraction_dir = ROOT / "xic_extractor" / "extraction"
    for module_name in ("serial_backend.py", "process_backend.py"):
        source = (extraction_dir / module_name).read_text(encoding="utf-8")
        assert "csv_writers" not in source
        assert "keep_intermediate_csv" not in source


def test_extractor_delegates_pipeline_flow() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.pipeline")

    source = (ROOT / "xic_extractor" / "extractor.py").read_text(
        encoding="utf-8"
    )

    assert "run_serial" not in source
    assert "run_process" not in source
    assert "write_outputs" not in source
    assert "preflight_raw_reader" not in source


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
