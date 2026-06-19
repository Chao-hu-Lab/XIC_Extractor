import csv
import json
from pathlib import Path

from scripts.check_discovery_architecture_ab_artifact import (
    check_discovery_architecture_ab_artifact,
    write_summary,
)
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def test_ab_checker_accepts_successor_identity_with_parser_compatible_candidate_id(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row(
                "focus",
                discovery_candidate_state="ms1_feature_nl_rescued",
                ms1_feature_row_id="TumorBC2312_DNA|DNA_dR|300.1605|23.3417",
            ),
            _row(
                "preserve",
                discovery_candidate_state="ms1_feature_nl_supported",
                ms1_feature_row_id="TumorBC2312_DNA|DNA_dR|301.165|23.3421",
            ),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert problems == []


def test_ab_checker_rejects_missing_successor_columns(tmp_path: Path) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(
        baseline_csv,
        [_row("focus"), _row("preserve")],
        include_successor_columns=False,
    )
    _write_candidates(candidate_csv, [_row("focus"), _row("preserve")])

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert any("ms1_feature_row_id" in problem for problem in problems)
    assert any("discovery_candidate_state" in problem for problem in problems)


def test_ab_checker_rejects_parser_incompatible_candidate_ids(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row(
                "focus",
                candidate_id="feature-primary-focus-row",
                discovery_candidate_state="ms1_feature_nl_rescued",
            ),
            _row("preserve", discovery_candidate_state="ms1_feature_nl_supported"),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert any("alignment parser" in problem for problem in problems)


def test_ab_checker_rejects_focus_pair_when_state_is_review_only(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row(
                "focus",
                ms1_peak_found="FALSE",
                ms1_apex_rt="",
                ms1_peak_rt_start="",
                ms1_peak_rt_end="",
                ms1_area="",
                discovery_candidate_state="review_only_orphan_nl",
                ms1_feature_row_id="",
            ),
            _row("preserve", discovery_candidate_state="ms1_feature_nl_supported"),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert any(
        "focus_300_184: unacceptable row state" in problem
        for problem in problems
    )


def test_ab_checker_rejects_preserve_pair_without_own_tag_evidence(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row("focus", discovery_candidate_state="ms1_feature_nl_rescued"),
            _row(
                "preserve",
                neutral_loss_tag="RNA_R",
                matched_tag_names="RNA_R",
                primary_tag_name="RNA_R",
                tag_evidence_json=json.dumps(
                    {
                        "RNA_R": {
                            "scan_count": 1,
                            "precursor_mz_basis": "scan_precursor",
                        }
                    },
                    sort_keys=True,
                ),
                discovery_candidate_state="ms1_feature_nl_supported",
            ),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert any(
        "preserve_301_185: lacks DNA_dR tag evidence" in problem
        for problem in problems
    )


def test_ab_checker_rejects_duplicate_normal_focus_rows(tmp_path: Path) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row("focus", discovery_candidate_state="ms1_feature_nl_rescued"),
            _row(
                "focus",
                candidate_id="TumorBC2312_DNA#19562@mz300.160612_p184.113201",
                best_ms2_scan_id="19562",
                seed_scan_ids="19562",
                feature_family_id="TumorBC2312_DNA@F9999",
                ms1_feature_row_id="TumorBC2312_DNA|DNA_dR|300.1606|23.3444",
                discovery_candidate_state="ms1_feature_nl_rescued",
            ),
            _row("preserve", discovery_candidate_state="ms1_feature_nl_supported"),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert any(
        "focus_300_184: expected exactly one candidate row" in problem
        for problem in problems
    )


def test_ab_checker_ignores_nearby_non_rescue_focus_candidates(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(
        candidate_csv,
        [
            _row("focus", discovery_candidate_state="ms1_feature_nl_rescued"),
            _row(
                "focus",
                candidate_id="TumorBC2312_DNA#19867@mz300.16062_p184.11322",
                best_ms2_scan_id="19867",
                seed_scan_ids="19867",
                feature_family_id="TumorBC2312_DNA@F0090",
                ms1_area="862833",
                ms1_apex_rt="23.6329",
                ms1_peak_rt_start="23.6329",
                ms1_peak_rt_end="23.8824",
                scan_precursor_mz="300.20281982421875",
                scan_precursor_delta_da="0.0421996",
                max_scan_precursor_abs_delta_da="0.0421996",
                discovery_candidate_state="ms1_feature_nl_rescued",
                tag_evidence_json=json.dumps(
                    {
                        "DNA_dR": {
                            "scan_count": 1,
                            "precursor_mz_basis": "product_plus_neutral_loss",
                            "max_scan_precursor_abs_delta_da": 0.0421996,
                        }
                    },
                    sort_keys=True,
                ),
            ),
            _row(
                "focus",
                candidate_id="TumorBC2312_DNA#20728@mz300.16088_p184.11348",
                best_ms2_scan_id="20728",
                seed_scan_ids="20728",
                feature_family_id="TumorBC2312_DNA@F0126",
                ms1_peak_found="FALSE",
                ms1_apex_rt="",
                ms1_peak_rt_start="",
                ms1_peak_rt_end="",
                ms1_area="",
                scan_precursor_mz="300.2028503417969",
                scan_precursor_delta_da="0.0419707",
                max_scan_precursor_abs_delta_da="0.0419707",
                discovery_candidate_state="review_only_orphan_nl",
            ),
            _row("preserve", discovery_candidate_state="ms1_feature_nl_supported"),
        ],
    )

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )

    assert problems == []


def test_ab_checker_writes_diagnostic_only_summary(tmp_path: Path) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    summary_json = tmp_path / "summary.json"
    _write_candidates(baseline_csv, [_row("focus"), _row("preserve")])
    _write_candidates(candidate_csv, [_row("focus"), _row("preserve")])

    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
    )
    write_summary(
        summary_json,
        baseline_candidates_csv=baseline_csv,
        candidate_candidates_csv=candidate_csv,
        problems=problems,
    )

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["readiness_label"] == "diagnostic_only"
    assert payload["schema_version"] == "discovery_architecture_ab_check_v1"
    assert payload["candidate"]["facts"]["focus_300_184"]["tag"] == "DNA_dR"
    assert payload["candidate"]["alignment_parser_status"] == "pass"


def _write_candidates(
    path: Path,
    rows: list[dict[str, str]],
    *,
    include_successor_columns: bool = True,
) -> None:
    fieldnames = tuple(
        dict.fromkeys(
            (
                *DISCOVERY_CANDIDATE_COLUMNS,
                *(
                    ("discovery_candidate_state", "ms1_feature_row_id")
                    if include_successor_columns
                    else ()
                ),
            )
        )
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {column: row.get(column, "") for column in fieldnames}
            for row in rows
        )


def _row(kind: str, **overrides: str) -> dict[str, str]:
    if kind == "focus":
        precursor_mz = "300.160635"
        product_mz = "184.113235"
        candidate_id = "TumorBC2312_DNA#19561@mz300.160635_p184.113235"
        basis = "product_plus_neutral_loss"
        error_basis = "configured_loss_inferred_precursor"
        scan_delta = "1.004343"
        state = "ms1_feature_nl_rescued"
        feature_id = "TumorBC2312_DNA@F0001"
    elif kind == "preserve":
        precursor_mz = "301.164978"
        product_mz = "185.115845"
        candidate_id = "TumorBC2312_DNA#19561@mz301.164978_p185.115845"
        basis = "scan_precursor"
        error_basis = "measured_scan_precursor_product"
        scan_delta = "0.0"
        state = "ms1_feature_nl_supported"
        feature_id = "TumorBC2312_DNA@F0002"
    else:
        raise ValueError(kind)

    row = {
        "review_priority": "HIGH",
        "evidence_tier": "A",
        "evidence_score": "90",
        "ms2_support": "strong",
        "ms1_support": "clean",
        "rt_alignment": "aligned",
        "family_context": "family",
        "candidate_id": candidate_id,
        "feature_family_id": feature_id,
        "feature_family_size": "1",
        "feature_superfamily_id": "TumorBC2312_DNA@SF0001",
        "feature_superfamily_size": "2",
        "feature_superfamily_role": "representative",
        "feature_superfamily_confidence": "MEDIUM",
        "feature_superfamily_evidence": "peak_boundary_overlap",
        "precursor_mz": precursor_mz,
        "product_mz": product_mz,
        "observed_neutral_loss_da": "116.0474",
        "best_seed_rt": "23.3417",
        "seed_event_count": "1",
        "ms1_peak_found": "TRUE",
        "ms1_apex_rt": "23.3417",
        "ms1_area": "205086000",
        "ms2_product_max_intensity": "12345",
        "reason": "strict NL seed",
        "raw_file": "C:/raw/TumorBC2312_DNA.raw",
        "sample_stem": "TumorBC2312_DNA",
        "best_ms2_scan_id": "19561",
        "seed_scan_ids": "19561",
        "neutral_loss_tag": "DNA_dR",
        "configured_neutral_loss_da": "116.0474",
        "neutral_loss_mass_error_ppm": "0.0",
        "neutral_loss_error_basis": error_basis,
        "precursor_mz_basis": basis,
        "scan_precursor_mz": str(float(precursor_mz) + float(scan_delta)),
        "scan_precursor_delta_da": scan_delta,
        "max_scan_precursor_abs_delta_da": scan_delta,
        "rt_seed_min": "23.30",
        "rt_seed_max": "23.38",
        "ms1_search_rt_min": "23.10",
        "ms1_search_rt_max": "23.58",
        "ms1_seed_delta_min": "0.0",
        "ms1_peak_rt_start": "23.20",
        "ms1_peak_rt_end": "23.48",
        "ms1_height": "20000",
        "ms1_trace_quality": "clean",
        "ms1_scan_support_score": "0.9",
        "selected_tag_count": "1",
        "matched_tag_count": "1",
        "matched_tag_names": "DNA_dR",
        "primary_tag_name": "DNA_dR",
        "tag_combine_mode": "single",
        "tag_intersection_status": "not_required",
        "tag_evidence_json": json.dumps(
            {"DNA_dR": {"scan_count": 1, "precursor_mz_basis": basis}},
            sort_keys=True,
        ),
        "discovery_candidate_state": state,
        "ms1_feature_row_id": feature_id,
    }
    row.update(overrides)
    return row
