"""Shared helpers for docs/superpowers artifact retention checkers.

This module owns the mechanical artifact-retention interface: policy decision
discovery, inventory indexing, repo path normalization, git-visible path
enumeration, and retained-file metadata checks. Validation and fixture checkers
keep their policy-specific rules local.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.tabular_io import file_sha256, read_tsv_with_header


@dataclass(frozen=True)
class RetainedFileMetadata:
    size_bytes: int
    line_count: int
    sha256: str


def read_policy_decisions(
    path: Path,
    *,
    required_decisions: set[str],
    problems: list[str],
    missing_message: str,
) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(f"could not read retention policy {path}: {exc}")
        return set()
    decisions = set(re.findall(r"\|\s*`([^`]+)`\s*\|", text))
    missing = required_decisions - decisions
    if missing:
        problems.append(missing_message + ", ".join(sorted(missing)))
    return decisions


def read_inventory_rows(
    path: Path,
    *,
    required_columns: Sequence[str],
    problems: list[str],
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        return read_tsv_with_header(path, required_columns=required_columns)
    except OSError as exc:
        problems.append(f"could not read inventory {path}: {exc}")
    except ValueError as exc:
        problems.append(str(exc))
    return (), []


def index_inventory_by_path(
    rows: Sequence[Mapping[str, str]],
    *,
    problems: list[str],
    self_index_path: str | None = None,
    self_index_message: str | None = None,
) -> dict[str, Mapping[str, str]]:
    by_path: dict[str, Mapping[str, str]] = {}
    seen = Counter(normalize_repo_path(row.get("path", "")) for row in rows)
    duplicates = sorted(path for path, count in seen.items() if path and count > 1)
    if duplicates:
        problems.append("duplicate inventory rows: " + ", ".join(duplicates))
    for index, row in enumerate(rows, start=2):
        path = normalize_repo_path(row.get("path", ""))
        if not path:
            problems.append(f"inventory row {index}: path is required")
            continue
        if self_index_path is not None and path == normalize_repo_path(self_index_path):
            message = self_index_message or f"{path}: inventory self row is not allowed"
            problems.append(message)
            continue
        if path not in by_path:
            by_path[path] = row
    return by_path


def present_existing_paths(
    candidate_paths: Sequence[str],
    *,
    repo_root: Path,
    exclude_paths: set[str] | None = None,
) -> set[str]:
    excluded = {normalize_repo_path(path) for path in (exclude_paths or set())}
    return {
        path
        for path in (normalize_repo_path(path) for path in candidate_paths)
        if path not in excluded and (repo_root / path).exists()
    }


def missing_inventory_paths(
    present_paths: Sequence[str] | set[str],
    inventory_by_path: Mapping[str, Mapping[str, str]],
) -> list[str]:
    return sorted(path for path in present_paths if path not in inventory_by_path)


def git_visible_paths(
    *,
    repo_root: Path,
    surface_dir: Path,
    problems: list[str],
    exclude_paths: set[str] | None = None,
    include_deleted: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    rel_surface = repo_relative(surface_dir, repo_root)
    excluded = {normalize_repo_path(path) for path in (exclude_paths or set())}
    tracked = git_lines(repo_root, "ls-files", rel_surface, problems=problems)
    untracked = git_lines(
        repo_root,
        "ls-files",
        "--others",
        "--exclude-standard",
        rel_surface,
        problems=problems,
    )
    deleted = (
        git_lines(repo_root, "ls-files", "--deleted", rel_surface, problems=problems)
        if include_deleted
        else ()
    )
    candidates = ({*tracked, *untracked} - set(deleted)) - excluded
    return tuple(sorted(candidates)), tuple(sorted(set(deleted) - excluded))


def git_lines(
    repo_root: Path,
    *args: str,
    problems: list[str],
) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        problems.append(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
        return ()
    return tuple(
        normalize_repo_path(line)
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def retained_file_metadata(path: Path) -> RetainedFileMetadata:
    data = path.read_bytes()
    line_count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    return RetainedFileMetadata(
        size_bytes=path.stat().st_size,
        line_count=line_count,
        sha256=file_sha256(path),
    )


def repo_relative(path: Path, repo_root: Path) -> str:
    relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    return normalize_repo_path(relative)


def normalize_repo_path(path: str) -> str:
    return path.strip().replace("\\", "/")
