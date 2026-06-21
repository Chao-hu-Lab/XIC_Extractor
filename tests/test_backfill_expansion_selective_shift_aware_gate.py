from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import check_backfill_expansion_selective_shift_aware_gate as checker
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_extract_source_family_from_sample_local_reason() -> None:
    assert (
        checker._extract_source_family(  # noqa: SLF001
            "primary family consolidation; source_family=FAM020407; "
            "source_reason=duplicate MS1 peak claim",
        )
        == "FAM020407"
    )
    assert checker._extract_source_family("no provenance") == ""  # noqa: SLF001


def test_selective_gate_keeps_strong_source_family_and_holds_weak_one(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)

    payload = checker.build_backfill_expansion_selective_shift_aware_gate(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        raw_trace_cells_tsv=paths.raw_trace_tsv,
        shift_aware_batch_summary_json=paths.batch_summary_json,
        shift_aware_batch_summary_tsv=paths.batch_summary_tsv,
        standard_peak_gate_tsv=paths.standard_gate_tsv,
        cells_tsv=paths.cells_tsv,
    )

    assert payload["candidate_cell_count"] == 666
    assert payload["source_family_shift_supported_cell_count"] == 1
    assert payload["source_family_attention_cell_count"] == 1
    assert payload["selective_evidence_pass_cell_count"] == 1
    assert payload["held_cell_count"] == 665
    assert payload["write_authority"] is False

    rows = read_tsv_required(paths.cells_tsv, checker.CELL_COLUMNS)
    by_sample = {row["sample_stem"]: row for row in rows}
    assert by_sample["SampleA_DNA"]["source_family_shift_status"] == "pass"
    assert by_sample["SampleA_DNA"]["selective_evidence_status"] == "pass"
    assert by_sample["SampleB_DNA"]["source_family_shift_status"] == "attention_only"
    assert by_sample["SampleB_DNA"]["selective_evidence_status"] == "held"
    assert by_sample["SampleB_DNA"]["primary_blocker"] == (
        "source_family_shift_attention_only"
    )


def test_selective_gate_own_max_still_blocks_supported_source_family(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path, sample_b_own_max="0.40")

    checker.build_backfill_expansion_selective_shift_aware_gate(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        raw_trace_cells_tsv=paths.raw_trace_tsv,
        shift_aware_batch_summary_json=paths.batch_summary_json,
        shift_aware_batch_summary_tsv=paths.batch_summary_tsv,
        standard_peak_gate_tsv=paths.standard_gate_tsv,
        support_min_shape_r=0.85,
        attention_min_shape_r=0.80,
        cells_tsv=paths.cells_tsv,
    )

    rows = read_tsv_required(paths.cells_tsv, checker.CELL_COLUMNS)
    sample_b = {row["sample_stem"]: row for row in rows}["SampleB_DNA"]
    assert sample_b["source_family_shift_status"] == "pass"
    assert sample_b["own_max_metric_status"] == "below_threshold"
    assert sample_b["selective_evidence_status"] == "held"
    assert sample_b["primary_blocker"] == "own_max_metric_below_threshold"


def test_validate_selective_gate_fails_on_summary_count_drift(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    checker.build_backfill_expansion_selective_shift_aware_gate(
        docs_dir=paths.docs_dir,
        output_dir=paths.output_dir,
        expected_diff_tsv=paths.expected_diff_tsv,
        sample_local_cells_tsv=paths.sample_local_tsv,
        raw_trace_cells_tsv=paths.raw_trace_tsv,
        shift_aware_batch_summary_json=paths.batch_summary_json,
        shift_aware_batch_summary_tsv=paths.batch_summary_tsv,
        standard_peak_gate_tsv=paths.standard_gate_tsv,
        cells_tsv=paths.cells_tsv,
    )
    summary_json = paths.docs_dir / checker.DEFAULT_SUMMARY_JSON.name
    checks_tsv = paths.docs_dir / checker.DEFAULT_CHECKS_TSV.name
    manifest_tsv = paths.docs_dir / checker.DEFAULT_ROW_MANIFEST_TSV.name
    drifted_summary_json = tmp_path / "drifted_summary.json"
    shutil.copyfile(summary_json, drifted_summary_json)
    payload = json.loads(drifted_summary_json.read_text(encoding="utf-8"))
    payload["candidate_cell_count"] = 665
    drifted_summary_json.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    problems = checker.validate_backfill_expansion_selective_shift_aware_gate(
        summary_json=drifted_summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        cells_tsv=paths.cells_tsv,
    )

    assert "summary candidate_cell_count mismatch" in problems


def test_missing_declared_externalized_cells_tsv_is_not_clean_checkout_blocker(
    tmp_path: Path,
) -> None:
    summary_json, checks_tsv, manifest_tsv = _copy_default_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "output/validation/__missing_selective_shift_aware/"
        "backfill_expansion_selective_shift_aware_gate_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    payload["artifacts"]["cells_tsv"]["sha256"] = "A" * 64
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_selective_shift_aware_gate(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        cells_tsv=missing_cells_tsv,
    )

    assert problems == []


def test_missing_retained_cells_tsv_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, manifest_tsv = _copy_default_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "docs/superpowers/validation/"
        "__missing_selective_shift_aware_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    payload["artifacts"]["cells_tsv"]["sha256"] = "A" * 64
    payload["artifacts"]["cells_tsv"]["retention_decision"] = "externalize"
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_selective_shift_aware_gate(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
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
        self.raw_trace_tsv = root / "raw_trace.tsv"
        self.standard_gate_tsv = root / "standard_gate.tsv"
        self.best_shift_tsv = root / "best_shift.tsv"
        self.batch_summary_tsv = root / "batch_summary.tsv"
        self.batch_summary_json = root / "batch_summary.json"
        self.cells_tsv = self.output_dir / "cells.tsv"


def _copy_default_contract(tmp_path: Path) -> tuple[Path, Path, Path]:
    summary_json = tmp_path / "summary.json"
    checks_tsv = tmp_path / "checks.tsv"
    manifest_tsv = tmp_path / "manifest.tsv"
    shutil.copyfile(checker.DEFAULT_SUMMARY_JSON, summary_json)
    shutil.copyfile(checker.DEFAULT_CHECKS_TSV, checks_tsv)
    shutil.copyfile(checker.DEFAULT_ROW_MANIFEST_TSV, manifest_tsv)
    return summary_json, checks_tsv, manifest_tsv


def _write_fixture(tmp_path: Path, *, sample_b_own_max: str = "0.82") -> FixturePaths:
    paths = FixturePaths(tmp_path)
    expected_rows = [
        {
            "peak_hypothesis_id": "FAM020411",
            "sample_stem": "SampleA_DNA",
            "expected_matrix_effect": "write_accepted_backfill",
        },
        {
            "peak_hypothesis_id": "FAM020411",
            "sample_stem": "SampleB_DNA",
            "expected_matrix_effect": "write_accepted_backfill",
        },
    ]
    expected_rows.extend(
        {
            "peak_hypothesis_id": f"FAMFILL{i:03d}",
            "sample_stem": "Filler_DNA",
            "expected_matrix_effect": "write_accepted_backfill",
        }
        for i in range(664)
    )
    write_tsv(
        paths.expected_diff_tsv,
        expected_rows,
        checker.EXPECTED_DIFF_COLUMNS,
        extrasaction="raise",
    )

    sample_rows = [
        _sample_local_row(
            "FAM020411",
            "SampleA_DNA",
            "primary family consolidation; source_family=FAM020407",
        ),
        _sample_local_row(
            "FAM020411",
            "SampleB_DNA",
            "primary family consolidation; source_family=FAM020423",
        ),
    ]
    sample_rows.extend(
        _sample_local_row(
            f"FAMFILL{i:03d}",
            "Filler_DNA",
            "primary family consolidation; source_family=FAMFILLREF",
        )
        for i in range(664)
    )
    write_tsv(
        paths.sample_local_tsv,
        sample_rows,
        checker.SAMPLE_LOCAL_COLUMNS,
        extrasaction="raise",
    )

    raw_rows = [
        _raw_trace_row("FAM020411", "SampleA_DNA", "0.91"),
        _raw_trace_row("FAM020411", "SampleB_DNA", sample_b_own_max),
    ]
    raw_rows.extend(
        _raw_trace_row(f"FAMFILL{i:03d}", "Filler_DNA", "0.91")
        for i in range(664)
    )
    write_tsv(
        paths.raw_trace_tsv,
        raw_rows,
        checker.RAW_TRACE_COLUMNS,
        extrasaction="raise",
    )

    gate_rows = [_standard_gate_row("FAM020411")]
    gate_rows.extend(_standard_gate_row(f"FAMFILL{i:03d}") for i in range(664))
    write_tsv(
        paths.standard_gate_tsv,
        gate_rows,
        checker.STANDARD_GATE_COLUMNS,
        extrasaction="raise",
    )

    best_shift_rows = [
        _best_shift_row("FAM020411", "FAM020407", "0.9994"),
        _best_shift_row("FAM020411", "FAM020423", "0.8791"),
    ]
    best_shift_rows.extend(
        _best_shift_row(f"FAMFILL{i:03d}", "FAMFILLREF", "0.70")
        for i in range(664)
    )
    write_tsv(
        paths.best_shift_tsv,
        best_shift_rows,
        checker.BEST_SHIFT_COLUMNS,
        extrasaction="raise",
    )
    batch_rows = [
        {
            "feature_family_id": "FAM020411",
            "source_best_shift_summary_tsv": str(paths.best_shift_tsv),
        },
    ]
    batch_rows.extend(
        {
            "feature_family_id": f"FAMFILL{i:03d}",
            "source_best_shift_summary_tsv": str(paths.best_shift_tsv),
        }
        for i in range(19)
    )
    write_tsv(
        paths.batch_summary_tsv,
        batch_rows,
        checker.BATCH_SUMMARY_COLUMNS,
        extrasaction="raise",
    )
    paths.batch_summary_json.write_text(
        json.dumps({"successful_shift_aware_row_count": 20}) + "\n",
        encoding="utf-8",
    )
    return paths


def _sample_local_row(
    family: str,
    sample: str,
    reason: str,
) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "alignment_cell_evidence_status": "present",
        "alignment_cell_status": "rescued",
        "production_cell_status": "review_rescue",
        "identity_decision": "production_family",
        "neutral_loss_tag": "DNA_dR",
        "cell_evidence_reason": reason,
    }


def _raw_trace_row(family: str, sample: str, own_max: str) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "trace_status": "rescued",
        "absolute_own_max_shape_similarity": own_max,
        "raw_trace_gate_status": "raw_trace_observed_expected_diff_candidate",
    }


def _standard_gate_row(family: str) -> dict[str, str]:
    return {
        "feature_family_id": family,
        "family_verdict": "ms1_shape_supports_family_backfill",
        "standard_peak_gate_call": "standard_peak_gate_blocked",
        "standard_peak_gate_reasons": (
            "family_overlay_gaussian_smoothed_standard_peak_supported"
        ),
        "standard_peak_gate_blockers": "shift_aware_same_pattern_not_supported",
        "min_shape_r_after_best_shift": "0.8791",
        "max_shape_r_after_best_shift": "0.9994",
    }


def _best_shift_row(family: str, source_family: str, shape_r: str) -> dict[str, str]:
    return {
        "feature_family_id": family,
        "source_family": source_family,
        "is_reference": "FALSE",
        "trace_count": "1",
        "detected_count": "0",
        "median_cell_apex_rt": "8.0",
        "shift_to_reference_sec": "1.8",
        "shape_similarity_to_reference_after_group_shift": shape_r,
    }
