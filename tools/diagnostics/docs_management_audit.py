"""Audit repo/Obsidian documentation management health.

This checker is read-only. It catches workflow drift that the staged
docs-placement guard intentionally does not cover, such as whole
docs/superpowers routing inventory and candidates with key-concept, repo-owner,
and Obsidian-lane hints, stale branch handoffs after a commit, vault manifest
stats that no longer match the vault, pending raw/staged wiki files, missing
wiki lifecycle metadata, and local-path exposure that needs a focused
retention/privacy review.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from tools.diagnostics import docs_scan as _docs_scan  # noqa: E402
from tools.diagnostics.docs_policy import (  # noqa: E402
    DOC_CANONICAL_OWNER_FILES,
    classify_doc,
    is_markdown_path,
)
from tools.diagnostics.docs_routing_review import (  # noqa: E402
    ROUTING_MANIFEST_FIELDS,
    TOPIC_CLUSTER_MANIFEST_FIELDS,
    docs_routing_review,
)
from tools.diagnostics.docs_topic_indexes import (  # noqa: E402
    write_topic_index_readmes as _write_topic_index_readmes,
)
from tools.diagnostics.handoff_retention_audit import (  # noqa: E402
    run_handoff_retention_audit,
)

_fallback_local_path_scan_paths = _docs_scan.fallback_local_path_scan_paths
_git_visible_paths = _docs_scan.git_visible_paths
_is_local_path_scan_target = _docs_scan.is_local_path_scan_target
_read_text = _docs_scan.read_text
_repo_rel = _docs_scan.repo_rel

DEFAULT_CONFIG = Path.home() / ".obsidian-wiki" / "config"
LOCAL_ENV_FILES = (".env.xic-local", ".env")
CANONICAL_METADATA_REVIEW_EXCLUDE_PREFIXES = (
    "docs/superpowers/",
)

STALE_HANDOFF_PATTERNS = (
    "no commit has been made",
    "the branch is not committed",
    "staged deletions",
    "staged for removal",
    "review staged diff",
    "before commit review",
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"C:\\Users\\user\\", re.IGNORECASE),
    re.compile(r"C:/Users/user/", re.IGNORECASE),
    re.compile(r"C:\\Vaults(?:\\|$)", re.IGNORECASE),
    re.compile(r"C:\\Xcalibur(?:\\|$)", re.IGNORECASE),
    re.compile(r"C:\\Python\d+(?:\\|$)", re.IGNORECASE),
    re.compile(r"Research Vault", re.IGNORECASE),
)
VALID_LIFECYCLES = {"draft", "reviewed", "verified", "disputed", "archived"}
VALID_TIERS = {"core", "supporting", "peripheral"}


@dataclass(frozen=True)
class AuditMessage:
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class AuditResult:
    messages: tuple[AuditMessage, ...]
    summary: dict[str, object]

    @property
    def blockers(self) -> tuple[AuditMessage, ...]:
        return tuple(msg for msg in self.messages if msg.severity == "blocker")




def parse_yaml_frontmatter(text: str) -> dict[str, str]:
    """Parse YAML frontmatter between ``---`` delimiters.

    Public so other diagnostics modules can reuse the same parser.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    values: dict[str, str] = {}
    current_key: str | None = None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith((" ", "\t")) or stripped.startswith("- "):
            if current_key and stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                values[current_key] = " ".join(
                    part for part in (values.get(current_key, ""), item) if part
                )
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip().strip('"').strip("'")
    return values




def _config_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_vault(root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    env_value = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_value:
        return Path(env_value)

    current = root.resolve()
    home = Path.home().resolve()
    for candidate_dir in (current, *current.parents):
        for filename in LOCAL_ENV_FILES:
            candidate = candidate_dir / filename
            if candidate.exists():
                values = _config_values(candidate)
                vault = values.get("OBSIDIAN_VAULT_PATH")
                if vault:
                    return Path(vault)
        if candidate_dir == home:
            break

    values = _config_values(DEFAULT_CONFIG)
    vault = values.get("OBSIDIAN_VAULT_PATH")
    return Path(vault) if vault else None


def audit_repo(
    root: Path,
    *,
    allow_filesystem_handoff_fallback: bool = False,
) -> tuple[list[AuditMessage], dict[str, object]]:
    messages: list[AuditMessage] = []
    docs = sorted((root / "docs").rglob("*.md"))
    docs_by_top = Counter(
        path.relative_to(root / "docs").parts[0]
        if path.relative_to(root / "docs").parts
        else "."
        for path in docs
    )

    stale_targets = [
        root
        / (
            "docs/superpowers/handoffs/current/"
            "codex-docs-cleanup-official-docs-and-handoff.md"
        ),
        root
        / (
            "docs/superpowers/closeouts/"
            "2026-06-26_codex-docs-cleanup_branch-closeout-summary.md"
        ),
    ]
    for path in stale_targets:
        if not path.exists():
            continue
        text = _read_text(path).lower()
        for pattern in STALE_HANDOFF_PATTERNS:
            if pattern in text:
                messages.append(
                    AuditMessage(
                        "blocker",
                        _repo_rel(path, root),
                        f"stale branch-state phrase after commit: {pattern!r}",
                    )
                )

    local_path_counts: Counter[str] = Counter()
    scan_paths = _git_visible_paths(root) or _fallback_local_path_scan_paths(root)
    for rel_path in scan_paths:
        path = root / rel_path
        if not _is_local_path_scan_target(path, rel_path):
            continue
        text = _read_text(path)
        count = sum(len(pattern.findall(text)) for pattern in LOCAL_PATH_PATTERNS)
        if count:
            local_path_counts[rel_path] = count

    top_local_path_files = [
        {"path": path, "count": count}
        for path, count in local_path_counts.most_common(20)
    ]
    if local_path_counts:
        messages.append(
            AuditMessage(
                "warning",
                "repo",
                (
                    "local/private path exposure remains in tracked text; "
                    f"{len(local_path_counts)} files, "
                    f"{sum(local_path_counts.values())} hits"
                ),
            )
        )

    routing_review = docs_routing_review(root, scan_paths)
    canonical_metadata_review = canonical_metadata_review_for_repo(root)
    routing_candidates = int(routing_review["candidate_files"])
    metadata_review_files = int(routing_review["metadata_review_files"])
    canonical_missing_metadata = int(
        canonical_metadata_review["missing_metadata_files"]
    )
    if routing_candidates:
        invalid_count = int(
            routing_review["disposition_counts"].get("invalid_repo_placement", 0)
        )
        if invalid_count:
            messages.append(
                AuditMessage(
                    "blocker",
                    "docs",
                    (
                        "tracked repo docs declare non-repo placement; "
                        f"{invalid_count} file(s) need routing repair"
                    ),
                )
            )
        messages.append(
            AuditMessage(
                "warning",
                "docs",
                (
                    "repo docs routing review has candidate files; inspect "
                    "summary.repo.docs_routing_review.top_candidates before "
                    f"writing another cleanup plan ({routing_candidates} file(s))"
                ),
            )
        )

    if metadata_review_files:
        messages.append(
            AuditMessage(
                "warning",
                "docs",
                (
                    "repo docs metadata review has retained files missing "
                    "metadata; inspect "
                    "summary.repo.docs_routing_review.top_metadata_reviews "
                    f"({metadata_review_files} file(s))"
                ),
            )
        )

    if canonical_missing_metadata:
        messages.append(
            AuditMessage(
                "warning",
                "docs",
                (
                    "canonical docs metadata review found missing metadata; "
                    "inspect summary.repo.canonical_metadata_review."
                    f"top_missing_metadata ({canonical_missing_metadata} file(s))"
                ),
            )
        )

    duplicate_topic_owner_groups = int(
        routing_review["topic_cluster_group_counts"].get(
            "potential_duplicate_owner", 0
        )
    )
    if duplicate_topic_owner_groups:
        messages.append(
            AuditMessage(
                "warning",
                "docs",
                (
                    "repo docs topic review found possible duplicate topic "
                    "owners; inspect "
                    "summary.repo.docs_routing_review.top_topic_clusters "
                    f"({duplicate_topic_owner_groups} group(s))"
                ),
            )
        )

    handoff_result = run_handoff_retention_audit(
        root,
        allow_filesystem_fallback=allow_filesystem_handoff_fallback,
    )
    messages.extend(
        AuditMessage(
            msg.severity,
            msg.path,
            f"handoff retention: {msg.message}",
        )
        for msg in handoff_result.messages
    )

    summary: dict[str, object] = {
        "repo_markdown_files": len(docs),
        "docs_by_top_level": dict(sorted(docs_by_top.items())),
        "local_path_files": len(local_path_counts),
        "local_path_hits": sum(local_path_counts.values()),
        "top_local_path_files": top_local_path_files,
        "docs_routing_review": routing_review,
        "canonical_metadata_review": canonical_metadata_review,
        "handoff_retention": handoff_result.summary,
    }
    return messages, summary


def canonical_metadata_review_for_repo(root: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for rel_path in sorted(DOC_CANONICAL_OWNER_FILES):
        if not is_markdown_path(rel_path):
            continue
        if rel_path.startswith(CANONICAL_METADATA_REVIEW_EXCLUDE_PREFIXES):
            continue
        path = root / rel_path
        if not path.exists() or not path.is_file():
            continue
        text = _read_text(path)
        classification = classify_doc(rel_path, text)
        if classification.metadata_status == "declared":
            continue
        rows.append(
            {
                "path": rel_path,
                "metadata_status": classification.metadata_status,
                "metadata_missing_fields": (
                    "; ".join(classification.metadata_missing_fields) or "none"
                ),
                "doc_kind": classification.doc_kind,
                "doc_kind_source": classification.doc_kind_source,
                "doc_lifecycle": classification.doc_lifecycle,
                "repo_owner": classification.repo_owner or "missing",
            }
        )
    return {
        "reviewed_files": len(rows),
        "missing_metadata_files": len(rows),
        "missing_metadata": rows,
        "top_missing_metadata": rows[:25],
    }


def _manifest_stats(manifest: Path) -> tuple[dict[str, object], list[str]]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    sources = data.get("sources", {})
    problems: list[str] = []
    source_values = sources.values() if isinstance(sources, dict) else []
    for source, metadata in sources.items() if isinstance(sources, dict) else []:
        if not Path(str(source)).exists():
            problems.append(f"manifest source missing on disk: {source}")
        if isinstance(metadata, dict):
            for key in ("pages_created", "pages_updated"):
                value = metadata.get(key)
                if value is not None and not isinstance(value, list):
                    problems.append(f"{source}: manifest {key} must be a list or null")
    stats = data.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}
    return {
        "source_count": len(sources) if isinstance(sources, dict) else 0,
        "stats_total_sources_ingested": stats.get("total_sources_ingested"),
        "stats_total_pages": stats.get("total_pages"),
        "stats_total_projects": stats.get("total_projects"),
        "source_type_counts": dict(
            Counter(
                str(metadata.get("source_type", "(missing)"))
                for metadata in source_values
                if isinstance(metadata, dict)
            )
        ),
    }, problems


def _vault_link_health(md_files: Sequence[Path], vault: Path) -> dict[str, object]:
    page_keys: dict[str, str] = {}
    base_keys: dict[str, list[str]] = {}
    for path in md_files:
        rel = path.relative_to(vault).as_posix()
        no_ext = rel[:-3]
        page_keys[rel.lower()] = rel
        page_keys[no_ext.lower()] = rel
        base_keys.setdefault(path.stem.lower(), []).append(rel)

    incoming: Counter[str] = Counter()
    broken: list[dict[str, str]] = []
    for path in md_files:
        rel = path.relative_to(vault).as_posix()
        text = _link_health_text(_read_text(path))
        for raw_target in re.findall(r"\[\[([^\]\n]+)\]\]", text):
            target = raw_target.split("|", 1)[0].strip().replace("\\", "/")
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http:", "https:")):
                continue
            no_ext = target[:-3] if target.endswith(".md") else target
            candidates: list[str] = []
            if target.lower() in page_keys:
                candidates = [page_keys[target.lower()]]
            elif no_ext.lower() in page_keys:
                candidates = [page_keys[no_ext.lower()]]
            else:
                candidates = base_keys.get(Path(no_ext).name.lower(), [])
            if candidates:
                incoming[candidates[0]] += 1
            else:
                broken.append({"source": rel, "target": target})

    all_pages = {path.relative_to(vault).as_posix() for path in md_files}
    orphans = sorted(page for page in all_pages if incoming[page] == 0)
    return {
        "broken_wikilinks": len(broken),
        "broken_wikilink_sample": broken[:20],
        "orphan_pages": len(orphans),
        "orphan_page_sample": orphans[:20],
    }


def _link_health_text(text: str) -> str:
    """Exclude preserved source bodies from live vault link-health checks."""
    if (
        "disposition: private_history_source_copy" in text
        and "\n## Original Content\n" in text
    ):
        return text.split("\n## Original Content\n", 1)[0]
    return text


def audit_vault(vault: Path | None) -> tuple[list[AuditMessage], dict[str, object]]:
    messages: list[AuditMessage] = []
    if vault is None:
        return [
            AuditMessage(
                "warning",
                "vault",
                "Obsidian vault path is not configured; vault audit skipped",
            )
        ], {"vault_configured": False}
    if not vault.exists():
        return [
            AuditMessage(
                "blocker",
                str(vault),
                "configured Obsidian vault path does not exist",
            )
        ], {"vault_configured": True, "vault_exists": False}

    md_files = sorted(vault.rglob("*.md"))
    top_level = Counter(path.relative_to(vault).parts[0] for path in md_files)
    staging_md = (
        list((vault / "_staging").rglob("*.md"))
        if (vault / "_staging").exists()
        else []
    )
    raw_files = [
        path
        for path in (vault / "_raw").glob("*")
        if path.name != ".gitkeep"
    ] if (vault / "_raw").exists() else []

    if staging_md:
        messages.append(
            AuditMessage(
                "blocker",
                "_staging",
                f"{len(staging_md)} staged wiki markdown files are pending review",
            )
        )
    if raw_files:
        messages.append(
            AuditMessage(
                "blocker",
                "_raw",
                f"{len(raw_files)} raw wiki files are pending ingest/classification",
            )
        )

    missing_visibility = 0
    missing_lifecycle = 0
    invalid_lifecycle = 0
    missing_tier = 0
    invalid_tier = 0
    for path in md_files:
        fm = parse_yaml_frontmatter(_read_text(path))
        tags = fm.get("tags", "")
        if "visibility/" not in tags:
            missing_visibility += 1
        lifecycle = fm.get("lifecycle")
        if not lifecycle:
            missing_lifecycle += 1
        elif lifecycle not in VALID_LIFECYCLES:
            invalid_lifecycle += 1
        tier = fm.get("tier")
        if not tier:
            missing_tier += 1
        elif tier not in VALID_TIERS:
            invalid_tier += 1

    for label, count in (
        ("missing visibility tag", missing_visibility),
        ("missing lifecycle", missing_lifecycle),
        ("invalid lifecycle", invalid_lifecycle),
        ("missing tier", missing_tier),
        ("invalid tier", invalid_tier),
    ):
        if count:
            messages.append(
                AuditMessage("warning", "vault", f"{count} pages have {label}")
            )

    manifest_summary: dict[str, object] = {"manifest_exists": False}
    manifest = vault / ".manifest.json"
    if manifest.exists():
        manifest_summary, manifest_problems = _manifest_stats(manifest)
        manifest_summary["manifest_exists"] = True
        expected_sources = manifest_summary.get("source_count")
        expected_pages = len(md_files)
        if manifest_summary.get("stats_total_sources_ingested") != expected_sources:
            messages.append(
                AuditMessage(
                    "blocker",
                    ".manifest.json",
                    "manifest stats.total_sources_ingested does not match source count",
                )
            )
        if manifest_summary.get("stats_total_pages") != expected_pages:
            messages.append(
                AuditMessage(
                    "blocker",
                    ".manifest.json",
                    "manifest stats.total_pages does not match vault markdown count",
                )
            )
        for problem in manifest_problems[:20]:
            messages.append(AuditMessage("blocker", ".manifest.json", problem))
    else:
        messages.append(
            AuditMessage("blocker", ".manifest.json", "manifest is missing")
        )

    link_health = _vault_link_health(md_files, vault)
    if link_health["broken_wikilinks"]:
        messages.append(
            AuditMessage(
                "warning",
                "vault",
                (
                    f"{link_health['broken_wikilinks']} approximate broken "
                    "wikilinks remain"
                ),
            )
        )

    summary: dict[str, object] = {
        "vault_configured": True,
        "vault_exists": True,
        "vault_path": str(vault),
        "vault_markdown_files": len(md_files),
        "vault_by_top_level": dict(sorted(top_level.items())),
        "staging_markdown_files": len(staging_md),
        "raw_top_level_files": len(raw_files),
        "frontmatter": {
            "missing_visibility": missing_visibility,
            "missing_lifecycle": missing_lifecycle,
            "invalid_lifecycle": invalid_lifecycle,
            "missing_tier": missing_tier,
            "invalid_tier": invalid_tier,
        },
        "manifest": manifest_summary,
        "link_health": link_health,
    }
    return messages, summary


def run_audit(
    root: Path = ROOT,
    vault: Path | None = None,
    *,
    allow_filesystem_handoff_fallback: bool = False,
) -> AuditResult:
    repo_messages, repo_summary = audit_repo(
        root,
        allow_filesystem_handoff_fallback=allow_filesystem_handoff_fallback,
    )
    resolved_vault = resolve_vault(root, vault)
    vault_messages, vault_summary = audit_vault(resolved_vault)
    messages = [*repo_messages, *vault_messages]
    summary = {"repo": repo_summary, "vault": vault_summary}
    return AuditResult(tuple(messages), summary)


def write_routing_manifest_tsv(result: AuditResult, path: Path) -> None:
    review = result.summary["repo"]["docs_routing_review"]
    rows = [
        *review["candidates"],
        *review.get("route_retained_reviews", ()),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ROUTING_MANIFEST_FIELDS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_topic_clusters_tsv(result: AuditResult, path: Path) -> None:
    clusters = result.summary["repo"]["docs_routing_review"]["topic_clusters"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TOPIC_CLUSTER_MANIFEST_FIELDS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(clusters)


def write_topic_index_readmes(result: AuditResult, directory: Path) -> None:
    clusters_obj = result.summary["repo"]["docs_routing_review"]["topic_clusters"]
    clusters: list[dict[str, object]] = []
    if isinstance(clusters_obj, list):
        clusters = [cluster for cluster in clusters_obj if isinstance(cluster, dict)]
    _write_topic_index_readmes(clusters, directory)




def format_text(result: AuditResult) -> str:
    lines = ["docs management audit"]
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
    parser.add_argument("--vault", type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text.",
    )
    parser.add_argument(
        "--routing-manifest-tsv",
        type=Path,
        help="Write actionable docs/superpowers routing candidates as TSV.",
    )
    parser.add_argument(
        "--topic-clusters-tsv",
        type=Path,
        help="Write docs/superpowers topic-owner clusters as TSV.",
    )
    parser.add_argument(
        "--topic-index-dir",
        type=Path,
        help="Write index-only topic README files under this directory.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_audit(args.root.resolve(), args.vault)
    if args.routing_manifest_tsv is not None:
        write_routing_manifest_tsv(result, args.routing_manifest_tsv)
    if args.topic_clusters_tsv is not None:
        write_topic_clusters_tsv(result, args.topic_clusters_tsv)
    if args.topic_index_dir is not None:
        write_topic_index_readmes(result, args.topic_index_dir)
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
