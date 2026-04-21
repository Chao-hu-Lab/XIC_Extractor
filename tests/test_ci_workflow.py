from pathlib import Path


def test_ci_workflow_runs_ruff_and_mypy() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "ruff" in workflow
    assert "mypy" in workflow
