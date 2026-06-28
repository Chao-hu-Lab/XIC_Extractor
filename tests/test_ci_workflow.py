from pathlib import Path

from tools.testing.test_shards import SHARD_PATTERNS

CORE_CI_COMMANDS = (
    "uv run ruff check xic_extractor tests",
    "uv run python scripts/check_diagnostics_index.py",
    "uv run mypy xic_extractor",
    "uv run python -m tools.testing.test_shards --check",
)


def test_ci_workflow_runs_ruff_and_mypy() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    for command in CORE_CI_COMMANDS:
        assert command in workflow


def test_ci_workflow_runs_sharded_tests() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    shard_command = (
        "uv run python -m tools.testing.test_shards "
        "${{ matrix.shard }} -- -v --tb=short -x"
    )

    assert "uv run python -m tools.testing.test_shards --check" in workflow
    assert _matrix_shards(workflow) == tuple(SHARD_PATTERNS)
    assert "repo-${{ matrix.python-version }}-${{ matrix.shard }}" in workflow
    assert shard_command in workflow
    assert "uv run pytest -v --tb=short -x" not in workflow


def test_pr_gate_docs_match_ci_commands() -> None:
    gate_docs = (
        Path("AGENTS.md").read_text(encoding="utf-8"),
        Path("docs/agent/execution-gates.md").read_text(encoding="utf-8"),
    )
    shard_commands = tuple(
        f"uv run python -m tools.testing.test_shards {shard} -- -v --tb=short -x"
        for shard in SHARD_PATTERNS
    )

    for doc in gate_docs:
        for command in (*CORE_CI_COMMANDS, *shard_commands):
            assert command in doc
        assert "uv run pytest -v --tb=short -x" not in doc


def _matrix_shards(workflow: str) -> tuple[str, ...]:
    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "shard:":
            continue
        shards: list[str] = []
        for follow in lines[index + 1 :]:
            stripped = follow.strip()
            if stripped.startswith("- "):
                shards.append(stripped[2:])
                continue
            if stripped:
                break
        return tuple(shards)
    raise AssertionError("missing test shard matrix")
