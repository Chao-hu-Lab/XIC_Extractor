from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import check_backfill_expansion_peak_mode_decomposition as checker
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_mode_assignment_uses_reference_mode_window() -> None:
    assert (
        checker._mode_assignment(apex=15.12, lower=15.02, upper=15.62)  # noqa: SLF001
        == "target_mode"
    )
    assert (
        checker._mode_assignment(apex=14.90, lower=15.02, upper=15.62)  # noqa: SLF001
        == "off_target_early"
    )
    assert (
        checker._mode_assignment(apex=None, lower=15.02, upper=15.62)  # noqa: SLF001
        == "missing_apex"
    )


def test_boundary_bridge_flags_target_mode_with_early_peak_boundary() -> None:
    assert checker._boundary_bridge_status(  # noqa: SLF001
        start=14.79,
        end=15.50,
        lower=15.02,
        upper=15.62,
        bridge_margin_min=0.05,
    ) == "bridges_lower_target_boundary"
    assert checker._boundary_bridge_status(  # noqa: SLF001
        start=15.08,
        end=15.40,
        lower=15.02,
        upper=15.62,
        bridge_margin_min=0.05,
    ) == "not_bridged"


def test_sample_subtype_from_sample_stem_uses_diagnostic_prefix() -> None:
    assert (
        checker._sample_subtype_from_sample_stem("TumorBC2264_DNA")  # noqa: SLF001
        == "tumor"
    )
    assert (
        checker._sample_subtype_from_sample_stem("NormalBC2287_DNA")  # noqa: SLF001
        == "normal"
    )
    assert (
        checker._sample_subtype_from_sample_stem(  # noqa: SLF001
            "BenignfatBC1108_DNA",
        )
        == "benignfat"
    )
    assert checker._sample_subtype_from_sample_stem(  # noqa: SLF001
        "Breast_Cancer_Tissue_pooled_QC5",
    ) == "qc"
    assert checker._sample_subtype_from_sample_stem("OtherSample_DNA") == "unknown"  # noqa: SLF001


def test_subtype_rt_context_flags_incoherence_and_cross_subtype_shift() -> None:
    rows = [
        _minimal_cell_row("FAM_INCOHERENT", "TumorA_DNA", "tumor", "14.80"),
        _minimal_cell_row("FAM_INCOHERENT", "TumorB_DNA", "tumor", "15.40"),
        _minimal_cell_row("FAM_SHIFT", "BenignfatA_DNA", "benignfat", "14.80"),
        _minimal_cell_row("FAM_SHIFT", "BenignfatB_DNA", "benignfat", "14.85"),
        _minimal_cell_row("FAM_SHIFT", "NormalA_DNA", "normal", "15.35"),
        _minimal_cell_row("FAM_SHIFT", "NormalB_DNA", "normal", "15.40"),
    ]

    checker._annotate_subtype_rt_context(  # noqa: SLF001
        rows,
        same_subtype_coherence_window_min=0.30,
    )

    by_sample = {row["sample_stem"]: row for row in rows}
    assert by_sample["TumorA_DNA"]["subtype_rt_coherence_status"] == (
        "same_subtype_rt_incoherent"
    )
    assert by_sample["TumorA_DNA"]["subtype_rt_review_action"] == (
        "review_same_subtype_rt_incoherence"
    )
    assert by_sample["BenignfatA_DNA"]["subtype_rt_coherence_status"] == (
        "same_subtype_rt_coherent"
    )
    assert by_sample["BenignfatA_DNA"]["subtype_rt_review_action"] == (
        "review_cross_subtype_rt_shift"
    )
    assert by_sample["NormalA_DNA"]["subtype_rt_review_action"] == (
        "review_cross_subtype_rt_shift"
    )


def test_subtype_split_review_queue_collapses_cells_to_review_groups() -> None:
    rows = [
        _minimal_cell_row(
            "FAM_A",
            "TumorA_DNA",
            "tumor",
            "14.80",
            mode_assignment="off_target_early",
        ),
        _minimal_cell_row("FAM_A", "TumorB_DNA", "tumor", "15.40"),
        _minimal_cell_row("FAM_A", "NormalA_DNA", "normal", "15.20"),
    ]
    checker._annotate_subtype_rt_context(  # noqa: SLF001
        rows,
        same_subtype_coherence_window_min=0.30,
    )

    queue = checker._build_subtype_split_review_queue(rows)  # noqa: SLF001

    assert len(queue) == 1
    row = queue[0]
    assert row["peak_hypothesis_id"] == "FAM_A"
    assert row["sample_subtype"] == "tumor"
    assert row["review_reason"] == "review_same_subtype_rt_incoherence"
    assert row["recommended_action"] == "review_split_same_subtype_modes"
    assert row["subtype_cell_count"] == "2"
    assert row["subtype_rt_span_min"] == "0.6000"
    assert row["representative_samples_by_mode"] == (
        "off_target_early:TumorA_DNA|target_mode:TumorB_DNA"
    )
    assert row["product_authority_effect"] == "diagnostic_only_no_write_authority"


def test_split_decision_rows_route_clean_boundary_and_hold_cells() -> None:
    rows = [
        _minimal_cell_row(
            "FAM_A",
            "TumorA_DNA",
            "tumor",
            "14.80",
            mode_assignment="off_target_early",
        ),
        _minimal_cell_row("FAM_A", "TumorB_DNA", "tumor", "15.40"),
        _minimal_cell_row(
            "FAM_A",
            "TumorC_DNA",
            "tumor",
            "15.45",
            boundary_bridge_status="bridges_lower_target_boundary",
        ),
        _minimal_cell_row("FAM_A", "NormalA_DNA", "normal", "15.20"),
    ]
    checker._annotate_subtype_rt_context(  # noqa: SLF001
        rows,
        same_subtype_coherence_window_min=0.30,
    )

    decisions = checker._build_split_decision_rows(rows)  # noqa: SLF001

    assert len(decisions) == 1
    row = decisions[0]
    assert row["peak_hypothesis_id"] == "FAM_A"
    assert row["sample_subtype"] == "tumor"
    assert row["decision_status"] == (
        "split_hold_off_target_and_review_boundaries"
    )
    assert row["target_mode_clean_cell_count"] == "1"
    assert row["target_mode_boundary_review_cell_count"] == "1"
    assert row["off_target_hold_or_remap_cell_count"] == "1"
    assert row["representative_clean_target_samples"] == "TumorB_DNA"
    assert row["representative_boundary_review_samples"] == "TumorC_DNA"
    assert row["representative_hold_or_remap_samples"] == "TumorA_DNA"
    assert row["product_authority_effect"] == "diagnostic_only_no_write_authority"


def test_peak_mode_decomposition_detects_mixed_family(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)

    payload = checker.build_backfill_expansion_peak_mode_decomposition(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        overlay_batch_summary_tsv=paths.overlay_batch_summary_tsv,
        manual_review_tsv=None,
        cells_tsv=paths.cells_tsv,
    )

    assert payload["candidate_cell_count"] == 666
    assert payload["mode_decomposition_status_counts"][
        "mixed_target_and_off_target_modes"
    ] == 1
    assert payload["sample_subtype_source"] == "diagnostic_filename_prefix"
    assert payload["subtype_split_review_queue_row_count"] == 0
    assert payload["split_decision_queue_row_count"] == 0
    assert payload["write_authority"] is False
    assert payload["product_writer_changed"] is False

    manifest_rows = read_tsv_required(paths.manifest_tsv, checker.ROW_MANIFEST_COLUMNS)
    fam = {row["peak_hypothesis_id"]: row for row in manifest_rows}["FAM017098"]
    assert fam["target_mode_cell_count"] == "2"
    assert fam["off_target_early_cell_count"] == "2"
    assert fam["boundary_bridge_cell_count"] == "1"
    assert fam["mode_decomposition_status"] == "mixed_target_and_off_target_modes"

    cell_rows = read_tsv_required(paths.cells_tsv, checker.CELL_COLUMNS)
    by_sample = {row["sample_stem"]: row for row in cell_rows}
    assert by_sample["LateA_DNA"]["mode_assignment"] == "target_mode"
    assert by_sample["LateA_DNA"]["boundary_bridge_status"] == (
        "bridges_lower_target_boundary"
    )
    assert by_sample["EarlyA_DNA"]["mode_assignment"] == "off_target_early"
    assert by_sample["EarlyA_DNA"]["next_gate"] == (
        "hold_or_remap_before_product_authority"
    )


def test_peak_mode_manual_review_labels_are_joined(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    write_tsv(
        paths.manual_review_tsv,
        [
            _manual_review_row(
                "FAM017098",
                "EarlyA_DNA",
                "off_target_left_peak",
                "left_peak_boundary_ok",
                "hold_or_split_to_left_peak",
            ),
            _manual_review_row(
                "FAM017098",
                "LateA_DNA",
                "target_right_peak",
                "boundary_wrong_spans_left_peak",
                "review_boundary_before_activation",
            ),
        ],
        checker.MANUAL_REVIEW_COLUMNS,
        extrasaction="raise",
    )

    payload = checker.build_backfill_expansion_peak_mode_decomposition(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        overlay_batch_summary_tsv=paths.overlay_batch_summary_tsv,
        manual_review_tsv=paths.manual_review_tsv,
        cells_tsv=paths.cells_tsv,
    )

    assert payload["manual_reviewed_cell_count"] == 2
    assert payload["manual_peak_mode_label_counts"] == {
        "off_target_left_peak": 1,
        "target_right_peak": 1,
    }
    assert payload["manual_review_action_counts"] == {
        "hold_or_split_to_left_peak": 1,
        "review_boundary_before_activation": 1,
    }
    assert "manual_review_tsv" in payload["input_artifacts"]

    cell_rows = read_tsv_required(paths.cells_tsv, checker.CELL_COLUMNS)
    by_sample = {row["sample_stem"]: row for row in cell_rows}
    assert by_sample["EarlyA_DNA"]["manual_peak_mode_label"] == (
        "off_target_left_peak"
    )
    assert by_sample["LateA_DNA"]["manual_boundary_label"] == (
        "boundary_wrong_spans_left_peak"
    )

    manifest_rows = read_tsv_required(paths.manifest_tsv, checker.ROW_MANIFEST_COLUMNS)
    fam = {row["peak_hypothesis_id"]: row for row in manifest_rows}["FAM017098"]
    assert fam["manual_reviewed_cell_count"] == "2"
    assert fam["manual_review_action_counts"] == (
        "hold_or_split_to_left_peak=1;review_boundary_before_activation=1"
    )


def test_validate_peak_mode_decomposition_fails_on_writer_flag(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    checker.build_backfill_expansion_peak_mode_decomposition(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        overlay_batch_summary_tsv=paths.overlay_batch_summary_tsv,
        manual_review_tsv=None,
        cells_tsv=paths.cells_tsv,
    )
    summary_json = paths.docs_dir / checker.DEFAULT_SUMMARY_JSON.name
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    payload["write_authority"] = True
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = checker.validate_backfill_expansion_peak_mode_decomposition(
        summary_json=summary_json,
        checks_tsv=paths.checks_tsv,
        row_manifest_tsv=paths.manifest_tsv,
        subtype_split_review_tsv=paths.subtype_split_review_tsv,
        split_decision_tsv=paths.split_decision_tsv,
        cells_tsv=paths.cells_tsv,
    )

    assert "summary write_authority must be false" in problems


def test_missing_declared_externalized_cells_tsv_is_not_clean_checkout_blocker(
    tmp_path: Path,
) -> None:
    (
        summary_json,
        checks_tsv,
        manifest_tsv,
        subtype_split_review_tsv,
        split_decision_tsv,
    ) = _copy_default_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "output/validation/__missing_peak_mode_decomposition/"
        "backfill_expansion_peak_mode_decomposition_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    payload["artifacts"]["cells_tsv"]["sha256"] = "A" * 64
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_peak_mode_decomposition(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        subtype_split_review_tsv=subtype_split_review_tsv,
        split_decision_tsv=split_decision_tsv,
        cells_tsv=missing_cells_tsv,
    )

    assert problems == []


def test_missing_retained_cells_tsv_fails_closed(tmp_path: Path) -> None:
    (
        summary_json,
        checks_tsv,
        manifest_tsv,
        subtype_split_review_tsv,
        split_decision_tsv,
    ) = _copy_default_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "docs/superpowers/validation/"
        "__missing_peak_mode_decomposition_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    payload["artifacts"]["cells_tsv"]["sha256"] = "A" * 64
    payload["artifacts"]["cells_tsv"]["retention_decision"] = "externalize"
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_peak_mode_decomposition(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        subtype_split_review_tsv=subtype_split_review_tsv,
        split_decision_tsv=split_decision_tsv,
        cells_tsv=missing_cells_tsv,
    )

    assert f"cells TSV missing: {missing_cells_tsv}" in problems
    assert any("summary artifacts cells_tsv missing" in problem for problem in problems)


class FixturePaths:
    def __init__(self, root: Path) -> None:
        self.docs_dir = root / "docs"
        self.output_dir = root / "output"
        self.expected_diff_tsv = root / "expected_diff.tsv"
        self.sample_local_tsv = root / "sample_local.tsv"
        self.overlay_batch_summary_tsv = root / "overlay_batch_summary.tsv"
        self.focus_trace_summary_tsv = root / "fam017098_trace_summary.tsv"
        self.filler_trace_summary_tsv = root / "filler_trace_summary.tsv"
        self.manual_review_tsv = root / "manual_review.tsv"
        self.cells_tsv = self.output_dir / "cells.tsv"
        self.checks_tsv = self.docs_dir / checker.DEFAULT_CHECKS_TSV.name
        self.manifest_tsv = self.docs_dir / checker.DEFAULT_ROW_MANIFEST_TSV.name
        self.subtype_split_review_tsv = (
            self.docs_dir / checker.DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV.name
        )
        self.split_decision_tsv = (
            self.docs_dir / checker.DEFAULT_SPLIT_DECISION_TSV.name
        )


def _copy_default_contract(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    summary_json = tmp_path / "summary.json"
    checks_tsv = tmp_path / "checks.tsv"
    manifest_tsv = tmp_path / "manifest.tsv"
    subtype_split_review_tsv = tmp_path / "subtype_split_review.tsv"
    split_decision_tsv = tmp_path / "split_decision.tsv"
    shutil.copyfile(checker.DEFAULT_SUMMARY_JSON, summary_json)
    shutil.copyfile(checker.DEFAULT_CHECKS_TSV, checks_tsv)
    shutil.copyfile(checker.DEFAULT_ROW_MANIFEST_TSV, manifest_tsv)
    shutil.copyfile(checker.DEFAULT_SUBTYPE_SPLIT_REVIEW_TSV, subtype_split_review_tsv)
    shutil.copyfile(checker.DEFAULT_SPLIT_DECISION_TSV, split_decision_tsv)
    return (
        summary_json,
        checks_tsv,
        manifest_tsv,
        subtype_split_review_tsv,
        split_decision_tsv,
    )


def _write_fixture(tmp_path: Path) -> FixturePaths:
    paths = FixturePaths(tmp_path)
    expected_rows = [
        _expected_row("FAM017098", "EarlyA_DNA"),
        _expected_row("FAM017098", "EarlyB_DNA"),
        _expected_row("FAM017098", "LateA_DNA"),
        _expected_row("FAM017098", "LateB_DNA"),
    ]
    expected_rows.extend(
        _expected_row(f"FAMFILL{i:03d}", "Filler_DNA") for i in range(662)
    )
    write_tsv(
        paths.expected_diff_tsv,
        expected_rows,
        checker.EXPECTED_DIFF_COLUMNS,
        extrasaction="raise",
    )

    sample_rows = [
        _sample_row("FAM017098", "EarlyA_DNA", "14.78", "14.77", "14.80"),
        _sample_row("FAM017098", "EarlyB_DNA", "14.90", "14.89", "14.92"),
        _sample_row("FAM017098", "LateA_DNA", "15.36", "14.79", "15.50"),
        _sample_row("FAM017098", "LateB_DNA", "15.12", "15.08", "15.15"),
    ]
    sample_rows.extend(
        _sample_row(f"FAMFILL{i:03d}", "Filler_DNA", "8.00", "7.95", "8.05")
        for i in range(662)
    )
    write_tsv(
        paths.sample_local_tsv,
        sample_rows,
        checker.SAMPLE_LOCAL_COLUMNS,
        extrasaction="raise",
    )

    focus_trace_rows = [
        _trace_row("DetectedA_DNA", "detected", "15.30", "15.20", "15.40"),
        _trace_row("DetectedB_DNA", "detected", "15.35", "15.25", "15.45"),
    ]
    write_tsv(
        paths.focus_trace_summary_tsv,
        focus_trace_rows,
        checker.TRACE_SUMMARY_COLUMNS,
        extrasaction="raise",
    )
    filler_trace_rows = [
        _trace_row("DetectedFill_DNA", "detected", "8.00", "7.95", "8.05"),
    ]
    write_tsv(
        paths.filler_trace_summary_tsv,
        filler_trace_rows,
        checker.TRACE_SUMMARY_COLUMNS,
        extrasaction="raise",
    )
    overlay_rows = [
        {
            "feature_family_id": "FAM017098",
            "trace_summary_tsv": str(paths.focus_trace_summary_tsv),
        },
    ]
    overlay_rows.extend(
        {
            "feature_family_id": f"FAMFILL{i:03d}",
            "trace_summary_tsv": str(paths.filler_trace_summary_tsv),
        }
        for i in range(19)
    )
    write_tsv(
        paths.overlay_batch_summary_tsv,
        overlay_rows,
        checker.OVERLAY_BATCH_COLUMNS,
        extrasaction="raise",
    )
    return paths


def _expected_row(family: str, sample: str) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "expected_matrix_effect": "write_accepted_backfill",
    }


def _sample_row(
    family: str,
    sample: str,
    apex: str,
    start: str,
    end: str,
) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "alignment_cell_evidence_status": "present",
        "apex_rt": apex,
        "peak_start_rt": start,
        "peak_end_rt": end,
        "cell_evidence_reason": "primary family consolidation",
    }


def _minimal_cell_row(
    family: str,
    sample: str,
    subtype: str,
    apex: str,
    *,
    mode_assignment: str = "target_mode",
    boundary_bridge_status: str = "not_bridged",
) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "sample_subtype": subtype,
        "cell_apex_rt": apex,
        "mode_assignment": mode_assignment,
        "boundary_bridge_status": boundary_bridge_status,
    }


def _manual_review_row(
    family: str,
    sample: str,
    peak_mode_label: str,
    boundary_label: str,
    action: str,
) -> dict[str, str]:
    return {
        "schema_version": checker.SCHEMA_VERSION,
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "reviewer_peak_mode_label": peak_mode_label,
        "reviewer_boundary_label": boundary_label,
        "reviewer_action": action,
        "reviewer_notes": "manual fixture note",
    }


def _trace_row(
    sample: str,
    status: str,
    apex: str,
    start: str,
    end: str,
) -> dict[str, str]:
    return {
        "sample_stem": sample,
        "status": status,
        "cell_apex_rt": apex,
        "cell_start_rt": start,
        "cell_end_rt": end,
        "highlight_group": "detected_seed",
    }
