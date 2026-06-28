from pathlib import Path

from tools.testing import test_shards
from tools.testing.test_shards import (
    SHARD_PATTERNS,
    assign_shards,
    check_coverage,
    discover_test_files,
)


def test_test_shards_cover_every_test_file() -> None:
    assert check_coverage() == ()


def test_test_shards_do_not_run_empty_primary_shards() -> None:
    assigned = assign_shards(discover_test_files())

    for shard in SHARD_PATTERNS:
        assert assigned[shard], shard


def test_test_shards_keep_changed_shard_contracts() -> None:
    assigned = assign_shards(
        (
            Path("tests/test_discovery_worker.py"),
            Path("tests/test_pyinstaller_spec.py"),
            Path("tests/test_peak_model_selection.py"),
            Path("tests/test_alignment_pipeline_outputs.py"),
            Path("tests/test_standard_peak_backfill_preset.py"),
        )
    )

    assert assigned["gui"] == (Path("tests/test_discovery_worker.py"),)
    assert assigned["docs-config"] == (
        Path("tests/test_pyinstaller_spec.py"),
        Path("tests/test_peak_model_selection.py"),
    )
    assert assigned["alignment-core"] == (
        Path("tests/test_alignment_pipeline_outputs.py"),
    )
    assert assigned["product-gates"] == (
        Path("tests/test_standard_peak_backfill_preset.py"),
    )


def test_test_shards_prefer_uv_runner_when_pytest_is_not_importable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(test_shards, "find_spec", lambda name: None)
    monkeypatch.setattr(
        test_shards.shutil,
        "which",
        lambda name: "C:/tools/uv.exe" if name == "uv" else "C:/global/pytest.exe",
    )

    assert test_shards._pytest_command() == ["C:/tools/uv.exe", "run", "pytest"]
