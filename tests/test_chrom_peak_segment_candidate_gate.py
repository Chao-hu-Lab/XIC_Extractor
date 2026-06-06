from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.chrom_peak_segment_candidate_gate import (
    build_gate_report,
    main,
)


def test_gate_report_summarizes_chrom_selected_area_changes() -> None:
    baseline = [
        _candidate_row(
            selected=True,
            sources="local_minimum",
            area="100",
            left="12.1",
            right="12.2",
            confidence="HIGH",
        )
    ]
    current = [
        _candidate_row(
            selected=True,
            sources="local_minimum;chrom_peak_segment",
            area="120",
            left="12.0",
            right="12.3",
            confidence="HIGH",
        ),
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason="decision: review only, not counted",
            role="Analyte",
        ),
    ]
    selected_envelope = [
        {
            "row_boundary_decision": "externalize",
            "boundary_change_class": "overmerge_rejected",
        }
    ]

    manifest, changed_rows, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=baseline,
        selected_envelope_rows=selected_envelope,
    )

    assert manifest["gate_decision"] == "defer"
    assert manifest["boundary_gate_decision"] == "promote"
    assert manifest["presence_gate_decision"] == "defer"
    assert manifest["selected_chrom_count"] == 2
    assert manifest["selected_chrom_by_role"] == {"Analyte": 1, "ISTD": 1}
    assert manifest["selected_chrom_by_confidence"] == {
        "HIGH": 1,
        "VERY_LOW": 1,
    }
    assert manifest["selected_area_changed_count"] == 1
    assert manifest["selected_area_increased_count"] == 1
    assert manifest["selected_area_decreased_count"] == 0
    assert manifest["selected_envelope_externalize_count"] == 1
    assert "selected_chrom_review_only_rows_require_presence_review" in (
        manifest["presence_blocking_reasons"]
    )
    assert manifest["boundary_blocking_reasons"] == []
    assert "selected_envelope_gate_stale_for_segment_candidates" in (
        manifest["advisory_reasons"]
    )
    assert manifest["review_row_count"] == 1
    assert manifest["review_rows_by_reason"] == {
        "selected_chrom_review_only": 1
    }
    assert changed_rows == [
        {
            "sample_name": "SampleA",
            "target_label": "TargetA",
            "role": "ISTD",
            "old_proposal_sources": "local_minimum",
            "new_proposal_sources": "local_minimum;chrom_peak_segment",
            "old_area_raw_counts_seconds": "100",
            "new_area_raw_counts_seconds": "120",
            "delta_ratio": "0.2",
            "old_rt_left_min": "12.1",
            "old_rt_right_min": "12.2",
            "new_rt_left_min": "12.0",
            "new_rt_right_min": "12.3",
            "selection_reference_rt_min": "",
            "old_rt_reference_delta_min": "",
            "new_rt_reference_delta_min": "",
            "area_change_class": "increase",
            "new_confidence": "HIGH",
        }
    ]
    assert review_rows[0]["sample_name"] == "SampleB"
    assert review_rows[0]["review_reason"] == "selected_chrom_review_only"
    assert review_rows[0]["confidence"] == "VERY_LOW"
    assert review_rows[0]["selected_envelope_decision"] == ""


def test_gate_report_flags_selected_area_decrease() -> None:
    baseline = [
        _candidate_row(
            selected=True,
            sources="local_minimum",
            area="100",
        )
    ]
    current = [
        _candidate_row(
            selected=True,
            sources="local_minimum;chrom_peak_segment",
            area="80",
        )
    ]

    manifest, changed_rows, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=baseline,
    )

    assert manifest["selected_area_decreased_count"] == 1
    assert manifest["max_selected_area_decrease_ratio"] == -0.2
    assert "selected_area_decrease_review_required" in (
        manifest["boundary_blocking_reasons"]
    )
    assert manifest["boundary_gate_decision"] == "defer"
    assert manifest["presence_gate_decision"] == "promote"
    assert changed_rows[0]["delta_ratio"] == "-0.2"
    assert review_rows == []


def test_gate_report_treats_rt_corrective_area_decrease_as_advisory() -> None:
    baseline = [
        _candidate_row(
            selected=True,
            sources="chrom_peak_segment;centwave_cwt",
            area="1000",
            left="16.9",
            apex="17.2",
            right="17.6",
            selection_reference_rt="16.35",
        )
    ]
    current = [
        _candidate_row(
            selected=True,
            sources="local_minimum;chrom_peak_segment;centwave_cwt",
            area="50",
            left="16.1",
            apex="16.4",
            right="16.7",
            selection_reference_rt="16.35",
        )
    ]

    manifest, changed_rows, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=baseline,
    )

    assert manifest["selected_area_decreased_count"] == 1
    assert manifest["selected_rt_corrective_area_decrease_count"] == 1
    assert "selected_area_decrease_review_required" not in (
        manifest["boundary_blocking_reasons"]
    )
    assert "selected_area_decrease_rt_reference_corrective" in (
        manifest["advisory_reasons"]
    )
    assert manifest["boundary_gate_decision"] == "promote"
    assert changed_rows[0]["area_change_class"] == "rt_reference_corrective_decrease"
    assert changed_rows[0]["old_rt_reference_delta_min"] == "0.85"
    assert changed_rows[0]["new_rt_reference_delta_min"] == "0.05"
    assert review_rows == []


def test_gate_report_promotes_presence_after_manual_review() -> None:
    baseline = [
        _candidate_row(
            selected=True,
            sources="local_minimum",
            area="100",
        )
    ]
    current = [
        _candidate_row(
            selected=True,
            sources="local_minimum;chrom_peak_segment",
            area="120",
        ),
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason="decision: review only, not counted",
            role="Analyte",
        ),
    ]
    manual_review = [
        {
            "sample_name": "SampleB",
            "target_label": "TargetA",
            "role": "Analyte",
            "manual_presence_verdict": "accepted_review_only",
            "manual_review_basis": "manual_eic_review",
            "manual_product_action": "keep_review_only_not_counted",
            "manual_review_note": "visual review accepts selected row as non-counted",
        }
    ]

    manifest, _, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=baseline,
        manual_presence_review_rows=manual_review,
    )

    assert manifest["gate_decision"] == "promote"
    assert manifest["presence_gate_decision"] == "promote"
    assert manifest["presence_blocking_reasons"] == []
    assert manifest["manual_presence_review_missing_count"] == 0
    assert manifest["manual_presence_review_by_verdict"] == {
        "accepted_review_only": 1
    }
    assert review_rows[0]["manual_presence_verdict"] == "accepted_review_only"
    assert review_rows[0]["manual_product_action"] == "keep_review_only_not_counted"


def test_gate_report_blocks_missing_manual_presence_review_rows() -> None:
    current = [
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason="decision: review only, not counted",
            role="Analyte",
        )
    ]
    unrelated_review = [
        {
            "sample_name": "OtherSample",
            "target_label": "TargetA",
            "role": "Analyte",
            "manual_presence_verdict": "accepted_review_only",
        }
    ]

    manifest, _, _ = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        manual_presence_review_rows=unrelated_review,
    )

    assert manifest["presence_gate_decision"] == "defer"
    assert "manual_presence_review_missing_rows" in (
        manifest["presence_blocking_reasons"]
    )
    assert manifest["manual_presence_review_missing_count"] == 1


def test_gate_report_does_not_block_typed_not_counted_review_only_rows() -> None:
    current = [
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason=(
                "decision: not_counted; evidence: chrom_peak_segment_context; "
                "missing_ms2_policy_not_counted"
            ),
            role="Analyte",
        )
    ]

    manifest, _, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
    )

    assert manifest["presence_gate_decision"] == "promote"
    assert manifest["presence_blocking_reasons"] == []
    assert manifest["manual_presence_review_missing_count"] == 0
    assert manifest["auto_noncounted_review_only_count"] == 1
    assert review_rows[0]["manual_presence_verdict"] == ""


def test_gate_report_blocks_manual_expected_peak_change_rows() -> None:
    current = [
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason="decision: review only, not counted",
            role="Analyte",
        )
    ]
    manual_review = [
        {
            "sample_name": "SampleB",
            "target_label": "TargetA",
            "role": "Analyte",
            "manual_presence_verdict": "expected_peak_change",
            "manual_review_basis": "manual_eic_review;paired_area_ratio_plausible",
            "manual_product_action": "select_alternate_chrom_segment_review_only",
        }
    ]

    manifest, _, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        manual_presence_review_rows=manual_review,
    )

    assert manifest["presence_gate_decision"] == "defer"
    assert "manual_presence_review_expected_peak_change_rows" in (
        manifest["presence_blocking_reasons"]
    )
    assert manifest["manual_presence_review_by_verdict"] == {
        "expected_peak_change": 1
    }
    assert review_rows[0]["manual_presence_verdict"] == "expected_peak_change"
    assert (
        review_rows[0]["manual_product_action"]
        == "select_alternate_chrom_segment_review_only"
    )


def test_gate_report_ignores_stale_manual_expected_peak_change_rows() -> None:
    current = [
        _candidate_row(
            sample_name="SampleB",
            selected=True,
            sources="chrom_peak_segment",
            area="50",
            confidence="VERY_LOW",
            reason="decision: review only, not counted",
            role="Analyte",
        )
    ]
    manual_review = [
        {
            "sample_name": "OldSample",
            "target_label": "TargetA",
            "role": "Analyte",
            "manual_presence_verdict": "expected_peak_change",
            "manual_product_action": "select_alternate_chrom_segment_review_only",
        },
        {
            "sample_name": "SampleB",
            "target_label": "TargetA",
            "role": "Analyte",
            "manual_presence_verdict": "accepted_review_only",
            "manual_product_action": "keep_review_only_not_counted",
        },
    ]

    manifest, _, review_rows = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        manual_presence_review_rows=manual_review,
    )

    assert manifest["presence_gate_decision"] == "promote"
    assert "manual_presence_review_expected_peak_change_rows" not in (
        manifest["presence_blocking_reasons"]
    )
    assert manifest["manual_presence_review_by_verdict"] == {
        "accepted_review_only": 1
    }
    assert review_rows[0]["manual_presence_verdict"] == "accepted_review_only"


def test_gate_report_blocks_manual_selected_envelope_boundary_extension() -> None:
    current = [
        _candidate_row(
            selected=True,
            sources="chrom_peak_segment",
            area="100",
        )
    ]
    selected_envelope = [
        _selected_envelope_row(
            selected_candidate_id="candidate-boundary-short",
            row_boundary_decision="externalize",
        )
    ]
    manual_review = [
        {
            "selected_candidate_id": "candidate-boundary-short",
            "manual_product_action": "extend_right_boundary_before_promotion",
        }
    ]

    manifest, _, _ = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        selected_envelope_rows=selected_envelope,
        manual_selected_envelope_review_rows=manual_review,
    )

    assert manifest["boundary_gate_decision"] == "defer"
    assert manifest["presence_gate_decision"] == "promote"
    assert "manual_selected_envelope_boundary_extension_rows" in (
        manifest["boundary_blocking_reasons"]
    )
    assert manifest["manual_selected_envelope_boundary_extension_count"] == 1
    assert manifest["matched_manual_selected_envelope_review_row_count"] == 1


def test_gate_report_clears_manual_boundary_extension_when_resolver_matches_review(
) -> None:
    current = [
        _candidate_row(
            selected=True,
            sources="chrom_peak_segment",
            area="100",
        )
    ]
    selected_envelope = [
        _selected_envelope_row(
            selected_candidate_id="candidate-boundary-fixed",
            row_boundary_decision="externalize",
            resolver_start="16.06619",
            resolver_end="17.17301",
        )
    ]
    manual_review = [
        {
            "selected_candidate_id": "candidate-boundary-fixed",
            "reviewed_rt_start_min": "16.06619",
            "reviewed_rt_end_min": "17.20000",
            "manual_product_action": "extend_right_boundary_before_promotion",
        }
    ]

    manifest, _, _ = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        selected_envelope_rows=selected_envelope,
        manual_selected_envelope_review_rows=manual_review,
    )

    assert manifest["boundary_gate_decision"] == "promote"
    assert "manual_selected_envelope_boundary_extension_rows" not in (
        manifest["boundary_blocking_reasons"]
    )
    assert manifest["manual_selected_envelope_boundary_extension_count"] == 0
    assert manifest["manual_selected_envelope_review_by_action"] == {
        "extend_right_boundary_before_promotion": 1
    }


def test_gate_report_blocks_manual_selected_envelope_expected_peak_change() -> None:
    current = [
        _candidate_row(
            selected=True,
            sources="chrom_peak_segment",
            area="100",
        )
    ]
    selected_envelope = [
        _selected_envelope_row(
            selected_candidate_id="candidate-late-small-peak",
            row_boundary_decision="externalize",
        )
    ]
    manual_review = [
        {
            "selected_candidate_id": "candidate-late-small-peak",
            "manual_product_action": "select_alternate_or_keep_not_counted_until_rerun",
        }
    ]

    manifest, _, _ = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        selected_envelope_rows=selected_envelope,
        manual_selected_envelope_review_rows=manual_review,
    )

    assert manifest["boundary_gate_decision"] == "promote"
    assert manifest["presence_gate_decision"] == "defer"
    assert "manual_selected_envelope_expected_peak_change_rows" in (
        manifest["presence_blocking_reasons"]
    )
    assert manifest["manual_selected_envelope_expected_peak_change_count"] == 1
    assert manifest["manual_selected_envelope_review_by_action"] == {
        "select_alternate_or_keep_not_counted_until_rerun": 1
    }


def test_gate_report_ignores_stale_manual_selected_envelope_review_rows() -> None:
    current = [
        _candidate_row(
            selected=True,
            sources="chrom_peak_segment",
            area="100",
        )
    ]
    selected_envelope = [
        _selected_envelope_row(
            selected_candidate_id="candidate-current",
            row_boundary_decision="externalize",
        )
    ]
    stale_review = [
        {
            "selected_candidate_id": "candidate-old",
            "manual_product_action": "select_alternate_or_keep_not_counted_until_rerun",
        }
    ]

    manifest, _, _ = build_gate_report(
        current,
        baseline_peak_candidate_rows=current,
        selected_envelope_rows=selected_envelope,
        manual_selected_envelope_review_rows=stale_review,
    )

    assert manifest["gate_decision"] == "promote"
    assert manifest["matched_manual_selected_envelope_review_row_count"] == 0
    assert "manual_selected_envelope_expected_peak_change_rows" not in (
        manifest["presence_blocking_reasons"]
    )


def test_cli_writes_manifest_and_changed_rows(tmp_path: Path) -> None:
    current = tmp_path / "current.tsv"
    baseline = tmp_path / "baseline.tsv"
    selected_envelope = tmp_path / "selected_envelope.tsv"
    output_dir = tmp_path / "out"
    _write_tsv(
        current,
        [
            _candidate_row(
                selected=True,
                sources="local_minimum;chrom_peak_segment",
                area="120",
            )
        ],
    )
    _write_tsv(
        baseline,
        [
            _candidate_row(
                selected=True,
                sources="local_minimum",
                area="100",
            )
        ],
    )
    _write_tsv(
        selected_envelope,
        [{"row_boundary_decision": "accept_candidate", "boundary_change_class": ""}],
    )

    exit_code = main(
        [
            "--peak-candidates-tsv",
            str(current),
            "--baseline-peak-candidates-tsv",
            str(baseline),
            "--selected-envelope-diagnostics-tsv",
            str(selected_envelope),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(
        (output_dir / "chrom_peak_segment_gate_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    changed_rows = (
        output_dir / "chrom_peak_segment_changed_rows.tsv"
    ).read_text(encoding="utf-8")
    review_rows = (
        output_dir / "chrom_peak_segment_review_rows.tsv"
    ).read_text(encoding="utf-8")
    assert manifest["selected_chrom_count"] == 1
    assert manifest["selected_area_increased_count"] == 1
    assert "SampleA" in changed_rows
    assert "review_reason" in review_rows


def _candidate_row(
    *,
    sample_name: str = "SampleA",
    target_label: str = "TargetA",
    role: str = "ISTD",
    selected: bool,
    sources: str,
    area: str,
    left: str = "12.0",
    apex: str = "12.15",
    right: str = "12.3",
    confidence: str = "HIGH",
    reason: str = "decision: accepted",
    selection_reference_rt: str = "",
) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_label": target_label,
        "role": role,
        "selected": "TRUE" if selected else "FALSE",
        "proposal_sources": sources,
        "area_raw_counts_seconds": area,
        "rt_left_min": left,
        "rt_apex_min": apex,
        "rt_right_min": right,
        "confidence": confidence,
        "reason": reason,
        "selection_reference_rt_min": selection_reference_rt,
    }


def _selected_envelope_row(
    *,
    selected_candidate_id: str,
    sample_name: str = "SampleA",
    target_label: str = "TargetA",
    role: str = "ISTD",
    row_boundary_decision: str = "accept_candidate",
    boundary_change_class: str = "",
    resolver_start: str = "",
    resolver_end: str = "",
) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_label": target_label,
        "role": role,
        "selected_candidate_id": selected_candidate_id,
        "row_boundary_decision": row_boundary_decision,
        "boundary_change_class": boundary_change_class,
        "resolver_rt_start": resolver_start,
        "resolver_rt_end": resolver_end,
    }


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0])
    lines = ["\t".join(fieldnames)]
    lines.extend("\t".join(row.get(field, "") for field in fieldnames) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
