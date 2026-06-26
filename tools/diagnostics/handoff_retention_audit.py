"""Audit repo-tracked handoff retention state.

The audit is read-only. It checks that every repo handoff current/archive file
has an explicit retention row, that active handoffs stay compact, and that
archive cleanup remains manifest-driven instead of ad hoc deletion.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_ROOT = Path("docs/superpowers/handoffs")
CURRENT_DIR = HANDOFF_ROOT / "current"
ARCHIVE_DIR = HANDOFF_ROOT / "archive"
RETENTION_INVENTORY = HANDOFF_ROOT / "RETENTION.tsv"
MAX_CURRENT_LINES = 200

VALID_DECISIONS = {
    "active_current",
    "productization_anchor",
    "keep_repo_public_evidence",
    "keep_repo_closeout_summary",
    "keep_repo_until_referrers_removed",
    "move_to_obsidian_after_pr",
    "superseded_by_pr",
    "remove_after_merge_approval",
}
VALID_REVIEW_EVENTS = {
    "active_branch_change",
    "pr_open_update",
    "pr_merge_or_close",
    "referrer_audit",
    "validation_cleanup",
    "productization_policy_change",
    "manual_review",
}
REQUIRED_COLUMNS = (
    "path",
    "retention_decision",
    "repo_owner",
    "next_review_event",
    "rationale",
)
STALE_CURRENT_SIGNALS = (
    "ready for local closeout commit",
    "ready for local closeout",
    "push and open",
    "open the pr",
    "pr creation",
    "no commit has been made",
    "staged deletions",
)


@dataclass(frozen=True)
class RetentionMessage:
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class RetentionResult:
    messages: tuple[RetentionMessage, ...]
    summary: dict[str, object]

    @property
    def blockers(self) -> tuple[RetentionMessage, ...]:
        return tuple(msg for msg in self.messages if msg.severity == "blocker")


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _tracked_handoff_files(root: Path) -> tuple[str, ...]:
    paths: list[str] = []
    for directory in (root / CURRENT_DIR, root / ARCHIVE_DIR):
        if not directory.exists():
            continue
        paths.extend(
            _repo_rel(path, root)
            for path in sorted(directory.rglob("*"))
            if path.is_file()
        )
    return tuple(paths)


def _read_inventory(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], ["retention inventory is missing"]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            return [], [f"retention inventory is missing columns: {', '.join(missing)}"]
        rows = [
            {
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]
    return rows, []


def _line_count(root: Path, rel_path: str) -> int:
    return len(_read_text(root / rel_path).splitlines())


def _is_markdown(rel_path: str) -> bool:
    return rel_path.lower().endswith((".md", ".markdown"))


def _is_current(rel_path: str) -> bool:
    return rel_path.startswith(CURRENT_DIR.as_posix() + "/")


def _is_archive(rel_path: str) -> bool:
    return rel_path.startswith(ARCHIVE_DIR.as_posix() + "/")


def _stale_current_signal(text: str) -> str:
    lowered = text.lower()
    for signal in STALE_CURRENT_SIGNALS:
        if signal in lowered:
            return signal
    return ""


def run_handoff_retention_audit(root: Path = ROOT) -> RetentionResult:
    root = root.resolve()
    messages: list[RetentionMessage] = []
    handoff_files = set(_tracked_handoff_files(root))
    inventory_path = root / RETENTION_INVENTORY
    rows, inventory_errors = _read_inventory(inventory_path)
    for error in inventory_errors:
        messages.append(
            RetentionMessage("blocker", RETENTION_INVENTORY.as_posix(), error)
        )

    rows_by_path: dict[str, dict[str, str]] = {}
    duplicate_paths: set[str] = set()
    for row in rows:
        path = row.get("path", "").replace("\\", "/")
        if not path:
            messages.append(
                RetentionMessage(
                    "blocker",
                    RETENTION_INVENTORY.as_posix(),
                    "retention row has blank path",
                )
            )
            continue
        if path in rows_by_path:
            duplicate_paths.add(path)
        rows_by_path[path] = row

    for path in sorted(duplicate_paths):
        messages.append(
            RetentionMessage("blocker", path, "duplicate retention inventory row")
        )

    for path in sorted(handoff_files - set(rows_by_path)):
        messages.append(
            RetentionMessage(
                "blocker",
                path,
                "handoff file has no retention inventory row",
            )
        )

    for path in sorted(set(rows_by_path) - handoff_files):
        messages.append(
            RetentionMessage(
                "warning",
                path,
                "retention inventory row points to a missing handoff file",
            )
        )

    decision_counts: Counter[str] = Counter()
    next_review_counts: Counter[str] = Counter()
    transfer_candidates: list[str] = []
    cleanup_candidates: list[str] = []
    current_files: list[str] = []
    archive_files: list[str] = []

    for path in sorted(handoff_files):
        row = rows_by_path.get(path, {})
        decision = row.get("retention_decision", "")
        review_event = row.get("next_review_event", "")
        repo_owner = row.get("repo_owner", "")
        rationale = row.get("rationale", "")
        decision_counts[decision or "(missing)"] += 1
        next_review_counts[review_event or "(missing)"] += 1

        if decision and decision not in VALID_DECISIONS:
            messages.append(
                RetentionMessage(
                    "blocker",
                    path,
                    f"unknown retention_decision: {decision}",
                )
            )
        if review_event and review_event not in VALID_REVIEW_EVENTS:
            messages.append(
                RetentionMessage(
                    "blocker",
                    path,
                    f"unknown next_review_event: {review_event}",
                )
            )
        if not repo_owner:
            messages.append(
                RetentionMessage("blocker", path, "repo_owner is required")
            )
        if not rationale:
            messages.append(
                RetentionMessage("blocker", path, "rationale is required")
            )

        if _is_current(path):
            current_files.append(path)
            if decision not in {"active_current", "productization_anchor"}:
                messages.append(
                    RetentionMessage(
                        "blocker",
                        path,
                        "current handoff must be active_current or productization_anchor",
                    )
                )
            if _is_markdown(path):
                line_count = _line_count(root, path)
                if line_count > MAX_CURRENT_LINES:
                    messages.append(
                        RetentionMessage(
                            "warning",
                            path,
                            (
                                f"current handoff has {line_count} lines; "
                                f"target is <= {MAX_CURRENT_LINES}"
                            ),
                        )
                    )
                signal = _stale_current_signal(_read_text(root / path))
                if signal:
                    messages.append(
                        RetentionMessage(
                            "warning",
                            path,
                            f"current handoff may be stale after closeout: {signal!r}",
                        )
                    )
        elif _is_archive(path):
            archive_files.append(path)
            if decision in {"active_current", "productization_anchor"}:
                messages.append(
                    RetentionMessage(
                        "blocker",
                        path,
                        "archive file cannot use a current-only retention decision",
                    )
                )
            if decision == "move_to_obsidian_after_pr":
                transfer_candidates.append(path)
            if decision in {"superseded_by_pr", "remove_after_merge_approval"}:
                cleanup_candidates.append(path)

    summary: dict[str, object] = {
        "handoff_files": len(handoff_files),
        "current_files": len(current_files),
        "archive_files": len(archive_files),
        "inventory_rows": len(rows_by_path),
        "retention_decisions": dict(sorted(decision_counts.items())),
        "next_review_events": dict(sorted(next_review_counts.items())),
        "move_to_obsidian_after_pr": transfer_candidates,
        "cleanup_after_approval": cleanup_candidates,
    }
    return RetentionResult(tuple(messages), summary)


def format_text(result: RetentionResult) -> str:
    lines = ["handoff retention audit"]
    lines.append(f"blockers: {len(result.blockers)}")
    warning_count = sum(1 for msg in result.messages if msg.severity == "warning")
    lines.append(f"warnings: {warning_count}")
    if result.messages:
        lines.append("")
    for msg in result.messages:
        lines.append(f"- {msg.severity}: {msg.path}: {msg.message}")
    lines.append("")
    lines.append(json.dumps(result.summary, indent=2, ensure_ascii=False))
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_handoff_retention_audit(args.root)
    if args.json:
        print(
            json.dumps(
                {
                    "blockers": [msg.__dict__ for msg in result.blockers],
                    "messages": [msg.__dict__ for msg in result.messages],
                    "summary": result.summary,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_text(result))
    return 1 if result.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
