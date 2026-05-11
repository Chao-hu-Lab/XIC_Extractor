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
