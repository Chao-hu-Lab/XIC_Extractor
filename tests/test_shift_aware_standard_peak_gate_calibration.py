from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics import shift_aware_standard_peak_gate_calibration as gate


def test_gate_uses_shift_aware_support_plus_overlay_family_verdict(
    tmp_path: Path,
) -> None:
    manual_pack = tmp_path / "manual_pack.tsv"
    _write_tsv(
        manual_pack,
        [
            _row("1", "FAM001", "ms1_shape_supports_family_backfill", "standard_peak"),
            _row(
                "2",
                "FAM002",
                "review_required_neighboring_ms1_interference",
                "non_standard_peak",
            ),
            _row(
                "3",
                "FAM003",
                "ms1_shape_supports_family_backfill",
                "non_standard_peak",
            ),
            _row(
                "4",
                "FAM004",
                "review_required_neighboring_ms1_interference",
                "standard_peak",
            ),
        ],
    )

    rows, summary = gate.evaluate_standard_peak_gate(manual_pack)

    assert [row["standard_peak_gate_call"] for row in rows] == [
        "standard_peak_gate_supported",
        "standard_peak_gate_blocked",
        "standard_peak_gate_supported",
        "standard_peak_gate_blocked",
    ]
    assert [row["calibration_outcome"] for row in rows] == [
        "true_positive",
        "true_negative",
        "false_positive",
        "false_negative",
    ]
    assert summary["row_count"] == 4
    assert summary["true_positive_count"] == 1
    assert summary["false_positive_count"] == 1
    assert summary["false_negative_count"] == 1
    assert summary["precision"] == 0.5
    assert summary["recall"] == 0.5


def test_unlabeled_machine_supported_rows_are_not_false_positives(
    tmp_path: Path,
) -> None:
    manual_pack = tmp_path / "manual_pack.tsv"
    _write_tsv(
        manual_pack,
        [
            {
                **_row(
                    "1",
                    "FAM001",
                    "ms1_shape_supports_family_backfill",
                    "",
                ),
                "manual_backfill_authority_call": "",
            },
            {
                **_row(
                    "2",
                    "FAM002",
                    "review_required_neighboring_ms1_interference",
                    "",
                ),
                "manual_backfill_authority_call": "",
            },
        ],
    )

    rows, summary = gate.evaluate_standard_peak_gate(manual_pack)

    assert [row["calibration_outcome"] for row in rows] == [
        "unlabeled_machine_supported",
        "unlabeled_machine_blocked",
    ]
    assert summary["manual_positive_count"] == 0
    assert summary["manual_negative_count"] == 0
    assert summary["unlabeled_count"] == 2
    assert summary["false_positive_count"] == 0
    assert summary["unlabeled_machine_supported_count"] == 1
    assert summary["unlabeled_machine_blocked_count"] == 1
    assert summary["precision"] is None
    assert summary["recall"] is None


def test_cli_writes_gate_calibration_outputs(tmp_path: Path) -> None:
    manual_pack = tmp_path / "manual_pack.tsv"
    _write_tsv(
        manual_pack,
        [
            _row("1", "FAM001", "ms1_shape_supports_family_backfill", "standard_peak"),
            _row(
                "2",
                "FAM002",
                "review_required_neighboring_ms1_interference",
                "non_standard_peak",
            ),
        ],
    )
    output_dir = tmp_path / "out"

    assert (
        gate.main(
            [
                "--manual-pack-tsv",
                str(manual_pack),
                "--output-dir",
                str(output_dir),
            ],
        )
        == 0
    )

    rows_tsv = output_dir / "shift_aware_standard_peak_gate_calibration.tsv"
    summary_json = (
        output_dir / "shift_aware_standard_peak_gate_calibration_summary.json"
    )
    assert rows_tsv.exists()
    assert summary_json.exists()
    assert "standard_peak_gate_supported" in rows_tsv.read_text(encoding="utf-8")
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["precision"] == 1.0
    assert summary["recall"] == 1.0
    assert summary["validation_label"] == "diagnostic_only"


def _row(
    rank: str,
    family: str,
    family_verdict: str,
    manual_standard_peak_call: str,
) -> dict[str, str]:
    authority = (
        "authorize_standard_peak_backfill"
        if manual_standard_peak_call == "standard_peak"
        else "reject_non_standard_peak"
    )
    return {
        "review_rank": rank,
        "feature_family_id": family,
        "machine_shift_aware_call": "shift_aware_same_pattern_support_review_only",
        "manual_same_peak_call": "",
        "manual_standard_peak_call": manual_standard_peak_call,
        "manual_backfill_authority_call": authority,
        "manual_notes": "",
        "nonref_source_families": f"{family}A",
        "nonref_group_count": "1",
        "min_shape_r_after_best_shift": "0.99",
        "max_shape_r_after_best_shift": "0.99",
        "max_abs_shift_sec": "1.0",
        "family_verdict": family_verdict,
        "top_blocker": "",
        "missing_evidence": "",
    }


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
