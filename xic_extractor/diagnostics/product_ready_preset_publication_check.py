"""Check current-run product-ready preset publication sidecars.

This checker verifies that the built-in product-ready preset is judged by its
own standard-peak publication manifest, not by a retained dataset-specific
Backfill expansion replay packet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from xic_extractor.tabular_io import (
    file_sha256,
    format_diagnostic_value,
    text_value,
    write_tsv,
)

SCHEMA_VERSION = "product_ready_preset_publication_check_v1"
DEFAULT_EXPECTED_SOURCE_RUN_PREFIX = "alignment-preset:builtin:dna_dr_product_ready"
SUMMARY_RELATIVE_PATH = Path(
    "standard_peak_backfill_preset/standard_peak_backfill_preset_summary.json",
)
MANIFEST_FILENAME = "standard_peak_default_matrix_manifest.json"
BACKFILL_EXPANSION_REPLAY_DIRNAME = "backfill_expansion_productization_preset"

CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)


@dataclass(frozen=True)
class ProductReadyPresetPublicationCheckOutputs:
    summary_json: Path
    checks_tsv: Path
    status: str


def check_product_ready_preset_publication(
    *,
    alignment_dir: Path,
    output_dir: Path | None = None,
    require_no_backfill_expansion_replay: bool = True,
    expected_source_run_prefix: str = DEFAULT_EXPECTED_SOURCE_RUN_PREFIX,
) -> ProductReadyPresetPublicationCheckOutputs:
    """Validate the product-ready preset's current-run publication sidecars."""

    alignment_dir = alignment_dir.resolve()
    output_dir = (
        output_dir or alignment_dir / "product_ready_preset_publication_check"
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    preset_summary_json = alignment_dir / SUMMARY_RELATIVE_PATH
    default_manifest_json = alignment_dir / MANIFEST_FILENAME
    replay_dir = alignment_dir / BACKFILL_EXPANSION_REPLAY_DIRNAME

    checks: list[dict[str, str]] = []
    preset_summary = _load_json_if_present(preset_summary_json)
    default_manifest = _load_json_if_present(default_manifest_json)

    _append_check(
        checks,
        "standard_peak_summary_exists",
        preset_summary_json.is_file(),
        observed=str(preset_summary_json),
        expected="existing file",
    )
    if preset_summary:
        _append_check(
            checks,
            "standard_peak_summary_pass",
            text_value(preset_summary.get("status")) == "pass",
            observed=text_value(preset_summary.get("status")),
            expected="pass",
        )
        if expected_source_run_prefix:
            _append_check(
                checks,
                "standard_peak_source_run_prefix",
                text_value(preset_summary.get("source_run_id")).startswith(
                    expected_source_run_prefix,
                ),
                observed=text_value(preset_summary.get("source_run_id")),
                expected=expected_source_run_prefix + "*",
            )

    queue_row_count = _intish(preset_summary.get("review_queue_row_count", "0"))
    matrix_cells_written = text_value(preset_summary.get("matrix_cells_written"))
    manifest_required = queue_row_count > 0
    _append_check(
        checks,
        "default_matrix_manifest_presence",
        default_manifest_json.is_file() or not manifest_required,
        observed="present" if default_manifest_json.is_file() else "missing",
        expected="present when review_queue_row_count > 0",
    )

    if default_manifest:
        _append_check(
            checks,
            "default_matrix_manifest_status",
            text_value(default_manifest.get("status")) == "pass",
            observed=text_value(default_manifest.get("status")),
            expected="pass",
        )
        _append_check(
            checks,
            "default_matrix_manifest_coverage",
            text_value(default_manifest.get("coverage_status")) == "complete",
            observed=text_value(default_manifest.get("coverage_status")),
            expected="complete",
        )
        _append_check(
            checks,
            "default_matrix_manifest_missing_queue_ranks",
            text_value(default_manifest.get("missing_queue_rank_count")) == "0",
            observed=text_value(default_manifest.get("missing_queue_rank_count")),
            expected="0",
        )
        _append_check(
            checks,
            "default_matrix_manifest_duplicate_queue_ranks",
            text_value(default_manifest.get("duplicate_queue_rank_count")) == "0",
            observed=text_value(default_manifest.get("duplicate_queue_rank_count")),
            expected="0",
        )
        _append_check(
            checks,
            "default_matrix_manifest_queue_count_matches_summary",
            text_value(default_manifest.get("queue_row_count")) == str(queue_row_count),
            observed=text_value(default_manifest.get("queue_row_count")),
            expected=str(queue_row_count),
        )
        _append_check(
            checks,
            "default_matrix_manifest_matrix_cells_written_matches_summary",
            text_value(default_manifest.get("matrix_cells_written"))
            == matrix_cells_written,
            observed=text_value(default_manifest.get("matrix_cells_written")),
            expected=matrix_cells_written,
        )
        _append_check(
            checks,
            "default_matrix_manifest_source_run_prefix",
            not expected_source_run_prefix
            or text_value(default_manifest.get("source_run_id")).startswith(
                expected_source_run_prefix,
            ),
            observed=text_value(default_manifest.get("source_run_id")),
            expected=(
                expected_source_run_prefix + "*"
                if expected_source_run_prefix
                else "not checked"
            ),
        )
        for path_field, hash_field in (
            (
                "published_alignment_matrix_tsv",
                "published_alignment_matrix_sha256",
            ),
            (
                "published_alignment_matrix_identity_tsv",
                "published_alignment_matrix_identity_sha256",
            ),
        ):
            published_path = _path_value(default_manifest.get(path_field))
            expected_hash = text_value(default_manifest.get(hash_field)).lower()
            _append_check(
                checks,
                f"default_matrix_manifest_{path_field}_exists",
                published_path is not None and published_path.is_file(),
                observed=str(published_path) if published_path else "",
                expected="existing file",
            )
            observed_hash = (
                file_sha256(published_path, uppercase=False)
                if published_path is not None and published_path.is_file()
                else ""
            )
            _append_check(
                checks,
                f"default_matrix_manifest_{hash_field}_matches",
                bool(expected_hash) and observed_hash == expected_hash,
                observed=observed_hash,
                expected=expected_hash,
            )

    _append_check(
        checks,
        "no_fixed_backfill_expansion_replay",
        (not replay_dir.exists()) or (not require_no_backfill_expansion_replay),
        observed="present" if replay_dir.exists() else "absent",
        expected=(
            "absent"
            if require_no_backfill_expansion_replay
            else "not enforced"
        ),
        notes=(
            "built-in product-ready preset must stay sample-universe-safe"
            if require_no_backfill_expansion_replay
            else ""
        ),
    )

    status = "pass" if all(row["status"] == "pass" for row in checks) else "fail"
    checks_tsv = output_dir / "product_ready_preset_publication_checks.tsv"
    summary_json = output_dir / "product_ready_preset_publication_summary.json"
    write_tsv(
        checks_tsv,
        checks,
        CHECK_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "alignment_dir": str(alignment_dir),
        "standard_peak_summary_json": str(preset_summary_json),
        "default_matrix_manifest_json": str(default_manifest_json),
        "backfill_expansion_replay_dir": str(replay_dir),
        "require_no_backfill_expansion_replay": (
            "TRUE" if require_no_backfill_expansion_replay else "FALSE"
        ),
        "expected_source_run_prefix": expected_source_run_prefix,
        "review_queue_row_count": str(queue_row_count),
        "matrix_cells_written": matrix_cells_written,
        "check_count": str(len(checks)),
        "failed_check_count": str(
            sum(1 for row in checks if row["status"] != "pass"),
        ),
        "checks_tsv": str(checks_tsv),
        "product_surface_changed": (
            "TRUE" if _intish(matrix_cells_written) > 0 else "FALSE"
        ),
        "authority_changed": "FALSE",
        "next_action": (
            "current_run_product_ready_preset_publication_verified"
            if status == "pass"
            else "review_product_ready_preset_publication_failures"
        ),
    }
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ProductReadyPresetPublicationCheckOutputs(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        status=status,
    )


def _append_check(
    rows: list[dict[str, str]],
    check_id: str,
    passed: bool,
    *,
    observed: str,
    expected: str,
    notes: str = "",
) -> None:
    rows.append(
        {
            "schema_version": SCHEMA_VERSION,
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "observed": observed,
            "expected": expected,
            "notes": notes,
        },
    )


def _load_json_if_present(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def _path_value(value: Any) -> Path | None:
    text = text_value(value)
    return Path(text) if text else None


def _intish(value: Any) -> int:
    text = text_value(value)
    return int(text) if text else 0
