from pathlib import Path

import pytest

from tools.diagnostics.build_target_pair_expected_diff_approval_registry import (
    build_expected_diff_approval_registry_rows,
    main,
)
from xic_extractor.peak_detection.model_selection import expected_diff_stable_row_id
from xic_extractor.peak_detection.model_selection_approval_registry import (
    load_expected_diff_approval_registry,
)


def test_build_expected_diff_approval_registry_from_explicit_row() -> None:
    review = _review_row(
        sample_name="BenignfatBC1055_DNA",
        target_label="8-oxodG",
        previous_candidate_id="legacy",
        selected_candidate_id="successor",
    )

    rows = build_expected_diff_approval_registry_rows(
        [review],
        approved_rows=[("BenignfatBC1055_DNA", "8-oxodG")],
    )

    assert rows == [
        {
            "stable_row_id": expected_diff_stable_row_id(
                legacy_selected_candidate_id="legacy",
                successor_selected_candidate_id="successor",
            ),
            "sample_name": "BenignfatBC1055_DNA",
            "target_label": "8-oxodG",
            "legacy_selected_candidate_id": "legacy",
            "successor_selected_candidate_id": "successor",
            "final_label": "expected_diff",
            "reviewer_verdict": "approved",
            "validation_tier": "manual_eic_ms2_review",
            "public_outputs_touched": (
                "candidate table selected marker;selected rt;area;boundary;"
                "confidence;reason;final matrix value"
            ),
            "matrix_value_impact": "area_value_changed",
            "evidence_sources": (
                "ms1_trace;role_aware_rt;paired_area_ratio;manual_eic_review"
            ),
            "evidence_summary": (
                "Manual EIC review approved target-pair expected-diff switch. "
                "RT 16.38663 -> 17.13547. Paired ISTD RT 16.42828. "
                "Paired area ratio 0.49834 (within_reference_range). "
                "MS2/NL state recorded as contradicted, not standalone authority. "
                "Review reasons: ms2_nl_contradicted;"
                "row_specific_expected_diff_required."
            ),
            "reviewer_role": "mass_spectrometry_reviewer",
        }
    ]


def test_approval_registry_tool_writes_loadable_registry(tmp_path: Path) -> None:
    review_path = tmp_path / "target_pair_rt_auto_reselection.tsv"
    output_path = tmp_path / "expected_diff_approvals.tsv"
    _write_review_tsv(
        review_path,
        [
            _review_row(
                sample_name="BenignfatBC1055_DNA",
                target_label="8-oxodG",
                previous_candidate_id="legacy",
                selected_candidate_id="successor",
            ),
            _review_row(
                sample_name="OtherSample",
                target_label="8-oxodG",
                previous_candidate_id="legacy-other",
                selected_candidate_id="successor-other",
            ),
        ],
    )

    exit_code = main(
        [
            "--target-pair-review-tsv",
            str(review_path),
            "--output",
            str(output_path),
            "--approved-row",
            "BenignfatBC1055_DNA::8-oxodG",
        ]
    )

    assert exit_code == 0
    approvals = load_expected_diff_approval_registry(output_path)
    assert tuple(approvals) == (
        expected_diff_stable_row_id(
            legacy_selected_candidate_id="legacy",
            successor_selected_candidate_id="successor",
        ),
    )
    approval = next(iter(approvals.values()))
    assert approval.sample_name == "BenignfatBC1055_DNA"
    assert approval.target_label == "8-oxodG"
    assert approval.matrix_value_impact == "area_value_changed"
    assert "manual_eic_review" in approval.evidence_sources


def test_approval_registry_tool_rejects_false_positive_review_row(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    review_path = tmp_path / "target_pair_rt_auto_reselection.tsv"
    output_path = tmp_path / "expected_diff_approvals.tsv"
    _write_review_tsv(
        review_path,
        [
            _review_row(
                sample_name="BenignfatBC1055_DNA",
                target_label="8-oxodG",
                previous_candidate_id="legacy",
                selected_candidate_id="successor",
                false_positive_review_status="false_positive_review_required",
            )
        ],
    )

    exit_code = main(
        [
            "--target-pair-review-tsv",
            str(review_path),
            "--output",
            str(output_path),
            "--approved-row",
            "BenignfatBC1055_DNA::8-oxodG",
        ]
    )

    assert exit_code == 2
    assert "row_approval_candidate" in capsys.readouterr().err
    assert not output_path.exists()


def test_approval_registry_tool_rejects_stable_row_mismatch() -> None:
    row = _review_row(
        sample_name="BenignfatBC1055_DNA",
        target_label="8-oxodG",
        previous_candidate_id="legacy",
        selected_candidate_id="successor",
    )
    row["expected_diff_stable_row_id"] = "wrong"

    with pytest.raises(ValueError, match="stable_row_id mismatch"):
        build_expected_diff_approval_registry_rows(
            [row],
            approved_rows=[("BenignfatBC1055_DNA", "8-oxodG")],
        )


def _write_review_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    headers = tuple(rows[0])
    path.write_text(
        "\t".join(headers)
        + "\n"
        + "\n".join("\t".join(row[header] for header in headers) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def _review_row(
    *,
    sample_name: str,
    target_label: str,
    previous_candidate_id: str,
    selected_candidate_id: str,
    false_positive_review_status: str = "row_approval_candidate",
) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_label": target_label,
        "previous_candidate_id": previous_candidate_id,
        "selected_candidate_id": selected_candidate_id,
        "selection_action": "shadow_auto_reselect_proposed",
        "selection_basis": "paired_rt_biological_high_confidence",
        "selection_status": "expected_diff",
        "expected_diff_stable_row_id": expected_diff_stable_row_id(
            legacy_selected_candidate_id=previous_candidate_id,
            successor_selected_candidate_id=selected_candidate_id,
        ),
        "evidence_comparison_policy": "limited_evidence_shadow",
        "previous_candidate_rt": "16.38663",
        "selected_candidate_rt": "17.13547",
        "paired_istd_rt": "16.42828",
        "paired_area_ratio_observed": "0.49834",
        "paired_area_ratio_status": "within_reference_range",
        "missing_ms2_explanation": "contradicted",
        "false_positive_review_status": false_positive_review_status,
        "false_positive_review_reasons": (
            "ms2_nl_contradicted;row_specific_expected_diff_required"
        ),
    }
