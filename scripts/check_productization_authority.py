"""Check productization authority/adjudication artifacts fail closed.

This is a contract guard, not a writer. It validates the current authority
manifest, mechanical adjudication schema, and adjudication index without
touching ProductWriter, matrices, workbooks, selected peaks, or counted
detections.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.check_productization_state import artifact_sha256

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "docs/superpowers/specs/productization_authority_manifest.v1.json"
)
DEFAULT_SCHEMA = (
    ROOT / "docs/superpowers/specs/mechanical_adjudication_schema.v1.json"
)
DEFAULT_INDEX = (
    ROOT / "docs/superpowers/validation/mechanical_adjudication_index_v1.tsv"
)

APPROVED_SCOPE = "backfill_policy_write_ready_rows"
CID_NL_APPROVED_SCOPE = "cid_nl_adopt_ready_feature_inclusion_95_cells"
APPROVED_SCOPES = {APPROVED_SCOPE, CID_NL_APPROVED_SCOPE}
PARKED_BROAD_BACKFILL = "broad_backfill"
NEGATIVE_SCOPE_IDS = {
    "all_stability",
    "apex_delta_clean",
    "width_only_clean",
    "shape_margin_clean",
    "shape_clean_reintegration_stable_writer_probe",
}


def check_productization_authority(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    schema_path: Path = DEFAULT_SCHEMA,
    index_path: Path = DEFAULT_INDEX,
    repo_root: Path = ROOT,
) -> list[str]:
    problems: list[str] = []
    manifest = _read_json(manifest_path, problems)
    schema = _read_json(schema_path, problems)
    header, rows = _read_tsv(index_path, problems)
    if not manifest or not schema:
        return problems

    _check_manifest(manifest, problems)
    _check_schema_and_index(schema, header, rows, problems)
    _check_index_authority(manifest, rows, problems)
    _check_source_hashes(manifest, rows, repo_root, problems)
    _check_cid_nl_source_hashes(manifest, repo_root, problems)
    return problems


def _check_manifest(manifest: Mapping[str, Any], problems: list[str]) -> None:
    policy = manifest.get("authority_policy")
    if not isinstance(policy, Mapping):
        problems.append("manifest missing authority_policy object")
        return
    if policy.get("unregistered_scope_policy") != "fail_closed":
        problems.append("unregistered_scope_policy must be fail_closed")
    if set(policy.get("product_writer_allowed_scopes", [])) != APPROVED_SCOPES:
        problems.append(
            "product_writer_allowed_scopes must match registered scopes: "
            f"{sorted(APPROVED_SCOPES)!r}",
        )

    backfill = _mapping_path(manifest, "current_authority", "backfill")
    if backfill is None:
        problems.append("manifest missing current_authority.backfill")
    else:
        expected = {
            "candidate_audit_universe_rows": 4613,
            "current_product_authority_rows": 511,
            "detected_flagged_rows": 0,
            "blocked_rows": 4102,
            "authority_scope": APPROVED_SCOPE,
        }
        for key, value in expected.items():
            if backfill.get(key) != value:
                problems.append(f"manifest backfill {key} must be {value!r}")

    cid_nl = _mapping_path(manifest, "current_authority", "cid_nl_default_activation")
    if cid_nl is None:
        problems.append("manifest missing current_authority.cid_nl_default_activation")
    else:
        expected_cid_nl = {
            "current_product_authority_rows": 95,
            "existing_successor_context_rows": 337,
            "omitted_no_target_rows": 27,
            "authority_scope": CID_NL_APPROVED_SCOPE,
        }
        for key, value in expected_cid_nl.items():
            if cid_nl.get(key) != value:
                problems.append(f"manifest CID-NL {key} must be {value!r}")

    parked = _mapping_path(manifest, "parked_lanes", PARKED_BROAD_BACKFILL)
    if parked is None:
        problems.append("manifest missing parked broad_backfill lane")
    else:
        if parked.get("status") != "parked":
            problems.append("broad_backfill status must be parked")
        if parked.get("may_grant_write_authority") is not False:
            problems.append("broad_backfill may_grant_write_authority must be false")

    explanation_sources = manifest.get("explanation_only_sources")
    if not isinstance(explanation_sources, list) or not explanation_sources:
        problems.append("manifest must list explanation_only_sources")
    else:
        for source in explanation_sources:
            if not isinstance(source, Mapping):
                problems.append("explanation_only_sources entries must be objects")
            elif source.get("may_grant_write_authority") is not False:
                problems.append("explanation_only source grants authority")

    negative_scope_ids = {
        scope.get("scope_id")
        for scope in manifest.get("blocked_or_negative_evidence_scopes", [])
        if isinstance(scope, Mapping)
    }
    missing_negative = sorted(NEGATIVE_SCOPE_IDS - negative_scope_ids)
    if missing_negative:
        problems.append(
            "manifest missing negative-evidence scopes: "
            + ", ".join(missing_negative)
        )


def _check_schema_and_index(
    schema: Mapping[str, Any],
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    required = schema.get("required_columns")
    if not isinstance(required, list) or not all(
        isinstance(column, str) for column in required
    ):
        problems.append("schema required_columns must be a string list")
        return
    missing = sorted(set(required) - set(header))
    if missing:
        problems.append("index missing required columns: " + ", ".join(missing))
    if len(rows) != 4613:
        problems.append(f"index must contain 4613 rows, found {len(rows)}")
    row_ids = [row.get("row_id", "") for row in rows]
    if len(set(row_ids)) != len(row_ids):
        problems.append("index row_id values must be unique")

    decision_counts = Counter(row.get("decision", "") for row in rows)
    if decision_counts != {"write_ready": 511, "evidence_required": 4102}:
        problems.append(f"unexpected decision counts: {dict(decision_counts)}")
    grade_counts = Counter(row.get("evidence_grade", "") for row in rows)
    if grade_counts != {"A": 511, "C": 3015, "D": 1087}:
        problems.append(f"unexpected evidence_grade counts: {dict(grade_counts)}")


def _check_index_authority(
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    policy = manifest.get("authority_policy")
    allowed = set(policy.get("product_writer_allowed_scopes", []))
    authority_scope_values: set[str] = set()
    for index, row in enumerate(rows, start=2):
        write_authority = row.get("write_authority")
        scope = row.get("product_authority_scope", "")
        if scope:
            authority_scope_values.add(scope)
        if write_authority == "TRUE":
            _require_row_value(row, index, "decision", "write_ready", problems)
            _require_row_value(
                row,
                index,
                "source_policy_decision",
                "write_ready",
                problems,
            )
            _require_row_value(row, index, "explanation_only", "FALSE", problems)
            _require_row_value(row, index, "may_touch_matrix", "TRUE", problems)
            if scope not in allowed:
                problems.append(f"row {index}: unregistered authority scope {scope!r}")
        elif write_authority == "FALSE":
            _require_row_value(row, index, "may_touch_matrix", "FALSE", problems)
            if scope:
                problems.append(f"row {index}: non-write row has authority scope")
        else:
            problems.append(f"row {index}: invalid write_authority {write_authority!r}")

        if row.get("explanation_only") == "TRUE" and write_authority != "FALSE":
            problems.append(f"row {index}: explanation_only row grants authority")
        if row.get("blockers") and write_authority != "FALSE":
            problems.append(f"row {index}: blocker row grants authority")

    if authority_scope_values != {APPROVED_SCOPE}:
        problems.append(
            "index authority scopes must be exactly "
            f"{APPROVED_SCOPE!r}, found {sorted(authority_scope_values)!r}"
        )
    forbidden = authority_scope_values & (NEGATIVE_SCOPE_IDS | {PARKED_BROAD_BACKFILL})
    if forbidden:
        problems.append("forbidden authority scopes present: " + ", ".join(forbidden))


def _check_source_hashes(
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, str]],
    repo_root: Path,
    problems: list[str],
) -> None:
    if not rows:
        return
    source_hash_sets = {row.get("source_hashes", "") for row in rows}
    if len(source_hash_sets) != 1:
        problems.append("index rows must share one source_hashes value")
        return
    source_hashes = _parse_semicolon_pairs(source_hash_sets.pop())
    backfill = _mapping_path(manifest, "current_authority", "backfill")
    explanation_sources = manifest.get("explanation_only_sources", [])
    if backfill is None or not explanation_sources:
        return
    expected_policy_hash = backfill.get("artifact_sha256")
    expected_quality_hash = explanation_sources[0].get("artifact_sha256")
    if source_hashes.get("policy") != expected_policy_hash:
        problems.append("index policy source hash does not match manifest")
    if source_hashes.get("quality") != expected_quality_hash:
        problems.append("index quality source hash does not match manifest")

    artifacts = {
        "policy": backfill.get("artifact"),
        "quality": explanation_sources[0].get("artifact"),
    }
    for source_id, relative in artifacts.items():
        if not isinstance(relative, str):
            continue
        path = repo_root / relative
        if path.exists() and artifact_sha256(path) != source_hashes.get(source_id):
            problems.append(f"{source_id} artifact hash does not match index")


def _check_cid_nl_source_hashes(
    manifest: Mapping[str, Any],
    repo_root: Path,
    problems: list[str],
) -> None:
    cid_nl = _mapping_path(manifest, "current_authority", "cid_nl_default_activation")
    if cid_nl is None:
        return
    artifact_fields = {
        "artifact": "artifact_sha256",
        "acceptance_artifact": "acceptance_artifact_sha256",
        "compact_manifest": "compact_manifest_sha256",
    }
    for path_key, sha_key in artifact_fields.items():
        relative = cid_nl.get(path_key)
        expected_hash = cid_nl.get(sha_key)
        if not isinstance(relative, str) or not relative:
            problems.append(f"manifest CID-NL {path_key} must be a non-empty path")
            continue
        if not isinstance(expected_hash, str) or not expected_hash:
            problems.append(f"manifest CID-NL {sha_key} must be a non-empty hash")
            continue
        path = repo_root / relative
        if not path.is_file():
            problems.append(f"CID-NL {path_key} artifact is missing: {relative}")
            continue
        if artifact_sha256(path) != expected_hash:
            problems.append(f"CID-NL {path_key} hash does not match manifest")


def _mapping_path(
    root: Mapping[str, Any],
    *keys: str,
) -> Mapping[str, Any] | None:
    current: Any = root
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _require_row_value(
    row: Mapping[str, str],
    row_number: int,
    field: str,
    expected: str,
    problems: list[str],
) -> None:
    if row.get(field) != expected:
        problems.append(f"row {row_number}: {field} must be {expected!r}")


def _read_json(path: Path, problems: list[str]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"{path}: cannot read JSON: {exc}")
    except json.JSONDecodeError as exc:
        problems.append(f"{path}: invalid JSON: {exc}")
    return {}


def _read_tsv(
    path: Path,
    problems: list[str],
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return tuple(reader.fieldnames or ()), list(reader)
    except OSError as exc:
        problems.append(f"{path}: cannot read TSV: {exc}")
        return (), []


def _parse_semicolon_pairs(value: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for part in value.split(";"):
        if not part:
            continue
        key, separator, item = part.partition("=")
        if separator:
            parsed[key] = item
    return parsed


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = check_productization_authority(
        manifest_path=args.manifest,
        schema_path=args.schema,
        index_path=args.index,
        repo_root=args.repo_root,
    )
    if problems:
        print("Productization authority contract failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Productization authority contract is fail-closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
