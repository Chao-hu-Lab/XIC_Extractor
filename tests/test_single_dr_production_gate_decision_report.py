import csv
import json
from pathlib import Path

from tools.diagnostics import single_dr_production_gate_decision_report as report


def test_extreme_dr_backfill_row_becomes_implement_candidate(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    output_dir = tmp_path / "diagnostics"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_EXT", q_detected=2, q_rescue=8),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_EXT", detected=2, rescued=8)),
    )

    code = report.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert code == 0
    families = _read_tsv(output_dir / "single_dr_gate_decision_families.tsv")
    assert families[0]["risk_classification"] == "risky_extreme_backfill"
    assert families[0]["rescue_fraction"] == "0.8000"

    candidates = _read_tsv(output_dir / "single_dr_gate_candidates.tsv")
    extreme = _candidate(candidates, "dr_extreme_backfill_dependency")
    assert extreme["affected_primary_rows"] == "1"
    assert extreme["affected_istd_rows"] == "0"
    assert extreme["recommended_action"] == "implement"
    assert (output_dir / "single_dr_gate_decision_summary.tsv").is_file()
    assert (output_dir / "single_dr_gate_decision_detected_cells.tsv").is_file()
    assert (output_dir / "single_dr_gate_decision.json").is_file()
    assert (output_dir / "single_dr_gate_decision.md").is_file()


def test_weak_seed_rescue_heavy_row_becomes_implement_candidate(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    output_dir = tmp_path / "diagnostics"
    discovery_dir = tmp_path / "discovery"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_WEAK", q_detected=3, q_rescue=6),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_WEAK", detected=3, rescued=6, absent=1)),
    )
    batch_index = _write_discovery_index(
        discovery_dir,
        [
            _candidate_row("S001", "FAM_WEAK_C001", evidence_score="55"),
            _candidate_row("S002", "FAM_WEAK_C002", seed_event_count="1"),
            _candidate_row("S003", "FAM_WEAK_C003", nl_ppm="12.5"),
        ],
    )

    result = report.build_decision_report(
        alignment_dir=alignment_dir,
        discovery_batch_index=batch_index,
    )

    family = result["families"][0]
    assert family["risk_classification"] == "risky_weak_seed_backfill"
    assert family["seed_quality_status"] == "weak"
    assert family["min_evidence_score"] == 55.0
    assert family["min_seed_event_count"] == 1.0
    assert family["max_abs_nl_ppm"] == 12.5

    report.write_outputs(output_dir, result)
    candidates = _read_tsv(output_dir / "single_dr_gate_candidates.tsv")
    weak_seed = _candidate(candidates, "dr_weak_seed_backfill_dependency")
    assert weak_seed["affected_primary_rows"] == "1"
    assert weak_seed["recommended_action"] == "implement"


def test_high_detected_rescue_heavy_row_remains_strong(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_STRONG", q_detected=20, q_rescue=60),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_STRONG", detected=20, rescued=60, absent=5)),
    )

    result = report.build_decision_report(alignment_dir=alignment_dir)

    assert result["families"][0]["risk_classification"] == "strong"
    candidates = {
        row["gate_candidate_id"]: row for row in result["gate_candidates"]
    }
    assert candidates["dr_extreme_backfill_dependency"]["affected_primary_rows"] == 0
    assert candidates["dr_weak_seed_backfill_dependency"]["affected_primary_rows"] == 0


def test_duplicate_pressure_low_detected_rescue_heavy_row_is_watch_only(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (
            _review_row(
                "FAM_DUP",
                q_detected=4,
                q_rescue=6,
                duplicate_assigned=3,
                row_flags="duplicate_claim_pressure;rescue_heavy",
            ),
        ),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_DUP", detected=4, rescued=6)),
    )

    result = report.build_decision_report(alignment_dir=alignment_dir)

    assert result["families"][0]["risk_classification"] == "watch_duplicate_rescue"
    duplicate = _candidate(
        result["gate_candidates"],
        "dr_duplicate_rescue_pressure",
    )
    assert duplicate["affected_primary_rows"] == 1
    assert duplicate["recommended_action"] == "keep_warning"


def test_rt_worsened_is_context_not_a_demotion_rule(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "alignment"
    rt_context = tmp_path / "rt_normalization_families.tsv"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_RT", q_detected=20, q_rescue=0),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_RT", detected=20, rescued=0)),
    )
    _write_tsv(
        rt_context,
        (
            {
                "feature_family_id": "FAM_RT",
                "rt_context": "context_rt_worsened",
                "normalized_rt_support": "worsened",
                "rt_delta_before_min": "0.03",
                "rt_delta_after_min": "0.09",
            },
        ),
    )

    result = report.build_decision_report(
        alignment_dir=alignment_dir,
        rt_normalization_families_tsv=rt_context,
    )

    family = result["families"][0]
    assert family["risk_classification"] == "strong"
    assert family["rt_context"] == "context_rt_worsened"
    assert all(
        candidate["recommended_action"] != "implement"
        for candidate in result["gate_candidates"]
    )


def test_missing_optional_enrichment_still_outputs_unavailable(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_WEAKISH", q_detected=3, q_rescue=6),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_WEAKISH", detected=3, rescued=6, absent=1)),
    )

    result = report.build_decision_report(alignment_dir=alignment_dir)

    family = result["families"][0]
    assert family["risk_classification"] == "weak"
    assert family["seed_quality_status"] == "unavailable"
    assert result["enrichment"]["discovery_batch_index"] == "not_provided"


def test_non_dr_primary_rows_are_out_of_scope(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "alignment"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (
            _review_row("FAM_DR", tag="DNA_dR", q_detected=2, q_rescue=8),
            _review_row("FAM_R", tag="RNA_R", q_detected=1, q_rescue=9),
            _review_row("FAM_MER", tag="DNA_MeR", q_detected=1, q_rescue=9),
        ),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_DR", detected=2, rescued=8))
        + tuple(_cells("FAM_R", detected=1, rescued=9))
        + tuple(_cells("FAM_MER", detected=1, rescued=9)),
    )

    result = report.build_decision_report(alignment_dir=alignment_dir)

    assert [family["feature_family_id"] for family in result["families"]] == [
        "FAM_DR",
    ]


def test_istd_impact_blocks_automatic_implement_recommendation(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    benchmark_json = tmp_path / "targeted_istd_benchmark.json"
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        (_review_row("FAM_ISTD", q_detected=2, q_rescue=8),),
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        tuple(_cells("FAM_ISTD", detected=2, rescued=8)),
    )
    benchmark_json.write_text(
        json.dumps(
            {
                "summaries": [
                    {
                        "target_label": "d3-N6-medA",
                        "selected_feature_id": "FAM_ISTD",
                        "primary_feature_ids": ["FAM_ISTD"],
                        "status": "FAIL",
                        "failure_modes": ["AREA_MISMATCH"],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    result = report.build_decision_report(
        alignment_dir=alignment_dir,
        targeted_istd_benchmark_json=benchmark_json,
    )

    family = result["families"][0]
    assert family["targeted_istd_labels"] == "d3-N6-medA"
    extreme = _candidate(
        result["gate_candidates"],
        "dr_extreme_backfill_dependency",
    )
    assert extreme["affected_istd_rows"] == 1
    assert extreme["recommended_action"] == "keep_warning"


def _review_row(
    feature_id: str,
    *,
    tag: str = "DNA_dR",
    primary: bool = True,
    q_detected: int,
    q_rescue: int,
    duplicate_assigned: int = 0,
    row_flags: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": feature_id,
        "neutral_loss_tag": tag,
        "family_center_mz": "300.0",
        "family_center_rt": "8.0",
        "family_product_mz": "184.0739",
        "family_observed_neutral_loss_da": "116.0474",
        "detected_count": str(q_detected),
        "accepted_rescue_count": str(q_rescue),
        "quantifiable_detected_count": str(q_detected),
        "quantifiable_rescue_count": str(q_rescue),
        "duplicate_assigned_count": str(duplicate_assigned),
        "include_in_primary_matrix": "TRUE" if primary else "FALSE",
        "identity_decision": "production_family" if primary else "audit_family",
        "identity_reason": "owner_complete_link",
        "family_evidence": "owner_complete_link",
        "primary_evidence": "owner_complete_link",
        "row_flags": row_flags,
        "warning": "",
        "present_rate": "1.0",
    }


def _cells(
    feature_id: str,
    *,
    detected: int,
    rescued: int,
    absent: int = 0,
) -> list[dict[str, str]]:
    rows = []
    for index in range(1, detected + 1):
        sample = f"S{index:03d}"
        rows.append(
            {
                "feature_family_id": feature_id,
                "sample_stem": sample,
                "status": "detected",
                "area": "1000",
                "apex_rt": "8.0",
                "source_candidate_id": f"{feature_id}_C{index:03d}",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.0",
                "family_center_rt": "8.0",
                "reason": "",
            },
        )
    for index in range(detected + 1, detected + rescued + 1):
        rows.append(
            {
                "feature_family_id": feature_id,
                "sample_stem": f"S{index:03d}",
                "status": "rescued",
                "area": "500",
                "apex_rt": "8.0",
                "source_candidate_id": "",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.0",
                "family_center_rt": "8.0",
                "reason": "owner_backfill",
            },
        )
    for index in range(detected + rescued + 1, detected + rescued + absent + 1):
        rows.append(
            {
                "feature_family_id": feature_id,
                "sample_stem": f"S{index:03d}",
                "status": "absent",
                "area": "",
                "apex_rt": "",
                "source_candidate_id": "",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.0",
                "family_center_rt": "8.0",
                "reason": "not_found",
            },
        )
    return rows


def _write_discovery_index(
    discovery_dir: Path,
    candidate_rows: list[dict[str, str]],
) -> Path:
    discovery_dir.mkdir(parents=True, exist_ok=True)
    rows_by_sample: dict[str, list[dict[str, str]]] = {}
    for row in candidate_rows:
        rows_by_sample.setdefault(row["sample_stem"], []).append(row)

    index_rows = []
    for sample, rows in sorted(rows_by_sample.items()):
        candidate_csv = discovery_dir / f"{sample}_candidates.csv"
        _write_csv(candidate_csv, rows)
        index_rows.append(
            {
                "sample_stem": sample,
                "candidate_csv": candidate_csv.name,
            },
        )
    batch_index = discovery_dir / "discovery_batch_index.tsv"
    _write_tsv(batch_index, tuple(index_rows))
    return batch_index


def _candidate_row(
    sample: str,
    candidate_id: str,
    *,
    evidence_score: str = "80",
    seed_event_count: str = "3",
    nl_ppm: str = "3.0",
    scan_support: str = "0.80",
) -> dict[str, str]:
    return {
        "sample_stem": sample,
        "candidate_id": candidate_id,
        "evidence_score": evidence_score,
        "seed_event_count": seed_event_count,
        "neutral_loss_mass_error_ppm": nl_ppm,
        "ms1_scan_support_score": scan_support,
    }


def _candidate(
    rows: list[dict[str, object]],
    candidate_id: str,
) -> dict[str, object]:
    return next(row for row in rows if row["gate_candidate_id"] == candidate_id)


def _write_tsv(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise AssertionError("test fixture must provide at least one row")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
