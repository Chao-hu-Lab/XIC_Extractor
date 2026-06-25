from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.instrument_qc_biological_istd_rt_envelope import main
from xic_extractor.instrument_qc.biological_istd_rt_envelope import (
    BiologicalIstdRtInputRow,
    build_biological_istd_rt_envelope,
)
from xic_extractor.instrument_qc.biological_istd_rt_envelope_io import (
    build_biological_istd_rt_envelope_from_files,
)


def test_stable_istd_with_large_raw_drift_can_define_normal_residual_envelope() -> None:
    rows = tuple(
        BiologicalIstdRtInputRow(
            sample_name=f"QC{idx}",
            injection_order=float(order),
            target_label="d3-N6-medA",
            rt_min=24.0 + 0.02 * order + wiggle,
            area=1_000_000.0,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="",
        )
        for idx, (order, wiggle) in enumerate(
            [(1, 0.00), (20, 0.03), (40, -0.02), (60, 0.00), (80, 0.02)],
            start=1,
        )
    )

    result = build_biological_istd_rt_envelope(rows)

    target = result.targets[0]
    assert result.run_verdict == "rt_envelope_ready"
    assert target.anchor_status == "stable_istd_anchor"
    assert target.high_raw_drift is True
    assert target.p95_abs_residual_min is not None
    assert target.p95_abs_residual_min < 0.05
    assert {row.envelope_status for row in result.rows} == {"inside_normal_envelope"}


def test_non_benchmark_rows_do_not_define_stable_anchor() -> None:
    rows = tuple(
        BiologicalIstdRtInputRow(
            sample_name=f"QC{idx}",
            injection_order=float(idx),
            target_label="bad-anchor",
            rt_min=10.0 + idx * 0.01,
            area=None,
            confidence="LOW",
            reliability_state="targeted_review_positive",
            risk_reasons="",
        )
        for idx in range(1, 7)
    )

    result = build_biological_istd_rt_envelope(rows)

    assert result.run_verdict == "no_stable_istd_anchor"
    assert result.targets[0].anchor_status == "insufficient_points"
    assert {row.envelope_status for row in result.rows} == {"anchor_not_stable"}


def test_hard_risk_row_excludes_target_from_stable_anchor() -> None:
    rows = [
        BiologicalIstdRtInputRow(
            sample_name=f"QC{idx}",
            injection_order=float(idx),
            target_label="risky-anchor",
            rt_min=10.0 + idx * 0.01,
            area=None,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="wrong_peak" if idx == 1 else "",
        )
        for idx in range(1, 7)
    ]

    result = build_biological_istd_rt_envelope(tuple(rows))

    assert result.run_verdict == "no_stable_istd_anchor"
    assert result.targets[0].anchor_status == "hard_risk_excluded"
    by_sample = {row.sample_name: row for row in result.rows}
    assert by_sample["QC1"].envelope_status == "hard_risk_excluded"
    assert by_sample["QC1"].predicted_rt_min is None
    assert by_sample["QC2"].envelope_status == "anchor_not_stable"


def test_outlier_row_is_labeled_outside_envelope() -> None:
    rows = [
        BiologicalIstdRtInputRow(
            sample_name=f"QC{idx}",
            injection_order=float(idx),
            target_label="stable",
            rt_min=10.0 + idx * 0.01,
            area=None,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="",
        )
        for idx in range(1, 7)
    ]
    rows.append(
        BiologicalIstdRtInputRow(
            sample_name="QC7",
            injection_order=7.0,
            target_label="stable",
            rt_min=10.8,
            area=None,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="",
        )
    )

    result = build_biological_istd_rt_envelope(tuple(rows))

    by_sample = {row.sample_name: row for row in result.rows}
    assert by_sample["QC7"].envelope_status == "outside_envelope"


def test_duplicate_sample_names_keep_row_specific_residuals() -> None:
    rows = (
        BiologicalIstdRtInputRow(
            sample_name="QC1",
            injection_order=1.0,
            target_label="stable",
            rt_min=10.01,
            area=None,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="",
        ),
        BiologicalIstdRtInputRow(
            sample_name="QC1",
            injection_order=2.0,
            target_label="stable",
            rt_min=10.02,
            area=None,
            confidence="HIGH",
            reliability_state="benchmark_eligible",
            risk_reasons="",
        ),
        *tuple(
            BiologicalIstdRtInputRow(
                sample_name=f"QC{idx}",
                injection_order=float(idx),
                target_label="stable",
                rt_min=10.0 + idx * 0.01,
                area=None,
                confidence="HIGH",
                reliability_state="benchmark_eligible",
                risk_reasons="",
            )
            for idx in range(3, 7)
        ),
    )

    result = build_biological_istd_rt_envelope(rows)

    assert result.run_verdict == "rt_envelope_ready"
    assert [row.predicted_rt_min for row in result.rows[:2]] == [10.01, 10.02]


def test_loader_and_cli_write_outputs(tmp_path: Path) -> None:
    input_tsv = tmp_path / "biological_qc_istd_drift_rows.tsv"
    _write_rows(
        input_tsv,
        [
            {
                "sample_name": f"QC{idx}",
                "injection_order": str(idx),
                "target_label": "stable",
                "rt_min": str(10.0 + idx * 0.01),
                "area": "1000",
                "confidence": "HIGH",
                "reliability_state": "benchmark_eligible",
                "risk_reasons": "",
            }
            for idx in range(1, 7)
        ],
    )

    loaded = build_biological_istd_rt_envelope_from_files(
        biological_istd_rows_tsv=input_tsv,
    )
    assert loaded.run_verdict == "rt_envelope_ready"

    output_dir = tmp_path / "out"
    exit_code = main(
        [
            "--biological-istd-rows-tsv",
            str(input_tsv),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0
    summary = json.loads(
        (output_dir / "biological_istd_rt_envelope.json").read_text(encoding="utf-8")
    )
    assert summary["run_verdict"] == "rt_envelope_ready"
    assert (output_dir / "biological_istd_rt_envelope_rows.tsv").exists()
    assert (output_dir / "biological_istd_rt_envelope_targets.tsv").exists()


def test_missing_required_columns_fail_clearly(tmp_path: Path) -> None:
    input_tsv = tmp_path / "bad.tsv"
    _write_rows(input_tsv, [{"sample_name": "QC1"}])

    try:
        build_biological_istd_rt_envelope_from_files(
            biological_istd_rows_tsv=input_tsv,
        )
    except ValueError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("Expected missing required column error.")


def test_invalid_numeric_input_fails_clearly(tmp_path: Path) -> None:
    input_tsv = tmp_path / "bad_numeric.tsv"
    _write_rows(
        input_tsv,
        [
            {
                "sample_name": "QC1",
                "injection_order": "not-a-number",
                "target_label": "stable",
                "rt_min": "10.1",
                "reliability_state": "benchmark_eligible",
            }
        ],
    )

    exit_code = main(
        [
            "--biological-istd-rows-tsv",
            str(input_tsv),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 2


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    columns = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
