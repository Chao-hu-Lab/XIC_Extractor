import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import scripts.build_trace_overlay_recovery_report as recovery
from scripts.build_trace_overlay_recovery_report import (
    REPORT_HEADER,
    build_recovery_report,
)
from scripts.check_productization_state import artifact_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/superpowers/specs/trace_overlay_recovery_contract.v1.json"
REPORT_PATH = ROOT / "docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv"
SUMMARY_PATH = (
    ROOT / "docs/superpowers/validation/missing_overlay_resolution_summary_v1.json"
)


def test_trace_overlay_recovery_schema_matches_report_header() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["required_report_columns"] == REPORT_HEADER
    assert schema["authority_rules"]["may_touch_matrix"] is False
    assert schema["authority_rules"]["may_grant_product_authority"] is False
    assert schema["source_policy"]["raw_rerun_required"] is False
    assert schema["source_policy"]["review_or_truth_required_after_recovery"]


def test_recovery_generator_is_deterministic_and_non_authoritative(
    tmp_path: Path,
) -> None:
    result = build_recovery_report(tmp_path)
    rows = _read_tsv(result["report_path"])
    summary = json.loads(Path(result["summary_path"]).read_text(encoding="utf-8"))

    assert result["row_count"] == 1087
    assert len(rows) == 1087
    assert len({row["family_id"] for row in rows}) == 114
    assert summary["candidate_rows"] == 1087
    assert summary["candidate_families"] == 114
    assert summary["authority"]["may_touch_matrix"] is False
    assert summary["authority"]["may_grant_product_authority"] is False
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in rows} == {"FALSE"}


def test_recovery_report_recovers_existing_family_artifacts() -> None:
    rows = _read_tsv(REPORT_PATH)
    statuses = Counter(row["recovery_status"] for row in rows)
    post_grades = Counter(row["post_recovery_evidence_grade"] for row in rows)

    assert statuses == {"family_trace_overlay_recovered": 1087}
    assert post_grades == {"C_trace_recovered": 1087}
    assert {row["source_evidence_grade"] for row in rows} == {"D"}
    assert {row["source_missing_reason"] for row in rows} == {"missing_overlay_path"}
    assert {row["source_mechanical_decision"] for row in rows} == {"evidence_required"}
    assert {row["post_recovery_mechanical_decision"] for row in rows} == {
        "evidence_required"
    }
    assert {row["sample_trace_present"] for row in rows} == {"TRUE"}
    assert all(row["recovered_family_trace_data_path"] for row in rows)
    assert all(row["recovered_overlay_png_path"] for row in rows)
    assert all(row["recovered_hypothesis_png_path"] for row in rows)
    assert {row["recovered_sample_trace_status"] for row in rows} == {"rescued"}
    assert all(row["recovered_sample_cell_area"] for row in rows)
    assert all(row["recovered_sample_cell_height"] for row in rows)
    assert all(row["recovered_sample_cell_apex_rt"] for row in rows)
    assert all(row["recovered_sample_cell_start_rt"] for row in rows)
    assert all(row["recovered_sample_cell_end_rt"] for row in rows)
    assert all(row["recovered_sample_trace_max_intensity"] for row in rows)
    assert all(
        row["post_recovery_next_required_evidence"]
        == "independent_peak_choice_or_area_truth_after_trace_recovery"
        for row in rows
    )


def test_recovered_artifact_paths_and_hashes_match_files() -> None:
    rows = _read_tsv(REPORT_PATH)
    missing_paths = _missing_recovered_artifact_paths(rows)
    if missing_paths:
        pytest.skip(
            "recovered trace-overlay artifacts are external output files: "
            + ", ".join(path.as_posix() for path in missing_paths[:3]),
        )

    seen_paths: dict[str, str] = {}
    for row in rows:
        for path_key, hash_key in (
            ("recovered_family_trace_data_path", "recovered_family_trace_data_sha256"),
            ("recovered_overlay_png_path", "recovered_overlay_png_sha256"),
            ("recovered_hypothesis_png_path", "recovered_hypothesis_png_sha256"),
        ):
            relative = row[path_key]
            expected = row[hash_key]
            assert relative
            assert expected
            if relative not in seen_paths:
                path = ROOT / relative
                assert path.exists()
                seen_paths[relative] = _sha256(path)
            assert seen_paths[relative] == expected


def test_recovery_status_requires_existing_hypothesis_png(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    trace_dir = tmp_path / "family_ms1_overlay_batch"
    trace_dir.mkdir()
    trace_path = (
        trace_dir / "001_fam000380_retained_backfill_missing_overlay_trace_data.json"
    )
    overlay_path = trace_dir / "001_fam000380_retained_backfill_missing_overlay.png"
    trace_path.write_text(
        json.dumps(
            {
                "trace_count": 1,
                "evidence_summary": {"detected_count": 0},
                "traces": [{"sample_stem": "BenignfatBC0979_DNA"}],
            }
        ),
        encoding="utf-8",
    )
    overlay_path.write_bytes(b"not-a-real-png")
    monkeypatch.setattr(recovery, "TRACE_ROOTS", [tmp_path])

    result = build_recovery_report(tmp_path / "out")
    rows = _read_tsv(result["report_path"])
    target = next(
        row
        for row in rows
        if row["family_id"] == "FAM000380"
        and row["sample_id"] == "BenignfatBC0979_DNA"
    )

    assert target["recovery_status"] == "family_hypothesis_png_missing"
    assert target["post_recovery_evidence_grade"] == "D"
    assert target["may_grant_product_authority"] == "FALSE"


def test_recovery_summary_matches_report() -> None:
    rows = _read_tsv(REPORT_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    assert summary["status"] == "all_existing_family_trace_overlays_recovered"
    assert summary["candidate_rows"] == len(rows) == 1087
    assert summary["recovery_status_counts"] == {
        "family_trace_overlay_recovered": 1087
    }
    assert summary["post_recovery_evidence_grade_counts"] == {
        "C_trace_recovered": 1087
    }
    assert artifact_sha256(ROOT / summary["report_path"]) == summary["report_sha256"]
    assert (
        artifact_sha256(ROOT / summary["source_index"])
        == summary["source_index_sha256"]
    )


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _missing_recovered_artifact_paths(rows: list[dict[str, str]]) -> list[Path]:
    missing: list[Path] = []
    seen: set[str] = set()
    for row in rows:
        for path_key in (
            "recovered_family_trace_data_path",
            "recovered_overlay_png_path",
            "recovered_hypothesis_png_path",
        ):
            relative = row[path_key]
            if relative in seen:
                continue
            seen.add(relative)
            path = ROOT / relative
            if not path.exists():
                missing.append(path)
    return missing
