from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_backfill_expansion_full_evidence_chain as runner
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_shift_aware_cell_evidence_adapter_preserves_sample_local_reason(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample_local_cells.tsv"
    output = tmp_path / "adapter.tsv"
    write_tsv(
        source,
        [
            {
                "peak_hypothesis_id": "FAM000736",
                "sample_stem": "SampleA_DNA",
                "cell_evidence_reason": (
                    "primary family consolidation; source_family=FAM000725"
                ),
            },
            {
                "peak_hypothesis_id": "FAM000736",
                "sample_stem": "SampleB_DNA",
                "cell_evidence_reason": "",
            },
        ],
        runner.SAMPLE_LOCAL_ADAPTER_SOURCE_COLUMNS,
        extrasaction="raise",
    )

    result = runner.write_shift_aware_cell_evidence_adapter(
        sample_local_cells_tsv=source,
        output_tsv=output,
    )

    assert result == output
    rows = read_tsv_required(output, runner.SHIFT_AWARE_CELL_EVIDENCE_ADAPTER_COLUMNS)
    assert rows == (
        {
            "feature_family_id": "FAM000736",
            "sample_stem": "SampleA_DNA",
            "reason": "primary family consolidation; source_family=FAM000725",
        },
        {
            "feature_family_id": "FAM000736",
            "sample_stem": "SampleB_DNA",
            "reason": "",
        },
    )


def test_reconciliation_groups_minimal_keeps_candidate_only_authority(
    tmp_path: Path,
) -> None:
    source = tmp_path / "overlay_summary.tsv"
    output = tmp_path / "groups.tsv"
    write_tsv(
        source,
        [
            {
                "feature_family_id": "FAM003973",
                "detected_count": "45",
                "rescued_count": "40",
            },
        ],
        runner.OVERLAY_RECONCILIATION_SOURCE_COLUMNS,
        extrasaction="raise",
    )

    result = runner.write_reconciliation_groups_minimal(
        overlay_batch_summary_tsv=source,
        output_tsv=output,
    )

    assert result == output
    rows = read_tsv_required(output, runner.RECONCILIATION_GROUP_COLUMNS)
    assert rows == (
        {
            "feature_family_id": "FAM003973",
            "product_behavior_state": "backfill_expansion_candidate_replay_held",
            "evidence_authority_state": "candidate_only_no_product_authority",
            "reconciliation_class": "expected_diff_candidate_needs_full_chain",
            "detected_cell_count": "45",
            "rescued_cell_count": "40",
            "top_support_component": "raw_overlay_trace_identity",
            "top_blocker": "shift_aware_own_max_product_authority_chain_incomplete",
            "missing_evidence": (
                "shift_aware_standard_peak_gate_or_ms1_product_authority_sidecar"
            ),
        },
    )


def test_raw_overlay_resolution_requires_raw_paths_or_existing_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runner.raw_trace,
        "DEFAULT_OVERLAY_BATCH_SUMMARY_TSV",
        tmp_path / "missing.tsv",
    )

    with pytest.raises(ValueError, match="Provide --raw-dir and --dll-dir"):
        runner._resolve_raw_overlay(
            raw_dir=None,
            dll_dir=None,
            reuse_existing_raw_overlay=False,
            steps=[],
        )

    with pytest.raises(FileNotFoundError, match="required artifact missing"):
        runner._resolve_raw_overlay(
            raw_dir=None,
            dll_dir=None,
            reuse_existing_raw_overlay=True,
            steps=[],
        )


def test_runner_executes_clean_target_activation_as_final_product_gate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def stub(label: str):
        def inner(*args, **kwargs):
            calls.append(label)
            return None

        return inner

    def resolve_overlay(**kwargs):
        calls.append("family_ms1_overlay_batch")
        kwargs["steps"].append(
            {
                "step": "family_ms1_overlay_batch",
                "status": "pass",
                "mode": "test",
            },
        )
        return tmp_path / "overlay.tsv", "test"

    def read_json(path: Path):
        if path == runner.full_chain.DEFAULT_SUMMARY_JSON:
            return {
                "validation_status": "diagnostic_only",
                "candidate_cell_count": 666,
                "full_chain_complete": False,
                "full_chain_pass_cell_count": 464,
                "held_cell_count": 202,
                "primary_blocker_counts": {},
            }
        if path == runner.clean_activation.DEFAULT_SUMMARY_JSON:
            return {
                "validation_status": "production_ready",
                "written_backfill_count": "84",
                "candidate_peak_count": 7,
                "product_authority_scope": (
                    "backfill_expansion_clean_target_selective_activation_84_cells"
                ),
                "default_activation_effect": (
                    "write_backfill_expansion_clean_target_selective_default_cell"
                ),
                "write_authority": True,
                "product_writer_changed": True,
                "default_quant_matrix_changed": True,
                "default_matrix_files_written": True,
                "workbook_or_gui_changed": False,
                "selected_peak_area_or_counting_changed": False,
            }
        raise AssertionError(f"unexpected summary path: {path}")

    monkeypatch.setattr(
        runner.census,
        "build_backfill_expansion_census",
        stub("backfill_expansion_census"),
    )
    monkeypatch.setattr(
        runner.availability,
        "build_backfill_expansion_evidence_availability",
        stub("backfill_expansion_evidence_availability"),
    )
    monkeypatch.setattr(
        runner.sample_local,
        "build_backfill_expansion_sample_local_ms1_evidence",
        stub("backfill_expansion_sample_local_ms1_evidence"),
    )
    monkeypatch.setattr(runner, "_resolve_raw_overlay", resolve_overlay)
    monkeypatch.setattr(
        runner.raw_trace,
        "build_backfill_expansion_raw_overlay_trace_identity",
        stub("backfill_expansion_raw_overlay_trace_identity"),
    )
    monkeypatch.setattr(
        runner.expected_diff,
        "build_backfill_expansion_expected_diff_provenance",
        stub("backfill_expansion_expected_diff_provenance"),
    )
    monkeypatch.setattr(
        runner.activation,
        "build_backfill_expansion_default_product_activation",
        stub("backfill_expansion_default_product_activation_candidate"),
    )
    monkeypatch.setattr(
        runner,
        "write_shift_aware_cell_evidence_adapter",
        stub("shift_aware_cell_evidence_adapter"),
    )
    monkeypatch.setattr(
        runner,
        "write_reconciliation_groups_minimal",
        stub("reconciliation_groups_minimal"),
    )
    monkeypatch.setattr(
        runner,
        "run_shift_aware_support_chain",
        stub("shift_aware_support_chain"),
    )
    monkeypatch.setattr(
        runner.full_chain,
        "build_backfill_expansion_full_evidence_chain",
        stub("backfill_expansion_full_evidence_chain_gate"),
    )
    monkeypatch.setattr(
        runner.full_chain,
        "validate_backfill_expansion_full_evidence_chain",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        runner.peak_mode,
        "build_backfill_expansion_peak_mode_decomposition",
        stub("backfill_expansion_peak_mode_decomposition"),
    )
    monkeypatch.setattr(
        runner.selective_shift,
        "build_backfill_expansion_selective_shift_aware_gate",
        stub("backfill_expansion_selective_shift_aware_gate"),
    )
    monkeypatch.setattr(
        runner.clean_replay,
        "build_backfill_expansion_clean_target_full_chain_replay",
        stub("backfill_expansion_clean_target_full_chain_replay"),
    )
    monkeypatch.setattr(
        runner.clean_activation,
        "build_backfill_expansion_clean_target_selective_product_activation",
        stub("backfill_expansion_clean_target_selective_product_activation"),
    )
    monkeypatch.setattr(
        runner.clean_activation,
        "validate_backfill_expansion_clean_target_selective_product_activation",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(runner, "_read_json_object", read_json)

    payload = runner.run_backfill_expansion_full_evidence_chain(
        reuse_existing_raw_overlay=True,
        summary_json=tmp_path / "runner_summary.json",
    )

    assert calls[-4:] == [
        "backfill_expansion_peak_mode_decomposition",
        "backfill_expansion_selective_shift_aware_gate",
        "backfill_expansion_clean_target_full_chain_replay",
        "backfill_expansion_clean_target_selective_product_activation",
    ]
    assert payload["validation_status"] == "production_ready"
    assert payload["active_backfill_cell_count"] == "84"
    assert payload["write_authority"] is True
    assert payload["product_writer_changed"] is True
    assert payload["default_quant_matrix_changed"] is True
    assert payload["workbook_or_gui_changed"] is False


def test_alignment_preset_wrapper_uses_current_alignment_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    for name in (
        "alignment_matrix.tsv",
        "alignment_matrix_identity.tsv",
        "alignment_backfill_cell_evidence.tsv",
        "alignment_review.tsv",
    ):
        (alignment_dir / name).write_text("x\n", encoding="utf-8")
    output_dir = tmp_path / "backfill_expansion_productization_preset"
    captured_cid: dict[str, object] = {}
    captured_chain: dict[str, object] = {}

    def fake_cid_activation(**kwargs):
        captured_cid.update(kwargs)
        return {}

    def fake_chain(**kwargs):
        captured_chain.update(kwargs)
        return {
            "clean_target_selective_activation_summary_json": str(
                kwargs["docs_root"]
                / "backfill_expansion_clean_target_selective_product_activation_v1"
                / (
                    "backfill_expansion_clean_target_selective_product_activation_"
                    "summary.json"
                )
            ),
            "product_authority_scope": (
                "backfill_expansion_clean_target_selective_activation_84_cells"
            ),
            "active_backfill_cell_count": 84,
        }

    monkeypatch.setattr(
        runner.cid_nl_activation,
        "build_cid_nl_default_product_activation",
        fake_cid_activation,
    )
    monkeypatch.setattr(
        runner,
        "run_backfill_expansion_full_evidence_chain",
        fake_chain,
    )

    outputs = (
        runner.run_backfill_expansion_clean_target_selective_preset_from_alignment(
            alignment_dir=alignment_dir,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            reuse_existing_raw_overlay=True,
            reuse_existing_shift_aware=True,
        )
    )

    assert captured_cid["input_quant_matrix_tsv"] == (
        alignment_dir / "alignment_matrix.tsv"
    )
    assert captured_cid["input_matrix_identity_tsv"] == (
        alignment_dir / "alignment_matrix_identity.tsv"
    )
    assert captured_chain["docs_root"] == output_dir / "docs"
    assert captured_chain["output_root"] == output_dir / "output"
    assert captured_chain["alignment_backfill_cell_evidence_tsv"] == (
        alignment_dir / "alignment_backfill_cell_evidence.tsv"
    )
    assert captured_chain["alignment_review_tsv"] == (
        alignment_dir / "alignment_review.tsv"
    )
    assert captured_chain["cid_nl_default_quant_matrix_tsv"] == (
        output_dir
        / "output"
        / "cid_nl_default_product_activation_v1"
        / "default_output"
        / "quant_matrix.tsv"
    )
    assert captured_chain["reuse_existing_raw_overlay"] is True
    assert captured_chain["reuse_existing_shift_aware"] is True
    assert outputs.summary_json == (
        output_dir / "backfill_expansion_productization_preset_summary.json"
    )
    assert (
        outputs.product_authority_scope
        == "backfill_expansion_clean_target_selective_activation_84_cells"
    )


def test_alignment_preset_wrapper_uses_pre_standard_peak_baseline_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    for name in (
        "alignment_matrix.tsv",
        "alignment_matrix_identity.tsv",
        "alignment_matrix.pre_standard_peak_backfill.tsv",
        "alignment_matrix_identity.pre_standard_peak_backfill.tsv",
        "alignment_backfill_cell_evidence.tsv",
        "alignment_review.tsv",
    ):
        (alignment_dir / name).write_text("x\n", encoding="utf-8")
    output_dir = tmp_path / "backfill_expansion_productization_preset"
    captured_cid: dict[str, object] = {}
    captured_chain: dict[str, object] = {}

    def fake_cid_activation(**kwargs):
        captured_cid.update(kwargs)
        return {}

    def fake_chain(**kwargs):
        captured_chain.update(kwargs)
        return {
            "clean_target_selective_activation_summary_json": str(
                kwargs["docs_root"]
                / "backfill_expansion_clean_target_selective_product_activation_v1"
                / (
                    "backfill_expansion_clean_target_selective_product_activation_"
                    "summary.json"
                )
            ),
            "product_authority_scope": (
                "backfill_expansion_clean_target_selective_activation_84_cells"
            ),
            "active_backfill_cell_count": 84,
        }

    monkeypatch.setattr(
        runner.cid_nl_activation,
        "build_cid_nl_default_product_activation",
        fake_cid_activation,
    )
    monkeypatch.setattr(
        runner,
        "run_backfill_expansion_full_evidence_chain",
        fake_chain,
    )

    runner.run_backfill_expansion_clean_target_selective_preset_from_alignment(
        alignment_dir=alignment_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
    )

    assert captured_cid["input_quant_matrix_tsv"] == (
        alignment_dir / "alignment_matrix.pre_standard_peak_backfill.tsv"
    )
    assert captured_cid["input_matrix_identity_tsv"] == (
        alignment_dir / "alignment_matrix_identity.pre_standard_peak_backfill.tsv"
    )
    assert captured_chain["input_matrix_identity_tsv"] == (
        alignment_dir / "alignment_matrix_identity.pre_standard_peak_backfill.tsv"
    )


def test_alignment_preset_wrapper_rejects_incomplete_pre_standard_peak_baseline(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    for name in (
        "alignment_matrix.tsv",
        "alignment_matrix_identity.tsv",
        "alignment_matrix.pre_standard_peak_backfill.tsv",
        "alignment_backfill_cell_evidence.tsv",
        "alignment_review.tsv",
    ):
        (alignment_dir / name).write_text("x\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="snapshot is incomplete"):
        runner.run_backfill_expansion_clean_target_selective_preset_from_alignment(
            alignment_dir=alignment_dir,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=tmp_path / "backfill_expansion_productization_preset",
        )
