"""Validate the tracked superpowers fixture retention surface.

This checker is metadata-only. It inspects fixture inventory rows, git-visible
files, hashes, and text references; it does not run RAW, scoring, extraction,
ProductWriter, workbook output, matrix generation, or GUI code.
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

from xic_extractor.tabular_io import file_sha256, read_tsv_with_header

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_DIR = ROOT / "docs/superpowers/fixtures"
DEFAULT_INVENTORY = DEFAULT_FIXTURES_DIR / "ARTIFACT_INVENTORY.tsv"
DEFAULT_RETENTION_POLICY = DEFAULT_FIXTURES_DIR / "RETENTION.md"
DEFAULT_LARGE_FILE_THRESHOLD_BYTES = 100_000

REQUIRED_INVENTORY_COLUMNS = (
    "path",
    "size_bytes",
    "line_count",
    "sha256",
    "category",
    "retention_decision",
    "authority_scope",
    "referenced_by",
    "keep_reason",
    "next_action",
)
ACTIVE_KEEP_DECISIONS = {
    "keep_contract",
    "keep_manual_oracle",
    "keep_manifest",
    "keep_summary",
}
TEMP_KEEP_DECISIONS = {"needs_human_review", "archive_later"}
DROP_DECISIONS = {"externalize", "remove_generated"}
SELF_INDEX_PATH = "docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv"
DATED_LEDGER_PREFIX = "docs/superpowers/fixtures/diagnostic_ledger_"


@dataclass(frozen=True)
class FixtureRetentionCheckResult:
    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: Mapping[str, Any]


def check_superpowers_fixture_retention(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    retention_policy_path: Path = DEFAULT_RETENTION_POLICY,
    fixtures_dir: Path = DEFAULT_FIXTURES_DIR,
    repo_root: Path = ROOT,
    strict: bool = False,
    large_file_threshold_bytes: int = DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    candidate_paths: Sequence[str] | None = None,
) -> FixtureRetentionCheckResult:
    problems: list[str] = []
    warnings: list[str] = []
    allowed_decisions = _read_policy_decisions(retention_policy_path, problems)
    header, rows = _read_inventory(inventory_path, problems)
    if header and tuple(header) != REQUIRED_INVENTORY_COLUMNS:
        problems.append("inventory header must exactly match fixture policy columns")

    inventory_by_path = _index_inventory(rows, problems)
    if candidate_paths is None:
        candidate_paths = _git_fixture_paths(repo_root, fixtures_dir, problems)
    present_paths = {
        path
        for path in (_normalize_repo_path(path) for path in candidate_paths)
        if path != SELF_INDEX_PATH and (repo_root / path).exists()
    }

    _check_inventory_rows(
        inventory_by_path,
        allowed_decisions,
        present_paths,
        repo_root,
        strict,
        large_file_threshold_bytes,
        problems,
        warnings,
    )
    _check_missing_inventory_rows(present_paths, inventory_by_path, problems)

    decision_counts = Counter(
        row.get("retention_decision", "") for row in inventory_by_path.values()
    )
    category_counts = Counter(
        row.get("category", "") for row in inventory_by_path.values()
    )
    summary: dict[str, Any] = {
        "inventory_rows": len(inventory_by_path),
        "present_fixture_files": len(present_paths),
        "decision_counts": dict(sorted(decision_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "needs_human_review_count": decision_counts.get("needs_human_review", 0),
        "archive_later_count": decision_counts.get("archive_later", 0),
        "problems": len(problems),
        "warnings": len(warnings),
    }
    return FixtureRetentionCheckResult(tuple(problems), tuple(warnings), summary)


def _read_policy_decisions(path: Path, problems: list[str]) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(f"could not read retention policy {path}: {exc}")
        return set()
    decisions = set(re.findall(r"\|\s*`([^`]+)`\s*\|", text))
    required = ACTIVE_KEEP_DECISIONS | TEMP_KEEP_DECISIONS | DROP_DECISIONS | {
        "keep_ledger_snapshot",
    }
    missing = required - decisions
    if missing:
        problems.append(
            "fixture retention policy is missing decisions: "
            + ", ".join(sorted(missing)),
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
        if path == SELF_INDEX_PATH:
            problems.append(f"{path}: inventory must not contain a self-hash row")
            continue
        if path not in by_path:
            by_path[path] = row
    return by_path


def _check_inventory_rows(
    inventory_by_path: Mapping[str, Mapping[str, str]],
    allowed_decisions: set[str],
    present_paths: set[str],
    repo_root: Path,
    strict: bool,
    large_file_threshold_bytes: int,
    problems: list[str],
    warnings: list[str],
) -> None:
    for path, row in inventory_by_path.items():
        decision = row.get("retention_decision", "")
        category = row.get("category", "")
        is_present = path in present_paths
        if decision not in allowed_decisions:
            problems.append(f"{path}: invalid retention_decision {decision!r}")
        keep_decisions = (
            ACTIVE_KEEP_DECISIONS | TEMP_KEEP_DECISIONS | {"keep_ledger_snapshot"}
        )
        if decision in keep_decisions:
            if not is_present:
                problems.append(f"{path}: inventory says {decision} but file is absent")
            if not row.get("keep_reason", ""):
                problems.append(f"{path}: retained fixture needs keep_reason")
        if decision in DROP_DECISIONS and is_present:
            problems.append(f"{path}: {decision} artifact is still present")
        if is_present:
            _check_declared_metadata(path, row, repo_root, problems)
            _check_large_file_row(
                path,
                row,
                repo_root,
                large_file_threshold_bytes,
                problems,
            )
        _check_reference_contract(
            path,
            row,
            category,
            decision,
            strict,
            problems,
            warnings,
        )


def _check_declared_metadata(
    path: str,
    row: Mapping[str, str],
    repo_root: Path,
    problems: list[str],
) -> None:
    file_path = repo_root / path
    try:
        data = file_path.read_bytes()
    except OSError as exc:
        problems.append(f"{path}: could not read retained file: {exc}")
        return
    declared_size = row.get("size_bytes", "")
    actual_size = str(file_path.stat().st_size)
    if declared_size != actual_size:
        problems.append(f"{path}: size_bytes {declared_size!r} != {actual_size}")
    declared_lines = row.get("line_count", "")
    actual_line_count = data.count(b"\n") + (
        0 if data.endswith(b"\n") or not data else 1
    )
    actual_lines = str(actual_line_count)
    if declared_lines != actual_lines:
        problems.append(f"{path}: line_count {declared_lines!r} != {actual_lines}")
    declared_sha = row.get("sha256", "")
    actual_sha = file_sha256(file_path)
    if declared_sha != actual_sha:
        problems.append(f"{path}: sha256 {declared_sha!r} != {actual_sha}")


def _check_large_file_row(
    path: str,
    row: Mapping[str, str],
    repo_root: Path,
    threshold: int,
    problems: list[str],
) -> None:
    try:
        size = (repo_root / path).stat().st_size
    except OSError as exc:
        problems.append(f"{path}: could not stat retained file: {exc}")
        return
    if size <= threshold:
        return
    decision = row.get("retention_decision", "")
    category = row.get("category", "")
    if decision not in {
        "keep_contract",
        "keep_manual_oracle",
        "keep_ledger_snapshot",
        "archive_later",
    }:
        problems.append(f"{path}: large fixture needs explicit keep/archive decision")
    if "generated" in category or "full_result" in category:
        if not row.get("keep_reason", "") or not row.get("referenced_by", ""):
            problems.append(f"{path}: large generated-like fixture needs policy reason")


def _check_reference_contract(
    path: str,
    row: Mapping[str, str],
    category: str,
    decision: str,
    strict: bool,
    problems: list[str],
    warnings: list[str],
) -> None:
    referenced_by = row.get("referenced_by", "")
    is_root_fixture = Path(path).parent.as_posix() == "docs/superpowers/fixtures"
    if is_root_fixture and decision in (ACTIVE_KEEP_DECISIONS | TEMP_KEEP_DECISIONS):
        if not referenced_by:
            problems.append(f"{path}: active root fixture needs referenced_by")
    if path.startswith(DATED_LEDGER_PREFIX) or category == "diagnostic_ledger_snapshot":
        if decision not in {"keep_ledger_snapshot", "keep_summary", "archive_later"}:
            problems.append(f"{path}: dated ledger fixture has incompatible decision")
        has_ledger_reference = (
            "docs/diagnostic-ledger.md" in referenced_by
            or "diagnostic_ledger_2026_05_28/README.md" in referenced_by
        )
        if not has_ledger_reference:
            problems.append(
                f"{path}: dated ledger fixture needs ledger or packet README "
                "reference",
            )
    if decision == "needs_human_review":
        message = f"{path}: needs_human_review remains unresolved"
        if strict:
            problems.append(message)
        else:
            warnings.append(message)


def _check_missing_inventory_rows(
    present_paths: Iterable[str],
    inventory_by_path: Mapping[str, Mapping[str, str]],
    problems: list[str],
) -> None:
    missing = sorted(path for path in present_paths if path not in inventory_by_path)
    if missing:
        problems.append("fixture files missing inventory rows: " + ", ".join(missing))


def _git_fixture_paths(
    repo_root: Path,
    fixtures_dir: Path,
    problems: list[str],
) -> tuple[str, ...]:
    rel_fixtures = _repo_relative(fixtures_dir, repo_root)
    tracked = _git_lines(repo_root, "ls-files", rel_fixtures, problems=problems)
    untracked = _git_lines(
        repo_root,
        "ls-files",
        "--others",
        "--exclude-standard",
        rel_fixtures,
        problems=problems,
    )
    return tuple(sorted({*tracked, *untracked} - {SELF_INDEX_PATH}))


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
        problems.append(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
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
    parser.add_argument("--fixtures-dir", type=Path, default=DEFAULT_FIXTURES_DIR)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--large-file-threshold-bytes",
        type=int,
        default=DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    )
    args = parser.parse_args(argv)
    result = check_superpowers_fixture_retention(
        inventory_path=args.inventory,
        retention_policy_path=args.retention_policy,
        fixtures_dir=args.fixtures_dir,
        repo_root=args.repo_root,
        strict=args.strict,
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
        "Superpowers fixture retention surface is consistent "
        f"({result.summary['present_fixture_files']} files, "
        f"{result.summary['needs_human_review_count']} needs_human_review, "
        f"{result.summary['archive_later_count']} archive_later).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
