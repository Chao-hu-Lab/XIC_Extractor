from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.production_candidate_gate import (
    PRODUCTION_CANDIDATE_GATE_COLUMNS,
    evaluate_production_candidate_gate,
    production_candidate_gate_as_row,
    source_context_for_artifacts,
    summarize_gate_decisions,
)


def test_retention_candidate_with_explicit_independent_tier2_support_tracks_candidate(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags=(
                "single_detected_seed;provisional_retention_candidate;"
                "skip_expensive_evidence"
            ),
            detected=1,
            rescued=2,
            independent_support="validated_tier2_trace_evidence",
        ),
        _cell_rows(detected=1, rescued=2),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "production_candidate"
    assert decision.recommended_action == "track_candidate"
    assert decision.evidence_tier == 2
    assert decision.support_components == ("validated_tier2_trace_evidence",)
    assert decision.dependent_context == (
        "owner_backfill_context",
        "family_ms1_context",
        "rescued_cell_scan_support_distribution",
        "selected_boundary_local_apex_consistency",
        "rescued_cell_rt_coherence",
    )
    assert decision.challenge_blockers == ()
    assert decision.tier2_evidence_available is True
    assert decision.candidate_confidence == "medium"


def test_retention_candidate_without_positive_tier2_support_stays_provisional(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1, scan_support_score="0.3"),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.recommended_action == "keep_provisional"
    assert decision.evidence_tier == 1
    assert decision.support_components == ()
    assert decision.dependent_context == (
        "owner_backfill_context",
        "family_ms1_context",
        "selected_boundary_local_apex_consistency",
    )
    assert decision.tier2_evidence_available is False
    assert "missing_positive_tier2_support" in decision.challenge_blockers
    assert decision.candidate_confidence == "review"


def test_neighboring_interference_forces_audit(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(
            detected=1,
            rescued=1,
            region_review_reason="neighboring_ms1_interference",
        ),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.recommended_action == "review"
    assert "neighboring_interference_challenge" in decision.challenge_blockers
    assert decision.candidate_confidence == "review"


def test_low_scan_support_forces_audit(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1, scan_support_score="0.1"),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.recommended_action == "review"
    assert "low_assessable_coverage_challenge" in decision.challenge_blockers
    assert "missing_positive_tier2_support" in decision.challenge_blockers


def test_missing_rescued_cell_evidence_blocks_explicit_tier2_candidate(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
            independent_support="validated_tier2_trace_evidence",
        ),
        (),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.recommended_action == "review"
    assert decision.evidence_tier == 2
    assert decision.support_components == ("validated_tier2_trace_evidence",)
    assert "missing_rescued_cell_evidence" in decision.challenge_blockers


def test_fractional_counts_are_not_valid_candidate_eligibility(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected="1.5",
            rescued=1,
            independent_support="validated_tier2_trace_evidence",
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.recommended_action == "keep_provisional"
    assert decision.tier2_evidence_available is False
    assert decision.support_components == ()
    assert decision.challenge_blockers == ("not_retention_candidate",)


def test_dependent_or_provenance_only_support_tokens_do_not_promote(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=2,
            independent_support="owner_backfill_context;rescued_cell_rt_coherence",
        ),
        _cell_rows(detected=1, rescued=2),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.support_components == ()
    assert decision.tier2_evidence_available is False
    assert "missing_positive_tier2_support" in decision.challenge_blockers


def test_unknown_support_token_does_not_promote(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=2,
            independent_support="unreviewed_tier2_placeholder",
        ),
        _cell_rows(detected=1, rescued=2),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.support_components == ()
    assert decision.tier2_evidence_available is False
    assert "missing_positive_tier2_support" in decision.challenge_blockers


def test_review_only_exact_token_excludes_but_rescue_only_review_does_not(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )

    review_only = evaluate_production_candidate_gate(
        _review_row(
            identity_reason="review_only",
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )
    rescue_only_review = evaluate_production_candidate_gate(
        _review_row(
            flags=(
                "single_detected_seed;provisional_retention_candidate;"
                "rescue_only_review"
            ),
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )

    assert review_only.candidate_gate_status == "audit"
    assert review_only.recommended_action == "review"
    assert "review_only" in review_only.challenge_blockers
    assert "review_only" not in rescue_only_review.challenge_blockers
    assert rescue_only_review.candidate_gate_status == "keep_provisional"
    assert "missing_positive_tier2_support" in rescue_only_review.challenge_blockers


def test_non_retention_candidate_is_reported_without_tier2_promotion(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(flags="single_detected_seed", detected=1, rescued=1),
        _cell_rows(detected=1, rescued=1),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.recommended_action == "keep_provisional"
    assert decision.evidence_tier == 1
    assert decision.tier2_evidence_available is False
    assert decision.challenge_blockers == ("not_retention_candidate",)


def test_gate_row_has_stable_columns_and_hashes(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    row = production_candidate_gate_as_row(decision)

    assert tuple(row) == PRODUCTION_CANDIDATE_GATE_COLUMNS
    assert row["source_review_artifact"] == str(review_path)
    assert row["source_cell_artifact"] == str(cell_path)
    assert row["source_matrix_artifact"] == str(matrix_path)
    assert len(row["source_review_sha256"]) == 64
    assert row["source_review_sha256"].isupper()
    assert len(row["source_cell_sha256"]) == 64
    assert row["source_cell_sha256"].isupper()
    assert len(row["source_matrix_sha256"]) == 64
    assert row["source_matrix_sha256"].isupper()


def test_summarize_gate_decisions_reports_diagnostic_only_counts(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    production_candidate = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
            independent_support="validated_tier2_trace_evidence",
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )
    keep_provisional = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(detected=1, rescued=1),
        source_context=context,
    )
    audit = evaluate_production_candidate_gate(
        _review_row(
            flags="single_detected_seed;provisional_retention_candidate",
            detected=1,
            rescued=1,
        ),
        _cell_rows(
            detected=1,
            rescued=1,
            region_review_reason="neighboring_ms1_interference",
        ),
        source_context=context,
    )

    summary = summarize_gate_decisions((production_candidate, keep_provisional, audit))

    assert summary["readiness_label"] == "diagnostic_only"
    assert summary["production_candidate_count"] == 1
    assert summary["keep_provisional_count"] == 1
    assert summary["audit_count"] == 1
    assert summary["excluded_count"] == 0
    assert summary["production_ready"] is False
    assert summary["matrix_contract_changed"] is False


def _review_row(
    *,
    flags: str,
    detected: object,
    rescued: object,
    decision: str = "provisional_discovery",
    identity_reason: str = "insufficient_detected_identity_support",
    duplicate: object = 0,
    ambiguous: object = 0,
    independent_support: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "neutral_loss_tag": "DNA_dR",
        "include_in_primary_matrix": "FALSE",
        "identity_decision": decision,
        "identity_confidence": "review",
        "identity_reason": identity_reason,
        "primary_evidence": "owner_complete_link",
        "quantifiable_detected_count": str(detected),
        "quantifiable_rescue_count": str(rescued),
        "accepted_rescue_count": str(rescued),
        "duplicate_assigned_count": str(duplicate),
        "ambiguous_ms1_owner_count": str(ambiguous),
        "row_flags": flags,
        "family_evidence": "owner_complete_link;owner_count=1",
        "independent_tier2_support_components": independent_support,
    }


def _cell_rows(
    *,
    detected: int,
    rescued: int,
    scan_support_score: str = "0.8",
    region_review_reason: str = "",
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index in range(detected):
        rows.append(_cell_row(index, "detected", "1000", "0.8", ""))
    for index in range(detected, detected + rescued):
        rows.append(
            _cell_row(
                index,
                "rescued",
                "500",
                scan_support_score,
                region_review_reason,
            )
        )
    return tuple(rows)


def _cell_row(
    index: int,
    status: str,
    area: str,
    scan_support_score: str,
    region_review_reason: str,
) -> dict[str, str]:
    return {
        "feature_family_id": "FAM001",
        "sample_stem": f"S{index + 1:03d}",
        "status": status,
        "area": area,
        "apex_rt": "8.00",
        "height": "100",
        "peak_start_rt": "7.95",
        "peak_end_rt": "8.05",
        "rt_delta_sec": "0.0",
        "trace_quality": "owner_backfill" if status == "rescued" else "clean",
        "scan_support_score": scan_support_score,
        "reason": status,
        "region_review_reason": region_review_reason,
    }


def _write_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    review_path = tmp_path / "alignment_review.tsv"
    cell_path = tmp_path / "alignment_cells.tsv"
    matrix_path = tmp_path / "alignment_matrix.tsv"
    review_path.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    cell_path.write_text(
        "feature_family_id\tsample_stem\nFAM001\tS001\n",
        encoding="utf-8",
    )
    matrix_path.write_text("feature_family_id\nFAM_PRIMARY\n", encoding="utf-8")
    return review_path, cell_path, matrix_path
