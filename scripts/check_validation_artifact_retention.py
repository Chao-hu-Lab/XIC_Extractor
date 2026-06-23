"""Validate the tracked validation artifact retention surface.

This checker is intentionally metadata-only. It inspects the validation
inventory, git-visible files, and text references; it does not run RAW,
scoring, ProductWriter, matrix generation, workbook output, or GUI code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xic_extractor.tabular_io import read_tsv_with_header

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION_DIR = ROOT / "docs/superpowers/validation"
DEFAULT_INVENTORY = DEFAULT_VALIDATION_DIR / "ARTIFACT_INVENTORY.tsv"
DEFAULT_RETENTION_POLICY = DEFAULT_VALIDATION_DIR / "RETENTION.md"
DEFAULT_LARGE_FILE_THRESHOLD_BYTES = 500_000

REQUIRED_INVENTORY_COLUMNS = (
    "path",
    "size_bytes",
    "line_count",
    "category",
    "retention_decision",
    "keep_reason",
    "generated_by",
    "required_by",
    "replacement_or_summary",
)
KEEP_DECISIONS = {
    "keep_contract",
    "keep_summary",
    "keep_minimal_fixture",
    "shrink_later",
}
DROP_DECISIONS = {"externalize", "delete_generated"}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".tsv", ".txt", ".yml", ".yaml"}
RENDERED_SUFFIXES = {".html", ".htm", ".png", ".jpg", ".jpeg", ".gif", ".svg"}
RENDERED_REFERENCE_RE = re.compile(
    r"docs[/\\]superpowers[/\\]validation[/\\][^\s\t;,)]+?\.(?:html|png)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RetentionCheckResult:
    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: Mapping[str, Any]


def check_validation_artifact_retention(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    retention_policy_path: Path = DEFAULT_RETENTION_POLICY,
    validation_dir: Path = DEFAULT_VALIDATION_DIR,
    repo_root: Path = ROOT,
    strict: bool = False,
    require_externalized_local: bool = False,
    large_file_threshold_bytes: int = DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    candidate_paths: Sequence[str] | None = None,
    deleted_paths: Sequence[str] | None = None,
) -> RetentionCheckResult:
    problems: list[str] = []
    warnings: list[str] = []
    allowed_decisions = _read_policy_decisions(retention_policy_path, problems)
    header, rows = _read_inventory(inventory_path, problems)
    if header and tuple(header) != REQUIRED_INVENTORY_COLUMNS:
        problems.append("inventory header must exactly match retention policy columns")

    inventory_by_path = _index_inventory(rows, problems)
    if candidate_paths is None or deleted_paths is None:
        git_candidate_paths, git_deleted_paths = _git_validation_paths(
            repo_root,
            validation_dir,
            problems,
        )
        if candidate_paths is None:
            candidate_paths = git_candidate_paths
        if deleted_paths is None:
            deleted_paths = git_deleted_paths

    present_paths = {
        _normalize_repo_path(path)
        for path in candidate_paths
        if (repo_root / _normalize_repo_path(path)).exists()
    }
    deleted_path_set = {_normalize_repo_path(path) for path in deleted_paths}
    _check_inventory_rows(
        inventory_by_path,
        allowed_decisions,
        present_paths,
        deleted_path_set,
        repo_root,
        strict,
        require_externalized_local,
        large_file_threshold_bytes,
        problems,
        warnings,
    )
    _check_missing_inventory_rows(present_paths, inventory_by_path, problems)
    _check_rendered_references(
        present_paths,
        inventory_by_path,
        repo_root,
        problems,
    )

    decision_counts = Counter(
        row.get("retention_decision", "") for row in inventory_by_path.values()
    )
    category_counts = Counter(
        row.get("category", "") for row in inventory_by_path.values()
    )
    summary: dict[str, Any] = {
        "inventory_rows": len(inventory_by_path),
        "present_validation_files": len(present_paths),
        "deleted_validation_files": len(deleted_path_set),
        "decision_counts": dict(sorted(decision_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "shrink_later_count": decision_counts.get("shrink_later", 0),
        "externalized_count": decision_counts.get("externalize", 0),
        "problems": len(problems),
        "warnings": len(warnings),
    }
    return RetentionCheckResult(tuple(problems), tuple(warnings), summary)


def _read_policy_decisions(path: Path, problems: list[str]) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(f"could not read retention policy {path}: {exc}")
        return set()
    decisions = set(re.findall(r"\|\s*`([^`]+)`\s*\|", text))
    missing = (KEEP_DECISIONS | DROP_DECISIONS) - decisions
    if missing:
        problems.append(
            "retention policy is missing decisions: " + ", ".join(sorted(missing)),
        )
    return decisions


def _read_inventory(
    path: Path,
    problems: list[str],
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        return read_tsv_with_header(path, required_columns=REQUIRED_INVENTORY_COLUMNS)
    except OSError as exc:
        problems.append(f"could not read inventory {path}: {exc}")
    except ValueError as exc:
        problems.append(str(exc))
    return (), []


def _index_inventory(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> dict[str, Mapping[str, str]]:
    by_path: dict[str, Mapping[str, str]] = {}
    seen = Counter(_normalize_repo_path(row.get("path", "")) for row in rows)
    duplicates = sorted(path for path, count in seen.items() if path and count > 1)
    if duplicates:
        problems.append("duplicate inventory rows: " + ", ".join(duplicates))
    for index, row in enumerate(rows, start=2):
        path = _normalize_repo_path(row.get("path", ""))
        if not path:
            problems.append(f"inventory row {index}: path is required")
            continue
        if path not in by_path:
            by_path[path] = row
    return by_path


def _check_inventory_rows(
    inventory_by_path: Mapping[str, Mapping[str, str]],
    allowed_decisions: set[str],
    present_paths: set[str],
    deleted_paths: set[str],
    repo_root: Path,
    strict: bool,
    require_externalized_local: bool,
    large_file_threshold_bytes: int,
    problems: list[str],
    warnings: list[str],
) -> None:
    for path, row in inventory_by_path.items():
        decision = row.get("retention_decision", "")
        category = row.get("category", "")
        if decision not in allowed_decisions:
            problems.append(f"{path}: invalid retention_decision {decision!r}")
        is_present = path in present_paths
        was_deleted = path in deleted_paths
        if decision in KEEP_DECISIONS and not is_present:
            problems.append(f"{path}: inventory says {decision} but file is absent")
        if decision in DROP_DECISIONS and is_present:
            problems.append(f"{path}: {decision} artifact is still present")
        if decision == "externalize" and not row.get("replacement_or_summary", ""):
            problems.append(f"{path}: externalized artifact needs replacement mapping")
        if require_externalized_local and decision == "externalize":
            replacement = row.get("replacement_or_summary", "")
            if replacement and not (repo_root / replacement).exists():
                problems.append(f"{path}: externalized local replacement missing")
        if decision == "shrink_later":
            message = f"{path}: shrink_later remains tracked"
            if strict:
                problems.append(message)
            else:
                warnings.append(message)

        suffix = Path(path).suffix.lower()
        if _is_rendered_artifact(path, category) and decision not in (
            DROP_DECISIONS | {"shrink_later"}
        ):
            problems.append(f"{path}: rendered artifact must be externalized or shrunk")
        if suffix in RENDERED_SUFFIXES and is_present and decision in DROP_DECISIONS:
            problems.append(f"{path}: generated rendered artifact still in git surface")
        if is_present:
            _check_large_file_row(
                path,
                row,
                repo_root,
                large_file_threshold_bytes,
                problems,
            )
        elif was_deleted and decision not in DROP_DECISIONS:
            problems.append(f"{path}: deleted from worktree without drop decision")


def _check_large_file_row(
    path: str,
    row: Mapping[str, str],
    repo_root: Path,
    threshold: int,
    problems: list[str],
) -> None:
    file_path = repo_root / path
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        problems.append(f"{path}: could not stat retained file: {exc}")
        return
    if size <= threshold:
        return
    decision = row.get("retention_decision", "")
    if decision not in {"keep_contract", "keep_minimal_fixture", "shrink_later"}:
        problems.append(
            f"{path}: large retained file needs explicit keep/shrink decision",
        )
    if not row.get("keep_reason", ""):
        problems.append(f"{path}: large retained file needs keep_reason")
    if not (
        row.get("generated_by", "")
        or row.get("required_by", "")
        or row.get("replacement_or_summary", "")
    ):
        problems.append(f"{path}: large retained file needs source or consumer")


def _check_missing_inventory_rows(
    present_paths: Iterable[str],
    inventory_by_path: Mapping[str, Mapping[str, str]],
    problems: list[str],
) -> None:
    missing = sorted(path for path in present_paths if path not in inventory_by_path)
    if missing:
        problems.append(
            "validation files missing inventory rows: " + ", ".join(missing),
        )


def _check_rendered_references(
    present_paths: Iterable[str],
    inventory_by_path: Mapping[str, Mapping[str, str]],
    repo_root: Path,
    problems: list[str],
) -> None:
    present_path_set = set(present_paths)
    for path in sorted(present_path_set):
        suffix = Path(path).suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = (repo_root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            problems.append(f"{path}: could not scan rendered references: {exc}")
            continue
        references = {
            _normalize_repo_path(match)
            for match in RENDERED_REFERENCE_RE.findall(text)
        }
        for reference in sorted(references):
            if reference in present_path_set:
                continue
            row = inventory_by_path.get(reference)
            if row is None:
                problems.append(
                    f"{path}: rendered reference lacks inventory mapping: {reference}",
                )
                continue
            decision = row.get("retention_decision", "")
            replacement = row.get("replacement_or_summary", "")
            if decision == "externalize" and not replacement:
                problems.append(
                    f"{path}: externalized reference lacks replacement: {reference}",
                )
            elif decision not in DROP_DECISIONS and decision != "shrink_later":
                problems.append(
                    f"{path}: rendered reference points to absent retained file: "
                    f"{reference}",
                )


def _is_rendered_artifact(path: str, category: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in RENDERED_SUFFIXES or category in {
        "rendered_html",
        "rendered_plot",
        "binary_review_media",
    }


def _git_validation_paths(
    repo_root: Path,
    validation_dir: Path,
    problems: list[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    rel_validation = _repo_relative(validation_dir, repo_root)
    tracked = _git_lines(repo_root, "ls-files", rel_validation, problems=problems)
    untracked = _git_lines(
        repo_root,
        "ls-files",
        "--others",
        "--exclude-standard",
        rel_validation,
        problems=problems,
    )
    deleted = _git_lines(
        repo_root,
        "ls-files",
        "--deleted",
        rel_validation,
        problems=problems,
    )
    candidates = sorted(({*tracked, *untracked} - set(deleted)))
    return tuple(candidates), tuple(sorted(deleted))


def _git_lines(
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
        problems.append(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}",
        )
        return ()
    return tuple(
        _normalize_repo_path(line)
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def _repo_relative(path: Path, repo_root: Path) -> str:
    relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    return _normalize_repo_path(relative)


def _normalize_repo_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument(
        "--retention-policy",
        type=Path,
        default=DEFAULT_RETENTION_POLICY,
    )
    parser.add_argument("--validation-dir", type=Path, default=DEFAULT_VALIDATION_DIR)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-externalized-local", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--large-file-threshold-bytes",
        type=int,
        default=DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    )
    args = parser.parse_args(argv)
    result = check_validation_artifact_retention(
        inventory_path=args.inventory,
        retention_policy_path=args.retention_policy,
        validation_dir=args.validation_dir,
        repo_root=args.repo_root,
        strict=args.strict,
        require_externalized_local=args.require_externalized_local,
        large_file_threshold_bytes=args.large_file_threshold_bytes,
    )
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    for warning in result.warnings:
        print("warning: " + warning, file=sys.stderr)
    if result.problems:
        for problem in result.problems:
            print(problem, file=sys.stderr)
        return 1
    print(
        "Validation artifact retention surface is consistent "
        f"({result.summary['present_validation_files']} retained files, "
        f"{result.summary['externalized_count']} externalized, "
        f"{result.summary['shrink_later_count']} shrink_later).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
