import json
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
            edge_evidence_tsv=output_dir / "owner_edge_evidence.tsv",
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
    assert captured["raw_workers"] == 1
    assert captured["drift_lookup"] is None
    stdout = capsys.readouterr().out
    assert "Alignment review TSV:" in stdout
    assert "alignment_review.tsv" in stdout
    assert "alignment_matrix_status.tsv" in stdout
    assert "Owner edge evidence TSV:" in stdout


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


def test_run_alignment_cli_passes_raw_workers(
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
            "--raw-workers",
            "4",
        ],
    )

    assert code == 0
    assert captured["raw_workers"] == 4


def test_run_alignment_cli_passes_raw_xic_batch_size(
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
            "--raw-xic-batch-size",
            "64",
        ],
    )

    assert code == 0
    assert captured["raw_xic_batch_size"] == 64


def test_run_alignment_cli_requires_sample_info_and_targeted_istd_together(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(tmp_path / "missing.csv"),
            "--raw-dir",
            str(tmp_path / "missing-raws"),
            "--dll-dir",
            str(tmp_path / "missing-dll"),
            "--sample-info",
            str(tmp_path / "sample_info.csv"),
        ],
    )

    assert code == 2
    assert (
        "--sample-info is required with --targeted-istd-workbook, "
        "and both must be provided together"
    ) in capsys.readouterr().err


def test_run_alignment_cli_builds_and_passes_drift_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")
    drift_lookup = object()
    captured = {}

    def fake_read_targeted_istd_drift_evidence(**kwargs):
        captured["drift_kwargs"] = kwargs
        return drift_lookup

    def fake_run_alignment(**kwargs):
        captured["run_kwargs"] = kwargs
        return AlignmentRunOutputs()

    monkeypatch.setattr(
        run_alignment,
        "read_targeted_istd_drift_evidence",
        fake_read_targeted_istd_drift_evidence,
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
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(targeted_workbook),
            "--raw-workers",
            "3",
            "--raw-xic-batch-size",
            "16",
        ],
    )

    assert code == 0
    assert captured["drift_kwargs"] == {
        "targeted_workbook": targeted_workbook.resolve(),
        "sample_info": sample_info.resolve(),
    }
    assert captured["run_kwargs"]["drift_lookup"] is drift_lookup
    assert captured["run_kwargs"]["raw_workers"] == 3
    assert captured["run_kwargs"]["raw_xic_batch_size"] == 16


def test_run_alignment_cli_rejects_missing_sample_info_with_targeted_workbook(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(tmp_path / "missing_sample_info.csv"),
            "--targeted-istd-workbook",
            str(targeted_workbook),
        ],
    )

    assert code == 2
    assert "sample info does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_targeted_workbook_with_sample_info(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(tmp_path / "missing_targeted.xlsx"),
        ],
    )

    assert code == 2
    assert "targeted ISTD workbook does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("exc", [OSError("cannot read workbook"), KeyError("Sample")])
def test_run_alignment_cli_returns_2_for_drift_reader_errors(
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
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")

    def fail_read_targeted_istd_drift_evidence(**kwargs):
        raise exc

    monkeypatch.setattr(
        run_alignment,
        "read_targeted_istd_drift_evidence",
        fail_read_targeted_istd_drift_evidence,
    )

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(targeted_workbook),
        ],
    )

    assert code == 2
    assert str(exc) in capsys.readouterr().err


def test_run_alignment_cli_passes_owner_backfill_min_detected_samples(
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
            "--owner-backfill-min-detected-samples",
            "3",
        ],
    )

    assert code == 0
    assert captured["alignment_config"].owner_backfill_min_detected_samples == 3


def test_run_alignment_cli_writes_timing_json(
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
    timing_path = tmp_path / "diagnostics" / "alignment_timing.json"

    def fake_run_alignment(**kwargs):
        timing_recorder = kwargs["timing_recorder"]
        with timing_recorder.stage(
            "alignment.read_candidates",
            metrics={"candidate_count": 0},
        ):
            pass
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
            "--timing-output",
            str(timing_path),
        ],
    )

    assert code == 0
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    assert payload["pipeline"] == "alignment"
    assert payload["records"][0]["stage"] == "alignment.read_candidates"
    assert payload["records"][0]["metrics"] == {"candidate_count": 0}
    assert "Timing JSON:" in capsys.readouterr().out


def test_run_alignment_cli_rejects_invalid_raw_workers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        run_alignment.main(
            [
                "--discovery-batch-index",
                str(batch_index),
                "--raw-dir",
                str(raw_dir),
                "--dll-dir",
                str(dll_dir),
                "--raw-workers",
                "0",
            ],
        )

    assert exc_info.value.code == 2
    assert "value must be an integer >= 1" in capsys.readouterr().err


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
