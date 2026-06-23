from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.standard_peak_reintegration_stability_audit import (
    audit_reintegration_stability,
)
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_reintegration_stability_audit_classifies_dual_agreement(
    tmp_path: Path,
) -> None:
    stable_trace = tmp_path / "stable_trace_data.json"
    drift_trace = tmp_path / "drift_trace_data.json"
    stable_reference = _write_trace_json(
        stable_trace,
        family_id="FAM_STABLE",
        sample_stem="StableSample",
        far_peak=False,
    )
    drift_reference = _write_trace_json(
        drift_trace,
        family_id="FAM_DRIFT",
        sample_stem="DriftSample",
        far_peak=True,
    )
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    write_tsv(
        audit_tsv,
        [
            _audit_row(
                "FAM_STABLE",
                "StableSample",
                "stable-sha",
                stable_trace,
                stable_reference,
            ),
            _audit_row(
                "FAM_DRIFT",
                "DriftSample",
                "drift-sha",
                drift_trace,
                drift_reference,
            ),
        ],
        _AUDIT_COLUMNS,
    )

    output_dir = tmp_path / "audit"
    outputs = audit_reintegration_stability(
        activation_scope_audit_tsv=audit_tsv,
        output_dir=output_dir,
        source_run_id="unit",
        expected_window_padding_min=0.5,
    )

    rows = read_tsv_required(outputs.audit_tsv, outputs.audit_columns)
    by_sample = {row["sample_id"]: row for row in rows}
    assert by_sample["StableSample"]["stability_status"] == "eligible"
    assert by_sample["StableSample"]["stability_blockers"] == ""
    assert by_sample["DriftSample"]["stability_status"] == "ineligible"
    assert "full_trace_boundary_error_gt_0.1" in (
        by_sample["DriftSample"]["stability_blockers"]
    )
    assert "method_boundary_disagreement_gt_0.1" in (
        by_sample["DriftSample"]["stability_blockers"]
    )

    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "standard_peak_reintegration_stability_audit_v1"
    assert outputs.status == "candidate_pool_blocked"
    assert summary["status"] == "candidate_pool_blocked"
    assert summary["readiness_label"] == "production_candidate"
    assert summary["writer_authority_status"] == "blocked"
    assert summary["production_ready"] == "FALSE"
    assert summary["matrix_contract_changed"] == "FALSE"
    assert summary["source_activation_scope_schema_version"] == (
        "standard_peak_activation_scope_audit_v1"
    )
    assert summary["source_activation_scope_source_run_ids"] == "unit"
    assert len(summary["source_activation_scope_audit_sha256"]) == 64
    assert summary["eligible_written_count"] == "1"
    assert summary["ineligible_written_count"] == "1"


def test_reintegration_stability_audit_marks_missing_trace_evidence(
    tmp_path: Path,
) -> None:
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    write_tsv(
        audit_tsv,
        [
            {
                **_audit_row(
                    "FAM_MISSING",
                    "MissingSample",
                    "missing-sha",
                    tmp_path / "missing_trace_data.json",
                    _Reference(start=1.0, end=1.2, apex=1.1, area=100.0),
                ),
                "trace_match_status": "missing_overlay_path",
                "trace_data_path": "",
            }
        ],
        _AUDIT_COLUMNS,
    )

    outputs = audit_reintegration_stability(
        activation_scope_audit_tsv=audit_tsv,
        output_dir=tmp_path / "audit",
        source_run_id="unit",
    )

    rows = read_tsv_required(outputs.audit_tsv, outputs.audit_columns)
    assert rows[0]["stability_status"] == "missing_evidence"
    assert rows[0]["stability_blockers"] == "trace_not_matched"
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["missing_evidence_written_count"] == "1"


def test_reintegration_stability_audit_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    from tools.diagnostics import standard_peak_reintegration_stability_audit as cli

    trace_path = tmp_path / "stable_trace_data.json"
    reference = _write_trace_json(
        trace_path,
        family_id="FAM_STABLE",
        sample_stem="StableSample",
        far_peak=False,
    )
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    write_tsv(
        audit_tsv,
        [
            _audit_row(
                "FAM_STABLE",
                "StableSample",
                "stable-sha",
                trace_path,
                reference,
            )
        ],
        _AUDIT_COLUMNS,
    )
    output_dir = tmp_path / "audit"

    assert (
        cli.main(
            [
                "--activation-scope-audit-tsv",
                str(audit_tsv),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-cli",
            ],
        )
        == 0
    )

    summary = json.loads(
        (output_dir / "reintegration_stability_summary.json").read_text(
            encoding="utf-8",
        ),
    )
    assert summary["source_run_id"] == "unit-cli"
    assert summary["eligible_written_count"] == "1"
    assert (
        cli.main(
            [
                "--activation-scope-audit-tsv",
                str(audit_tsv),
                "--output-dir",
                str(tmp_path / "audit_bad_padding"),
                "--source-run-id",
                "unit-cli",
                "--expected-window-padding-min",
                "inf",
            ],
        )
        == 2
    )


@pytest.mark.parametrize(
    "padding",
    [float("nan"), float("inf"), 0.500001],
)
def test_reintegration_stability_audit_rejects_unsafe_padding(
    tmp_path: Path,
    padding: float,
) -> None:
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    write_tsv(
        audit_tsv,
        [
            _audit_row(
                "FAM_STABLE",
                "StableSample",
                "stable-sha",
                tmp_path / "stable_trace_data.json",
                _Reference(start=1.0, end=1.2, apex=1.1, area=100.0),
            )
        ],
        _AUDIT_COLUMNS,
    )

    with pytest.raises(ValueError, match="expected_window_padding_min"):
        audit_reintegration_stability(
            activation_scope_audit_tsv=audit_tsv,
            output_dir=tmp_path / "audit",
            source_run_id="unit",
            expected_window_padding_min=padding,
        )


def test_reintegration_stability_audit_rejects_wrong_source_schema(
    tmp_path: Path,
) -> None:
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    row = _audit_row(
        "FAM_STABLE",
        "StableSample",
        "stable-sha",
        tmp_path / "stable_trace_data.json",
        _Reference(start=1.0, end=1.2, apex=1.1, area=100.0),
    )
    row["schema_version"] = "wrong_schema_v1"
    write_tsv(audit_tsv, [row], _AUDIT_COLUMNS)

    with pytest.raises(ValueError, match="expected schema_version"):
        audit_reintegration_stability(
            activation_scope_audit_tsv=audit_tsv,
            output_dir=tmp_path / "audit",
            source_run_id="unit",
        )


def test_reintegration_stability_audit_rejects_blank_source_run_id(
    tmp_path: Path,
) -> None:
    audit_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    row = _audit_row(
        "FAM_STABLE",
        "StableSample",
        "stable-sha",
        tmp_path / "stable_trace_data.json",
        _Reference(start=1.0, end=1.2, apex=1.1, area=100.0),
    )
    row["source_run_id"] = ""
    write_tsv(audit_tsv, [row], _AUDIT_COLUMNS)

    with pytest.raises(ValueError, match="source_run_id"):
        audit_reintegration_stability(
            activation_scope_audit_tsv=audit_tsv,
            output_dir=tmp_path / "audit",
            source_run_id="unit",
        )


class _Reference:
    def __init__(self, *, start: float, end: float, apex: float, area: float) -> None:
        self.start = start
        self.end = end
        self.apex = apex
        self.area = area


_AUDIT_COLUMNS = (
    "schema_version",
    "source_run_id",
    "feature_family_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    "trace_match_status",
    "trace_status",
    "cell_area",
    "cell_start_rt",
    "cell_end_rt",
    "cell_apex_rt",
    "trace_data_path",
)


def _audit_row(
    family_id: str,
    sample_id: str,
    row_sha: str,
    trace_path: Path,
    reference: _Reference,
) -> dict[str, str]:
    return {
        "schema_version": "standard_peak_activation_scope_audit_v1",
        "source_run_id": "unit",
        "feature_family_id": family_id,
        "sample_id": sample_id,
        "matrix_value_effect": "written",
        "matrix_value_source_row_sha256": row_sha,
        "trace_match_status": "matched",
        "trace_status": "rescued",
        "cell_area": f"{reference.area:.8f}",
        "cell_start_rt": f"{reference.start:.5f}",
        "cell_end_rt": f"{reference.end:.5f}",
        "cell_apex_rt": f"{reference.apex:.5f}",
        "trace_data_path": str(trace_path),
    }


def _write_trace_json(
    path: Path,
    *,
    family_id: str,
    sample_stem: str,
    far_peak: bool,
) -> _Reference:
    rt = np.round(np.arange(0.0, 3.01, 0.03), 4)
    central = 2_500_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.08**2))
    far = 8_000_000.0 * np.exp(-((rt - 2.1) ** 2) / (2 * 0.08**2))
    intensity = 1_000.0 + central + (far if far_peak else 0.0)
    mask = (rt >= 0.5) & (rt <= 1.5)
    reference = _integrate_reference(rt[mask], intensity[mask])
    path.write_text(
        json.dumps(
            {
                "family_id": family_id,
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": sample_stem,
                        "status": "rescued",
                        "cell_area": reference.area,
                        "cell_height": float(max(intensity)),
                        "cell_start_rt": reference.start,
                        "cell_end_rt": reference.end,
                        "cell_apex_rt": reference.apex,
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.98,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    }
                ],
            },
        ),
        encoding="utf-8",
    )
    return reference


def _integrate_reference(rt: np.ndarray, intensity: np.ndarray) -> _Reference:
    result = find_peak_and_area(
        rt,
        intensity,
        _config(),
        preferred_rt=1.0,
        strict_preferred_rt=True,
    )
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    return _Reference(
        start=result.peak.peak_start,
        end=result.peak.peak_end,
        apex=result.peak.rt,
        area=integration.area_ms1_morphology,
    )


def _config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("unused.csv"),
        diagnostics_csv=Path("unused_diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.05,
        peak_min_prominence_ratio=0.0,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.0,
        resolver_mode="local_minimum",
        resolver_min_search_range_min=0.08,
        resolver_min_relative_height=0.02,
        resolver_min_ratio_top_edge=1.7,
        resolver_peak_duration_max=2.0,
        baseline_integration_method="asls",
    )
