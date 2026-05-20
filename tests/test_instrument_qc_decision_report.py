import json
from pathlib import Path

from tools.diagnostics import instrument_qc_decision_report
from xic_extractor.instrument_qc.decision_report import (
    build_instrument_qc_decision,
    render_instrument_qc_decision_markdown,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_decision_report_marks_missing_manifest_metadata_incomplete(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "instrument_qc_sdolek_trend.json",
        {
            "summary": {"total_rows": 2, "status_counts": {"detected": 2}},
            "rows": [
                {
                    "sample_name": "SDOLEK",
                    "compound": "SDO",
                    "status": "detected",
                    "trend_flags": "",
                    "identity_evidence": "MS1_ONLY",
                }
            ],
            "diagnostics": [],
        },
    )

    decision = build_instrument_qc_decision(tmp_path)

    assert decision.verdict == "metadata_incomplete"
    assert "method-doc" in decision.top_concerns[0]


def test_decision_report_marks_rt_drift_when_rt_outlier_present(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "instrument_qc_sequence_manifest.json",
        {"summary": {"total_rows": 1}},
    )
    _write_json(
        tmp_path / "instrument_qc_sdolek_trend.json",
        {
            "summary": {"total_rows": 1, "status_counts": {"detected": 1}},
            "rows": [
                {
                    "sample_name": "SDOLEK",
                    "compound": "LEK",
                    "status": "detected",
                    "trend_flags": "RT_OUTLIER",
                    "identity_evidence": "MS1_ONLY",
                }
            ],
            "diagnostics": [],
        },
    )

    decision = build_instrument_qc_decision(tmp_path)

    assert decision.verdict == "rt_drift_review"
    assert decision.ms2_readiness == "not_recommended"


def test_decision_report_render_is_human_first() -> None:
    decision = build_instrument_qc_decision(Path("missing"))
    text = render_instrument_qc_decision_markdown(decision)

    assert text.startswith("# Instrument QC Decision Report")
    assert "Verdict" in text.splitlines()[2]
    assert "MS1-only" in text


def test_decision_report_cli_writes_markdown(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "instrument_qc_sdolek_trend.json",
        {"summary": {"total_rows": 0}, "rows": [], "diagnostics": []},
    )
    output_md = tmp_path / "report" / "decision.md"

    rc = instrument_qc_decision_report.main(
        [
            "--instrument-qc-dir",
            str(tmp_path),
            "--output-md",
            str(output_md),
        ]
    )

    assert rc == 0
    assert output_md.exists()
    assert "Instrument QC Decision Report" in output_md.read_text(encoding="utf-8")
