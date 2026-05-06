import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_csv_to_excel_is_thin_compatibility_wrapper() -> None:
    script_path = ROOT / "scripts" / "csv_to_excel.py"

    assert _openpyxl_imports(script_path) == []
    assert len(script_path.read_text(encoding="utf-8").splitlines()) <= 300


def test_workbook_inputs_exists_and_is_openpyxl_free() -> None:
    assert importlib.util.find_spec("xic_extractor.output.workbook_inputs") is not None

    input_source = (
        ROOT / "xic_extractor" / "output" / "workbook_inputs.py"
    ).read_text(encoding="utf-8")
    assert "workbook_styles" not in input_source
    assert (
        _openpyxl_imports(ROOT / "xic_extractor" / "output" / "workbook_inputs.py")
        == []
    )


def test_review_report_writer_delegates_visual_components() -> None:
    assert importlib.util.find_spec("xic_extractor.output.review_report_components")
    assert importlib.util.find_spec("xic_extractor.output.review_report_bars")
    assert importlib.util.find_spec("xic_extractor.output.review_report_focus")
    assert importlib.util.find_spec("xic_extractor.output.review_report_trend")

    report_path = ROOT / "xic_extractor" / "output" / "review_report.py"
    bars_path = ROOT / "xic_extractor" / "output" / "review_report_bars.py"
    focus_path = ROOT / "xic_extractor" / "output" / "review_report_focus.py"
    components_path = ROOT / "xic_extractor" / "output" / "review_report_components.py"
    assert len(report_path.read_text(encoding="utf-8").splitlines()) <= 220
    assert len(bars_path.read_text(encoding="utf-8").splitlines()) <= 120
    assert len(focus_path.read_text(encoding="utf-8").splitlines()) <= 220
    assert len(components_path.read_text(encoding="utf-8").splitlines()) <= 260


def _openpyxl_imports(path: Path) -> list[ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [node for node in ast.walk(tree) if _is_openpyxl_import(node)]


def _is_openpyxl_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(_is_openpyxl_name(alias.name) for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return _is_openpyxl_name(node.module)
    return False


def _is_openpyxl_name(name: str) -> bool:
    return name == "openpyxl" or name.startswith("openpyxl.")
