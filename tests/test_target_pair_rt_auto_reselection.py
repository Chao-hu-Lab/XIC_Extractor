import csv
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.output_dispatch import write_outputs
from xic_extractor.extractor import FileResult, RunOutput
from xic_extractor.output.target_pair_rt_auto_reselection import (
    TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS,
    build_target_pair_rt_auto_reselection_rows,
    summarize_target_pair_rt_auto_reselection_rows,
    write_target_pair_rt_auto_reselection_tsv,
)
from xic_extractor.peak_detection.model_selection import PeakModelSelectionResult
from xic_extractor.target_pair_rt_calibration import (
    TARGET_PAIR_RT_CALIBRATION_SCHEMA_VERSION,
    TargetPairRTCalibrationRow,
    write_target_pair_rt_calibration_tsv,
)


def test_shadow_rows_can_propose_8oxodg_without_product_mutation() -> None:
    targets = [_target("8-oxodG", istd_pair="15N5-8-oxodG"), _istd()]
    file_result = _file_result(
        sample_name="TumorBC2263_DNA",
        target_label="8-oxodG",
        paired_label="15N5-8-oxodG",
        model=_model_result(
            legacy_selected_candidate_id="legacy-15min",
            selected_candidate_id="successor-16min",
            selection_status="expected_diff",
        ),
        peak_candidate_rows=[
            _candidate_row("8-oxodG", "legacy-15min", "15.20000"),
            _candidate_row("8-oxodG", "successor-16min", "16.60000"),
        ],
    )

    rows = build_target_pair_rt_auto_reselection_rows(
        [file_result],
        targets=targets,
        calibration_rows=[_calibration(target_label="8-oxodG")],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_name"] == "TumorBC2263_DNA"
    assert row["target_label"] == "8-oxodG"
    assert row["selection_action"] == "shadow_auto_reselect_proposed"
    assert row["product_switch_allowed"] == "FALSE"
    assert row["previous_candidate_id"] == "legacy-15min"
    assert row["selected_candidate_id"] == "successor-16min"
    assert row["selected_candidate_rt"] == "16.60000"
    assert row["paired_istd_rt"] == "16.55000"
    assert row["pair_rt_delta_observed"] == "0.05000"
    assert row["gate_decision"] == "externalize"
    assert "phase_2_product_switch_blocked" in row["block_reason"]

    summary = summarize_target_pair_rt_auto_reselection_rows(rows)
    assert summary["shadow_auto_reselect_proposed_count"] == "1"
    assert summary["changed_row_denominator"] == "1"
    assert summary["product_switch_allowed_true_count"] == "0"
    assert summary["auto_reselected_count"] == "0"


def test_shadow_rows_block_hash_mismatch_and_do_not_promote() -> None:
    target = _target("d3-5-medC", is_istd=True)
    file_result = _file_result(
        sample_name="TumorBC2289_DNA",
        target_label="d3-5-medC",
        paired_label="",
        model=_model_result(
            legacy_selected_candidate_id="legacy",
            selected_candidate_id="legacy",
            selection_status="parity",
        ),
        peak_candidate_rows=[_candidate_row("d3-5-medC", "legacy", "12.05000")],
    )
    calibration = _calibration(
        target_label="d3-5-medC",
        paired_istd_label="d3-5-medC",
        activation_block_reason="target_config_hash_mismatch",
    )

    rows = build_target_pair_rt_auto_reselection_rows(
        [file_result],
        targets=[target],
        calibration_rows=[calibration],
    )

    assert rows[0]["selection_action"] == "auto_reselect_blocked"
    assert rows[0]["product_switch_allowed"] == "FALSE"
    assert rows[0]["block_reason"] == "target_config_hash_mismatch"


def test_shadow_writer_serializes_schema_and_forces_product_switch_false(
    tmp_path: Path,
) -> None:
    path = tmp_path / "target_pair_rt_auto_reselection.tsv"
    row = {
        header: "value" for header in TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS
    }
    row["selection_action"] = "shadow_auto_reselect_proposed"
    row["product_switch_allowed"] = "TRUE"

    write_target_pair_rt_auto_reselection_tsv(path, [row])

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames == list(TARGET_PAIR_RT_AUTO_RESELECTION_HEADERS)
        rows = list(reader)
    assert rows[0]["product_switch_allowed"] == "FALSE"


def test_output_dispatch_emits_shadow_tsv_only_with_peer_diagnostics(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "target_pair_rt_calibration.tsv"
    write_target_pair_rt_calibration_tsv(
        calibration_path,
        [_calibration(target_config_hash="targethash")],
    )
    config = _config(
        tmp_path,
        emit_peak_candidates=True,
        calibration_path=calibration_path,
        target_config_hash="targethash",
    )
    targets = [_target("8-oxodG", istd_pair="15N5-8-oxodG"), _istd()]
    output = RunOutput(
        file_results=[
            _file_result(
                sample_name="TumorBC2263_DNA",
                target_label="8-oxodG",
                paired_label="15N5-8-oxodG",
                model=_model_result(
                    legacy_selected_candidate_id="legacy",
                    selected_candidate_id="successor",
                    selection_status="expected_diff",
                ),
                peak_candidate_rows=[
                    _candidate_row("8-oxodG", "legacy", "15.20000"),
                    _candidate_row("8-oxodG", "successor", "16.60000"),
                ],
            )
        ],
        diagnostics=[],
    )

    write_outputs(config, targets, output)

    assert config.output_csv.with_name("peak_candidates.tsv").exists()
    assert config.output_csv.with_name("target_pair_rt_auto_reselection.tsv").exists()
    assert config.output_csv.with_name(
        "target_pair_rt_auto_reselection_summary.tsv"
    ).exists()


def test_output_dispatch_skips_shadow_tsv_when_candidate_diagnostics_disabled(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "target_pair_rt_calibration.tsv"
    write_target_pair_rt_calibration_tsv(calibration_path, [_calibration()])
    config = _config(
        tmp_path,
        emit_peak_candidates=False,
        calibration_path=calibration_path,
    )
    output = RunOutput(file_results=[], diagnostics=[])

    write_outputs(config, [_target("8-oxodG")], output)

    assert not config.output_csv.with_name(
        "target_pair_rt_auto_reselection.tsv"
    ).exists()
    assert output.diagnostics[0].issue == "TARGET_PAIR_RT_AUTO_RESELECTION_SKIPPED"


def _config(
    tmp_path: Path,
    *,
    emit_peak_candidates: bool,
    calibration_path: Path,
    target_config_hash: str = "",
) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path,
        output_csv=tmp_path / "output" / "xic_results.csv",
        diagnostics_csv=tmp_path / "output" / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        emit_peak_candidates=emit_peak_candidates,
        target_pair_rt_calibration_path=calibration_path,
        target_config_hash=target_config_hash,
    )


def _target(
    label: str,
    *,
    istd_pair: str = "",
    is_istd: bool = False,
) -> Target:
    return Target(
        label=label,
        mz=284.0989,
        rt_min=15.0,
        rt_max=18.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=is_istd,
        istd_pair=istd_pair,
        paired_rt_relation="learned_delta_only" if istd_pair else "none",
    )


def _istd() -> Target:
    return _target("15N5-8-oxodG", is_istd=True)


def _file_result(
    *,
    sample_name: str,
    target_label: str,
    paired_label: str,
    model: PeakModelSelectionResult,
    peak_candidate_rows: list[dict[str, str]],
) -> FileResult:
    return FileResult(
        sample_name=sample_name,
        results={
            target_label: SimpleNamespace(
                model_selection_result=model,
                reported_rt=15.2,
                candidate_ms2_evidence=None,
                nl_token="NO_MS2",
            ),
            paired_label: SimpleNamespace(reported_rt=16.55),
        },
        peak_candidate_rows=peak_candidate_rows,
    )


def _candidate_row(
    target_label: str,
    candidate_id: str,
    rt_apex_min: str,
) -> dict[str, str]:
    return {
        "sample_name": "TumorBC2263_DNA",
        "target_label": target_label,
        "candidate_id": candidate_id,
        "rt_apex_min": rt_apex_min,
    }


def _model_result(
    *,
    legacy_selected_candidate_id: str,
    selected_candidate_id: str,
    selection_status: str,
) -> PeakModelSelectionResult:
    return PeakModelSelectionResult(
        selected_candidate_id=selected_candidate_id,
        legacy_selected_candidate_id=legacy_selected_candidate_id,
        stable_row_id="model_selection|legacy=legacy|successor=successor",
        trace_group_id="TumorBC2263_DNA|8-oxodG|region_first_safe_merge",
        decision_class="review",
        selection_status=selection_status,
        selection_reasons=("paired_rt_support",),
        legacy_reasons=("selected_by_legacy_scoring",),
        diff_reasons=(),
        public_projection={},
        evidence_sources=("ms1_trace", "role_aware_rt"),
        compatibility_oracle="legacy_peak_scoring_current_oracle",
        policy_source="selected_hypothesis_model_selection_v1",
        product_switch_allowed=False,
        evidence_comparison_policy="limited_evidence_shadow",
    )


def _calibration(
    *,
    target_label: str = "8-oxodG",
    paired_istd_label: str = "15N5-8-oxodG",
    target_config_hash: str = "targethash",
    activation_block_reason: str = "",
) -> TargetPairRTCalibrationRow:
    return TargetPairRTCalibrationRow(
        schema_version=TARGET_PAIR_RT_CALIBRATION_SCHEMA_VERSION,
        target_config_hash=target_config_hash,
        source_artifact="mixstds.tsv",
        source_hash="sourcehash",
        source_hash_status="present",
        target_label=target_label,
        paired_istd_label=paired_istd_label,
        pair_rt_delta_min=0.05,
        delta_source="mixstds_clean_standard",
        point_count=6,
        rt_delta_median_min=0.05,
        rt_delta_mad_min=0.01,
        rt_delta_direction="target_later",
        isotope_label_type="heavy_non_deuterium",
        paired_rt_relation="learned_delta_only",
        calibration_status="usable",
        calibration_level="clean_standard_only",
        product_transfer_status="not_assessed",
        activation_block_reason=activation_block_reason,
    )
