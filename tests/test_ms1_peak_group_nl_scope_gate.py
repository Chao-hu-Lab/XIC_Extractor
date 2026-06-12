from __future__ import annotations

import json

import pytest

from tools.diagnostics.ms1_peak_group_nl_scope_gate import (
    _write_tsv as _write_gate_tsv,
)
from tools.diagnostics.ms1_peak_group_nl_scope_gate import (
    build_gate_report,
    main,
)


def test_gate_promotes_when_selected_chrom_nl_support_is_group_scoped() -> None:
    rows = [
        _row(
            selected=True,
            ms2_present="TRUE",
            nl_match="TRUE",
            strict_nl_scan_count="2",
            ms1_group_strict_nl_scan_count="2",
            ms1_group_strict_nl_event_count="1",
        ),
        _row(
            selected=False,
            candidate_id="SampleA|TargetA|Analyte|candidate-2",
            ms2_present="TRUE",
            nl_match="TRUE",
            strict_nl_scan_count="1",
            ms1_group_strict_nl_scan_count="1",
            ms1_group_strict_nl_event_count="1",
        ),
    ]

    manifest, review_rows, context_rows = build_gate_report(rows)

    assert manifest["gate_decision"] == "promote"
    assert manifest["blocking_reasons"] == []
    assert manifest["selected_chrom_peak_group_rows"] == 1
    assert manifest["selected_chrom_peak_group_strict_nl_scan_count"] == 2
    assert manifest["selected_chrom_peak_group_strict_nl_event_count"] == 1
    assert manifest["selected_chrom_repeated_strict_nl_scan_rows"] == 1
    assert review_rows == []
    assert context_rows == []


def test_gate_blocks_borrowed_strict_nl_outside_selected_ms1_group() -> None:
    rows = [
        _row(
            selected=True,
            ms2_present="TRUE",
            nl_match="TRUE",
            nl_status="STRICT_MATCH",
            strict_nl_scan_count="1",
            ms1_group_strict_nl_scan_count="0",
            ms1_group_strict_nl_event_count="0",
            outside_strict_nl_scan_count="1",
        )
    ]

    manifest, review_rows, context_rows = build_gate_report(rows)

    assert manifest["gate_decision"] == "defer"
    assert "borrowed_strict_nl_support_outside_ms1_peak_group" in (
        manifest["blocking_reasons"]
    )
    assert manifest["borrowed_strict_nl_support_rows"] == 1
    assert review_rows[0]["review_reason"] == (
        "borrowed_strict_nl_support_outside_ms1_peak_group"
    )
    assert review_rows[0]["best_ms2_scan_rt_min"] == "16.7"
    assert context_rows[0]["context_reason"] == "outside_strict_nl_observed"


def test_gate_blocks_selected_chrom_rows_missing_group_scope() -> None:
    rows = [
        _row(
            selected=True,
            ms1_group_source="",
            ms1_group_rt_min="",
            ms1_group_rt_max="",
        )
    ]

    manifest, review_rows, context_rows = build_gate_report(rows)

    assert manifest["gate_decision"] == "defer"
    assert "selected_chrom_peak_segment_missing_ms1_peak_group_scope" in (
        manifest["blocking_reasons"]
    )
    assert manifest["selected_chrom_missing_scope_rows"] == 1
    assert review_rows[0]["review_reason"] == (
        "selected_chrom_peak_segment_missing_ms1_peak_group_scope"
    )
    assert context_rows == []


def test_gate_blocks_unexpected_ms1_peak_group_source() -> None:
    rows = [
        _row(
            selected=True,
            ms1_group_source="legacy_window",
        )
    ]

    manifest, review_rows, _ = build_gate_report(rows)

    assert manifest["gate_decision"] == "defer"
    assert "unexpected_ms1_peak_group_source" in manifest["blocking_reasons"]
    assert manifest["unexpected_ms1_peak_group_source_rows"] == 1
    assert review_rows[0]["review_reason"] == "unexpected_ms1_peak_group_source"


def test_gate_blocks_selected_apex_outside_ms1_peak_group() -> None:
    rows = [
        _row(
            selected=True,
            rt_apex_min="17.5",
            ms1_group_rt_min="16.4",
            ms1_group_rt_max="17.2",
        )
    ]

    manifest, review_rows, _ = build_gate_report(rows)

    assert manifest["gate_decision"] == "defer"
    assert "selected_apex_outside_ms1_peak_group_scope" in (
        manifest["blocking_reasons"]
    )
    assert manifest["selected_apex_outside_scope_rows"] == 1
    assert review_rows[0]["review_reason"] == (
        "selected_apex_outside_ms1_peak_group_scope"
    )


def test_gate_writes_nonblocking_context_for_outside_strict_nl() -> None:
    rows = [
        _row(
            selected=True,
            ms2_present="TRUE",
            nl_match="TRUE",
            nl_status="OK",
            strict_nl_scan_count="3",
            ms1_group_strict_nl_scan_count="3",
            ms1_group_strict_nl_event_count="1",
            outside_strict_nl_scan_count="2",
            best_ms2_scan_rt_min="16.8",
        )
    ]

    manifest, review_rows, context_rows = build_gate_report(rows)

    assert manifest["gate_decision"] == "promote"
    assert review_rows == []
    assert context_rows == [
        {
            "sample_name": "SampleA",
            "target_label": "TargetA",
            "role": "Analyte",
            "candidate_id": "SampleA|TargetA|Analyte|candidate-1",
            "context_reason": "outside_strict_nl_observed",
            "selected": "TRUE",
            "proposal_sources": "chrom_peak_segment",
            "rt_left_min": "16.2",
            "rt_apex_min": "16.8",
            "rt_right_min": "17.3",
            "best_ms2_scan_rt_min": "16.8",
            "apex_ms2_delta_min": "0.0",
            "ms2_present": "TRUE",
            "nl_match": "TRUE",
            "nl_status": "OK",
            "strict_nl_scan_count": "3",
            "ms1_peak_group_source": "gaussian15_ms1_peak_group",
            "ms1_peak_group_rt_min": "16.4",
            "ms1_peak_group_rt_max": "17.2",
            "ms1_peak_group_trigger_scan_count": "0",
            "ms1_peak_group_strict_nl_scan_count": "3",
            "ms1_peak_group_strict_nl_event_count": "1",
            "outside_ms1_peak_group_trigger_scan_count": "0",
            "outside_ms1_peak_group_strict_nl_scan_count": "2",
            "diagnostic_product_absence_reason": "",
            "confidence": "HIGH",
            "reason": "decision: selected",
        }
    ]


def test_gate_blocks_when_required_columns_are_missing() -> None:
    manifest, review_rows, context_rows = build_gate_report(
        [{"sample_name": "SampleA"}]
    )

    assert manifest["gate_decision"] == "defer"
    assert "missing_required_columns" in manifest["blocking_reasons"]
    assert "ms1_peak_group_source" in manifest["missing_required_columns"]
    assert review_rows == []
    assert context_rows == []


def test_gate_cli_writes_manifest_and_review_rows(tmp_path) -> None:
    input_path = tmp_path / "peak_candidates.tsv"
    output_dir = tmp_path / "gate"
    input_path.write_text(
        "\t".join(_headers()) + "\n"
        + "\t".join(
            _row(
                selected=True,
                ms2_present="TRUE",
                nl_match="TRUE",
                strict_nl_scan_count="1",
                ms1_group_strict_nl_scan_count="0",
                ms1_group_strict_nl_event_count="0",
                outside_strict_nl_scan_count="1",
            )[header]
            for header in _headers()
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(
        [
            "--peak-candidates-tsv",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ]
    ) == 1

    manifest = json.loads(
        (output_dir / "ms1_peak_group_nl_scope_gate_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["gate_decision"] == "defer"
    assert (output_dir / "ms1_peak_group_nl_scope_review_rows.tsv").exists()
    assert (output_dir / "ms1_peak_group_nl_scope_context_rows.tsv").exists()


def test_gate_writer_preserves_explicit_field_contract(tmp_path) -> None:
    path = tmp_path / "rows.tsv"

    _write_gate_tsv(
        path,
        [{"flag": True, "empty": None, "count": 1}],
        ("flag", "empty", "count"),
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "flag\tempty\tcount",
        "True\t\t1",
    ]

    empty_path = tmp_path / "empty.tsv"
    _write_gate_tsv(empty_path, [], ("flag", "empty"))
    assert empty_path.read_text(encoding="utf-8").splitlines() == [
        "flag\tempty",
    ]

    with pytest.raises(ValueError, match="dict contains fields not in fieldnames"):
        _write_gate_tsv(
            tmp_path / "extra.tsv",
            [{"flag": "TRUE", "unexpected": "value"}],
            ("flag",),
        )


def _row(
    *,
    sample_name: str = "SampleA",
    target_label: str = "TargetA",
    role: str = "Analyte",
    candidate_id: str = "SampleA|TargetA|Analyte|candidate-1",
    selected: bool = False,
    proposal_sources: str = "chrom_peak_segment",
    rt_left_min: str = "16.2",
    rt_apex_min: str = "16.8",
    rt_right_min: str = "17.3",
    best_ms2_scan_rt_min: str = "16.7",
    apex_ms2_delta_min: str = "0.0",
    ms2_present: str = "FALSE",
    nl_match: str = "FALSE",
    nl_status: str = "NO_MS2",
    strict_nl_scan_count: str = "0",
    ms1_group_source: str = "gaussian15_ms1_peak_group",
    ms1_group_rt_min: str = "16.4",
    ms1_group_rt_max: str = "17.2",
    ms1_group_trigger_scan_count: str = "0",
    ms1_group_strict_nl_scan_count: str = "0",
    ms1_group_strict_nl_event_count: str = "0",
    outside_trigger_scan_count: str = "0",
    outside_strict_nl_scan_count: str = "0",
    diagnostic_product_absence_reason: str = "",
    confidence: str = "HIGH",
    reason: str = "decision: selected",
) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_label": target_label,
        "role": role,
        "candidate_id": candidate_id,
        "selected": "TRUE" if selected else "FALSE",
        "proposal_sources": proposal_sources,
        "rt_left_min": rt_left_min,
        "rt_apex_min": rt_apex_min,
        "rt_right_min": rt_right_min,
        "best_ms2_scan_rt_min": best_ms2_scan_rt_min,
        "apex_ms2_delta_min": apex_ms2_delta_min,
        "ms2_present": ms2_present,
        "nl_match": nl_match,
        "nl_status": nl_status,
        "strict_nl_scan_count": strict_nl_scan_count,
        "ms1_peak_group_source": ms1_group_source,
        "ms1_peak_group_rt_min": ms1_group_rt_min,
        "ms1_peak_group_rt_max": ms1_group_rt_max,
        "ms1_peak_group_trigger_scan_count": ms1_group_trigger_scan_count,
        "ms1_peak_group_strict_nl_scan_count": ms1_group_strict_nl_scan_count,
        "ms1_peak_group_strict_nl_event_count": ms1_group_strict_nl_event_count,
        "outside_ms1_peak_group_trigger_scan_count": outside_trigger_scan_count,
        "outside_ms1_peak_group_strict_nl_scan_count": (
            outside_strict_nl_scan_count
        ),
        "diagnostic_product_absence_reason": diagnostic_product_absence_reason,
        "confidence": confidence,
        "reason": reason,
    }


def _headers() -> list[str]:
    return list(_row().keys())
