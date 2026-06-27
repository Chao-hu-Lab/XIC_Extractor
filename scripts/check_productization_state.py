"""Check the machine-readable productization status index.

This is a control-plane consistency guard. It validates the current lane status
index against the authority manifest, productization status anchor document, and
control-plane anchors without touching ProductWriter, matrices, workbooks,
selected peaks, or counted detections. The default anchor is not the active
handoff for every branch; active branch handoffs are ignored local files such
as docs/superpowers/handoffs/current/ACTIVE.local.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT / "docs/superpowers/specs/productization_control_plane_schema.v1.json"
)
DEFAULT_STATUS_INDEX = (
    ROOT / "docs/superpowers/validation/productization_status_index_v1.tsv"
)
DEFAULT_AUTHORITY_MANIFEST = (
    ROOT / "docs/superpowers/specs/productization_authority_manifest.v1.json"
)
DEFAULT_PRODUCTIZATION_STATUS_ANCHOR = (
    ROOT
    / "docs/superpowers/productization/status"
    / "cc-framework-improvements-productization.md"
)
DEFAULT_HANDOFF = DEFAULT_PRODUCTIZATION_STATUS_ANCHOR
DEFAULT_CONTROL_PLANE = (
    ROOT / "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
)

WRITER_LANE_AUTHORITY = {
    "backfill_current_write_ready_scope": {
        "authority_key": "backfill",
        "scope": "backfill_policy_write_ready_rows",
    },
    "cid_nl_default_product_activation_v1": {
        "authority_key": "cid_nl_default_activation",
        "scope": "cid_nl_adopt_ready_feature_inclusion_95_cells",
    },
    "backfill_expansion_clean_target_selective_product_activation_v1": {
        "authority_key": "backfill_expansion_clean_target_selective_activation",
        "scope": "backfill_expansion_clean_target_selective_activation_84_cells",
    },
}
WRITE_FORBIDDEN_STATUSES = {
    "parked",
    "blocked",
    "diagnostic_only",
    "frozen",
    "out_of_scope",
}
NON_AUTHORITY_LANE_GROUPS = {"review", "truth", "evidence"}
CANONICAL_TEXT_HASH_EXTENSIONS = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


def check_productization_state(
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    status_index_path: Path = DEFAULT_STATUS_INDEX,
    authority_manifest_path: Path = DEFAULT_AUTHORITY_MANIFEST,
    handoff_path: Path = DEFAULT_HANDOFF,
    control_plane_path: Path = DEFAULT_CONTROL_PLANE,
    repo_root: Path = ROOT,
) -> list[str]:
    problems: list[str] = []
    schema = _read_json(schema_path, problems)
    authority = _read_json(authority_manifest_path, problems)
    header, rows = _read_tsv(status_index_path, problems)
    handoff_text = _read_text(handoff_path, problems)
    control_plane_text = _read_text(control_plane_path, problems)
    if not schema or not authority:
        return problems

    _check_schema_and_rows(schema, header, rows, problems)
    _check_authority_boundaries(authority, rows, problems)
    _check_artifacts(rows, repo_root, problems)
    _check_doc_anchors(rows, handoff_text, control_plane_text, problems)
    return problems


def _check_schema_and_rows(
    schema: Mapping[str, Any],
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    required = schema.get("required_status_index_columns")
    if not isinstance(required, list) or not all(
        isinstance(column, str) for column in required
    ):
        problems.append("schema required_status_index_columns must be a string list")
        return
    if list(header) != required:
        problems.append("status index header must exactly match schema")
    allowed_statuses = set(schema.get("allowed_readiness_statuses", []))
    required_lane_ids = set(schema.get("required_lane_ids", []))
    lane_ids = [row.get("lane_id", "") for row in rows]
    duplicates = sorted(
        lane_id for lane_id, count in Counter(lane_ids).items() if count > 1
    )
    if duplicates:
        problems.append("duplicate lane_id values: " + ", ".join(duplicates))
    missing = sorted(required_lane_ids - set(lane_ids))
    if missing:
        problems.append("missing required lane_id values: " + ", ".join(missing))
    extra = sorted(set(lane_ids) - required_lane_ids)
    if extra:
        problems.append("unregistered lane_id values: " + ", ".join(extra))
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != "productization_status_index_v1":
            problems.append(f"row {index}: invalid schema_version")
        if row.get("readiness_status") not in allowed_statuses:
            problems.append(
                f"row {index}: invalid readiness_status "
                f"{row.get('readiness_status')!r}"
            )
        for field in (
            "write_authority",
            "may_touch_matrix",
            "may_change_quant_output",
            "may_change_workbook",
            "may_change_selected_peak",
            "may_change_selected_area",
            "may_change_counted_detection",
        ):
            if row.get(field) not in {"TRUE", "FALSE"}:
                problems.append(f"row {index}: {field} must be TRUE or FALSE")


def _check_authority_boundaries(
    authority: Mapping[str, Any],
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    policy = authority.get("authority_policy")
    current = _mapping_path(authority, "current_authority", "backfill")
    if not isinstance(policy, Mapping) or not isinstance(current, Mapping):
        problems.append("authority manifest missing policy/current backfill")
        return
    allowed_scopes = set(policy.get("product_writer_allowed_scopes", []))
    expected_scopes = {item["scope"] for item in WRITER_LANE_AUTHORITY.values()}
    if allowed_scopes != expected_scopes:
        problems.append("authority manifest allowed scopes drifted")
    authority_rows = [row for row in rows if row.get("write_authority") == "TRUE"]
    writer_lane_ids = {row.get("lane_id", "") for row in authority_rows}
    expected_writer_lane_ids = set(WRITER_LANE_AUTHORITY)
    if writer_lane_ids != expected_writer_lane_ids:
        problems.append(
            "status index writer lanes mismatch: "
            f"expected {sorted(expected_writer_lane_ids)!r}, "
            f"found {sorted(writer_lane_ids)!r}",
        )
    for row in authority_rows:
        lane_id = row.get("lane_id", "")
        expected = WRITER_LANE_AUTHORITY.get(lane_id)
        if expected is None:
            problems.append(f"unregistered writer lane: {lane_id}")
            continue
        if row.get("product_authority_scope") != expected["scope"]:
            problems.append("writer row has unexpected product_authority_scope")
        current_scope = _mapping_path(
            authority,
            "current_authority",
            expected["authority_key"],
        )
        if not isinstance(current_scope, Mapping):
            problems.append(f"authority manifest missing {expected['authority_key']}")
            continue
        if row.get("row_count") != str(
            current_scope.get("current_product_authority_rows")
        ):
            problems.append("writer row_count does not match authority manifest")
        if row.get("may_touch_matrix") != "TRUE":
            problems.append("writer row must explicitly mark matrix touch")

    for index, row in enumerate(rows, start=2):
        status = row.get("readiness_status", "")
        lane_group = row.get("lane_group", "")
        write = row.get("write_authority") == "TRUE"
        scope = row.get("product_authority_scope", "")
        output_change_flags = {
            field: row.get(field)
            for field in (
                "may_change_quant_output",
                "may_change_workbook",
                "may_change_selected_peak",
                "may_change_selected_area",
                "may_change_counted_detection",
            )
        }
        output_change = any(value == "TRUE" for value in output_change_flags.values())
        is_writer_lane = row.get("lane_id") in WRITER_LANE_AUTHORITY
        if not is_writer_lane:
            if scope:
                problems.append(f"row {index}: non-writer row has authority scope")
            if output_change:
                changed = sorted(
                    field
                    for field, value in output_change_flags.items()
                    if value == "TRUE"
                )
                problems.append(
                    f"row {index}: non-writer row changes product output: "
                    + ", ".join(changed)
                )
        if status in WRITE_FORBIDDEN_STATUSES and (
            write or scope or row.get("may_touch_matrix") == "TRUE" or output_change
        ):
            problems.append(f"row {index}: {status} lane grants authority")
        if lane_group in NON_AUTHORITY_LANE_GROUPS and (
            write or scope or row.get("may_touch_matrix") == "TRUE" or output_change
        ):
            problems.append(f"row {index}: {lane_group} lane grants authority")
        if scope and scope not in allowed_scopes:
            problems.append(f"row {index}: unregistered authority scope {scope!r}")
        if row.get("lane_id") == "broad_backfill_autowrite":
            if status != "parked" or write or scope:
                problems.append(
                    "broad_backfill_autowrite must stay parked/no authority"
                )
        if row.get("lane_id") == "quality_explanation_sidecar_v1":
            if status != "diagnostic_only" or write or scope:
                problems.append(
                    "quality_explanation_sidecar_v1 must be diagnostic only"
                )


def _check_artifacts(
    rows: Sequence[Mapping[str, str]],
    repo_root: Path,
    problems: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        artifact = row.get("current_artifact", "")
        expected_hash = row.get("artifact_sha256", "")
        if not artifact:
            continue
        path = repo_root / artifact
        if not path.exists():
            problems.append(f"row {index}: artifact does not exist: {artifact}")
            continue
        if not expected_hash:
            problems.append(f"row {index}: artifact_sha256 is required")
        elif artifact_sha256(path) != expected_hash:
            problems.append(f"row {index}: artifact_sha256 mismatch for {artifact}")


def _check_doc_anchors(
    rows: Sequence[Mapping[str, str]],
    handoff_text: str,
    control_plane_text: str,
    problems: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        lane_id = row.get("lane_id", "")
        handoff_anchor = row.get("handoff_anchor", "")
        control_anchor = row.get("control_plane_anchor", "")
        if not handoff_anchor:
            problems.append(f"row {index}: handoff anchor is required")
        if not control_anchor:
            problems.append(f"row {index}: control-plane anchor is required")
        if (
            handoff_anchor
            and handoff_anchor not in handoff_text
            and lane_id not in handoff_text
        ):
            problems.append(f"row {index}: handoff anchor not found")
        if (
            control_anchor
            and control_anchor not in control_plane_text
            and lane_id not in control_plane_text
        ):
            problems.append(f"row {index}: control-plane anchor not found")


def _mapping_path(root: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    current: Any = root
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _read_json(path: Path, problems: list[str]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"failed to read {path}: {exc}")
    except json.JSONDecodeError as exc:
        problems.append(f"invalid JSON {path}: {exc}")
    return {}


def _read_tsv(
    path: Path,
    problems: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return list(reader.fieldnames or []), list(reader)
    except OSError as exc:
        problems.append(f"failed to read {path}: {exc}")
        return [], []


def _read_text(path: Path, problems: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(f"failed to read {path}: {exc}")
        return ""


def artifact_sha256(path: Path) -> str:
    """Hash productization artifacts independently of checkout line endings."""

    normalized_path = f"/{path.as_posix()}"
    if path.suffix.lower() in CANONICAL_TEXT_HASH_EXTENSIONS and (
        "/docs/superpowers/" in normalized_path
        or "/output/productization_realdata_seed_guard_85raw_20260617/"
        "generated_policy_quality_explained_no_raw_productization/"
        in normalized_path
    ):
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return hashlib.sha256(data).hexdigest().upper()
    return _sha256(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--status-index", type=Path, default=DEFAULT_STATUS_INDEX)
    parser.add_argument(
        "--authority-manifest",
        type=Path,
        default=DEFAULT_AUTHORITY_MANIFEST,
    )
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--control-plane", type=Path, default=DEFAULT_CONTROL_PLANE)
    args = parser.parse_args(argv)
    problems = check_productization_state(
        schema_path=args.schema,
        status_index_path=args.status_index,
        authority_manifest_path=args.authority_manifest,
        handoff_path=args.handoff,
        control_plane_path=args.control_plane,
    )
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("Productization state index is consistent and fail-closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
