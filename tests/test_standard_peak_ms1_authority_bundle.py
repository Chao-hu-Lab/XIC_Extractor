from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics import standard_peak_ms1_authority_bundle as cli
from xic_extractor.alignment.backfill_evidence_projection import (
    PRODUCT_AUTHORITY_SCOPE_FIELD,
    PRODUCT_AUTHORITY_SOURCE_FIELD,
    PRODUCT_AUTHORITY_STATUS_FIELD,
    PRODUCT_AUTHORIZED_SCOPE,
    PRODUCT_AUTHORIZED_STATUS,
)
from xic_extractor.alignment.backfill_ms1_product_authority import SCHEMA_VERSION
from xic_extractor.alignment.promotion_policy import (
    STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
)
from xic_extractor.diagnostics.standard_peak_ms1_authority_bundle import (
    AUTHORITY_MODE_MACHINE_GATE,
    run_standard_peak_ms1_authority_bundle,
)


def test_standard_peak_gate_bundle_authorizes_manual_supported_rescued_cells(
    tmp_path: Path,
) -> None:
    overlay_dir = tmp_path / "overlay"
    trace_json = _write_trace_json(overlay_dir, "FAM_STD")
    trace_summary = overlay_dir / "fam_std_trace_summary.tsv"
    _write_tsv(
        trace_summary,
        (
            "sample_stem",
            "status",
            "cell_area",
            "cell_height",
            "cell_apex_rt",
            "cell_start_rt",
            "cell_end_rt",
            "local_window_apex_delta_min",
            "local_window_to_global_max_ratio",
            "apex_aligned_shape_similarity",
            "absolute_own_max_shape_similarity",
        ),
        [
            {
                "sample_stem": "S1",
                "status": "rescued",
                "cell_area": "1234",
                "cell_height": "200",
                "cell_apex_rt": "10.0",
                "cell_start_rt": "9.8",
                "cell_end_rt": "10.2",
                "local_window_apex_delta_min": "0.01",
                "local_window_to_global_max_ratio": "0.95",
                "apex_aligned_shape_similarity": "0.70",
                "absolute_own_max_shape_similarity": "0.92",
            },
            {
                "sample_stem": "S2",
                "status": "detected",
                "cell_area": "500",
                "cell_height": "80",
                "cell_apex_rt": "10.0",
                "cell_start_rt": "9.8",
                "cell_end_rt": "10.2",
                "local_window_apex_delta_min": "0.0",
                "local_window_to_global_max_ratio": "1.0",
                "apex_aligned_shape_similarity": "0.99",
                "absolute_own_max_shape_similarity": "0.99",
            },
        ],
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    _write_tsv(
        overlay_summary,
        (
            "feature_family_id",
            "family_verdict",
            "detected_count",
            "rescued_count",
            "detected_rescued_count",
            "absolute_own_max_shape_supported_count",
            "trace_summary_tsv",
            "trace_data_json",
        ),
        [
            {
                "feature_family_id": "FAM_STD",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "detected_count": "1",
                "rescued_count": "1",
                "detected_rescued_count": "2",
                "absolute_own_max_shape_supported_count": "2",
                "trace_summary_tsv": str(trace_summary),
                "trace_data_json": str(trace_json),
            }
        ],
    )
    standard_gate = tmp_path / "shift_aware_standard_peak_gate_calibration.tsv"
    _write_tsv(
        standard_gate,
        (
            "feature_family_id",
            "standard_peak_gate_call",
            "standard_peak_gate_reasons",
            "standard_peak_gate_blockers",
            "manual_backfill_authority_call",
            "calibration_outcome",
            "min_shape_r_after_best_shift",
            "max_abs_shift_sec",
        ),
        [
            {
                "feature_family_id": "FAM_STD",
                "standard_peak_gate_call": "standard_peak_gate_supported",
                "standard_peak_gate_reasons": "shift_aware_same_pattern_supported",
                "standard_peak_gate_blockers": "",
                "manual_backfill_authority_call": (
                    "authorize_standard_peak_backfill"
                ),
                "calibration_outcome": "true_positive",
                "min_shape_r_after_best_shift": "0.99",
                "max_abs_shift_sec": "0",
            },
            {
                "feature_family_id": "FAM_BLOCK",
                "standard_peak_gate_call": "standard_peak_gate_blocked",
                "standard_peak_gate_reasons": "shift_aware_same_pattern_supported",
                "standard_peak_gate_blockers": "not_standard",
                "manual_backfill_authority_call": "reject_non_standard_peak",
                "calibration_outcome": "true_negative",
                "min_shape_r_after_best_shift": "0.99",
                "max_abs_shift_sec": "0",
            },
        ],
    )

    outputs = run_standard_peak_ms1_authority_bundle(
        standard_peak_gate_tsv=standard_gate,
        overlay_batch_summary_tsv=overlay_summary,
        output_dir=tmp_path / "out",
    )

    source_rows = _read_tsv(outputs.ms1_pattern_evidence_tsv)
    allowlist_rows = _read_tsv(outputs.authority_allowlist_tsv)
    authorized_rows = _read_tsv(outputs.authorized_ms1_pattern_tsv)
    audit_rows = _read_tsv(outputs.authority_audit_tsv)
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))

    assert [row["sample_stem"] for row in source_rows] == ["S1"]
    assert source_rows[0]["diagnostic_only"] == "TRUE"
    assert source_rows[0]["reason"] == STANDARD_PEAK_GATE_MS1_SUPPORT_REASON
    assert (
        source_rows[0]["family_ms1_overlay_trace_data_json"]
        == "trace_data/FAM_STD_trace_data.json"
    )
    assert allowlist_rows[0]["schema_version"] == SCHEMA_VERSION
    assert allowlist_rows[0]["authority_status"] == PRODUCT_AUTHORIZED_STATUS
    assert len(authorized_rows) == 1
    assert authorized_rows[0]["diagnostic_only"] == "FALSE"
    assert (
        authorized_rows[0][PRODUCT_AUTHORITY_STATUS_FIELD]
        == PRODUCT_AUTHORIZED_STATUS
    )
    assert (
        authorized_rows[0][PRODUCT_AUTHORITY_SCOPE_FIELD]
        == PRODUCT_AUTHORIZED_SCOPE
    )
    assert (
        authorized_rows[0][PRODUCT_AUTHORITY_SOURCE_FIELD]
        == "manual_standard_peak_gate_calibration"
    )
    assert audit_rows[0]["decision"] == "authorized"
    assert summary["authorized_row_count"] == 1
    assert summary["matrix_contract_changed"] is False
    assert summary["product_behavior_changed"] is False


def test_machine_gate_authorizes_supported_standard_peak_without_manual_allowlist(
    tmp_path: Path,
) -> None:
    overlay_dir = tmp_path / "overlay"
    trace_json = _write_trace_json(overlay_dir, "FAM_AUTO")
    trace_summary = overlay_dir / "fam_auto_trace_summary.tsv"
    _write_tsv(
        trace_summary,
        (
            "sample_stem",
            "status",
            "cell_area",
            "cell_height",
            "cell_apex_rt",
            "cell_start_rt",
            "cell_end_rt",
            "local_window_apex_delta_min",
            "local_window_to_global_max_ratio",
            "apex_aligned_shape_similarity",
            "absolute_own_max_shape_similarity",
        ),
        [
            {
                "sample_stem": "S1",
                "status": "rescued",
                "cell_area": "1234",
                "cell_height": "200",
                "cell_apex_rt": "10.0",
                "cell_start_rt": "9.8",
                "cell_end_rt": "10.2",
                "local_window_apex_delta_min": "0.01",
                "local_window_to_global_max_ratio": "0.95",
                "apex_aligned_shape_similarity": "0.70",
                "absolute_own_max_shape_similarity": "0.92",
            }
        ],
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    _write_tsv(
        overlay_summary,
        (
            "feature_family_id",
            "family_verdict",
            "detected_count",
            "rescued_count",
            "detected_rescued_count",
            "absolute_own_max_shape_supported_count",
            "trace_summary_tsv",
            "trace_data_json",
        ),
        [
            {
                "feature_family_id": "FAM_AUTO",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "detected_count": "1",
                "rescued_count": "1",
                "detected_rescued_count": "2",
                "absolute_own_max_shape_supported_count": "2",
                "trace_summary_tsv": str(trace_summary),
                "trace_data_json": str(trace_json),
            }
        ],
    )
    standard_gate = tmp_path / "shift_aware_standard_peak_gate_calibration.tsv"
    _write_tsv(
        standard_gate,
        (
            "feature_family_id",
            "standard_peak_gate_call",
            "standard_peak_gate_reasons",
            "standard_peak_gate_blockers",
            "manual_backfill_authority_call",
            "calibration_outcome",
            "min_shape_r_after_best_shift",
            "max_abs_shift_sec",
        ),
        [
            {
                "feature_family_id": "FAM_AUTO",
                "standard_peak_gate_call": "standard_peak_gate_supported",
                "standard_peak_gate_reasons": "shift_aware_same_pattern_supported",
                "standard_peak_gate_blockers": "",
                "manual_backfill_authority_call": "",
                "calibration_outcome": "unlabeled_machine_supported",
                "min_shape_r_after_best_shift": "0.99",
                "max_abs_shift_sec": "0",
            }
        ],
    )

    manual_outputs = run_standard_peak_ms1_authority_bundle(
        standard_peak_gate_tsv=standard_gate,
        overlay_batch_summary_tsv=overlay_summary,
        output_dir=tmp_path / "manual_out",
    )
    machine_outputs = run_standard_peak_ms1_authority_bundle(
        standard_peak_gate_tsv=standard_gate,
        overlay_batch_summary_tsv=overlay_summary,
        output_dir=tmp_path / "machine_out",
        authority_mode=AUTHORITY_MODE_MACHINE_GATE,
    )

    manual_summary = json.loads(
        manual_outputs.summary_json.read_text(encoding="utf-8"),
    )
    machine_summary = json.loads(
        machine_outputs.summary_json.read_text(encoding="utf-8"),
    )
    manual_authorized = _read_tsv(manual_outputs.authorized_ms1_pattern_tsv)
    machine_authorized = _read_tsv(machine_outputs.authorized_ms1_pattern_tsv)

    assert manual_summary["authorized_row_count"] == 0
    assert manual_summary["skipped_counts"] == {
        "gate_not_manual_authorized_standard_peak": 1
    }
    assert manual_authorized == []
    assert machine_summary["authority_mode"] == "machine-gate"
    assert (
        machine_summary["authority_source"]
        == "machine_shift_aware_standard_peak_gate"
    )
    assert machine_summary["authorized_row_count"] == 1
    assert len(machine_authorized) == 1
    assert (
        machine_authorized[0][PRODUCT_AUTHORITY_SOURCE_FIELD]
        == "machine_shift_aware_standard_peak_gate"
    )
    assert "machine_standard_peak_gate_authorized" in machine_authorized[0][
        "product_authority_reason"
    ]
    assert (
        machine_authorized[0]["reason"]
        == STANDARD_PEAK_GATE_MS1_SUPPORT_REASON
    )


def test_standard_peak_authority_cli_writes_bundle(tmp_path: Path) -> None:
    overlay_dir = tmp_path / "overlay"
    trace_json = _write_trace_json(overlay_dir, "FAM_STD")
    trace_summary = overlay_dir / "fam_std_trace_summary.tsv"
    _write_tsv(
        trace_summary,
        (
            "sample_stem",
            "status",
            "cell_area",
            "cell_height",
            "cell_apex_rt",
            "cell_start_rt",
            "cell_end_rt",
            "local_window_apex_delta_min",
            "local_window_to_global_max_ratio",
            "apex_aligned_shape_similarity",
            "absolute_own_max_shape_similarity",
        ),
        [
            {
                "sample_stem": "S1",
                "status": "rescued",
                "cell_area": "1234",
                "cell_height": "200",
                "cell_apex_rt": "10.0",
                "cell_start_rt": "9.8",
                "cell_end_rt": "10.2",
                "local_window_apex_delta_min": "0.01",
                "local_window_to_global_max_ratio": "1",
                "apex_aligned_shape_similarity": "0.90",
                "absolute_own_max_shape_similarity": "0.95",
            },
        ],
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    _write_tsv(
        overlay_summary,
        (
            "feature_family_id",
            "family_verdict",
            "detected_count",
            "rescued_count",
            "detected_rescued_count",
            "absolute_own_max_shape_supported_count",
            "trace_summary_tsv",
            "trace_data_json",
        ),
        [
            {
                "feature_family_id": "FAM_STD",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "detected_count": "1",
                "rescued_count": "1",
                "detected_rescued_count": "2",
                "absolute_own_max_shape_supported_count": "2",
                "trace_summary_tsv": str(trace_summary),
                "trace_data_json": str(trace_json),
            }
        ],
    )
    standard_gate = tmp_path / "standard_gate.tsv"
    _write_tsv(
        standard_gate,
        (
            "feature_family_id",
            "standard_peak_gate_call",
            "standard_peak_gate_reasons",
            "standard_peak_gate_blockers",
            "manual_backfill_authority_call",
            "calibration_outcome",
            "min_shape_r_after_best_shift",
            "max_abs_shift_sec",
        ),
        [
            {
                "feature_family_id": "FAM_STD",
                "standard_peak_gate_call": "standard_peak_gate_supported",
                "standard_peak_gate_reasons": "shift_aware_same_pattern_supported",
                "standard_peak_gate_blockers": "",
                "manual_backfill_authority_call": (
                    "authorize_standard_peak_backfill"
                ),
                "calibration_outcome": "true_positive",
                "min_shape_r_after_best_shift": "0.99",
                "max_abs_shift_sec": "0",
            }
        ],
    )

    assert (
        cli.main(
            [
                "--standard-peak-gate-tsv",
                str(standard_gate),
                "--overlay-batch-summary-tsv",
                str(overlay_summary),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    assert (
        tmp_path
        / "out"
        / "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
    ).is_file()


def _write_trace_json(base_dir: Path, family_id: str) -> Path:
    path = base_dir / f"{family_id.lower()}_trace_data.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "family_id": family_id,
                "traces": [
                    {
                        "sample_stem": "S1",
                        "status": "rescued",
                        "absolute_own_max_shape_similarity": 0.92,
                        "rt": [9.8, 10.0, 10.2],
                        "intensity": [10.0, 200.0, 9.0],
                    },
                    {
                        "sample_stem": "S2",
                        "status": "detected",
                        "absolute_own_max_shape_similarity": 0.99,
                        "rt": [9.8, 10.0, 10.2],
                        "intensity": [10.0, 180.0, 9.0],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_tsv(
    path: Path,
    columns: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
