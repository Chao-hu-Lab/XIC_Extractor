from pathlib import Path

from scripts import run_instrument_qc
from xic_extractor.instrument_qc.models import InstrumentQCRunOutput


def _fake_output(output_dir: Path) -> InstrumentQCRunOutput:
    trend_tsv = output_dir / "instrument_qc_sdolek_trend.tsv"
    trend_json = output_dir / "instrument_qc_sdolek_trend.json"
    diagnostics_tsv = output_dir / "instrument_qc_sdolek_diagnostics.tsv"
    output_dir.mkdir(parents=True, exist_ok=True)
    trend_tsv.write_text("sample_name\n", encoding="utf-8")
    trend_json.write_text("{}\n", encoding="utf-8")
    diagnostics_tsv.write_text(
        "sample_name\traw_path\tissue\tdetail\n", encoding="utf-8"
    )
    return InstrumentQCRunOutput(
        trend_rows=(),
        diagnostics=(),
        trend_tsv=trend_tsv,
        trend_json=trend_json,
        diagnostics_tsv=diagnostics_tsv,
    )


def test_run_instrument_qc_cli_calls_sdolek_pipeline(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls: dict[str, object] = {}

    def fake_run_sdolek_pipeline(**kwargs):
        calls.update(kwargs)
        return _fake_output(kwargs["output_dir"])

    monkeypatch.setattr(
        run_instrument_qc, "run_sdolek_pipeline", fake_run_sdolek_pipeline
    )

    rc = run_instrument_qc.main(
        [
            "--raw-dir",
            str(tmp_path / "raw"),
            "--output-dir",
            str(tmp_path / "out"),
            "--mode",
            "sdolek",
        ]
    )

    assert rc == 0
    assert calls["raw_dir"] == tmp_path / "raw"
    assert calls["output_dir"] == tmp_path / "out"
    assert "instrument_qc_sdolek_trend.tsv" in capsys.readouterr().out


def test_run_instrument_qc_cli_rejects_unknown_mode(capsys) -> None:
    rc = run_instrument_qc.main(
        [
            "--raw-dir",
            "raw",
            "--output-dir",
            "out",
            "--mode",
            "blank",
        ]
    )

    assert rc == 2
    assert "unsupported mode" in capsys.readouterr().err
