"""Shared QuantMatrix artifact path and replay-contract helpers.

These helpers are deliberately mechanical. They resolve bundle-local artifacts,
read summary JSON, compare SHA-bound replay outputs, and validate source-summary
input hashes. They do not decide matrix authority, run RAW, score peaks, or
change ProductWriter behavior.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from xic_extractor.alignment.quant_matrix_fixture_contract import (
    validate_fixture_contract,
)
from xic_extractor.tabular_io import file_sha256, read_tsv_required

ACTIVATION_INPUT_LABELS = (
    "baseline_quant_matrix",
    "input_matrix_identity",
    "production_acceptance_manifest",
    "expected_diff",
)


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def raise_if_problems(label: str, problems: Sequence[str]) -> None:
    if problems:
        raise ValueError(f"{label}: " + "; ".join(problems))


def resolve_source(path: Path, *, source_root: Path) -> Path:
    return path if path.is_absolute() else source_root / path


def source_relpath(path: Path, *, source_root: Path) -> str:
    return source_relpath_existing(path, source_root=source_root)


def source_relpath_existing(path: Path, *, source_root: Path) -> str:
    try:
        return path.resolve(strict=True).relative_to(
            source_root.resolve(strict=True),
        ).as_posix()
    except ValueError:
        return str(path.resolve(strict=True))


def source_relpath_reference(path: Path, *, source_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(
            source_root.resolve(strict=True),
        ).as_posix()
    except ValueError:
        return str(path.resolve(strict=False))


def artifact_record(path: Path, *, base_dir: Path) -> dict[str, str]:
    return {
        "path": path.resolve(strict=False).relative_to(
            base_dir.resolve(strict=False),
        ).as_posix(),
        "sha256": file_sha256(path),
    }


def resolve_real_bundle_paths(
    payload: Mapping[str, Any],
    summary_json: Path,
    *,
    required_labels: Sequence[str],
    source_root: Path | None = None,
    include_cell_provenance: bool = False,
    include_cell_provenance_reference: bool = False,
    optional_labels: Sequence[str] = (),
) -> dict[str, Path]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("real bundle artifacts must be an object")
    output_dir = summary_json.parent
    result: dict[str, Path] = {}
    for label in required_labels:
        raw_entry = artifacts.get(label)
        if not isinstance(raw_entry, dict):
            raise ValueError(f"real bundle {label} artifact is missing")
        result[label] = resolve_real_bundle_artifact(
            raw_entry,
            output_dir=output_dir,
            label=label,
        )
    if include_cell_provenance:
        append_real_bundle_cell_provenance_paths(
            artifacts,
            output_dir=output_dir,
            result=result,
            source_root=source_root,
            include_reference=include_cell_provenance_reference,
        )
    for label in optional_labels:
        raw_entry = artifacts.get(label)
        if isinstance(raw_entry, dict) and label not in result:
            result[label] = resolve_real_bundle_artifact(
                raw_entry,
                output_dir=output_dir,
                label=label,
            )
    return result


def append_real_bundle_cell_provenance_paths(
    artifacts: Mapping[str, Any],
    *,
    output_dir: Path,
    result: dict[str, Path],
    source_root: Path | None = None,
    include_reference: bool = False,
) -> None:
    raw_entry = artifacts.get("cell_provenance")
    if not isinstance(raw_entry, dict):
        raise ValueError("real bundle cell_provenance artifact is missing")
    resolved = resolve_real_bundle_artifact_path(
        raw_entry,
        output_dir=output_dir,
        label="cell_provenance",
    )
    if include_reference:
        result["cell_provenance_reference"] = resolved
    if resolved.is_file():
        result["cell_provenance"] = resolved
        return
    if raw_entry.get("externalized") is not True:
        raise FileNotFoundError(str(resolved))
    externalized_path = _resolve_externalized_artifact_path(
        raw_entry,
        source_root=source_root,
        label="cell_provenance",
    )
    if externalized_path is not None:
        result["cell_provenance_externalized"] = externalized_path
    summary_relpath = str(raw_entry.get("replacement_or_summary", "")).strip()
    if not summary_relpath:
        raise ValueError("real bundle cell_provenance replacement is missing")
    result["cell_provenance_summary"] = resolve_real_bundle_artifact(
        {"path": summary_relpath},
        output_dir=output_dir,
        label="cell_provenance_summary",
    )


def _resolve_externalized_artifact_path(
    raw_entry: Mapping[str, Any],
    *,
    source_root: Path | None,
    label: str,
) -> Path | None:
    if source_root is None:
        return None
    relpath = str(raw_entry.get("externalized_path", "")).strip()
    if not relpath:
        return None
    path = Path(relpath)
    if path.is_absolute() or ".." in path.parts:
        return None
    return (source_root / path).resolve(strict=False)


def resolve_real_bundle_artifact(
    raw_entry: Mapping[str, Any],
    *,
    output_dir: Path,
    label: str,
) -> Path:
    resolved = resolve_real_bundle_artifact_path(
        raw_entry,
        output_dir=output_dir,
        label=label,
    )
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def resolve_real_bundle_artifact_path(
    raw_entry: Mapping[str, Any],
    *,
    output_dir: Path,
    label: str,
) -> Path:
    relpath = str(raw_entry.get("path", "")).strip()
    path = Path(relpath)
    if not relpath or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"real bundle {label} path must be bundle-relative")
    resolved = (output_dir / path).resolve(strict=False)
    try:
        resolved.relative_to(output_dir.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(f"real bundle {label} path escapes bundle") from exc
    return resolved


def source_summary_input_hash_problems(
    source_summary_tsv: Path,
    *,
    expected_inputs: Mapping[str, Path],
) -> list[str]:
    rows = read_tsv_required(source_summary_tsv, ("schema_version",))
    if len(rows) != 1:
        return ["source_summary must contain exactly one row"]
    row = rows[0]
    expected_hashes = {
        "input_quant_matrix_sha256": file_sha256(
            expected_inputs["baseline_quant_matrix"],
        ),
        "input_matrix_identity_sha256": file_sha256(
            expected_inputs["input_matrix_identity"],
        ),
        "production_acceptance_manifest_sha256": file_sha256(
            expected_inputs["production_acceptance_manifest"],
        ),
        "expected_diff_sha256": file_sha256(expected_inputs["expected_diff"]),
    }
    problems: list[str] = []
    for field, expected in expected_hashes.items():
        if row.get(field) != expected:
            problems.append(f"source_summary {field} mismatch")
    return problems


def cell_provenance_rerun_problems(
    rerun_cell_provenance_tsv: Path,
    summary_json: Path,
    *,
    invalid_message_prefix: str,
    mismatch_message: str,
) -> list[str]:
    try:
        payload = read_json_object(summary_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"{invalid_message_prefix}: {exc}"]
    source_sha = str(payload.get("source_sha256", "")).upper()
    if file_sha256(rerun_cell_provenance_tsv) != source_sha:
        return [mismatch_message]
    return []


def materialize_cell_provenance_for_replay(
    *,
    bundle_paths: Mapping[str, Path],
    source_root: Path,
    output_dir: Path,
    activation_runner: Callable[..., Mapping[str, Path]],
    problems: list[str],
    problem_prefix: str,
    mismatch_message: str,
) -> Path | None:
    existing = bundle_paths.get("cell_provenance")
    if existing is not None:
        return existing

    summary = bundle_paths.get("cell_provenance_summary")
    fixture = bundle_paths.get("cell_provenance_minimal_fixture")
    if summary is None or fixture is None:
        problems.append(f"{problem_prefix} cell_provenance replacement missing")
        return None

    contract_problems = validate_fixture_contract(summary, fixture)
    if contract_problems:
        problems.extend(
            f"{problem_prefix} cell_provenance contract: {problem}"
            for problem in contract_problems
        )
        return None

    externalized = bundle_paths.get("cell_provenance_externalized")
    if externalized is not None and externalized.is_file():
        externalized_problems = cell_provenance_rerun_problems(
            externalized,
            summary,
            invalid_message_prefix=(
                f"{problem_prefix} cell_provenance summary invalid "
                "for externalized copy comparison"
            ),
            mismatch_message=(
                f"{problem_prefix} externalized cell_provenance sha256 mismatch"
            ),
        )
        if externalized_problems:
            problems.extend(externalized_problems)
            return None
        return externalized

    activation_outputs = dict(
        activation_runner(
            input_quant_matrix_tsv=bundle_paths["baseline_quant_matrix"],
            input_matrix_identity_tsv=bundle_paths["input_matrix_identity"],
            production_acceptance_manifest_tsv=bundle_paths[
                "production_acceptance_manifest"
            ],
            expected_diff_tsv=bundle_paths["expected_diff"],
            output_dir=output_dir,
            manifest_root=source_root,
        )
    )
    cell_provenance = activation_outputs["cell_provenance"]
    problems.extend(
        cell_provenance_rerun_problems(
            cell_provenance,
            summary,
            invalid_message_prefix=(
                f"{problem_prefix} cell_provenance summary invalid "
                "for rerun comparison"
            ),
            mismatch_message=mismatch_message,
        )
    )
    return cell_provenance
