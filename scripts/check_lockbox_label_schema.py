"""Validate Lockbox Label Collection Pack v1.

The default mode validates the committed packet/template contract
structurally. It does not require ignored local ``output/`` evidence files to be
present, so it can run on a clean checkout. Use ``--verify-evidence-files`` on a
machine that has the referenced evidence artifacts to verify file hashes. Use
``--require-complete`` after reviewers fill labels to require two complete,
distinct reviewer labels per lockbox case. This checker never grants product
authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.lockbox_reviewer_identity import (
    allowed_human_truth_reviewer_ids_from_schema,
    truth_label_reviewer_id_blocker,
)
from xic_extractor.tabular_io import file_sha256, read_tsv_with_header

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/superpowers/schemas/lockbox_label_schema_v1.json"
LOCKBOX_MANIFEST = (
    ROOT / "docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv"
)
PACKET_DIR = ROOT / "docs/superpowers/validation/lockbox_review_packets_v1"
LABEL_TEMPLATE = ROOT / "docs/superpowers/validation/lockbox_label_template_v1.tsv"
_SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


def check_lockbox_label_schema(
    *,
    schema_path: Path = SCHEMA_PATH,
    manifest_path: Path = LOCKBOX_MANIFEST,
    packet_dir: Path = PACKET_DIR,
    label_template_path: Path = LABEL_TEMPLATE,
    require_complete: bool = False,
    verify_evidence_files: bool = False,
) -> list[str]:
    problems: list[str] = []
    schema = _read_json(schema_path, problems)
    manifest_header, manifest_rows = _read_tsv(
        manifest_path,
        required_columns=("lockbox_case_id", "required_reviewer_count"),
        problems=problems,
    )
    template_header, template_rows = _read_tsv(
        label_template_path,
        problems=problems,
    )
    packet_index_header, packet_rows = _read_tsv(
        packet_dir / "packet_index.tsv",
        problems=problems,
    )
    if not schema:
        return problems
    _check_manifest(manifest_rows, problems)
    _check_packet_index(
        schema,
        packet_index_header,
        packet_rows,
        manifest_rows,
        packet_dir,
        verify_evidence_files,
        problems,
    )
    _check_label_template(
        schema,
        template_header,
        template_rows,
        manifest_rows,
        packet_rows,
        require_complete,
        problems,
    )
    if manifest_header and len(manifest_rows) != 72:
        problems.append("lockbox manifest must contain exactly 72 cases")
    return problems


def _check_manifest(
    manifest_rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    case_ids = [row.get("lockbox_case_id", "") for row in manifest_rows]
    duplicates = sorted(case for case, count in Counter(case_ids).items() if count > 1)
    if duplicates:
        problems.append("duplicate lockbox cases in manifest: " + ", ".join(duplicates))
    for index, row in enumerate(manifest_rows, start=2):
        if row.get("may_touch_matrix") != "FALSE":
            problems.append(f"manifest row {index}: may_touch_matrix must be FALSE")
        if row.get("may_grant_product_authority") != "FALSE":
            problems.append(
                f"manifest row {index}: may_grant_product_authority must be FALSE",
            )


def _check_packet_index(
    schema: Mapping[str, Any],
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    manifest_rows: Sequence[Mapping[str, str]],
    packet_dir: Path,
    verify_evidence_files: bool,
    problems: list[str],
) -> None:
    expected_header = schema.get("required_packet_index_columns", [])
    if list(header) != expected_header:
        problems.append("packet index header must match schema")
    manifest_ids = {row["lockbox_case_id"] for row in manifest_rows}
    packet_ids = [row.get("lockbox_case_id", "") for row in rows]
    if set(packet_ids) != manifest_ids:
        problems.append("packet index case IDs must match lockbox manifest")
    duplicates = sorted(
        case for case, count in Counter(packet_ids).items() if count > 1
    )
    if duplicates:
        problems.append("duplicate packet rows: " + ", ".join(duplicates))
    allowed_evidence = set(schema.get("allowed_evidence_status", []))
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != "lockbox_review_packet_v1":
            problems.append(f"packet row {index}: invalid schema_version")
        if row.get("may_touch_matrix") != "FALSE":
            problems.append(f"packet row {index}: may_touch_matrix must be FALSE")
        if row.get("may_grant_product_authority") != "FALSE":
            problems.append(
                f"packet row {index}: may_grant_product_authority must be FALSE",
            )
        if row.get("evidence_status") not in allowed_evidence:
            problems.append(f"packet row {index}: invalid evidence_status")
        case_id = row.get("lockbox_case_id", "")
        packet_path = _resolve_path(row.get("packet_path", ""))
        expected_packet_path = packet_dir / f"{case_id}.md"
        if packet_path.resolve() != expected_packet_path.resolve():
            problems.append(f"packet row {index}: packet path must be canonical")
        if not packet_path.exists():
            problems.append(f"packet row {index}: packet file missing")
        else:
            text = packet_path.read_text(encoding="utf-8")
            if case_id not in text:
                problems.append(f"packet row {index}: packet file missing case id")
        _check_packet_evidence(row, index, verify_evidence_files, problems)


def _check_packet_evidence(
    row: Mapping[str, str],
    index: int,
    verify_evidence_files: bool,
    problems: list[str],
) -> None:
    status = row.get("evidence_status", "")
    if status == "missing_evidence_recorded":
        if not row.get("missing_evidence_reason"):
            problems.append(f"packet row {index}: missing evidence reason required")
        return
    for path_field, hash_field in (
        ("trace_data_path", "trace_data_sha256"),
        ("overlay_png_path", "overlay_png_sha256"),
        ("hypothesis_png_path", "hypothesis_png_sha256"),
    ):
        path_value = row.get(path_field, "")
        if not path_value:
            problems.append(f"packet row {index}: {path_field} required")
            continue
        expected_hash = row.get(hash_field, "")
        if not _is_sha256(expected_hash):
            problems.append(f"packet row {index}: {hash_field} must be SHA256")
            continue
        if not verify_evidence_files:
            continue
        path = _resolve_path(path_value)
        if not path.exists():
            problems.append(f"packet row {index}: {path_field} missing")
        elif file_sha256(path) != expected_hash:
            problems.append(f"packet row {index}: {hash_field} mismatch")


def _check_label_template(
    schema: Mapping[str, Any],
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    manifest_rows: Sequence[Mapping[str, str]],
    packet_rows: Sequence[Mapping[str, str]],
    require_complete: bool,
    problems: list[str],
) -> None:
    expected_header = schema.get("required_label_template_columns", [])
    if list(header) != expected_header:
        problems.append("label template header must match schema")
    manifest_by_case = {row["lockbox_case_id"]: row for row in manifest_rows}
    packets_by_case = {row.get("lockbox_case_id", ""): row for row in packet_rows}
    required_total = sum(
        int(row.get("required_reviewer_count", "2") or "2")
        for row in manifest_rows
    )
    if len(rows) != required_total:
        problems.append("label template row count must match reviewer slots")
    rows_by_case: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        case_id = row.get("lockbox_case_id", "")
        rows_by_case[case_id].append(row)
        _check_label_row(
            schema,
            row,
            index,
            expected_packet=packets_by_case.get(case_id),
            require_complete=require_complete,
            problems=problems,
        )
    if set(rows_by_case) != set(manifest_by_case):
        problems.append("label template case IDs must match lockbox manifest")
    for case_id, manifest_row in manifest_by_case.items():
        expected = int(manifest_row.get("required_reviewer_count", "2") or "2")
        case_rows = rows_by_case.get(case_id, [])
        slots = {row.get("reviewer_slot", "") for row in case_rows}
        expected_slots = {str(slot) for slot in range(1, expected + 1)}
        if len(case_rows) != expected or slots != expected_slots:
            problems.append(f"{case_id}: reviewer slots must be 1..{expected}")
        if require_complete:
            reviewer_ids = [row.get("reviewer_id", "") for row in case_rows]
            if len(set(reviewer_ids)) != expected:
                problems.append(f"{case_id}: reviewer IDs must be distinct")


def _check_label_row(
    schema: Mapping[str, Any],
    row: Mapping[str, str],
    index: int,
    *,
    expected_packet: Mapping[str, str] | None,
    require_complete: bool,
    problems: list[str],
) -> None:
    if row.get("schema_version") != "lockbox_label_v1":
        problems.append(f"label row {index}: invalid schema_version")
    if row.get("round_trip_oracle_used") != "FALSE":
        problems.append(f"label row {index}: round_trip_oracle_used must be FALSE")
    if row.get("label_grants_product_authority") != "FALSE":
        problems.append(
            f"label row {index}: label_grants_product_authority must be FALSE",
        )
    if row.get("may_touch_matrix") != "FALSE":
        problems.append(f"label row {index}: may_touch_matrix must be FALSE")
    enum_fields = {
        "peak_choice_label": set(schema.get("allowed_peak_choice_labels", [])),
        "area_label": set(schema.get("allowed_area_labels", [])),
        "boundary_label": set(schema.get("allowed_boundary_labels", [])),
        "reviewer_confidence": set(schema.get("allowed_reviewer_confidence", [])),
        "reviewer_reason_code": set(
            schema.get("allowed_reviewer_reason_codes", []),
        ),
        "evidence_viewed": set(schema.get("allowed_evidence_viewed", [])),
    }
    for field, allowed in enum_fields.items():
        value = row.get(field, "")
        if value and value not in allowed:
            problems.append(f"label row {index}: invalid {field}")
        if require_complete and not value:
            problems.append(f"label row {index}: {field} is required")
    if expected_packet:
        for field in ("row_id", "family_id", "sample_id", "analyte"):
            if row.get(field, "") != expected_packet.get(field, ""):
                problems.append(f"label row {index}: {field} must match packet")
        if (
            row.get("source_artifact_hashes", "")
            != expected_packet.get("source_artifact_hashes", "")
        ):
            problems.append(
                f"label row {index}: source_artifact_hashes must match packet",
            )
    elif require_complete:
        problems.append(f"label row {index}: packet source hashes unavailable")
    for field in ("reviewer_id", "reviewed_at_utc"):
        if require_complete and not row.get(field, ""):
            problems.append(f"label row {index}: {field} is required")
    if require_complete:
        blocker = truth_label_reviewer_id_blocker(
            row.get("reviewer_id", ""),
            allowed_human_truth_reviewer_ids_from_schema(schema),
        )
        if blocker:
            problems.append(
                f"label row {index}: reviewer_id is not human truth: {blocker}",
            )


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


def _is_sha256(value: str) -> bool:
    return bool(_SHA256_RE.match(value))


def _read_json(path: Path, problems: list[str]) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"could not read {path}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        problems.append(f"invalid json {path}: {exc}")
        return None
    if not isinstance(value, Mapping):
        problems.append(f"json root must be object: {path}")
        return None
    return value


def _read_tsv(
    path: Path,
    *,
    required_columns: Sequence[str] = (),
    problems: list[str],
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        return read_tsv_with_header(path, required_columns=required_columns)
    except OSError as exc:
        problems.append(f"could not read {path}: {exc}")
    except ValueError as exc:
        problems.append(str(exc))
    return (), []


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--manifest", type=Path, default=LOCKBOX_MANIFEST)
    parser.add_argument("--packet-dir", type=Path, default=PACKET_DIR)
    parser.add_argument("--label-template", type=Path, default=LABEL_TEMPLATE)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument(
        "--verify-evidence-files",
        action="store_true",
        help=(
            "also require referenced local output evidence files to exist "
            "and match hashes"
        ),
    )
    args = parser.parse_args(argv)
    problems = check_lockbox_label_schema(
        schema_path=args.schema,
        manifest_path=args.manifest,
        packet_dir=args.packet_dir,
        label_template_path=args.label_template,
        require_complete=args.require_complete,
        verify_evidence_files=args.verify_evidence_files,
    )
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("Lockbox label collection pack is structurally valid and non-authoritative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
