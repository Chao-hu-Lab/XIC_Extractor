import ast
from pathlib import Path


def test_alignment_backfill_does_not_import_io_or_pipeline_boundaries():
    path = (
        Path(__file__).parents[1]
        / "xic_extractor"
        / "alignment"
        / "backfill.py"
    )
    banned_roots = (
        "gui",
        "scripts",
        "xic_extractor.discovery.pipeline",
        "xic_extractor.discovery.csv_writer",
        "xic_extractor.extraction",
        "xic_extractor.extractor",
        "xic_extractor.raw_reader",
        "xic_extractor.output",
    )

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = [
        imported_name
        for node in ast.walk(tree)
        for imported_name in _imported_module_names(node)
        if imported_name.startswith(banned_roots)
    ]

    assert violations == []


def test_alignment_exports_plan2_public_api_names():
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


def test_alignment_csv_and_tsv_modules_do_not_import_raw_reader():
    for module_name in ("csv_io.py", "tsv_writer.py"):
        path = (
            Path(__file__).parents[1]
            / "xic_extractor"
            / "alignment"
            / module_name
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = [
            imported_name
            for node in ast.walk(tree)
            for imported_name in _imported_module_names(node)
            if imported_name.startswith("xic_extractor.raw_reader")
        ]

        assert violations == []


def test_alignment_pipeline_raw_reader_import_is_lazy_default_opener_only():
    path = (
        Path(__file__).parents[1]
        / "xic_extractor"
        / "alignment"
        / "pipeline.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parents = _parent_map(tree)
    raw_reader_imports = [
        node
        for node in ast.walk(tree)
        if any(
            imported_name.startswith("xic_extractor.raw_reader")
            for imported_name in _imported_module_names(node)
        )
    ]

    assert raw_reader_imports
    for node in raw_reader_imports:
        assert _enclosing_function_name(node, parents) == "_default_raw_opener"


def test_alignment_ownership_module_stays_domain_focused():
    source = (
        Path(__file__).parents[1]
        / "xic_extractor"
        / "alignment"
        / "ownership.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "xic_extractor.alignment.tsv_writer",
        "scripts.run_alignment",
        "openpyxl",
        "csv.",
    )
    for token in forbidden:
        assert token not in source


def _imported_module_names(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        imported_names = [node.module] if node.module else []
        imported_names.extend(
            f"{node.module}.{alias.name}"
            for alias in node.names
            if node.module
        )
        return imported_names
    return []


def _parent_map(tree):
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _enclosing_function_name(node, parents):
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.FunctionDef):
            return current.name
    return None
