import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extractor_delegates_backend_orchestration() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.serial_backend")
    assert importlib.util.find_spec("xic_extractor.extraction.process_backend")
    assert importlib.util.find_spec("xic_extractor.extraction.jobs")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    function_names = _function_names(extractor_path)

    assert "_run_serial" not in function_names
    assert "_run_process" not in function_names
    assert "_collect_raw_file_results_process" not in function_names
    assert "_collect_istd_prepass_process" not in function_names
    assert len(extractor_path.read_text(encoding="utf-8").splitlines()) <= 850


def test_process_jobs_live_under_extraction_package() -> None:
    execution_path = ROOT / "xic_extractor" / "execution.py"
    process_backend_path = (
        ROOT / "xic_extractor" / "extraction" / "process_backend.py"
    )

    assert _function_names(execution_path) == set()
    assert len(execution_path.read_text(encoding="utf-8").splitlines()) <= 60
    assert "xic_extractor.execution" not in process_backend_path.read_text(
        encoding="utf-8"
    )


def test_backends_delegate_output_dispatch() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.output_dispatch")

    extraction_dir = ROOT / "xic_extractor" / "extraction"
    for module_name in ("serial_backend.py", "process_backend.py"):
        source = (extraction_dir / module_name).read_text(encoding="utf-8")
        assert "csv_writers" not in source
        assert "keep_intermediate_csv" not in source


def test_pipeline_owns_raw_path_resolution() -> None:
    extraction_dir = ROOT / "xic_extractor" / "extraction"

    pipeline_source = (extraction_dir / "pipeline.py").read_text(encoding="utf-8")
    assert 'glob("*.raw")' in pipeline_source

    for module_name in ("serial_backend.py", "process_backend.py"):
        source = (extraction_dir / module_name).read_text(encoding="utf-8")
        assert 'glob("*.raw")' not in source


def test_extractor_delegates_pipeline_flow() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.pipeline")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    source = extractor_path.read_text(encoding="utf-8")
    function_names = _function_names(extractor_path)

    assert "run_serial" not in source
    assert "run_process" not in source
    assert "write_outputs" not in source
    assert "preflight_raw_reader" not in source
    assert "_resolve_injection_order" not in function_names
    assert "_resolve_rt_prior_library" not in function_names
    assert "_fallback_injection_order_from_mtime" not in function_names


def test_extractor_delegates_istd_prepass() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.istd_prepass")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    function_names = _function_names(extractor_path)

    assert "_extract_istd_anchors_only" not in function_names


def test_extractor_delegates_target_extraction() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.target_extraction")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    function_names = _function_names(extractor_path)

    assert "_extract_raw_file_result" not in function_names
    assert "_process_file" not in function_names
    assert "_extract_one_target" not in function_names


def test_target_extraction_delegates_diagnostic_evidence_helpers() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.diagnostics")

    target_path = ROOT / "xic_extractor" / "extraction" / "target_extraction.py"
    function_names = _function_names(target_path)

    assert "_check_target_nl" not in function_names
    assert "_candidate_ms2_evidence_builder" not in function_names
    assert len(target_path.read_text(encoding="utf-8").splitlines()) <= 350


def test_extractor_delegates_rt_anchor_and_drift_helpers() -> None:
    assert importlib.util.find_spec("xic_extractor.extraction.rt_windows")
    assert importlib.util.find_spec("xic_extractor.extraction.anchors")
    assert importlib.util.find_spec("xic_extractor.extraction.drift")

    extractor_path = ROOT / "xic_extractor" / "extractor.py"
    function_names = _function_names(extractor_path)

    assert "_get_rt_window" not in function_names
    assert "_recover_istd_peak_with_wider_anchor_window" not in function_names
    assert "_estimate_sample_drift" not in function_names
    assert "_paired_anchor_mismatch_diagnostic" not in function_names
    assert "_apply_anchor_mismatch_penalty" not in function_names
    assert "_anchor_mismatch_confidence" not in function_names
    assert "_check_target_nl" not in function_names
    assert "_candidate_ms2_evidence_builder" not in function_names
    assert len(extractor_path.read_text(encoding="utf-8").splitlines()) <= 250


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
