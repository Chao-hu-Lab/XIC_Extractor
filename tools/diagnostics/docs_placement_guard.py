from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.diagnostics import docs_scan as _docs_scan  # noqa: E402
from tools.diagnostics.docs_policy import (  # noqa: E402
    DOC_EXIT_RULE_MARKER,
    DOC_KIND_MARKER,
    DOC_KIND_VALUES,
    DOC_LIFECYCLE_MARKER,
    DOC_LIFECYCLE_VALUES,
    DOC_PLACEMENT_MARKER,
    DOC_PLACEMENT_VALUES,
    DOC_REPO_OWNER_MARKER,
    DOC_RETIRED_TRACKED_DIRS,
    classify_doc,
    classify_doc_path,
    doc_exit_rule_value,
    doc_kind_value,
    doc_lifecycle_requires_exit_rule,
    doc_lifecycle_value,
    doc_placement_is_non_repo,
    doc_placement_requires_repo_owner,
    has_private_history_signal,
    is_invalid_superpowers_spec_payload_path,
    is_markdown_path,
    is_superpowers_spec_lane_path,
    normalize_path_text,
)

ACTIVE_STUB_FIELDS = {
    "objective": "objective",
    "scope": "scope",
    "constraints": "constraints",
    "next": "next 1-3 actions",
    "verification": "verification",
    "stop rule": "stop rule",
}
NEWLY_STAGED_STATUSES = {"A", "C", "R"}
RETIREMENT_EVIDENCE_DIR = "docs/superpowers/file-management/docs-cleanup/"
RETIREMENT_EVIDENCE_TOKENS = ("retirement-evidence", "retirement_evidence")


@dataclass(frozen=True)
class StagedMarkdown:
    status: str
    path: str
    staged_text: str | None = None


@dataclass(frozen=True)
class PlacementProblem:
    path: str
    reason: str
    required_marker: str


@dataclass(frozen=True)
class PlacementResult:
    checked_count: int
    ignored_deletions: int
    problems: tuple[PlacementProblem, ...]


def normalize_status(status: str) -> str:
    return status.strip().upper()[:1]


def parse_name_status(output: str) -> tuple[list[StagedMarkdown], int]:
    entries: list[StagedMarkdown] = []
    ignored_deletions = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = normalize_status(parts[0])
        if len(parts) < 2:
            continue
        path = parts[-1]
        if status == "D":
            if is_markdown_path(path):
                entries.append(StagedMarkdown(status=status, path=path))
            else:
                ignored_deletions += 1
            continue
        if status not in {"A", "M", "R", "C"}:
            continue
        if (
            is_markdown_path(path)
            or is_superpowers_spec_lane_path(path)
            or is_retirement_evidence_path(path)
        ):
            entries.append(StagedMarkdown(status=status, path=path))
    return entries, ignored_deletions


def staged_markdown(root: Path) -> tuple[list[StagedMarkdown], int]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=AMRCD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff --cached failed")
    entries, ignored_deletions = parse_name_status(result.stdout)
    return [
        StagedMarkdown(
            status=entry.status,
            path=entry.path,
            staged_text=(
                None
                if normalize_status(entry.status) == "D"
                else read_staged_text(root, entry.path)
            ),
        )
        for entry in entries
    ], ignored_deletions


def read_text(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def read_staged_text(root: Path, path: str) -> str:
    staged_path = path.replace("\\", "/")
    result = subprocess.run(
        ["git", "show", f":{staged_path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or f"git show failed for staged Markdown file: {path}",
        )
    return result.stdout


def required_marker_text(*placements: str) -> str:
    placement_text = "|".join(placements)
    return (
        f"{DOC_PLACEMENT_MARKER} {placement_text}; "
        f"{DOC_REPO_OWNER_MARKER} <path-or-topic>"
    )


def missing_active_stub_fields(text: str) -> list[str]:
    lowered = text.lower()
    return [
        label
        for needle, label in ACTIVE_STUB_FIELDS.items()
        if needle not in lowered
    ]


def is_retirement_evidence_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./").lower()
    filename = Path(normalized).name
    return (
        normalized.startswith(RETIREMENT_EVIDENCE_DIR)
        and normalized.endswith(".json")
        and any(token in filename for token in RETIREMENT_EVIDENCE_TOKENS)
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scan_paths(root: Path) -> tuple[str, ...]:
    return (
        _docs_scan.git_visible_paths(root)
        or _docs_scan.fallback_local_path_scan_paths(root)
    )


def _staged_text_by_path(entries: Sequence[StagedMarkdown]) -> dict[str, str]:
    return {
        normalize_path_text(entry.path).lstrip("./"): entry.staged_text
        for entry in entries
        if normalize_status(entry.status) != "D" and entry.staged_text is not None
    }


def _deleted_paths(entries: Sequence[StagedMarkdown]) -> frozenset[str]:
    return frozenset(
        normalize_path_text(entry.path).lstrip("./")
        for entry in entries
        if normalize_status(entry.status) == "D"
    )


def _exact_referrers(
    root: Path,
    rel_path: str,
    entries: Sequence[StagedMarkdown],
) -> tuple[str, ...]:
    normalized = normalize_path_text(rel_path).lstrip("./")
    deleted_paths = _deleted_paths(entries)
    staged_text_by_path = _staged_text_by_path(entries)
    scan_paths = set(_scan_paths(root))
    scan_paths.update(staged_text_by_path)
    referrers: list[str] = []
    for scan_rel in sorted(scan_paths):
        scan_rel = normalize_path_text(scan_rel).lstrip("./")
        if scan_rel == normalized or scan_rel in deleted_paths:
            continue
        if is_retirement_evidence_path(scan_rel):
            continue
        scan_path = root / scan_rel
        if scan_rel in staged_text_by_path:
            text = staged_text_by_path[scan_rel]
        else:
            if not _docs_scan.is_local_path_scan_target(scan_path, scan_rel):
                continue
            text = _docs_scan.read_text(scan_path)
        if normalized in text:
            referrers.append(scan_rel)
    return tuple(sorted(referrers))


def read_deleted_text(root: Path, entry: StagedMarkdown) -> str | None:
    if entry.staged_text is not None:
        return entry.staged_text
    staged_path = entry.path.replace("\\", "/")
    result = subprocess.run(
        ["git", "show", f"HEAD:{staged_path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _owner_paths_exist(
    root: Path,
    owner_paths: list[str],
    entries: Sequence[StagedMarkdown],
) -> bool:
    staged_text_by_path = _staged_text_by_path(entries)
    for owner_path in owner_paths:
        normalized = normalize_path_text(owner_path).lstrip("./")
        if normalized in staged_text_by_path:
            continue
        if not (root / normalized).is_file():
            return False
    return True


def _is_usable_retirement_evidence_entry(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("review_result") != "pass_can_retire":
        return False
    for field_name in (
        "owner_paths",
        "owner_anchors",
        "absorbed_claims",
        "absorbed_negative_claims",
    ):
        if not _string_list(entry.get(field_name)):
            return False
    if entry.get("source_copy_readback_verified") is not True:
        return False
    source_hash = entry.get("source_hash")
    if not isinstance(source_hash, str) or not source_hash.strip():
        return False
    return not _string_list(entry.get("active_followups"))


def retirement_evidence_by_path(
    entries: Sequence[StagedMarkdown],
) -> dict[str, dict[str, object]]:
    evidence_by_path: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not is_retirement_evidence_path(entry.path):
            continue
        if entry.staged_text is None:
            continue
        try:
            data = json.loads(entry.staged_text)
        except json.JSONDecodeError:
            continue
        evidence_entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(evidence_entries, list):
            continue
        for evidence_entry in evidence_entries:
            if not _is_usable_retirement_evidence_entry(evidence_entry):
                continue
            source_path = evidence_entry.get("source_path")
            if isinstance(source_path, str) and source_path:
                evidence_by_path[normalize_path_text(source_path).lstrip("./")] = (
                    evidence_entry
                )
    return evidence_by_path


def deletion_retirement_problem(
    root: Path,
    entry: StagedMarkdown,
    *,
    evidence_by_path: dict[str, dict[str, object]],
    entries: Sequence[StagedMarkdown],
) -> PlacementProblem | None:
    path = normalize_path_text(entry.path).lstrip("./")
    evidence = evidence_by_path.get(path)
    if evidence is None:
        return PlacementProblem(
            path=path,
            reason="lifecycle-managed doc deletion requires staged retirement evidence",
            required_marker=(
                "Stage docs/superpowers/file-management/docs-cleanup/"
                "*retirement-evidence*.json with a pass_can_retire entry "
                "for this source_path."
            ),
        )

    old_text = read_deleted_text(root, entry)
    if old_text is None:
        return PlacementProblem(
            path=path,
            reason="deleted lifecycle-managed doc blob could not be read",
            required_marker=(
                "Run the deletion from a git worktree with the source in HEAD."
            ),
        )
    if evidence.get("source_hash") != _source_hash(old_text):
        return PlacementProblem(
            path=path,
            reason="retirement evidence source_hash mismatch",
            required_marker="Regenerate evidence from the exact deleted source text.",
        )

    owner_paths = _string_list(evidence.get("owner_paths"))
    if not _owner_paths_exist(root, owner_paths, entries):
        return PlacementProblem(
            path=path,
            reason="retirement evidence owner_paths do not all exist in repo",
            required_marker=(
                "Point owner_paths at existing/staged repo owner documents."
            ),
        )

    referrers = _exact_referrers(root, path, entries)
    evidence_referrers = tuple(sorted(_string_list(evidence.get("exact_referrers"))))
    if referrers:
        return PlacementProblem(
            path=path,
            reason="exact repo referrers require retargeting before deletion",
            required_marker=(
                "Retarget repo referrers to the durable owner or keep a stub."
            ),
        )
    if evidence_referrers != tuple(sorted(referrers)):
        return PlacementProblem(
            path=path,
            reason="retirement evidence exact_referrers mismatch",
            required_marker="Regenerate evidence after the final staged referrer scan.",
        )
    return None


def lifecycle_metadata_problems(path: str, text: str) -> list[PlacementProblem]:
    problems: list[PlacementProblem] = []
    doc_kind = doc_kind_value(text)
    lifecycle = doc_lifecycle_value(text)
    exit_rule = doc_exit_rule_value(text)
    if not doc_kind:
        problems.append(
            PlacementProblem(
                path=path,
                reason="lifecycle-managed doc is missing Doc kind",
                required_marker=(
                    f"{DOC_KIND_MARKER} <one of "
                    f"{', '.join(sorted(DOC_KIND_VALUES))}>"
                ),
            )
        )
    elif doc_kind not in DOC_KIND_VALUES:
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"unknown doc kind value: {doc_kind}",
                required_marker=(
                    f"{DOC_KIND_MARKER} <one of "
                    f"{', '.join(sorted(DOC_KIND_VALUES))}>"
                ),
            )
        )
    if not lifecycle:
        problems.append(
            PlacementProblem(
                path=path,
                reason="lifecycle-managed doc is missing Doc lifecycle",
                required_marker=(
                    f"{DOC_LIFECYCLE_MARKER} <one of "
                    f"{', '.join(sorted(DOC_LIFECYCLE_VALUES))}>"
                ),
            )
        )
    elif lifecycle not in DOC_LIFECYCLE_VALUES:
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"unknown doc lifecycle value: {lifecycle}",
                required_marker=(
                    f"{DOC_LIFECYCLE_MARKER} <one of "
                    f"{', '.join(sorted(DOC_LIFECYCLE_VALUES))}>"
                ),
            )
        )
    elif doc_lifecycle_requires_exit_rule(lifecycle) and not exit_rule:
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"{lifecycle} lifecycle requires Doc exit rule",
                required_marker=(
                    f"{DOC_EXIT_RULE_MARKER} <closeout, promotion, retirement, "
                    "or Obsidian migration condition>"
                ),
            )
        )
    return problems


def check_entry(
    root: Path,
    entry: StagedMarkdown,
    *,
    evidence_by_path: dict[str, dict[str, object]] | None = None,
    entries: Sequence[StagedMarkdown] = (),
) -> list[PlacementProblem]:
    path = entry.path.replace("\\", "/")
    status = normalize_status(entry.status)
    path_classification = classify_doc_path(path)
    if status == "D":
        if not (
            is_markdown_path(path)
            and path_classification.is_repo_doc
            and path_classification.is_lifecycle_managed
        ):
            return []
        problem = deletion_retirement_problem(
            root,
            entry,
            evidence_by_path=evidence_by_path or {},
            entries=entries,
        )
        return [] if problem is None else [problem]

    if is_invalid_superpowers_spec_payload_path(path):
        return [
            PlacementProblem(
                path=path,
                reason=(
                    "docs/superpowers/specs is Markdown-only; move JSON "
                    "contracts to docs/superpowers/schemas and non-doc "
                    "artifacts to validation, ignored output, or Obsidian"
                ),
                required_marker=(
                    "Use docs/superpowers/specs/*.md for transient specs only."
                ),
            )
        ]
    if not path_classification.is_repo_doc:
        return []

    try:
        text = (
            entry.staged_text
            if entry.staged_text is not None
            else read_text(root, path)
        )
    except OSError as exc:
        return [
            PlacementProblem(
                path=path,
                reason=f"staged Markdown file could not be read: {exc}",
                required_marker=required_marker_text(
                    "formal_repo_doc",
                    "repo_active_stub",
                    "repo_stub_plus_obsidian",
                ),
            )
        ]

    classification = classify_doc(path, text)
    problems: list[PlacementProblem] = []
    placement = classification.placement
    repo_owner = classification.repo_owner
    lifecycle_problems: list[PlacementProblem] = []
    if status in NEWLY_STAGED_STATUSES and classification.is_lifecycle_managed:
        lifecycle_problems = lifecycle_metadata_problems(path, text)

    if classification.is_docs_root_scatter:
        problems.append(
            PlacementProblem(
                path=path,
                reason=(
                    "docs root only allows cross-cutting authority docs; "
                    "move this file under docs/agent, docs/product, "
                    "docs/architecture, docs/validation, docs/user, "
                    "docs/solutions, or docs/superpowers"
                ),
                required_marker=(
                    "Use docs/project-layout.md root allowlist; do not add "
                    "new non-allowlisted Markdown directly under docs/."
                ),
            )
        )

    if classification.is_retired_tracked_dir and status in NEWLY_STAGED_STATUSES:
        reason = DOC_RETIRED_TRACKED_DIRS.get(
            classification.retired_tracked_dir,
            "retired docs lane is not a tracked destination",
        )
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"retired docs lane: {reason}",
                required_marker=(
                    "Route to the canonical owner, a named public artifact "
                    "lane, ignored output/, ignored handoff, or Obsidian."
                ),
            )
        )

    if placement and placement not in DOC_PLACEMENT_VALUES:
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"unknown doc placement value: {placement}",
                required_marker=(
                    f"{DOC_PLACEMENT_MARKER} <one of "
                    f"{', '.join(sorted(DOC_PLACEMENT_VALUES))}>"
                ),
            )
        )
        return [*problems, *lifecycle_problems]

    if placement and doc_placement_is_non_repo(placement):
        problems.append(
            PlacementProblem(
                path=path,
                reason=(
                    f"{placement} is not a repo-trackable placement; write it "
                    "to Obsidian staged draft or ignored scratch instead"
                ),
                required_marker=required_marker_text("repo_stub_plus_obsidian"),
            )
        )

    if placement and doc_placement_requires_repo_owner(placement) and not repo_owner:
        problems.append(
            PlacementProblem(
                path=path,
                reason=f"{placement} requires a repo owner",
                required_marker=f"{DOC_REPO_OWNER_MARKER} <path-or-topic>",
            )
        )

    if (
        classification.is_canonical_owner
        and not classification.is_branch_closeout_summary
    ):
        if path.startswith("docs/user/"):
            if placement and placement != "formal_repo_doc":
                problems.append(
                    PlacementProblem(
                        path=path,
                        reason=(
                            f"{placement} is not valid in docs/user; user docs "
                            "must be public user guides, not branch stubs, "
                            "Obsidian stubs, closeouts, or artifact records"
                        ),
                        required_marker=(
                            f"{DOC_PLACEMENT_MARKER} formal_repo_doc "
                            "or omit the marker for canonical user guides"
                        ),
                    )
                )
            if has_private_history_signal(text):
                problems.append(
                    PlacementProblem(
                        path=path,
                        reason=(
                            "user guide contains private-history signals; "
                            "move implementation diary, command transcript, "
                            "or review rationale to Obsidian"
                        ),
                        required_marker=required_marker_text("formal_repo_doc"),
                    )
                )
        return [*problems, *lifecycle_problems]

    if classification.is_misplaced_handoff_public_record:
        problems.append(
            PlacementProblem(
                path=path,
                reason=(
                    "public productization/file-management/closeout records "
                    "do not belong under handoffs/current or handoffs/archive"
                ),
                required_marker=(
                    "Move to docs/superpowers/productization/, "
                    "docs/superpowers/file-management/, or "
                    "docs/superpowers/closeouts/."
                ),
            )
        )

    if placement == "repo_active_stub":
        missing = missing_active_stub_fields(text)
        if missing:
            problems.append(
                PlacementProblem(
                    path=path,
                    reason="repo_active_stub is missing fields: " + ", ".join(missing),
                    required_marker=(
                        "Include objective, scope, constraints, next 1-3 actions, "
                        "verification, and stop rule."
                    ),
                )
            )

    if (
        placement == "branch_closeout_summary"
        or classification.is_branch_closeout_summary
    ) and "pr body seed" not in text.lower():
        problems.append(
            PlacementProblem(
                path=path,
                reason="branch closeout summary is missing PR Body Seed",
                required_marker="Add a PR Body Seed section.",
            )
        )

    if problems:
        return [*problems, *lifecycle_problems]

    if classification.is_canonical_owner:
        return []

    if status in NEWLY_STAGED_STATUSES and not placement:
        if classification.is_high_risk_repo_doc:
            problems.append(
                PlacementProblem(
                    path=path,
                    reason=(
                        "new high-risk docs path lacks placement marker and "
                        "repo owner"
                    ),
                    required_marker=required_marker_text(
                        "formal_repo_doc",
                        "repo_active_stub",
                        "repo_stub_plus_obsidian",
                    ),
                )
            )
        else:
            problems.append(
                PlacementProblem(
                    path=path,
                    reason=(
                        "new repo doc outside canonical owner path lacks "
                        "placement marker"
                    ),
                    required_marker=required_marker_text(
                        "formal_repo_doc",
                        "repo_active_stub",
                        "repo_stub_plus_obsidian",
                    ),
                )
            )
    elif (
        status == "M"
        and not placement
        and classification.is_high_risk_repo_doc
        and has_private_history_signal(text)
    ):
        problems.append(
            PlacementProblem(
                path=path,
                reason=(
                    "modified high-risk docs path looks like private history "
                    "but lacks placement marker"
                ),
                required_marker=required_marker_text(
                    "repo_stub_plus_obsidian",
                    "formal_repo_doc",
                ),
            )
        )

    return [*problems, *lifecycle_problems]


def check_doc_placement(
    root: Path,
    entries: Sequence[StagedMarkdown],
    *,
    ignored_deletions: int = 0,
) -> PlacementResult:
    problems: list[PlacementProblem] = []
    checked_count = 0
    skipped_deletions = ignored_deletions
    evidence_by_path = retirement_evidence_by_path(entries)
    for entry in entries:
        status = normalize_status(entry.status)
        if status == "D":
            path = entry.path.replace("\\", "/")
            path_classification = classify_doc_path(path)
            if not (
                is_markdown_path(path)
                and path_classification.is_repo_doc
                and path_classification.is_lifecycle_managed
            ):
                skipped_deletions += 1
                continue
            checked_count += 1
            problems.extend(
                check_entry(
                    root,
                    entry,
                    evidence_by_path=evidence_by_path,
                    entries=entries,
                )
            )
            continue
        if is_retirement_evidence_path(entry.path):
            continue
        if not (
            is_markdown_path(entry.path)
            or is_superpowers_spec_lane_path(entry.path)
        ):
            continue
        checked_count += 1
        problems.extend(check_entry(root, entry))
    return PlacementResult(
        checked_count=checked_count,
        ignored_deletions=skipped_deletions,
        problems=tuple(problems),
    )


def format_result(result: PlacementResult) -> str:
    if not result.problems:
        return (
            "docs placement guard passed: "
            f"{result.checked_count} staged Markdown file(s) checked; "
            f"{result.ignored_deletions} non-lifecycle deletion(s) ignored."
        )
    lines = ["docs placement guard failed:"]
    for problem in result.problems:
        lines.append(f"- {problem.path}: {problem.reason}")
        lines.append(f"  required: {problem.required_marker}")
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged",
        action="store_true",
        help=(
            "Check staged A/M/R/C Markdown files and lifecycle-managed "
            "Markdown deletions."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root. Defaults to the current checkout.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.staged:
        raise SystemExit("docs_placement_guard.py requires --staged")
    root = args.root.resolve()
    entries, ignored_deletions = staged_markdown(root)
    result = check_doc_placement(
        root,
        entries,
        ignored_deletions=ignored_deletions,
    )
    print(format_result(result))
    return 1 if result.problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
