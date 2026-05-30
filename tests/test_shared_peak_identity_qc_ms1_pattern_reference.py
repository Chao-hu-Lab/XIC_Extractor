from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics import qc_ms1_pattern_reference as qc_reference_cli
from xic_extractor.alignment.shared_peak_identity_explanation import (
    qc_ms1_pattern_reference,
)


def test_qc_ms1_pattern_reference_supports_nearest_qc_match(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_overlay(
        overlay,
        target_apex_rt=10.01,
        qc_apex_rt=10.00,
        target_intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
        qc_intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "TumorBC0001_DNA"),),
        injection_order={
            "TumorBC0001_DNA": 10,
            "Breast_Cancer_Tissue_pooled_QC5": 11,
        },
    )

    assert rows[0]["qc_reference_status"] == "supportive"
    assert rows[0]["qc_reference_evidence_level"] == (
        "nearest_complete_peak_qc_overlay"
    )
    assert rows[0]["nearest_qc_sample_stem"] == "Breast_Cancer_Tissue_pooled_QC5"
    assert rows[0]["nearest_qc_injection_order_delta"] == "1"
    assert rows[0]["reason"] == "nearest_qc_ms1_pattern_supported"


def test_qc_ms1_pattern_reference_conflicts_when_qc_peak_is_separated(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_overlay(
        overlay,
        target_apex_rt=18.50,
        qc_apex_rt=19.50,
        target_intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
        qc_intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "TumorBC0001_DNA"),),
        injection_order={
            "TumorBC0001_DNA": 10,
            "Breast_Cancer_Tissue_pooled_QC5": 11,
        },
    )

    assert rows[0]["qc_reference_status"] == "conflict"
    assert rows[0]["target_qc_apex_abs_delta_sec"] == "60"
    assert rows[0]["reason"] == "nearest_qc_peak_separated_from_target_cell"


def test_qc_ms1_pattern_reference_requires_qc_injection_order(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    _write_overlay(
        overlay,
        target_apex_rt=10.0,
        qc_apex_rt=10.0,
        target_intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
        qc_intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "TumorBC0001_DNA"),),
        injection_order={"TumorBC0001_DNA": 10},
    )

    assert rows[0]["qc_reference_status"] == "not_available"
    assert rows[0]["reason"] == "nearest_qc_reference_missing"


def test_qc_ms1_pattern_reference_prefers_nearby_complete_qc_peak(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    overlay.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "traces": [
                    _trace(
                        "TumorBC0001_DNA",
                        "Tumor",
                        apex_rt=18.50,
                        intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
                    ),
                    {
                        "sample_stem": "Breast_Cancer_Tissue_pooled_QC3",
                        "group": "QC",
                    },
                    _trace(
                        "Breast_Cancer_Tissue_pooled_QC5",
                        "QC",
                        apex_rt=19.50,
                        intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "TumorBC0001_DNA"),),
        injection_order={
            "TumorBC0001_DNA": 10,
            "Breast_Cancer_Tissue_pooled_QC3": 9,
            "Breast_Cancer_Tissue_pooled_QC5": 30,
        },
    )

    assert rows[0]["nearest_qc_sample_stem"] == "Breast_Cancer_Tissue_pooled_QC5"
    assert rows[0]["qc_reference_status"] == "conflict"
    assert rows[0]["reason"] == "nearest_qc_peak_separated_from_target_cell"


def test_qc_ms1_pattern_reference_prefers_family_centered_qc_peak(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    overlay.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "family_center_rt": 19.50,
                "traces": [
                    _trace(
                        "BenignfatBC0001_DNA",
                        "Benign",
                        apex_rt=19.49,
                        intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
                    ),
                    _trace(
                        "Breast_Cancer_Tissue_pooled_QC6",
                        "QC",
                        apex_rt=18.91,
                        intensity=(0.0, 25.0, 100.0, 30.0, 0.0),
                    ),
                    _trace(
                        "Breast_Cancer_Tissue_pooled_QC5",
                        "QC",
                        apex_rt=19.50,
                        intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "BenignfatBC0001_DNA"),),
        injection_order={
            "BenignfatBC0001_DNA": 84,
            "Breast_Cancer_Tissue_pooled_QC6": 81,
            "Breast_Cancer_Tissue_pooled_QC5": 65,
        },
    )

    assert rows[0]["nearest_qc_sample_stem"] == "Breast_Cancer_Tissue_pooled_QC5"
    assert rows[0]["qc_reference_status"] == "supportive"
    assert rows[0]["qc_reference_evidence_level"] == (
        "nearest_complete_family_centered_qc_overlay"
    )


def test_qc_ms1_pattern_reference_rejects_blank_raw_trace_qc(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    blank_qc = _trace(
        "Breast_Cancer_Tissue_pooled_QC6",
        "QC",
        apex_rt=19.50,
        intensity=(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    blank_qc["trace_apex_rt"] = None
    blank_qc["local_window_max_intensity"] = None
    blank_qc["local_window_to_global_max_ratio"] = None
    overlay.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "family_center_rt": 19.50,
                "traces": [
                    _trace(
                        "BenignfatBC0001_DNA",
                        "Benign",
                        apex_rt=19.49,
                        intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
                    ),
                    blank_qc,
                    _trace(
                        "Breast_Cancer_Tissue_pooled_QC5",
                        "QC",
                        apex_rt=19.50,
                        intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = qc_ms1_pattern_reference.build_qc_ms1_pattern_reference_rows(
        family_ms1_overlay_trace_data_jsons=(overlay,),
        oracle_keys=(("FAM001", "BenignfatBC0001_DNA"),),
        injection_order={
            "BenignfatBC0001_DNA": 84,
            "Breast_Cancer_Tissue_pooled_QC6": 83,
            "Breast_Cancer_Tissue_pooled_QC5": 65,
        },
    )

    assert rows[0]["nearest_qc_sample_stem"] == "Breast_Cancer_Tissue_pooled_QC5"
    assert rows[0]["qc_reference_status"] == "supportive"


def test_qc_ms1_pattern_reference_cli_writes_tsv(tmp_path: Path) -> None:
    overlay = tmp_path / "fam001_overlay_trace_data.json"
    injection_order = tmp_path / "injection_order.csv"
    output = tmp_path / "qc_reference.tsv"
    _write_overlay(
        overlay,
        target_apex_rt=10.01,
        qc_apex_rt=10.00,
        target_intensity=(0.0, 30.0, 100.0, 35.0, 0.0),
        qc_intensity=(0.0, 28.0, 100.0, 32.0, 0.0),
    )
    injection_order.write_text(
        "Sample_Name,Injection_Order\n"
        "TumorBC0001_DNA,10\n"
        "Breast_Cancer_Tissue_pooled_QC5,11\n",
        encoding="utf-8",
    )

    exit_code = qc_reference_cli.main(
        (
            "--overlay-trace-data-json",
            str(overlay),
            "--injection-order-source",
            str(injection_order),
            "--oracle-key",
            "FAM001|TumorBC0001_DNA",
            "--output-tsv",
            str(output),
        )
    )

    assert exit_code == 0
    assert "nearest_qc_ms1_pattern_supported" in output.read_text(encoding="utf-8")


def _write_overlay(
    path: Path,
    *,
    target_apex_rt: float,
    qc_apex_rt: float,
    target_intensity: tuple[float, ...],
    qc_intensity: tuple[float, ...],
) -> None:
    path.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "traces": [
                    _trace(
                        "TumorBC0001_DNA",
                        "Tumor",
                        apex_rt=target_apex_rt,
                        intensity=target_intensity,
                    ),
                    _trace(
                        "Breast_Cancer_Tissue_pooled_QC5",
                        "QC",
                        apex_rt=qc_apex_rt,
                        intensity=qc_intensity,
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )


def _trace(
    sample_stem: str,
    group: str,
    *,
    apex_rt: float,
    intensity: tuple[float, ...],
) -> dict[str, object]:
    offsets = (-0.2, -0.1, 0.0, 0.1, 0.2)
    return {
        "sample_stem": sample_stem,
        "group": group,
        "cell_apex_rt": apex_rt,
        "trace_apex_rt": apex_rt,
        "cell_height": max(intensity),
        "local_window_max_intensity": max(intensity),
        "trace_max_intensity": max(intensity),
        "local_window_to_global_max_ratio": 1.0,
        "rt": [apex_rt + offset for offset in offsets],
        "intensity": list(intensity),
    }
