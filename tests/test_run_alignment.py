from pathlib import Path

import pytest
import tomllib

from scripts import run_alignment
from xic_extractor.alignment.pipeline import AlignmentRunOutputs
from xic_extractor.raw_reader import RawReaderError


def test_run_alignment_cli_passes_paths_settings_and_debug_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "alignment"
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        output_dir.mkdir(parents=True, exist_ok=True)
        review = output_dir / "alignment_review.tsv"
        matrix = output_dir / "alignment_matrix.tsv"
        cells = output_dir / "alignment_cells.tsv"
        status = output_dir / "alignment_matrix_status.tsv"
        for path in (review, matrix, cells, status):
            path.write_text("x\n", encoding="utf-8")
        return AlignmentRunOutputs(
            workbook=output_dir / "alignment_results.xlsx",
            review_html=output_dir / "review_report.html",
            review_tsv=review,
            matrix_tsv=matrix,
            cells_tsv=cells,
            status_matrix_tsv=status,
        )

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
            "--resolver-mode",
            "legacy_savgol",
            "--emit-alignment-cells",
            "--emit-alignment-status-matrix",
        ]
    )

    assert code == 0
    assert captured["discovery_batch_index"] == batch_index.resolve()
    assert captured["raw_dir"] == raw_dir.resolve()
    assert captured["dll_dir"] == dll_dir.resolve()
    assert captured["output_dir"] == output_dir.resolve()
    assert captured["alignment_config"].max_ppm == 50.0
    peak_config = captured["peak_config"]
    assert peak_config.data_dir == raw_dir.resolve()
    assert peak_config.dll_dir == dll_dir.resolve()
    assert peak_config.output_csv == output_dir.resolve() / "xic_results.csv"
    assert peak_config.diagnostics_csv == output_dir.resolve() / "xic_diagnostics.csv"
    assert peak_config.resolver_mode == "legacy_savgol"
    assert captured["output_level"] == "machine"
    assert captured["emit_alignment_cells"] is True
    assert captured["emit_alignment_status_matrix"] is True
    stdout = capsys.readouterr().out
    assert "Alignment review TSV:" in stdout
    assert "alignment_review.tsv" in stdout
    assert "alignment_matrix_status.tsv" in stdout


def test_run_alignment_cli_accepts_output_level_debug(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-level",
            "debug",
        ],
    )

    assert code == 0
    assert captured["output_level"] == "debug"


def test_run_alignment_cli_rejects_missing_batch_index(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(tmp_path / "missing.csv"),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert "discovery batch index does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_raw_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(tmp_path / "missing-raws"),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert "raw directory does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_dll_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(tmp_path / "missing-dll"),
        ]
    )

    assert code == 2
    assert "dll directory does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("exc", [RawReaderError("raw fail"), ValueError("bad input")])
def test_run_alignment_cli_returns_2_for_user_visible_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    exc: Exception,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    def fail_run_alignment(**kwargs):
        raise exc

    monkeypatch.setattr(run_alignment, "run_alignment", fail_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert str(exc) in capsys.readouterr().err


def test_run_alignment_cli_returns_2_for_missing_candidate_csv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text(
        "sample_stem,raw_file,candidate_csv\n"
        "Sample_A,C:/stale/Sample_A.raw,missing/discovery_candidates.csv\n",
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    stderr = capsys.readouterr().err
    assert "missing" in stderr
    assert "discovery_candidates.csv" in stderr


def test_pyproject_registers_alignment_cli_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert (
        pyproject["project"]["scripts"]["xic-align-cli"]
        == "scripts.run_alignment:main"
    )
