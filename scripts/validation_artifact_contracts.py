"""Shared validation-artifact hash checks for retained summary packets."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from xic_extractor.tabular_io import file_sha256, text_value

EXTERNALIZED_PATH_PREFIXES = (
    "output/",
    "local_validation_artifacts/",
)
TEXT_HASH_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".txt",
    ".tsv",
}


def check_summary_artifact_hashes(
    payload: Mapping[str, Any],
    *,
    root: Path,
    problems: list[str],
    section_names: Sequence[str] = ("artifacts", "input_artifacts"),
) -> None:
    """Validate retained artifact metadata without requiring externalized files.

    Retained docs/config artifacts are clean-checkout prerequisites and must be
    present. Externalized artifacts, usually under output/, are provenance
    records; they may be absent in CI, but if present their hash must match.
    """
    for section_name in section_names:
        section = payload.get(section_name)
        if not isinstance(section, Mapping):
            problems.append(f"summary {section_name} must be an object")
            continue
        _check_artifact_section(
            section,
            section_name=section_name,
            root=root,
            problems=problems,
        )


def _check_artifact_section(
    section: Mapping[str, Any],
    *,
    section_name: str,
    root: Path,
    problems: list[str],
) -> None:
    for label, entry in section.items():
        if not isinstance(entry, Mapping):
            problems.append(f"summary {section_name} {label} must be an object")
            continue
        relpath = text_value(entry.get("path"))
        expected_sha = text_value(entry.get("sha256"))
        if not relpath:
            problems.append(f"summary {section_name} {label} path missing")
            continue
        if not expected_sha:
            if label == "summary_json":
                continue
            problems.append(f"summary {section_name} {label} sha256 missing")
            continue
        path = root / relpath
        if not path.exists():
            if is_externalized_artifact_entry(entry, relpath):
                continue
            problems.append(f"summary {section_name} {label} missing: {relpath}")
            continue
        if expected_sha not in _hash_candidates(path):
            problems.append(f"summary {section_name} {label} sha256 mismatch")


def is_externalized_artifact_entry(
    entry: Mapping[str, Any],
    relpath: str,
) -> bool:
    normalized = relpath.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        return False
    return normalized.startswith(EXTERNALIZED_PATH_PREFIXES)


def is_declared_externalized_artifact_path(
    payload: Mapping[str, Any],
    label: str,
    path: Path,
    *,
    root: Path,
    section_name: str = "artifacts",
) -> bool:
    section = payload.get(section_name)
    if not isinstance(section, Mapping):
        return False
    entry = section.get(label)
    if not isinstance(entry, Mapping):
        return False
    relpath = text_value(entry.get("path"))
    if not relpath:
        return False
    declared_path = (root / relpath).resolve()
    return path.resolve() == declared_path and is_externalized_artifact_entry(
        entry,
        relpath,
    )


def resolve_existing_summary_artifact_path(
    artifacts: Mapping[str, Any],
    label: str,
    *,
    root: Path,
    problems: list[str],
    section_name: str = "artifacts",
) -> Path | None:
    """Return an artifact path only when detailed content checks can run.

    Retained artifacts are required in a clean checkout. Externalized artifacts
    may be absent, but if present they should still be consumed by callers.
    """
    entry = artifacts.get(label)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
        problems.append(f"summary {section_name} {label} path missing")
        return None
    relpath = text_value(entry.get("path"))
    path = root / relpath
    if path.exists():
        return path.resolve()
    if is_externalized_artifact_entry(entry, relpath):
        return None
    problems.append(f"summary {section_name} {label} missing: {relpath}")
    return None


def artifact_hash_matches(path: Path, expected_sha: str) -> bool:
    return text_value(expected_sha) in _hash_candidates(path)


def _hash_candidates(path: Path) -> set[str]:
    raw_hash = file_sha256(path)
    if path.suffix.lower() not in TEXT_HASH_SUFFIXES:
        return {raw_hash}
    raw = path.read_bytes()
    lf_bytes = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf_bytes = lf_bytes.replace(b"\n", b"\r\n")
    return {
        raw_hash,
        hashlib.sha256(lf_bytes).hexdigest().upper(),
        hashlib.sha256(crlf_bytes).hexdigest().upper(),
    }
