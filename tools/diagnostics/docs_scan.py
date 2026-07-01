"""Shared text-file discovery helpers for docs diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

LOCAL_PATH_SCAN_EXCLUSIONS = {"tools/diagnostics/docs_management_audit.py"}
LOCAL_PATH_SCAN_FALLBACK_DIRS = (
    "config",
    "docs",
    "tests",
    "tools",
    "scripts",
    ".github",
    ".codex/hooks",
)
LOCAL_PATH_SCAN_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".env",
    ".example",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
LOCAL_PATH_SCAN_TEXT_FILENAMES = {
    ".gitignore",
    "AGENTS.md",
    "README.md",
}


def repo_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def git_visible_paths(root: Path) -> tuple[str, ...] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return tuple(
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def fallback_local_path_scan_paths(root: Path) -> tuple[str, ...]:
    paths: set[str] = set()
    for base in LOCAL_PATH_SCAN_FALLBACK_DIRS:
        base_path = root / base
        if base_path.is_file():
            paths.add(repo_rel(base_path, root))
        elif base_path.exists():
            paths.update(repo_rel(path, root) for path in base_path.rglob("*"))
    for filename in LOCAL_PATH_SCAN_TEXT_FILENAMES:
        if (root / filename).exists():
            paths.add(filename)
    return tuple(sorted(paths))


def is_local_path_scan_target(path: Path, rel_path: str) -> bool:
    if rel_path in LOCAL_PATH_SCAN_EXCLUSIONS:
        return False
    if not path.is_file():
        return False
    if path.name in LOCAL_PATH_SCAN_TEXT_FILENAMES:
        return True
    return path.suffix.lower() in LOCAL_PATH_SCAN_TEXT_SUFFIXES
