from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.selected_envelope_review_queue import (
    main,
    run_selected_envelope_review_queue,
)
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
)
from xic_extractor.peak_detection.selected_envelope_oracle_artifacts import (
    SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS,
)


def test_run_selected_envelope_review_queue_writes_changed_rows_and_queue(
    tmp_path: Path,
) -> None:
    diagnostics_tsv = tmp_path / "selected_envelope_diagnostics.tsv"
    _write_tsv(
        diagnostics_tsv,
        [
            _diagnostic_row(
                sample_name="sample-a",
                selected_candidate_id="candidate-001",
                boundary_change_class="no_change",
                row_boundary_decision="accept_candidate",
            ),
            _diagnostic_row(
                sample_name="sample-b",
                selected_candidate_id="candidate-002",
                boundary_change_class="flank_recovered",
                row_boundary_decision="accept_candidate",
            ),
            _diagnostic_row(
                sample_name="sample-c",
                selected_candidate_id="candidate-003",
                boundary_change_class="tail_uncertain",
                row_boundary_decision="defer",
                boundary_stop_reason="context_edge_above_baseline_return",
            ),
        ],
    )

    outputs, result = run_selected_envelope_review_queue(
        selected_envelope_diagnostics_tsv=diagnostics_tsv,
        output_dir=tmp_path / "review",
    )

    changed_rows = _read_tsv(outputs.changed_rows_tsv)
    queue_rows = _read_tsv(outputs.oracle_review_queue_tsv)
    manifest_rows = _read_tsv(outputs.diagnostic_manifest_tsv)
    payload = json.loads(outputs.json_path.read_text(encoding="utf-8"))

    assert result.input_row_count == 3
    assert result.changed_row_count == 2
    assert result.oracle_review_queue_row_count == 2
    assert list(changed_rows[0]) == list(SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS)
    assert {row["sample_name"] for row in changed_rows} == {"sample-b", "sample-c"}
    assert list(queue_rows[0]) == list(SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS)
    assert queue_rows[1]["review_priority"] == "high_risk_boundary_review"
    assert manifest_rows[0]["gate_decision"] == "defer"
    assert manifest_rows[0]["changed_row_count"] == "2"
    assert manifest_rows[0]["changed_row_denominator"] == "3"
    assert manifest_rows[0]["high_risk_strata"] == "tail_uncertain"
    assert payload["readiness_label"] == "diagnostic_only"
    assert payload["outputs"]["oracle_review_queue_tsv"].endswith(
        "selected_envelope_oracle_review_queue.tsv"
    )


def test_run_selected_envelope_review_queue_writes_empty_review_artifacts(
    tmp_path: Path,
) -> None:
    diagnostics_tsv = tmp_path / "selected_envelope_diagnostics.tsv"
    _write_tsv(
        diagnostics_tsv,
        [
            _diagnostic_row(
                selected_candidate_id="candidate-001",
                boundary_change_class="no_change",
                row_boundary_decision="accept_candidate",
            ),
        ],
    )

    outputs, result = run_selected_envelope_review_queue(
        selected_envelope_diagnostics_tsv=diagnostics_tsv,
        output_dir=tmp_path / "review",
    )

    assert result.changed_row_count == 0
    assert _read_tsv(outputs.changed_rows_tsv) == []
    assert _read_tsv(outputs.oracle_review_queue_tsv) == []
    assert _read_tsv(outputs.diagnostic_manifest_tsv)[0]["gate_decision"] == "promote"


def test_selected_envelope_review_queue_cli_returns_zero(tmp_path: Path) -> None:
    diagnostics_tsv = tmp_path / "selected_envelope_diagnostics.tsv"
    _write_tsv(
        diagnostics_tsv,
        [_diagnostic_row(selected_candidate_id="candidate-001")],
    )

    code = main(
        [
            "--selected-envelope-diagnostics-tsv",
            str(diagnostics_tsv),
            "--output-dir",
            str(tmp_path / "review"),
        ]
    )

    assert code == 0
    assert (tmp_path / "review" / "selected_envelope_review_queue.json").exists()


def test_selected_envelope_review_queue_cli_fails_on_missing_columns(
    tmp_path: Path,
) -> None:
    diagnostics_tsv = tmp_path / "bad.tsv"
    _write_tsv(diagnostics_tsv, [{"sample_name": "sample-a"}])

    code = main(
        [
            "--selected-envelope-diagnostics-tsv",
            str(diagnostics_tsv),
            "--output-dir",
            str(tmp_path / "review"),
        ]
    )

    assert code == 2


def _diagnostic_row(
    *,
    sample_name: str = "sample-a",
    target_label: str = "5-medC",
    selected_candidate_id: str = "candidate-001",
    boundary_change_class: str = "flank_recovered",
    row_boundary_decision: str = "accept_candidate",
    boundary_stop_reason: str = "baseline_return_reached",
) -> dict[str, str]:
    row = {header: "" for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS}
    row.update(
        {
            "sample_name": sample_name,
            "target_label": target_label,
            "role": "Analyte",
            "selected_candidate_id": selected_candidate_id,
            "selected_boundary_mode": "selected_full_envelope",
            "row_boundary_decision": row_boundary_decision,
            "legacy_resolver_provenance": "local_minimum",
            "resolver_rt_start": "4.00000",
            "resolver_rt_end": "6.00000",
            "envelope_rt_start": "2.00000",
            "envelope_rt_end": "8.00000",
            "quantitation_context_rt_start": "0.00000",
            "quantitation_context_rt_end": "10.00000",
            "boundary_change_class": boundary_change_class,
            "boundary_stop_reason": boundary_stop_reason,
            "asls_area_old_interval": "100.00",
            "asls_area_selected_envelope": "160.00",
            "area_delta_ratio": "0.60000",
        }
    )
    return row


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
