from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    machine_evidence_support,
)
from xic_extractor.alignment.shared_peak_identity_explanation.machine_artifacts import (
    MachineMatch,
)
from xic_extractor.alignment.shared_peak_identity_explanation.shadow_labels import (
    build_shadow_alignment_summary,
    build_shadow_label_rows,
    build_v2_readiness,
)
from xic_extractor.alignment.shared_peak_identity_explanation.writers import (
    write_v2_outputs,
)


def test_shadow_labels_map_manual_evidence_classes_without_promotion() -> None:
    rows = build_shadow_label_rows(
        [
            _explanation(
                "row-pass-low",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_low_opportunity",
            ),
            _explanation(
                "row-fail-conflict",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_rt_pattern_conflict",
            ),
            _explanation(
                "row-shape-bad",
                manual_label="human_unjudgeable",
                evidence_gap_class="human_unjudgeable_shape_bad",
            ),
            _explanation(
                "row-context",
                manual_label="not_applicable",
                evidence_gap_class="delta_mass_related_context_only",
            ),
        ]
    )

    by_id = {row["oracle_row_id"]: row for row in rows}
    assert by_id["row-pass-low"]["shadow_label"] == "low_opportunity_supported"
    assert by_id["row-pass-low"]["shadow_alignment_status"] == "aligned"
    assert (
        by_id["row-fail-conflict"]["shadow_label"]
        == "rt_pattern_conflict_blocked"
    )
    assert by_id["row-fail-conflict"]["shadow_alignment_status"] == "aligned"
    assert by_id["row-shape-bad"]["shadow_alignment_status"] == "unjudgeable"
    assert by_id["row-context"]["shadow_alignment_status"] == "context_only"
    assert {row["diagnostic_only"] for row in rows} == {"TRUE"}


def test_v2_readiness_is_exploratory_when_blast_radius_is_unassessed() -> None:
    shadow_rows = build_shadow_label_rows(
        [
            _explanation(
                "row-pass-low",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_low_opportunity",
            ),
            _explanation(
                "row-fail-conflict",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_rt_pattern_conflict",
            ),
        ]
    )

    readiness = build_v2_readiness(
        run_facts={
            **_slice1_run_facts(),
            "blast_radius_assessed": "not_assessed",
            "max_overfit_risk": "unassessed",
        },
        shadow_rows=shadow_rows,
        machine_evidence_support_rows=[
            _support_row(
                "row-pass-low",
                evidence_support_status="machine_proxy_only",
                missing_machine_evidence="formal_shape_metric",
            )
        ],
    )

    assert readiness["v2_gate_status"] == "exploratory_only"
    assert readiness["machine_only_labeler_ready"] == "FALSE"
    assert readiness["machine_evidence_basis"] == "machine_proxy_or_manual_derived"
    assert readiness["semantic_generalization_evidence"] == (
        "seed_only_manual_oracle_derived"
    )
    assert "blast_radius_not_current" in readiness["clear_answer"]
    assert "overfit_risk_unassessed" in readiness["clear_answer"]


def test_v2_readiness_can_be_shadow_ready_candidate_after_current_low_risk() -> None:
    shadow_rows = build_shadow_label_rows(
        [
            _explanation(
                "row-pass",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_shape_or_pattern_unmodeled",
            ),
            _explanation(
                "row-fail",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_scope_rule_conflict",
            ),
        ]
    )

    readiness = build_v2_readiness(
        run_facts={
            **_slice1_run_facts(),
            "blast_radius_assessed": "present_current",
            "max_overfit_risk": "low",
            "blast_radius_stale_artifact_count": "0",
        },
        shadow_rows=shadow_rows,
        machine_evidence_support_rows=[
            _support_row(
                "row-pass",
                evidence_support_status="machine_observed_sufficient",
            ),
            _support_row(
                "row-fail",
                evidence_support_status="machine_observed_sufficient",
            ),
        ],
    )

    assert readiness["v2_gate_status"] == "shadow_ready_candidate"
    assert readiness["machine_only_labeler_ready"] == "TRUE"
    assert readiness["readiness_label"] == "diagnostic_only"
    assert readiness["machine_evidence_coverage_fraction"] == "1.000000"


def test_v2_readiness_does_not_promote_without_machine_observed_evidence() -> None:
    shadow_rows = build_shadow_label_rows(
        [
            _explanation(
                "row-pass",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_shape_or_pattern_unmodeled",
            )
        ]
    )

    readiness = build_v2_readiness(
        run_facts={
            **_slice1_run_facts(),
            "blast_radius_assessed": "present_current",
            "max_overfit_risk": "low",
            "blast_radius_stale_artifact_count": "0",
        },
        shadow_rows=shadow_rows,
        machine_evidence_support_rows=[
            _support_row(
                "row-pass",
                evidence_support_status="machine_proxy_only",
                missing_machine_evidence="formal_shape_metric",
            )
        ],
    )

    assert readiness["v2_gate_status"] == "exploratory_only"
    assert "machine_evidence_not_sufficient" in readiness["clear_answer"]


def test_machine_evidence_support_marks_manual_derived_metric_gaps() -> None:
    explanations = [
        {
            **_explanation(
                "row-pass",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_low_opportunity",
            ),
            "manual_reason_tags": (
                "rt_close;shape_complete;pattern_similar;low_intensity;"
                "dda_stochastic_missing"
            ),
            "manual_scope": "reviewed_cell",
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "row-pass": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={
                        "status": "rescued",
                        "apex_rt": "1.0",
                        "peak_start_rt": "0.9",
                        "peak_end_rt": "1.1",
                        "rt_delta_sec": "0.0",
                        "trace_quality": "owner_backfill",
                        "scan_support_score": "0.25",
                        "reason": "low scan support",
                    },
                ),
                _machine_match(
                    source_role="selected_peak",
                    sample_level=False,
                    row={
                        "feature_family_id": "row",
                        "neutral_loss_tag": "loss_116",
                        "family_product_mz": "123.0",
                        "family_observed_neutral_loss_da": "116.0",
                    },
                ),
            )
        },
    )

    row = rows[0]
    assert row["rt_basis_status"] == "machine_observed"
    assert row["shape_basis_status"] == "mixed"
    assert row["pattern_basis_status"] == "mixed"
    assert row["opportunity_basis_status"] == "mixed"
    assert row["evidence_support_status"] == "machine_proxy_only"
    assert "formal_shape_metric" in row["missing_machine_evidence"]
    assert "formal_pattern_metric" in row["missing_machine_evidence"]
    assert "cid_nl_pattern_context=family_level_present" in row[
        "observed_machine_metrics"
    ]
    assert "neutral_loss_tag=loss_116" in row["observed_machine_metrics"]
    assert "zhang_2014_eic_quality" in row["literature_support_refs"]
    assert "neutral_loss_product_ion_annotation" in row["literature_support_refs"]
    assert "koelmel_2017_iterative_exclusion" in row["literature_support_refs"]


def test_machine_evidence_support_uses_cwt_and_tier2_as_observed_metrics() -> None:
    explanations = [
        {
            **_explanation(
                "FAM001|S1",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_low_opportunity",
            ),
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_reason_tags": (
                "rt_close;shape_complete;pattern_similar;low_intensity;"
                "dda_stochastic_missing"
            ),
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "FAM001|S1": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={
                        "status": "rescued",
                        "apex_rt": "1.0",
                        "peak_start_rt": "0.9",
                        "peak_end_rt": "1.1",
                        "rt_delta_sec": "0.0",
                        "trace_quality": "owner_backfill",
                        "scan_support_score": "0.25",
                        "reason": "low scan support",
                    },
                ),
            )
        },
        cwt_shape_evidence={
            ("FAM001", "S1"): {
                "cwt_status": "OK",
                "cwt_shape_status": "cwt_near_expected",
                "cwt_apex_delta_sec": "0.01",
                "cwt_boundary_width_sec": "5.0",
                "cwt_prominence": "1000",
                "cwt_region_scan_count": "3",
                "cwt_quality_flags": "",
            }
        },
        tier2_trace_evidence={
            "FAM001": {
                "raw_trace_reread_status": "pass",
                "scan_support_score": "1",
                "trace_scan_count": "7",
                "scan_availability_score": "1",
                "trace_signal_to_noise_proxy": "4.0",
                "trace_apex_prominence_score": "0.5",
                "challenge_blockers": "",
            }
        },
    )

    row = rows[0]
    assert row["shape_basis_status"] == "machine_observed"
    assert row["opportunity_basis_status"] == "machine_observed"
    assert row["evidence_support_status"] == "machine_observed_partial"
    assert "formal_shape_metric" not in row["missing_machine_evidence"]
    assert "intensity_opportunity_metric" not in row["missing_machine_evidence"]
    assert "formal_pattern_metric" in row["missing_machine_evidence"]
    assert "dda_opportunity_policy" in row["missing_machine_evidence"]
    assert "cwt_status=OK" in row["observed_machine_metrics"]
    assert "tier2_raw_trace_status=pass" in row["observed_machine_metrics"]


def test_machine_evidence_support_marks_no_missing_machine_basis_sufficient() -> None:
    explanations = [
        {
            **_explanation(
                "FAM001|S1",
                manual_label="pass",
                evidence_gap_class="machine_agrees_with_manual",
            ),
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_reason_tags": "rt_close;shape_complete;pattern_similar",
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "FAM001|S1": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={
                        "status": "rescued",
                        "apex_rt": "1.0",
                        "peak_start_rt": "0.9",
                        "peak_end_rt": "1.1",
                        "rt_delta_sec": "0.0",
                        "trace_quality": "owner_backfill",
                    },
                ),
                _machine_match(
                    source_role="selected_peak",
                    sample_level=False,
                    row={
                        "feature_family_id": "FAM001",
                        "neutral_loss_tag": "loss_116",
                        "family_product_mz": "230.0",
                        "family_observed_neutral_loss_da": "116.0",
                    },
                ),
            )
        },
        cwt_shape_evidence={
            ("FAM001", "S1"): {
                "cwt_status": "OK",
                "cwt_shape_status": "cwt_near_expected",
                "cwt_apex_delta_sec": "0.01",
                "cwt_boundary_width_sec": "5.0",
                "cwt_prominence": "1000",
                "cwt_region_scan_count": "3",
                "cwt_quality_flags": "",
            }
        },
        candidate_ms2_pattern_evidence={
            ("FAM001", "S1"): {
                "candidate_ms2_pattern_status": "supportive",
                "candidate_ms2_evidence_level": "sample_boundary_aligned",
            }
        },
    )

    row = rows[0]
    assert row["manual_derived_facts"] == "pattern_similar;rt_close;shape_complete"
    assert row["missing_machine_evidence"] == ""
    assert row["evidence_support_status"] == "machine_observed_sufficient"


def test_machine_evidence_support_keeps_cid_nl_below_sample_ms2_pattern() -> None:
    explanations = [
        {
            **_explanation(
                "FAM001|S1",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_rt_pattern_conflict",
            ),
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_reason_tags": "rt_too_far;pattern_mismatch;shape_normal",
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "FAM001|S1": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={
                        "status": "rescued",
                        "apex_rt": "18.4783",
                        "rt_delta_sec": "'-82.5403",
                        "trace_quality": "owner_backfill",
                    },
                ),
                _machine_match(
                    source_role="selected_peak",
                    sample_level=False,
                    row={
                        "feature_family_id": "FAM001",
                        "neutral_loss_tag": "loss_116",
                        "family_product_mz": "230.0",
                        "family_observed_neutral_loss_da": "116.0",
                    },
                ),
            )
        },
        cwt_shape_evidence={
            ("FAM001", "S1"): {
                "cwt_status": "OK",
                "cwt_shape_status": "cwt_near_expected",
                "cwt_apex_delta_sec": "0.01",
                "cwt_boundary_width_sec": "5.0",
                "cwt_prominence": "1000",
                "cwt_region_scan_count": "3",
                "cwt_quality_flags": "",
            }
        },
        candidate_ms2_pattern_evidence={
            ("FAM001", "S1"): {
                "candidate_ms2_pattern_status": "not_available",
                "candidate_ms2_evidence_level": "not_available",
            }
        },
    )

    row = rows[0]
    assert row["pattern_basis_status"] == "mixed"
    assert row["evidence_support_status"] == "machine_observed_partial"
    assert "formal_pattern_metric" in row["missing_machine_evidence"]
    assert "shape_metric_not_supportive" not in row["missing_machine_evidence"]
    assert "candidate_aligned_ms2_pattern" in row["missing_machine_evidence"]
    assert "rt_pattern_conflict_gate" not in row["missing_machine_evidence"]
    assert "family_ms2_pattern_context" not in row["missing_machine_evidence"]
    assert "rt_preferred_window_status=outside_preferred_window" in row[
        "observed_machine_metrics"
    ]
    assert "neutral_loss_tag=loss_116" in row["observed_machine_metrics"]
    assert "cid_nl_pattern_context=family_level_present" in row[
        "observed_machine_metrics"
    ]


def test_candidate_ms2_pattern_sidecar_can_close_pattern_mismatch() -> None:
    explanations = [
        {
            **_explanation(
                "FAM001|S1",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_rt_pattern_conflict",
            ),
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_reason_tags": "rt_too_far;pattern_mismatch;shape_normal",
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "FAM001|S1": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={
                        "status": "rescued",
                        "apex_rt": "18.4783",
                        "rt_delta_sec": "'-82.5403",
                        "trace_quality": "owner_backfill",
                    },
                ),
            )
        },
        cwt_shape_evidence={
            ("FAM001", "S1"): {
                "cwt_status": "OK",
                "cwt_shape_status": "cwt_near_expected",
                "cwt_apex_delta_sec": "0.01",
                "cwt_boundary_width_sec": "5.0",
                "cwt_prominence": "1000",
                "cwt_region_scan_count": "3",
                "cwt_quality_flags": "",
            }
        },
        candidate_ms2_pattern_evidence={
            ("FAM001", "S1"): {
                "candidate_ms2_pattern_status": "conflict",
                "candidate_ms2_evidence_level": "sample_candidate_aligned",
                "candidate_ms2_similarity_score": "0.12",
                "matched_product_count": "0",
                "matched_neutral_loss_count": "0",
                "apex_ms2_delta_sec": "4.0",
                "ms2_alignment_source": "unit_test_sidecar",
            }
        },
    )

    row = rows[0]
    assert row["pattern_basis_status"] == "machine_observed"
    assert row["missing_machine_evidence"] == ""
    assert row["evidence_support_status"] == "machine_observed_sufficient"
    assert "candidate_ms2_pattern_status=conflict" in row[
        "observed_machine_metrics"
    ]
    assert "candidate_ms2_evidence_level=sample_candidate_aligned" in row[
        "observed_machine_metrics"
    ]


def test_candidate_ms2_pattern_sidecar_conflict_stays_fail_closed() -> None:
    explanations = [
        {
            **_explanation(
                "FAM001|S1",
                manual_label="fail",
                evidence_gap_class="machine_too_permissive_rt_pattern_conflict",
            ),
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_reason_tags": "pattern_mismatch",
        }
    ]
    shadow_rows = build_shadow_label_rows(explanations)

    rows = machine_evidence_support.build_machine_evidence_support_rows(
        explanations=explanations,
        shadow_rows=shadow_rows,
        machine_matches={
            "FAM001|S1": (
                _machine_match(
                    source_role="rescued_cell",
                    sample_level=True,
                    row={"status": "rescued"},
                ),
            )
        },
        candidate_ms2_pattern_evidence={
            ("FAM001", "S1"): {
                "candidate_ms2_pattern_status": "supportive",
                "candidate_ms2_evidence_level": "sample_candidate_aligned",
            }
        },
    )

    row = rows[0]
    assert row["pattern_basis_status"] == "machine_observed"
    assert row["missing_machine_evidence"] == "pattern_metric_not_supportive"
    assert row["evidence_support_status"] == "machine_observed_conflict"


def test_v2_writer_outputs_readiness_report_and_summary(tmp_path: Path) -> None:
    prior_outputs = _write_prior_outputs(tmp_path)
    shadow_rows = build_shadow_label_rows(
        [
            _explanation(
                "row-pass",
                manual_label="pass",
                evidence_gap_class="machine_too_conservative_shape_or_pattern_unmodeled",
            )
        ]
    )
    summary_rows = build_shadow_alignment_summary(shadow_rows)
    readiness = build_v2_readiness(
        run_facts={
            **_slice1_run_facts(),
            "blast_radius_assessed": "not_assessed",
            "max_overfit_risk": "unassessed",
        },
        shadow_rows=shadow_rows,
    )

    outputs = write_v2_outputs(
        output_dir=tmp_path,
        prior_outputs=prior_outputs,
        shadow_rows=shadow_rows,
        summary_rows=summary_rows,
        readiness_row=readiness,
        machine_evidence_support_rows=[
            _support_row(
                "row-pass",
                evidence_support_status="machine_proxy_only",
                missing_machine_evidence="formal_shape_metric",
            )
        ],
    )

    assert outputs["shadow_labels"].name == "shared_peak_identity_shadow_labels.tsv"
    assert outputs["shadow_alignment_summary"].name == (
        "shared_peak_identity_shadow_alignment_summary.tsv"
    )
    assert outputs["v2_readiness"].name == "shared_peak_identity_v2_readiness.tsv"
    assert outputs["machine_evidence_support"].name == (
        "shared_peak_identity_machine_evidence_support.tsv"
    )
    report = (tmp_path / "shared_peak_identity_v2_report.md").read_text(
        encoding="utf-8"
    )
    assert "exploratory_only" in report
    assert "production_ready" not in report
    assert "formal_shape_metric" in report
    assert "Machine Evidence Provenance" in report


def _explanation(
    oracle_row_id: str,
    *,
    manual_label: str,
    evidence_gap_class: str,
) -> dict[str, str]:
    return {
        "oracle_row_id": oracle_row_id,
        "feature_family_id": oracle_row_id.split("-", 1)[0],
        "sample_id": "sample",
        "manual_label": manual_label,
        "manual_confidence": "high",
        "machine_current_label": "rescued",
        "machine_match_status": "single_match",
        "evidence_gap_class": evidence_gap_class,
        "manual_reason_tags": "",
        "manual_scope": "reviewed_cell",
    }


def _support_row(
    oracle_row_id: str,
    *,
    evidence_support_status: str,
    missing_machine_evidence: str = "",
) -> dict[str, str]:
    return {
        "oracle_row_id": oracle_row_id,
        "evidence_support_status": evidence_support_status,
        "missing_machine_evidence": missing_machine_evidence,
        "shape_basis_status": "machine_observed",
        "pattern_basis_status": "machine_observed",
        "opportunity_basis_status": "machine_observed",
        "scope_basis_status": "not_applicable",
    }


def _machine_match(
    *,
    source_role: str,
    sample_level: bool,
    row: dict[str, str],
) -> MachineMatch:
    return MachineMatch(
        evidence_source="alignment_cells" if sample_level else "alignment_review",
        source_role=source_role,
        source_artifact=Path("artifact.tsv"),
        source_artifact_sha256="A" * 64,
        source_row_id="artifact.tsv:1",
        row=row,
        sample_level=sample_level,
    )


def _slice1_run_facts() -> dict[str, str]:
    return {
        "run_facts_schema_version": "shared_peak_identity_run_facts_v1",
        "slice": "slice1",
        "seed_rows_total": "2",
        "seed_rows_explained": "2",
        "seed_rows_unexplained": "0",
        "seed_rows_inconclusive": "0",
        "vocabulary_special_casing_detected": "FALSE",
        "blast_radius_assessed": "present_current",
        "blast_radius_stale_artifact_count": "0",
        "max_overfit_risk": "low",
        "durable_oracle_path": "oracle.tsv",
        "durable_oracle_sha256": "A" * 64,
    }


def _write_prior_outputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "oracle": tmp_path / "shared_peak_identity_manual_oracle.tsv",
        "evidence_vectors": tmp_path / "shared_peak_identity_evidence_vectors.tsv",
        "explanations": tmp_path / "shared_peak_identity_explanations.tsv",
        "run_facts": tmp_path / "shared_peak_identity_run_facts.tsv",
        "report": tmp_path / "shared_peak_identity_explanation_report.md",
    }
    for path in paths.values():
        path.write_text("placeholder\n", encoding="utf-8")
    return paths
