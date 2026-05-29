from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from tools.diagnostics import provisional_backfill_candidate_gate as gate_cli


def test_cli_writes_sidecar_and_summary_without_mutating_matrix(
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")
    matrix_path = alignment_dir / "alignment_matrix.tsv"
    before_hash = _sha256_file(matrix_path)
    output_dir = tmp_path / "gate"

    code = gate_cli.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert code == 0
    assert _sha256_file(matrix_path) == before_hash
    rows = _read_tsv(output_dir / "alignment_production_candidate_gate.tsv")
    by_id = {row["feature_family_id"]: row for row in rows}
    assert set(by_id) == {"FAM_CAND"}
    assert by_id["FAM_CAND"]["candidate_gate_status"] == "keep_provisional"
    assert by_id["FAM_CAND"]["support_components"] == ""
    assert "missing_positive_tier2_support" in by_id["FAM_CAND"][
        "challenge_blockers"
    ]
    assert by_id["FAM_CAND"]["source_matrix_sha256"] == before_hash
    payload = json.loads(
        (output_dir / "alignment_production_candidate_gate.json").read_text(
            encoding="utf-8",
        ),
    )
    assert payload["readiness_label"] == "diagnostic_only"
    assert payload["production_ready"] is False
    assert payload["matrix_contract_changed"] is False
    assert payload["production_candidate_count"] == 0
    assert payload["row_count"] == 1
    assert payload["source_review_artifact"] == str(
        alignment_dir / "alignment_review.tsv"
    )
    assert payload["source_cell_artifact"] == str(
        alignment_dir / "alignment_cells.tsv"
    )
    assert payload["source_matrix_artifact"] == str(matrix_path)
    assert payload["source_matrix_sha256"] == before_hash


def test_cli_defaults_output_dir_to_alignment_dir(tmp_path: Path) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 0
    assert (alignment_dir / "alignment_production_candidate_gate.tsv").is_file()
    assert (alignment_dir / "alignment_production_candidate_gate.json").is_file()


def test_cli_reports_missing_required_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 2
    stderr = capsys.readouterr().err
    assert f"Required TSV not found: {alignment_dir / 'alignment_review.tsv'}" in stderr


def test_cli_reports_missing_required_columns(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    _write_tsv(alignment_dir / "alignment_review.tsv", [{"feature_family_id": "FAM"}])
    _write_tsv(alignment_dir / "alignment_cells.tsv", [{"feature_family_id": "FAM"}])
    _write_tsv(alignment_dir / "alignment_matrix.tsv", [{"feature_family_id": "FAM"}])

    code = gate_cli.main(["--alignment-dir", str(alignment_dir)])

    assert code == 2
    stderr = capsys.readouterr().err
    assert "missing required columns" in stderr
    assert "identity_decision" in stderr


def _write_alignment_run(path: Path) -> Path:
    path.mkdir(parents=True)
    _write_tsv(
        path / "alignment_review.tsv",
        [
            _review_row(
                "FAM_KEEP",
                flags="single_detected_seed",
                detected=1,
                rescued=1,
            ),
            _review_row(
                "FAM_CAND",
                flags="single_detected_seed;provisional_retention_candidate",
                detected=1,
                rescued=2,
            ),
            _review_row(
                "FAM_PRIMARY",
                include="TRUE",
                decision="production_family",
                reason="owner_complete_link",
                flags="",
                detected=2,
                rescued=0,
            ),
        ],
    )
    _write_tsv(
        path / "alignment_cells.tsv",
        [
            _cell_row("FAM_KEEP", "S1", "detected"),
            _cell_row("FAM_KEEP", "S2", "rescued"),
            _cell_row("FAM_CAND", "S1", "detected"),
            _cell_row("FAM_CAND", "S2", "rescued"),
            _cell_row("FAM_CAND", "S3", "rescued"),
            _cell_row("FAM_PRIMARY", "S1", "detected"),
            _cell_row("FAM_PRIMARY", "S2", "detected"),
        ],
    )
    _write_tsv(
        path / "alignment_matrix.tsv",
        [{"feature_family_id": "FAM_PRIMARY", "S1": "100", "S2": "90"}],
    )
    return path


def _review_row(
    family_id: str,
    *,
    flags: str,
    detected: int,
    rescued: int,
    include: str = "FALSE",
    decision: str = "provisional_discovery",
    reason: str = "insufficient_detected_identity_support",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "include_in_primary_matrix": include,
        "identity_decision": decision,
        "identity_confidence": "review",
        "identity_reason": reason,
        "primary_evidence": "owner_complete_link",
        "quantifiable_detected_count": str(detected),
        "quantifiable_rescue_count": str(rescued),
        "accepted_rescue_count": str(rescued),
        "duplicate_assigned_count": "0",
        "ambiguous_ms1_owner_count": "0",
        "row_flags": flags,
        "family_evidence": "owner_complete_link;owner_count=1",
    }


def _cell_row(family_id: str, sample: str, status: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": status,
        "area": "100",
        "apex_rt": "8.00",
        "height": "50",
        "peak_start_rt": "7.95",
        "peak_end_rt": "8.05",
        "rt_delta_sec": "0.0",
        "trace_quality": "owner_backfill" if status == "rescued" else "clean",
        "scan_support_score": "0.8",
        "reason": status,
    }


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
