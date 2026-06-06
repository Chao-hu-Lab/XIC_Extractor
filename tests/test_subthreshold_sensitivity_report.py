from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.changed_row_mode_overlay_review import SubThresholdCandidate
from tools.diagnostics.subthreshold_sensitivity_report import (
    run_subthreshold_sensitivity_report,
    summarize_subthreshold_sensitivity,
)

_SHOULDER_PROFILE = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    2.0, 8.0, 30.0, 70.0, 100.0, 70.0, 30.0, 8.0, 2.0,
    0.0, 0.0,
    4.0, 9.0, 13.0, 14.0, 13.0, 9.0, 4.0,
    0.0, 0.0, 0.0, 0.0,
]


def _candidate(
    accepted: bool,
    reasons: list[str],
    *,
    height_fraction: float = 0.14,
) -> SubThresholdCandidate:
    return SubThresholdCandidate(
        sample_stem="S1",
        apex_rt=8.0,
        height_fraction=height_fraction,
        prominence_fraction=0.05,
        accepted=accepted,
        reject_reasons=tuple(reasons),
    )


def test_summarize_counts_gates_and_height_recovery() -> None:
    data = [
        (
            "FAM:S1",
            [
                _candidate(True, []),
                _candidate(False, ["height 0.14<0.20"], height_fraction=0.14),
                _candidate(
                    False,
                    ["height 0.05<0.20", "edge<0.20"],
                    height_fraction=0.05,
                ),
                _candidate(False, ["edge<0.20"]),
            ],
        ),
    ]

    summary = summarize_subthreshold_sensitivity(data)

    assert summary.total_local_maxima == 4
    assert summary.accepted == 1
    assert summary.rejected == 3

    gates = {row["gate"]: row for row in summary.gate_rows}
    assert gates["height"]["candidates_with_gate"] == "2"
    assert gates["height"]["candidates_sole_gate"] == "1"
    assert gates["edge"]["candidates_with_gate"] == "2"
    assert gates["edge"]["candidates_sole_gate"] == "1"

    recovery = {
        row["height_fraction_threshold"]: row for row in summary.recovery_rows
    }
    # only the sole-height candidate (hf=0.14) is recoverable, at thresholds <=0.14
    assert recovery["0.15"]["peaks_recovered_upper_bound"] == "0"
    assert recovery["0.12"]["peaks_recovered_upper_bound"] == "1"
    assert recovery["0.12"]["traces_with_recovery"] == "1"
    assert recovery["0.05"]["peaks_recovered_upper_bound"] == "1"


def test_run_report_end_to_end_writes_tsvs(tmp_path: Path) -> None:
    rt = [8.0 + index * 0.04 for index in range(len(_SHOULDER_PROFILE))]
    trace = {
        "sample_stem": "S1",
        "status": "detected",
        "rt": rt,
        "intensity": _SHOULDER_PROFILE,
    }
    trace_json = tmp_path / "fam_trace_data.json"
    trace_json.write_text(
        json.dumps({"family_id": "FAM", "traces": [trace, trace]}),
        encoding="utf-8",
    )

    gate_tsv, recovery_tsv, summary = run_subthreshold_sensitivity_report(
        trace_data_jsons=[trace_json],
        output_dir=tmp_path / "out",
    )

    assert gate_tsv.is_file()
    assert recovery_tsv.is_file()
    assert summary.traces_scanned == 2
    assert summary.rejected >= 1
    # the shoulder is below the 20% height gate, so height must be a blocker
    gates = {row["gate"]: row for row in summary.gate_rows}
    assert int(gates["height"]["candidates_with_gate"]) >= 1
