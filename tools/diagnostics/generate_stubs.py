"""Generate repo stub files from a Link Stub Blockers TSV.

Usage (dry-run):
    uv run python tools/diagnostics/generate_stubs.py <path-to-tsv>

Usage (write stubs):
    uv run python tools/diagnostics/generate_stubs.py <path-to-tsv> --execute
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from tools.diagnostics.docs_policy import (
    DOC_KIND_MARKER,
    DOC_REPO_OWNER_MARKER,
    marker_value,
)


@dataclass(frozen=True)
class BlockerRow:
    target_source_path: str
    target_note: str
    target_doc_class: str
    target_line_count: int
    reference_type: str
    referrer_path: str
    referrer_kind: str
    referrer_line: int
    referrer_text: str
    suggested_resolution: str
    evidence_terms: str
    strong_risk_terms: str


def parse_blocker_tsv(tsv_path: Path) -> list[BlockerRow]:
    """Parse a Link Stub Blockers TSV and return a list of BlockerRow objects."""
    rows: list[BlockerRow] = []
    with open(tsv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t", quotechar='"')
        for record in reader:
            rows.append(
                BlockerRow(
                    target_source_path=record["target_source_path"],
                    target_note=record["target_note"],
                    target_doc_class=record["target_doc_class"],
                    target_line_count=int(record["target_line_count"]),
                    reference_type=record["reference_type"],
                    referrer_path=record["referrer_path"],
                    referrer_kind=record["referrer_kind"],
                    referrer_line=int(record["referrer_line"]),
                    referrer_text=record["referrer_text"],
                    suggested_resolution=record["suggested_resolution"],
                    evidence_terms=record.get("evidence_terms", ""),
                    strong_risk_terms=record.get("strong_risk_terms", ""),
                )
            )
    return rows


def generate_stub_content(
    target_source_path: str,
    target_note: str,
    doc_kind: str,
    repo_owner: str,
) -> str:
    """Return the text content for a repo stub file."""
    lines = [
        "Doc placement: repo_stub_plus_obsidian",
        f"Doc kind: {doc_kind}",
        "Doc lifecycle: retired",
        f"Repo owner: {repo_owner}",
        (
            f"Doc exit rule: Remove after confirming vault note"
            f" [[{target_note}]] is promoted and no repo referrers"
            f" depend on this path."
        ),
        "",
        "Canonical content migrated to Research Vault.",
        f"See: [[{target_note}]]",
    ]
    return "\n".join(lines) + "\n"


def extract_doc_kind(text: str) -> str:
    """Extract the Doc kind marker value from file text; default to 'note'."""
    kind = marker_value(text, DOC_KIND_MARKER)
    return kind if kind else "note"


def infer_repo_owner(text: str, source_path: str) -> str:
    """Extract Repo owner from file text; fall back to source_path itself."""
    owner = marker_value(text, DOC_REPO_OWNER_MARKER)
    return owner if owner else source_path


@dataclass(frozen=True)
class StubPlan:
    target_source_path: str
    target_note: str
    doc_kind: str
    repo_owner: str
    stub_content: str


@dataclass
class GenerateResult:
    planned: list[StubPlan]
    written: list[StubPlan]
    skipped: list[tuple[str, str]]
    errors: list[tuple[str, str]]


def generate_stubs(
    tsv_path: Path,
    repo_root: Path,
    *,
    dry_run: bool = True,
) -> GenerateResult:
    """Read TSV and generate (or plan) stub files under repo_root.

    Args:
        tsv_path: Path to the Link Stub Blockers TSV.
        repo_root: Root directory of the repository.
        dry_run: If True, plan but do not write any files.

    Returns:
        GenerateResult with planned, written, skipped, and error lists.
    """
    rows = parse_blocker_tsv(tsv_path)
    result = GenerateResult(planned=[], written=[], skipped=[], errors=[])

    for row in rows:
        if row.suggested_resolution != "keep_target_or_leave_stub_first":
            result.skipped.append(
                (row.target_source_path, f"resolution={row.suggested_resolution}")
            )
            continue

        target_file = repo_root / row.target_source_path
        if not target_file.exists():
            result.errors.append(
                (row.target_source_path, "target file does not exist")
            )
            continue

        existing_text = target_file.read_text(encoding="utf-8")

        if marker_value(existing_text, "Doc placement:") == "repo_stub_plus_obsidian":
            result.skipped.append(
                (row.target_source_path, "already a stub")
            )
            continue

        doc_kind = extract_doc_kind(existing_text)
        repo_owner = infer_repo_owner(existing_text, row.target_source_path)
        stub_content = generate_stub_content(
            target_source_path=row.target_source_path,
            target_note=row.target_note,
            doc_kind=doc_kind,
            repo_owner=repo_owner,
        )

        plan = StubPlan(
            target_source_path=row.target_source_path,
            target_note=row.target_note,
            doc_kind=doc_kind,
            repo_owner=repo_owner,
            stub_content=stub_content,
        )
        result.planned.append(plan)

        if not dry_run:
            target_file.write_text(stub_content, encoding="utf-8")
            result.written.append(plan)

    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for generate_stubs."""
    parser = argparse.ArgumentParser(
        description="Generate repo stubs from link stub blockers TSV",
    )
    parser.add_argument("tsv_path", type=Path, help="path to blockers TSV")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="repo root directory (default: cwd)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually write stubs (default: dry-run only)",
    )
    args = parser.parse_args(argv)
    result = generate_stubs(args.tsv_path, args.repo_root, dry_run=not args.execute)

    for plan in result.planned:
        action = "WROTE" if plan in result.written else "PLAN"
        print(f"  {action}: {plan.target_source_path} → stub for [[{plan.target_note}]]")

    for path, reason in result.skipped:
        print(f"  SKIP: {path} ({reason})")

    for path, reason in result.errors:
        print(f"  ERROR: {path} ({reason})")

    total = len(result.planned) + len(result.skipped) + len(result.errors)
    print(
        f"\nSummary: {len(result.written)} written,"
        f" {len(result.planned) - len(result.written)} planned,"
        f" {len(result.skipped)} skipped,"
        f" {len(result.errors)} errors"
        f" (of {total} rows)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
